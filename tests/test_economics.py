from dataclasses import replace
from decimal import Decimal

import pytest

from retail_configuration_lab.economics import (
    EconomicValidationError, ORIGINAL_ANNUAL_BURDEN, ORIGINAL_RECOVERABLE_VALUE,
    analyze_economics, apply_sensitivity, dominance_analysis, load_economic_options,
    sensitivity_definitions, validate_options,
)


def test_required_options_and_preserved_baselines():
    options=load_economic_options()
    assert {x.option_id for x in options} == {"do-nothing","buy-configure","configure-automation","configure-narrow-edge","full-custom"}
    assert ORIGINAL_ANNUAL_BURDEN == Decimal("111020.00")
    assert ORIGINAL_RECOVERABLE_VALUE == Decimal("51513.80")
    full=next(x for x in options if x.option_id=="full-custom")
    assert full.setup_cost == Decimal("62000.00")
    assert full.annual_recurring_cash_cost == Decimal("15000.00")


def test_component_math_payback_and_three_year_math():
    option=next(x for x in load_economic_options() if x.option_id=="buy-configure")
    assert option.annual_ownership_cost == sum((option.annual_platform_cash_cost,option.annual_administration_cost,option.annual_support_labor_cost,option.annual_custom_code_support_cost,option.annual_risk_allowance),Decimal())
    assert option.annual_gross_burden_reduction == ORIGINAL_ANNUAL_BURDEN-option.residual_operational_burden
    assert option.first_year_net_benefit == option.annual_net_benefit_before_setup-option.setup_cost
    assert option.simple_payback_years == option.setup_cost/option.annual_net_benefit_before_setup
    assert option.three_year_net_benefit == 3*option.annual_net_benefit_before_setup-option.setup_cost
    assert option.three_year_total_cost == option.setup_cost+3*option.total_recurring_year_economic_cost


def test_do_nothing_and_recoverable_guardrail():
    option=load_economic_options()[0]
    assert option.setup_cost == 0
    assert option.residual_operational_burden == ORIGINAL_ANNUAL_BURDEN
    assert option.simple_payback_years is None
    assert option.recoverable_value_capture_ratio == 0


def test_chapter_inputs_are_reconciled_and_separate():
    options=load_economic_options(); auto=options[2]; edge=options[3]
    assert auto.annual_platform_cash_cost == Decimal("9000.00")
    assert auto.annual_administration_cost == Decimal("1800")
    assert auto.annual_support_labor_cost == Decimal("3000")
    assert edge.annual_custom_code_support_cost == Decimal("3000")
    assert edge.setup_cost-auto.setup_cost == Decimal("11250")


def test_rankings_dominance_sensitivity_and_result_are_deterministic():
    a=analyze_economics(); b=analyze_economics()
    assert {k:v.option_id if v else None for k,v in a.rankings.items()} == {k:v.option_id if v else None for k,v in b.rankings.items()}
    assert dominance_analysis(a.options) == a.dominated_options
    original=a.options
    changed=apply_sensitivity(original,sensitivity_definitions()[0])
    assert original[2].annual_support_labor_cost == Decimal("3000")
    assert changed[2].annual_support_labor_cost == Decimal("1800")
    assert a.result_rationale and a.overall_lab_verdict == "UNTESTED"


def test_validation_rejects_negative_full_price_and_duplicate_component():
    options=load_economic_options()
    with pytest.raises(EconomicValidationError,match="negative"):
        validate_options((replace(options[0],annual_risk_allowance=Decimal("-1")),)+options[1:])
    with pytest.raises(EconomicValidationError,match="implementation price"):
        validate_options(options[:-1]+(replace(options[-1],setup_implementation_cash_cost=Decimal("1")),))
    with pytest.raises(EconomicValidationError,match="duplicate cost component"):
        validate_options((replace(options[0],component_ids=("x","x")),)+options[1:])


def test_invalid_sensitivity_reference():
    scenario=replace(sensitivity_definitions()[0],option_id="missing")
    with pytest.raises(EconomicValidationError,match="invalid sensitivity reference"):
        apply_sensitivity(load_economic_options(),scenario)
