from dataclasses import replace
from decimal import Decimal
import subprocess
import sys

import pytest

from retail_configuration_lab.custom_edge import (
    DEFAULT_DEFINITION, CustomEdgeError, CustomResult, EdgeDecision,
    calculate_payback, fixture_inputs, reconcile, run_custom_edge, validate_definition,
)


def test_candidate_contract_is_chapter_16_bounded_gap():
    validate_definition()
    assert DEFAULT_DEFINITION.residual_gap_id == "cross-channel-exception-rule"
    assert DEFAULT_DEFINITION.scope.value == "BOUNDED"
    assert DEFAULT_DEFINITION.input_evidence and set(DEFAULT_DEFINITION.output_evidence) == {x.value for x in CustomResult}


def test_contract_guardrails():
    with pytest.raises(CustomEdgeError, match="nonexistent Chapter 16"):
        validate_definition(replace(DEFAULT_DEFINITION, residual_gap_id="missing"))
    with pytest.raises(CustomEdgeError, match="business-question"):
        validate_definition(replace(DEFAULT_DEFINITION, affected_question_ids=("NOPE",)))
    with pytest.raises(CustomEdgeError, match="input contract"):
        validate_definition(replace(DEFAULT_DEFINITION, input_evidence=()))
    with pytest.raises(CustomEdgeError, match="output contract"):
        validate_definition(replace(DEFAULT_DEFINITION, output_evidence=()))
    with pytest.raises(CustomEdgeError, match="ownership boundary"):
        validate_definition(replace(DEFAULT_DEFINITION, ownership_boundary=""))
    with pytest.raises(CustomEdgeError, match="excluded"):
        validate_definition(replace(DEFAULT_DEFINITION, excluded_responsibilities=()))
    with pytest.raises(CustomEdgeError, match="unknown custom result"):
        validate_definition(replace(DEFAULT_DEFINITION, output_evidence=("MAGIC",)))


def test_deterministic_results_preserve_provenance_identity_and_sources():
    records=fixture_inputs(); before=tuple(records[0].__dict__.items())
    first=reconcile(records[0]); second=reconcile(records[0])
    assert first == second and first.result is CustomResult.RECONCILED
    assert first.source_systems == records[0].source_systems
    assert first.source_record_ids == records[0].source_record_ids
    assert records[0].canonical_sku in first.canonical_ids
    assert first.rule_version and first.input_evidence_used and first.rationale
    assert tuple(records[0].__dict__.items()) == before


def test_exception_missing_identity_and_scope_are_not_absorbed():
    outcomes={x.record_id:reconcile(x) for x in fixture_inputs()}
    assert outcomes["TRUE-X"].result is CustomResult.EXCEPTION
    assert outcomes["MISSING"].result is CustomResult.INSUFFICIENT_EVIDENCE
    assert outcomes["AMBIG"].result is CustomResult.UNRESOLVED_IDENTITY
    assert outcomes["PURCHASE"].result is CustomResult.OUT_OF_SCOPE
    assert outcomes["ACCOUNT"].result is CustomResult.OUT_OF_SCOPE
    assert outcomes["ACQUIRED"].result is CustomResult.OUT_OF_SCOPE


def test_before_after_burden_effort_support_ownership_and_decision():
    a=run_custom_edge()
    assert (a.manual_review_before_custom,a.manual_review_after_custom)==(9,6)
    assert a.custom_edge_manual_review_reduction_ratio == Decimal(1)/Decimal(3)
    assert a.modeled_burden_before_custom == Decimal("14200")
    assert a.modeled_burden_after_custom == Decimal("14200")*Decimal(2)/Decimal(3)
    assert a.modeled_incremental_burden_reduction == Decimal("14200")/Decimal(3)
    assert sum(x.hours for x in a.effort) == 90 < 378
    assert a.modeled_custom_edge_setup_cost == Decimal("11250")
    assert a.annual_custom_edge_support_hours == 30
    assert a.annual_custom_edge_support_cost == 3000
    assert a.simple_custom_edge_payback_years == calculate_payback(Decimal(11250),Decimal(14200)/3,Decimal(3000))
    assert set(a.before_question_statuses)==set(a.after_question_statuses)=={"ECOM-01","ECOM-02"}
    assert "export" in a.custom_workaround_layers and "mapping" in a.custom_workaround_layers
    assert "manual review for residuals" in a.custom_workaround_layers
    assert a.custom_added_ownership == ("one custom rule/component","its tests","runtime/deployment assumption","its failure path")
    assert a.decision is EdgeDecision.EDGE_JUSTIFIED_FOR_FURTHER_ECONOMIC_TEST
    assert a.overall_lab_verdict == "UNTESTED"


def test_payback_and_cost_validation():
    assert calculate_payback(Decimal(10),Decimal(5),Decimal(5)) is None
    assert calculate_payback(Decimal(10),Decimal(4),Decimal(5)) is None
    with pytest.raises(CustomEdgeError, match="negative"):
        calculate_payback(Decimal(-1),Decimal(4),Decimal(2))
    with pytest.raises(CustomEdgeError, match="negative modeled cost"):
        run_custom_edge(hourly_rate=Decimal(-1))


def test_cli_compares_incremental_paths_and_keeps_verdict_untested():
    result=subprocess.run([sys.executable,"-m","retail_configuration_lab","custom-edge"],capture_output=True,text=True)
    assert result.returncode == 0
    assert "BEST CONFIGURED ALTERNATIVE + NARROW CUSTOM EDGE" in result.stdout
    assert "OUT OF SCOPE" in result.stdout and "Incremental economics preview" in result.stdout
    assert "Overall lab verdict: UNTESTED" in result.stdout
