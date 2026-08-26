import json
from decimal import Decimal

import pytest

from retail_configuration_lab.baseline import assess, load_baseline
from retail_configuration_lab.evidence import EvidenceCategory
from retail_configuration_lab.models import BaselineCase, BaselineValidationError


def test_baseline_loads_and_preserves_expected_case():
    case = load_baseline()
    assert case.customer_name == "James River Outfitters"
    assert case.stores == 6
    assert case.ecommerce_channels == 1
    assert case.annual_current_state_burden == Decimal("111020.00")
    assert case.recoverable_annual_value == Decimal("51513.80")
    assert case.custom_implementation_price == Decimal("62000.00")
    assert case.custom_annual_recurring_fee == Decimal("15000.00")
    assert case.modeled_engineering_hours == Decimal("378")
    assert case.modeled_direct_delivery_cost == Decimal("32440.00")


def test_verdicts_and_evidence_are_explicit():
    case = load_baseline()
    assert case.original_verdict == "BUY / CONFIGURE"
    assert case.current_lab_verdict == "UNTESTED"
    assert case.evidence["original_verdict"] is EvidenceCategory.MODELED_ALTERNATIVE_ASSUMPTION
    assert case.evidence["original_verdict"] is not EvidenceCategory.OBSERVED_LAB_RESULT


def test_assessment_calculations():
    result = assess(load_baseline())
    assert result.recoverable_value_ratio == Decimal("51513.80") / Decimal("111020.00")
    assert result.custom_first_year_customer_cash_cost == Decimal("77000.00")
    assert result.custom_first_year_buyer_surplus == Decimal("-25486.20")
    assert result.custom_recurring_year_buyer_surplus == Decimal("36513.80")
    assert result.direct_delivery_contribution_before_recurring_support == Decimal("29560.00")
    assert result.simple_first_year_coverage_ratio == Decimal("51513.80") / Decimal("77000.00")


def test_negative_money_is_rejected():
    path = load_baseline.__defaults__[0]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["custom_implementation_price"] = "-0.01"
    with pytest.raises(BaselineValidationError, match="custom_implementation_price must be nonnegative"):
        BaselineCase.from_dict(data)


def test_missing_evidence_classification_is_rejected():
    path = load_baseline.__defaults__[0]
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["evidence"]["recoverable_annual_value"]
    with pytest.raises(BaselineValidationError, match="Missing evidence classification"):
        BaselineCase.from_dict(data)

