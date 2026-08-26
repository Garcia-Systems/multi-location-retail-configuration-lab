"""Small, dependency-free domain models and validation for Chapter 0."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .evidence import EvidenceCategory


class BaselineValidationError(ValueError):
    """Raised when baseline input cannot represent a valid synthetic case."""


def _required(data: dict[str, Any], key: str) -> Any:
    if key not in data or data[key] in (None, ""):
        raise BaselineValidationError(f"Missing required field: {key}")
    return data[key]


def _nonnegative_decimal(data: dict[str, Any], key: str) -> Decimal:
    value = _required(data, key)
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BaselineValidationError(f"{key} must be a decimal number") from exc
    if not result.is_finite() or result < 0:
        raise BaselineValidationError(f"{key} must be nonnegative")
    return result


def _nonnegative_int(data: dict[str, Any], key: str) -> int:
    value = _required(data, key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BaselineValidationError(f"{key} must be a nonnegative integer")
    return value


@dataclass(frozen=True)
class BaselineCase:
    customer_name: str
    stores: int
    ecommerce_channels: int
    business_description: str
    workflow_stages: tuple[str, ...]
    system_categories: tuple[str, ...]
    annual_current_state_burden: Decimal
    recoverable_annual_value: Decimal
    custom_implementation_price: Decimal
    custom_annual_recurring_fee: Decimal
    modeled_engineering_hours: Decimal
    modeled_direct_delivery_cost: Decimal
    original_verdict: str
    original_verdict_reasoning: str
    current_lab_verdict: str
    experiment_questions: tuple[str, ...]
    evidence: dict[str, EvidenceCategory]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaselineCase":
        if not isinstance(data, dict):
            raise BaselineValidationError("Baseline root must be an object")
        evidence_data = _required(data, "evidence")
        if not isinstance(evidence_data, dict):
            raise BaselineValidationError("evidence must be an object")
        classified_fields = (
            "customer_name", "stores", "ecommerce_channels", "business_description",
            "workflow_stages", "system_categories",
            "annual_current_state_burden", "recoverable_annual_value",
            "custom_implementation_price", "custom_annual_recurring_fee",
            "modeled_engineering_hours", "modeled_direct_delivery_cost",
            "original_verdict", "original_verdict_reasoning", "current_lab_verdict",
            "experiment_questions",
        )
        evidence: dict[str, EvidenceCategory] = {}
        for field in classified_fields:
            if field not in evidence_data:
                raise BaselineValidationError(f"Missing evidence classification: {field}")
            try:
                evidence[field] = EvidenceCategory(evidence_data[field])
            except ValueError as exc:
                raise BaselineValidationError(
                    f"Unknown evidence classification for {field}: {evidence_data[field]}"
                ) from exc

        workflow = _required(data, "workflow_stages")
        systems = _required(data, "system_categories")
        questions = _required(data, "experiment_questions")
        for name, value in (("workflow_stages", workflow), ("system_categories", systems),
                            ("experiment_questions", questions)):
            if not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value):
                raise BaselineValidationError(f"{name} must be a nonempty list of strings")

        return cls(
            customer_name=str(_required(data, "customer_name")),
            stores=_nonnegative_int(data, "stores"),
            ecommerce_channels=_nonnegative_int(data, "ecommerce_channels"),
            business_description=str(_required(data, "business_description")),
            workflow_stages=tuple(workflow), system_categories=tuple(systems),
            annual_current_state_burden=_nonnegative_decimal(data, "annual_current_state_burden"),
            recoverable_annual_value=_nonnegative_decimal(data, "recoverable_annual_value"),
            custom_implementation_price=_nonnegative_decimal(data, "custom_implementation_price"),
            custom_annual_recurring_fee=_nonnegative_decimal(data, "custom_annual_recurring_fee"),
            modeled_engineering_hours=_nonnegative_decimal(data, "modeled_engineering_hours"),
            modeled_direct_delivery_cost=_nonnegative_decimal(data, "modeled_direct_delivery_cost"),
            original_verdict=str(_required(data, "original_verdict")),
            original_verdict_reasoning=str(_required(data, "original_verdict_reasoning")),
            current_lab_verdict=str(_required(data, "current_lab_verdict")),
            experiment_questions=tuple(questions), evidence=evidence,
        )


@dataclass(frozen=True)
class BaselineAssessment:
    recoverable_value_ratio: Decimal
    custom_first_year_customer_cash_cost: Decimal
    custom_first_year_buyer_surplus: Decimal
    custom_recurring_year_buyer_surplus: Decimal
    direct_delivery_contribution_before_recurring_support: Decimal
    simple_first_year_coverage_ratio: Decimal
