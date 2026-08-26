from dataclasses import replace
from decimal import Decimal
import subprocess
import sys

import pytest

from retail_configuration_lab.full_custom_counterfactual import (
    AUTHORITATIVE_SYSTEMS, CounterfactualValidationError, FullCustomResult,
    OwnershipClassification, ReliabilityRequirement, ReuseClassification,
    derive_result, load_full_custom_counterfactual, validate_counterfactual,
)
from retail_configuration_lab.weak_native_coverage import AnswerStatus


def test_inventory_authority_and_required_structure():
    s=load_full_custom_counterfactual()
    assert len({x.component_id for x in s.components}) == len(s.components)
    assert all(not x.authoritative for x in s.components)
    assert AUTHORITATIVE_SYSTEMS == {"sales":"pos","inventory":"inventory","purchase orders":"purchasing","online orders":"e-commerce","accounting":"accounting"}
    assert s.adapter_count == len(s.adapters_required) == 6
    assert {x.component_id for x in s.adapters_required} == {"adapter-pos","adapter-inventory","adapter-purchasing","adapter-e-commerce","adapter-accounting","adapter-scheduling/exports"}
    assert any(x.component_id == "canonical-identity" for x in s.components)
    assert len(s.reconciliation_domains) == 6
    assert {x.name for x in s.reliability} >= {"idempotency","retry","replay","acknowledgements","reconciliation","logging","alerting","monitoring"}
    assert all(x.requirement is ReliabilityRequirement.REQUIRED for x in s.reliability)
    assert all(isinstance(x.reuse, ReuseClassification) for x in s.components)


def test_original_economics_support_and_chapter17_baseline():
    s=load_full_custom_counterfactual()
    assert s.engineering_hours == 378
    assert s.direct_delivery_cost == Decimal("32440")
    assert s.implementation_price == Decimal("62000")
    assert s.annual_customer_fee == Decimal("15000")
    assert s.modeled_full_custom_support_hours == 144
    assert s.modeled_full_custom_support_cost == Decimal("14400")
    assert s.configuration_burden.residual_operational == Decimal("38200")-Decimal("14200")/3
    assert s.configuration_burden.administration == 22000
    assert s.configuration_burden.support == 3000
    assert s.configuration_burden.unknown == 6400


def test_coverage_incremental_value_and_ownership_are_transparent():
    s=load_full_custom_counterfactual()
    assert (s.configuration_answered_questions,s.full_custom_answered_questions,s.incremental_question_gain_full_custom)==(1,13,12)
    fin=next(x for x in s.question_coverage if x.question_id=="FIN-01")
    assert not fin.required_source_evidence_available and fin.full_custom_status is AnswerStatus.NOT_ANSWERED
    assert s.incremental_modeled_burden_reduction_full_custom == Decimal("38200")-Decimal("14200")/3-Decimal("18000")
    assert s.configuration_custom_ownership_count == 1
    assert s.full_custom_ownership_count == len(s.components) == 20
    assert s.incremental_custom_ownership_count == 19
    assert s.customer_specific_component_count > 1
    vendor=[x for x in s.configuration_responsibilities if x.ownership is OwnershipClassification.VENDOR_OWNED]
    assert {x.name for x in vendor} >= {"POS runtime","native reporting"}
    assert derive_result(s)[0] is s.result is FullCustomResult.FULL_CUSTOM_ADDS_MATERIAL_VALUE
    assert s.result_rationale and s.overall_lab_verdict=="UNTESTED"


def test_validation_rejects_invalid_allocations_costs_and_evidence_claims():
    s=load_full_custom_counterfactual()
    bad_effort=(replace(s.effort_allocation[0],amount=Decimal("39")),)+s.effort_allocation[1:]
    with pytest.raises(CounterfactualValidationError,match="378"):
        validate_counterfactual(replace(s,effort_allocation=bad_effort))
    bad_support=(replace(s.support_allocation[0],amount=Decimal("-1")),)+s.support_allocation[1:]
    with pytest.raises(CounterfactualValidationError,match="negative"):
        validate_counterfactual(replace(s,support_allocation=bad_support))
    coverage=tuple(replace(q,full_custom_status=AnswerStatus.ANSWERED) if q.question_id=="FIN-01" else q for q in s.question_coverage)
    with pytest.raises(CounterfactualValidationError,match="source evidence"):
        validate_counterfactual(replace(s,question_coverage=coverage))


def test_cli_comparison_and_original_values():
    r=subprocess.run([sys.executable,"-m","retail_configuration_lab","full-custom-counterfactual"],capture_output=True,text=True)
    assert r.returncode==0
    for text in ("Configuration-first + narrow custom edge","FULL CUSTOM COMPONENT","378 hours","$32,440.00","$62,000.00","$15,000.00","Chapter result:","Overall lab verdict: UNTESTED"):
        assert text in r.stdout
