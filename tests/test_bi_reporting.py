import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from retail_configuration_lab.bi_reporting import (BIQuestionStatus, BIValidationError,
    load_bi_configuration, run_bi_reporting)
from retail_configuration_lab.native_reporting import run_native_reporting
from retail_configuration_lab.purchasing import run_purchasing_experiment
from retail_configuration_lab.returns_transfers import run_returns_transfers_experiment
from retail_configuration_lab.ecommerce_reconciliation import run_ecommerce_reconciliation


def test_configuration_and_references_load():
    c = load_bi_configuration()
    assert c.platform == "RiverBI" and len(c.datasets) == 6 and len(c.reports) == 7
    assert len({x.dataset_id for x in c.datasets}) == len(c.datasets)
    assert len({x.report_id for x in c.reports}) == len(c.reports)
    assert {r.dataset_id for r in c.reports} <= {d.dataset_id for d in c.datasets}


def test_reports_reuse_upstream_outcomes_and_identity():
    result = run_bi_reporting()
    native = run_native_reporting().reports["store-sales"]
    assert [x["net_sales"] for x in result.reports["cross-store-sales-summary"]] == [x["net_sales"] for x in native]
    assert [x["reconciliation_result"] for x in result.reports["purchasing-exception-report"]] == [x.result.value for x in run_purchasing_experiment().outcomes]
    rt = run_returns_transfers_experiment()
    assert [x["reconciliation_result"] for x in result.reports["return-discrepancy-report"]] == [x.result.value for x in rt.return_outcomes]
    assert [x["transfer_result"] for x in result.reports["transfer-status-report"]] == [x.result.value for x in rt.transfer_outcomes]
    assert [x["reconciliation_result"] for x in result.reports["channel-reconciliation-report"]] == [x.result.value for x in run_ecommerce_reconciliation().outcomes]
    assert any(x["canonical_sku"] == "UNRESOLVED" for x in result.reports["return-discrepancy-report"])


def test_briefing_and_metrics():
    r = run_bi_reporting()
    assert r.count_before == {BIQuestionStatus.ANSWERED:4, BIQuestionStatus.PARTIALLY_ANSWERED:5, BIQuestionStatus.NOT_ANSWERED:3, BIQuestionStatus.UNKNOWN:1}
    assert r.count_after == {BIQuestionStatus.ANSWERED:8, BIQuestionStatus.PARTIALLY_ANSWERED:3, BIQuestionStatus.NOT_ANSWERED:1, BIQuestionStatus.UNKNOWN:1}
    assert r.bi_question_answer_rate == 8/13 and r.bi_incremental_question_gain == 4
    assert r.manual_reporting_steps_before == 7 and r.manual_reporting_steps_after == 3
    assert r.manual_reporting_step_reduction_ratio == 4/7
    assert "PUR-01" in r.questions_improved_by_bi
    assert next(x for x in r.question_transitions if x.question_id == "FIN-01").after is BIQuestionStatus.PARTIALLY_ANSWERED
    assert any(x.get("transfer_id") == "JRO-TR-1007" for x in r.management_briefing)
    assert not any(x.get("transfer_result") == "RECONCILED" for x in r.management_briefing)


def _invalid_copy(tmp_path, mutate):
    target = tmp_path / "bi"; shutil.copytree(Path("config/bi"), target); mutate(target); return target


def test_invalid_report_field_and_question_fail(tmp_path):
    def bad_field(p):
        f=p/"reports.json"; d=json.loads(f.read_text()); d["reports"][0]["columns"].append("invented"); f.write_text(json.dumps(d))
    with pytest.raises(BIValidationError, match="unavailable field"): load_bi_configuration(_invalid_copy(tmp_path/"a", bad_field))
    def bad_q(p):
        f=p/"reports.json"; d=json.loads(f.read_text()); d["reports"][0]["question_ids"]=["NOPE"]; f.write_text(json.dumps(d))
    with pytest.raises(BIValidationError, match="question reference"): load_bi_configuration(_invalid_copy(tmp_path/"b", bad_q))


def test_cli():
    p=subprocess.run([sys.executable,"-m","retail_configuration_lab","bi-reporting"],text=True,capture_output=True)
    assert p.returncode == 0
    for text in ("Question coverage before BI","Question coverage after BI","Central Management Exception Briefing","JRO-TR-1007","Current lab verdict: UNTESTED"):
        assert text in p.stdout
