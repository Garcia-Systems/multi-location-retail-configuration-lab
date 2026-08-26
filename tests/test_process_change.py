import json
from pathlib import Path

import pytest

from retail_configuration_lab.cli import main, process_change_report
from retail_configuration_lab.process_change import (
    ComplianceStatus, ProcessValidationError, ResidualCause,
    load_process_configuration, run_process_change_experiment,
)


def test_process_rules_load_are_unique_and_owned():
    rules, scenarios = load_process_configuration()
    assert len(rules) == 5
    assert len({x.rule_id for x in rules}) == len(rules)
    assert all(x.owner and x.required_behavior and x.completion_condition for x in rules)
    assert len(scenarios) == 6


def test_existing_reconciliation_engines_eliminate_process_exceptions():
    result = run_process_change_experiment()
    outcomes = {x.scenario.scenario_id: x for x in result.outcomes}
    assert outcomes["inconsistent-receiving"].before_result == "MISSING_RECEIPT"
    assert outcomes["inconsistent-receiving"].after_result == "RECONCILED"
    assert outcomes["return-reason"].before_result == "MISSING_REASON"
    assert outcomes["return-reason"].after_result == "RECONCILED"
    assert outcomes["transfer-closure"].before_result == "MISSING_RECEIPT"
    assert outcomes["transfer-closure"].after_result == "RECONCILED"
    assert all(outcomes[x].scenario.after.compliance is ComplianceStatus.COMPLIANT
               for x in ("inconsistent-receiving", "return-reason", "transfer-closure"))


def test_governance_reporting_and_technical_residual():
    result = run_process_change_experiment()
    outcomes = {x.scenario.scenario_id: x for x in result.outcomes}
    mapping = outcomes["mapping-governance"]
    assert mapping.before_result == "UNRESOLVED_IDENTITY" and mapping.after_result == "RECONCILED"
    assert mapping.scenario.primary_residual_cause is ResidualCause.DATA_GOVERNANCE
    assert outcomes["spreadsheet-duplication"].scenario.before.manual_steps == 4
    assert outcomes["spreadsheet-duplication"].scenario.after.manual_steps == 1
    assert result.chapter9_report_evidence_unchanged
    accounting = outcomes["accounting-reconciliation"]
    assert accounting.exception_before and accounting.exception_after
    assert accounting.scenario.primary_residual_cause is ResidualCause.TECHNICAL_GAP


def test_metrics_and_conservative_question_impacts():
    result = run_process_change_experiment()
    assert (result.noncompliant_before, result.noncompliant_after) == (5, 0)
    assert (result.operational_exceptions_before, result.operational_exceptions_after) == (6, 1)
    assert result.process_caused_exceptions_eliminated == 4
    assert result.data_governance_exceptions_eliminated == 1
    assert result.technical_exceptions_unchanged == 1
    assert result.process_exception_reduction_ratio == 1
    assert result.manual_process_step_reduction_ratio == pytest.approx(10 / 12)
    impacts = {x.question_id: x.status.value for x in result.question_impacts}
    assert impacts["INV-03"] == "UNKNOWN" and impacts["FIN-01"] == "PARTIALLY_ANSWERED"


def test_invalid_configuration_is_distinct_from_valid_noncompliance(tmp_path: Path):
    source = json.loads(Path("config/process/process_rules.json").read_text())
    source["rules"][1]["id"] = source["rules"][0]["id"]
    invalid = tmp_path / "rules.json"; invalid.write_text(json.dumps(source))
    with pytest.raises(ProcessValidationError, match="duplicate"):
        load_process_configuration(invalid)
    # The shipped NONCOMPLIANT states are valid subjects, not invalid configuration.
    _, scenarios = load_process_configuration()
    assert any(x.before.compliance is ComplianceStatus.NONCOMPLIANT for x in scenarios)


def test_process_change_cli(capsys):
    assert main(["process-change"]) == 0
    output = capsys.readouterr().out
    assert "Before process change" in output and "After process change" in output
    assert "process-caused exception eliminated" in output
    assert "ROOT CAUSE\nTECHNICAL GAP" in output and "RESULT\nUNCHANGED" in output
    assert "Current lab verdict: UNTESTED" in output
    assert process_change_report().startswith("James River Outfitters")
