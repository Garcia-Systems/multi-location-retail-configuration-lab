"""Loading and deterministic economic reconstruction of the baseline case."""

import json
from json import JSONDecodeError
from pathlib import Path

from .models import BaselineAssessment, BaselineCase, BaselineValidationError

DEFAULT_BASELINE_PATH = Path(__file__).resolve().parent.parent / "data" / "baseline_case.json"


def load_baseline(path: str | Path = DEFAULT_BASELINE_PATH) -> BaselineCase:
    try:
        with Path(path).open(encoding="utf-8") as source:
            raw = json.load(source)
    except (OSError, JSONDecodeError) as exc:
        raise BaselineValidationError(f"Could not load baseline file {path}: {exc}") from exc
    return BaselineCase.from_dict(raw)


def assess(case: BaselineCase) -> BaselineAssessment:
    first_year_cost = case.custom_implementation_price + case.custom_annual_recurring_fee
    if case.annual_current_state_burden == 0:
        raise BaselineValidationError("annual_current_state_burden must be greater than zero for assessment")
    if first_year_cost == 0:
        raise BaselineValidationError("custom first-year customer cash cost must be greater than zero")
    return BaselineAssessment(
        recoverable_value_ratio=case.recoverable_annual_value / case.annual_current_state_burden,
        custom_first_year_customer_cash_cost=first_year_cost,
        custom_first_year_buyer_surplus=case.recoverable_annual_value - first_year_cost,
        custom_recurring_year_buyer_surplus=(
            case.recoverable_annual_value - case.custom_annual_recurring_fee
        ),
        direct_delivery_contribution_before_recurring_support=(
            case.custom_implementation_price - case.modeled_direct_delivery_cost
        ),
        simple_first_year_coverage_ratio=case.recoverable_annual_value / first_year_cost,
    )

