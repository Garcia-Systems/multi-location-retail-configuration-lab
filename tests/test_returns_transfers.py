import json
import subprocess
import sys

import pytest

from retail_configuration_lab.returns_transfers import (
    DATA, ReturnResult, ReturnsTransfersValidationError, TransferResult,
    load_returns_transfers_configuration, load_returns_transfers_records,
    run_returns_transfers_experiment,
)


def test_configurations_load_with_explicit_semantics():
    config = load_returns_transfers_configuration()
    assert config.return_rules["cross_store_returns_supported"] is True
    assert "COMPLETED" in config.return_rules["reason_required_for_statuses"]
    assert config.transfer_rules["closure_status"] == "RECEIVED"
    assert "does not imply" in config.transfer_rules["sent_semantics"]


def test_return_scenarios_and_location_identity_are_preserved():
    result = run_returns_transfers_experiment()
    values = {x.result for x in result.return_outcomes}
    assert set(ReturnResult) - {ReturnResult.UNKNOWN} <= values
    cross = next(x for x in result.return_outcomes if x.record.return_id == "JRO-RET-1002")
    assert cross.result is ReturnResult.CROSS_STORE_RECONCILED
    assert cross.record.original_sale_store == "JRO-STORE-002"
    assert cross.record.return_store == "JRO-STORE-005"
    assert cross.record.inventory_effect == 1
    assert any(x.result is ReturnResult.RECONCILED for x in result.return_outcomes)
    assert any(x.result is ReturnResult.MISSING_REASON for x in result.return_outcomes)
    assert any(x.result is ReturnResult.MISSING_ORIGINAL_REFERENCE for x in result.return_outcomes)
    assert any(x.result is ReturnResult.UNRESOLVED_IDENTITY for x in result.return_outcomes)
    assert any(x.result is ReturnResult.INVENTORY_EFFECT_EXCEPTION for x in result.return_outcomes)
    assert not any(x.accounting_evidence for x in result.return_outcomes)


def test_transfer_scenarios_keep_sender_receiver_and_quantity_evidence_distinct():
    result = run_returns_transfers_experiment()
    values = {x.result for x in result.transfer_outcomes}
    required = {TransferResult.RECONCILED, TransferResult.MISSING_RECEIPT,
        TransferResult.PARTIAL_RECEIPT, TransferResult.OVER_RECEIPT,
        TransferResult.LOCATION_EXCEPTION, TransferResult.CANCELLED_TRANSFER_MOVEMENT,
        TransferResult.UNRESOLVED_IDENTITY, TransferResult.INVENTORY_EFFECT_EXCEPTION}
    assert required <= values
    clean = next(x for x in result.transfer_outcomes if x.record.transfer_id == "JRO-TR-1001")
    assert clean.record.sending_store != clean.record.receiving_store
    assert clean.result is TransferResult.RECONCILED
    missing = next(x for x in result.transfer_outcomes if x.record.transfer_id == "JRO-TR-1007")
    assert missing.record.status.value == "SENT" and missing.result is TransferResult.MISSING_RECEIPT
    inventory = next(x for x in result.transfer_outcomes if x.record.transfer_id == "JRO-TR-1011")
    assert inventory.record.status.value == "RECEIVED"
    assert inventory.record.quantity_sent == inventory.record.quantity_received
    assert inventory.result is TransferResult.INVENTORY_EFFECT_EXCEPTION


def test_metrics_process_gap_and_question_impacts():
    result = run_returns_transfers_experiment()
    assert result.before["manual_return_transfer_reviews"] == 20
    assert result.manual_reviews_after == 13
    assert result.return_reconciliation_rate == pytest.approx(.5)
    assert result.transfer_reconciliation_rate == pytest.approx(.2)
    assert result.manual_return_transfer_review_reduction_ratio == pytest.approx(.35)
    impacts = {x.question_id: x.status.value for x in result.question_impacts}
    assert impacts == {"TRN-01":"ANSWERED", "TRN-02":"ANSWERED",
        "RET-01":"PARTIALLY_ANSWERED", "RET-02":"ANSWERED",
        "INV-02":"PARTIALLY_ANSWERED", "FIN-01":"NOT_ANSWERED"}
    assert result.return_counts[ReturnResult.MISSING_REASON] == 1


def _alter(tmp_path, mutate):
    raw = json.loads(DATA.read_text())
    mutate(raw)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(raw))
    return path


@pytest.mark.parametrize("mutate", [
    lambda r: r["returns"].append(r["returns"][0]),
    lambda r: r["returns"][0].update(status="DONE"),
    lambda r: r["returns"][0].update(reason="BORED"),
    lambda r: r["returns"][0].update(quantity=-1),
    lambda r: r["returns"][0].update(return_store="NOPE"),
    lambda r: r["returns"][0].update(canonical_sku="NOPE"),
    lambda r: r["returns"][0].update(original_reference="broken"),
    lambda r: r["returns"][0].update(provenance=""),
    lambda r: r["transfers"].append(r["transfers"][0]),
    lambda r: r["transfers"][0].update(receiving_store="JRO-STORE-001"),
    lambda r: r["transfers"][0].update(sending_store="NOPE"),
    lambda r: r["transfers"][0].update(status="CLOSED"),
    lambda r: r["transfers"][0].update(quantity_received=-1),
    lambda r: r["transfers"][0].update(canonical_sku="NOPE"),
    lambda r: r["transfers"][0].update(provenance=""),
    lambda r: r["transfers"][0].update(sender_inventory_effect=5),
])
def test_malformed_records_are_rejected_but_incomplete_evidence_is_not(tmp_path, mutate):
    with pytest.raises(ReturnsTransfersValidationError):
        load_returns_transfers_records(_alter(tmp_path, mutate))


def test_cli_returns_transfers():
    run = subprocess.run([sys.executable, "-m", "retail_configuration_lab", "returns-transfers"], capture_output=True, text=True)
    assert run.returncode == 0
    assert "Returns after configuration" in run.stdout
    assert "Transfers after configuration" in run.stdout
    assert "MISSING REASON: 1" in run.stdout
    assert "TRUE INVENTORY-EFFECT EXCEPTION" in run.stdout
    assert "Current lab verdict: UNTESTED" in run.stdout
