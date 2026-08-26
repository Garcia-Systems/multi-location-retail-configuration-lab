import json
from pathlib import Path
import subprocess
import sys

import pytest

from retail_configuration_lab.purchasing import (CONFIG, DATA, PurchasingResult,
    PurchasingValidationError, load_purchasing_configuration, load_purchasing_records,
    run_purchasing_experiment)


def test_configuration_and_identity_distinctions():
    config=load_purchasing_configuration(); mapping=config.supplier_items[0]
    assert mapping.supplier_id != mapping.supplier_item_id != mapping.canonical_skus[0]
    assert config.resolve_item("BR-1042")==config.resolve_item("1042")=="JRO-1042-BLU-M"
    assert config.resolve_item("BR-UNKNOWN") is None
    assert config.resolve_item("BR-AMBIG") is None


def test_po_provenance_and_all_scenarios():
    result=run_purchasing_experiment(); values={x.result for x in result.outcomes}
    assert {PurchasingResult.RECONCILED,PurchasingResult.PARTIAL_RECEIPT,
        PurchasingResult.OVER_RECEIPT,PurchasingResult.MISSING_RECEIPT,
        PurchasingResult.LOCATION_EXCEPTION,PurchasingResult.CANCELLED_PO_RECEIPT,
        PurchasingResult.UNRESOLVED_IDENTITY,PurchasingResult.INVENTORY_EFFECT_EXCEPTION} <= values
    po=result.outcomes[0].po
    assert (po.canonical_po_id,po.source_po_id,po.provenance)==("JRO-PO-82451","PO-82451","fictional RiverBuy export")
    assert any(x.result is PurchasingResult.RECONCILED and x.receipt.inventory_effect==x.receipt.received_quantity for x in result.outcomes)
    assert any(x.result is PurchasingResult.INVENTORY_EFFECT_EXCEPTION for x in result.outcomes)
    assert sum(x.accounting_evidence_required for x in result.outcomes)==1


def test_metrics_and_question_impacts():
    result=run_purchasing_experiment()
    assert result.before["manual_po_receipt_links"]==10 and result.manual_links_after==3
    assert result.purchasing_manual_reconciliation_reduction_ratio==pytest.approx(.7)
    assert result.po_line_reconciliation_rate==pytest.approx(.25)
    impacts={x.question_id:x.status.value for x in result.question_impacts}
    assert impacts=={"PUR-01":"ANSWERED","PUR-02":"ANSWERED","INV-03":"PARTIALLY_ANSWERED","FIN-01":"PARTIALLY_ANSWERED"}


def _alter(tmp_path, mutate):
    raw=json.loads(DATA.read_text()); mutate(raw); path=tmp_path/"bad.json"; path.write_text(json.dumps(raw)); return path


def test_invalid_store_and_quantities_fail(tmp_path):
    config=load_purchasing_configuration()
    with pytest.raises(PurchasingValidationError): load_purchasing_records(_alter(tmp_path,lambda r:r["purchase_orders"][0].update(destination_store_id="NOPE")),config)
    with pytest.raises(PurchasingValidationError): load_purchasing_records(_alter(tmp_path,lambda r:r["purchase_orders"][0]["lines"][0].update(ordered_quantity=-1)),config)
    with pytest.raises(PurchasingValidationError): load_purchasing_records(_alter(tmp_path,lambda r:r["receipts"][0].update(received_quantity=-1)),config)


def test_cli_purchasing():
    run=subprocess.run([sys.executable,"-m","retail_configuration_lab","purchasing"],text=True,capture_output=True)
    assert run.returncode==0
    assert "Before configuration" in run.stdout and "After configuration" in run.stdout
    assert "PARTIAL RECEIPT: 1" in run.stdout and "LOCATION EXCEPTION" in run.stdout
    assert "Current lab verdict: UNTESTED" in run.stdout
