"""Chapter 15: a bounded, fictional strong-native-suite sensitivity scenario."""

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import json
from pathlib import Path

from .evidence import EvidenceCategory
from .models import CapabilityStatus
from .questions import load_questions
from .residual_gaps import ResidualStatus, analyze_residual_gaps, load_residual_gaps

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "strong_native_suite.json"


class StrongSuiteValidationError(ValueError): pass


class AnswerStatus(StrEnum):
    ANSWERED = "ANSWERED"
    PARTIALLY_ANSWERED = "PARTIALLY_ANSWERED"
    NOT_ANSWERED = "NOT_ANSWERED"
    UNKNOWN = "UNKNOWN"


class ReconciliationStatus(StrEnum):
    RECONCILED = "RECONCILED"
    EXCEPTION = "EXCEPTION"


class CustomRelevance(StrEnum):
    NONE_MATERIAL = "NONE_MATERIAL"
    PROCESS_ONLY = "PROCESS_ONLY"
    ADMINISTRATION_ONLY = "ADMINISTRATION_ONLY"
    NARROW_TECHNICAL_EDGE = "NARROW_TECHNICAL_EDGE"
    MATERIAL_TECHNICAL_GAP = "MATERIAL_TECHNICAL_GAP"
    UNKNOWN = "UNKNOWN"


class ScenarioVerdict(StrEnum):
    BUY_CONFIGURE = "BUY_CONFIGURE"
    BUY_CONFIGURE_WITH_PROCESS_CHANGE = "BUY_CONFIGURE_WITH_PROCESS_CHANGE"
    NARROW_CUSTOM_EDGE = "NARROW_CUSTOM_EDGE"
    INVESTIGATE = "INVESTIGATE"
    NO_DEAL = "NO_DEAL"
    UNKNOWN = "UNKNOWN"


def _money(value, field):
    try: result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc: raise StrongSuiteValidationError(f"invalid {field}") from exc
    if not result.is_finite() or result < 0: raise StrongSuiteValidationError(f"{field} cannot be negative")
    return result


@dataclass(frozen=True)
class AccountingResult:
    posting_id: str; record_type: str; operational_amount: Decimal; accounting_amount: Decimal
    @property
    def difference(self): return self.accounting_amount - self.operational_amount
    @property
    def status(self): return ReconciliationStatus.RECONCILED if self.difference == 0 else ReconciliationStatus.EXCEPTION


@dataclass(frozen=True)
class StrongSuiteScenario:
    raw: dict
    capabilities: tuple[dict, ...]
    question_comparisons: tuple[dict, ...]
    burden_categories: tuple[dict, ...]
    accounting_results: tuple[AccountingResult, ...]
    setup_costs: dict[str, Decimal]
    platform_cost: Decimal
    connector_cost: Decimal
    administration_cost: Decimal
    custom_relevance: CustomRelevance

    @property
    def total_questions(self): return len(self.question_comparisons)
    @property
    def base_questions_answered(self): return sum(x["base_status"] is AnswerStatus.ANSWERED for x in self.question_comparisons)
    @property
    def strong_questions_answered(self): return sum(x["strong_status"] is AnswerStatus.ANSWERED for x in self.question_comparisons)
    @property
    def strong_suite_question_gain(self): return self.strong_questions_answered - self.base_questions_answered
    @property
    def base_residual_operational_burden(self): return analyze_residual_gaps().residual_operational_burden
    @property
    def base_administration_support_cost(self): return analyze_residual_gaps().new_administration_burden
    @property
    def strong_residual_operational_burden(self): return sum((x["remaining"] for x in self.burden_categories), Decimal())
    @property
    def strong_suite_residual_burden_reduction(self): return self.base_residual_operational_burden - self.strong_residual_operational_burden
    @property
    def recurring_platform_cost(self): return self.platform_cost + self.connector_cost
    @property
    def setup_migration_cost(self): return sum(self.setup_costs.values(), Decimal())
    @property
    def remaining_technical_gaps(self): return sum(x["status"] is CapabilityStatus.GAP for x in self.capabilities)
    @property
    def remaining_unknowns(self): return sum(x["status"] is CapabilityStatus.UNKNOWN for x in self.capabilities)
    @property
    def overall_lab_verdict(self): return "UNTESTED"


def derive_verdict(scenario: StrongSuiteScenario) -> tuple[ScenarioVerdict, str]:
    """Ordered rules, not a score or a hard-coded fixture answer."""
    material = scenario.custom_relevance is CustomRelevance.MATERIAL_TECHNICAL_GAP
    major_unknown = any(x["strong_status"] is AnswerStatus.UNKNOWN and x.get("material", True) for x in scenario.question_comparisons)
    if scenario.raw["economics"].get("unfavorable", False):
        return ScenarioVerdict.NO_DEAL, "Modeled economics are explicitly unfavorable despite coverage."
    if major_unknown: return ScenarioVerdict.INVESTIGATE, "A material business question remains unknown."
    if material: return ScenarioVerdict.NARROW_CUSTOM_EDGE, "One bounded material technical gap remains after native configuration."
    if scenario.custom_relevance is CustomRelevance.PROCESS_ONLY:
        return ScenarioVerdict.BUY_CONFIGURE_WITH_PROCESS_CHANGE, "Native coverage is sufficient, but a material process change remains."
    return ScenarioVerdict.BUY_CONFIGURE, "Nearly all material questions are answered and the remaining technical edge is explicitly immaterial."


def load_strong_native_suite(path: Path | str = DATA_PATH) -> StrongSuiteScenario:
    raw = json.loads(Path(path).read_text())
    try: EvidenceCategory(raw["scenario_evidence"])
    except (KeyError, ValueError) as exc: raise StrongSuiteValidationError("missing evidence classification") from exc
    caps = tuple(raw.get("capabilities", ()))
    ids = [x.get("capability_id") for x in caps]
    if None in ids or len(ids) != len(set(ids)): raise StrongSuiteValidationError("duplicate scenario capability IDs")
    for cap in caps:
        try: cap["status"] = CapabilityStatus(cap["status"]); EvidenceCategory(cap["evidence"])
        except (KeyError, ValueError) as exc: raise StrongSuiteValidationError("invalid capability status or evidence classification") from exc
    valid_questions = {q.question_id for q in load_questions().questions}
    comparisons = tuple(raw.get("question_comparisons", ()))
    if {x.get("question_id") for x in comparisons} != valid_questions: raise StrongSuiteValidationError("scenario question references do not resolve")
    for item in comparisons:
        try: item["base_status"] = AnswerStatus(item["base_status"]); item["strong_status"] = AnswerStatus(item["strong_status"]); EvidenceCategory(item["evidence"])
        except (KeyError, ValueError) as exc: raise StrongSuiteValidationError("invalid question classification") from exc
    valid_burdens = {x.category_id for x in load_residual_gaps().categories}
    burdens = tuple(raw.get("burden_categories", ()))
    if {x.get("category_id") for x in burdens} != valid_burdens: raise StrongSuiteValidationError("invalid burden category references")
    for item in burdens:
        try: item["status"] = ResidualStatus(item["status"].replace("_", " ")); item["remaining"] = _money(item["remaining"], "scenario residual"); EvidenceCategory(item["evidence"])
        except (KeyError, ValueError) as exc: raise StrongSuiteValidationError("invalid burden classification") from exc
    declared = _money(raw["strong_residual_total"], "scenario residual total")
    if declared != sum((x["remaining"] for x in burdens), Decimal()): raise StrongSuiteValidationError("scenario residual totals inconsistent with categories")
    costs = raw["costs"]
    setup = {k: _money(v, f"{k} setup/migration cost") for k,v in costs["setup_migration"].items()}
    accounting = tuple(AccountingResult(x["posting_id"], x["record_type"], _money(x["operational_amount"], "operational amount"), _money(x["accounting_amount"], "accounting amount")) for x in raw["accounting_postings"])
    scenario = StrongSuiteScenario(raw, caps, comparisons, burdens, accounting, setup,
        _money(costs["subscription_platform"], "recurring cost"), _money(costs["connector_modules"], "recurring cost"),
        _money(costs["administration_support_labor"], "administration cost"), CustomRelevance(raw["custom_edge"]["classification"]))
    verdict, rationale = derive_verdict(scenario)
    if not rationale: raise StrongSuiteValidationError("scenario verdict without rationale")
    if verdict is ScenarioVerdict.BUY_CONFIGURE and scenario.custom_relevance is CustomRelevance.MATERIAL_TECHNICAL_GAP:
        raise StrongSuiteValidationError("BUY_CONFIGURE has unexplained material technical gap")
    return scenario


run_strong_native_suite = load_strong_native_suite
