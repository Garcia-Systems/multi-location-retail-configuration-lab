"""Chapter 11: deterministic synthesis of configuration-first residual burdens."""

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import json
from pathlib import Path
from typing import Any

from .evidence import EvidenceCategory
from .questions import load_questions

DEFAULT_RESIDUAL_GAPS_PATH = Path(__file__).resolve().parent.parent / "data" / "residual_gaps.json"
EXPECTED_ORIGINAL_BURDEN = Decimal("111020.00")
ORIGINAL_RECOVERABLE_VALUE = Decimal("51513.80")
VALID_INTERVENTION_CHAPTERS = frozenset(range(3, 11))


class ResidualStatus(StrEnum):
    ELIMINATED = "ELIMINATED"
    REDUCED = "REDUCED"
    UNCHANGED = "UNCHANGED"
    MOVED_TO_ADMINISTRATION = "MOVED TO ADMINISTRATION"
    NEW_SUPPORT_OBLIGATION = "NEW SUPPORT OBLIGATION"
    UNKNOWN = "UNKNOWN"


class CustomSoftwareRelevance(StrEnum):
    CONFIGURATION_RESIDUAL = "CONFIGURATION_RESIDUAL"
    PROCESS_RESIDUAL = "PROCESS_RESIDUAL"
    ADMINISTRATION_RESIDUAL = "ADMINISTRATION_RESIDUAL"
    TECHNICAL_GAP = "TECHNICAL_GAP"
    SUPPORT_OBLIGATION = "SUPPORT_OBLIGATION"
    UNKNOWN = "UNKNOWN"


class QuestionResidualStatus(StrEnum):
    ANSWERED_WITH_LOW_RESIDUAL_BURDEN = "ANSWERED_WITH_LOW_RESIDUAL_BURDEN"
    ANSWERED_WITH_RESIDUAL_EXCEPTIONS = "ANSWERED_WITH_RESIDUAL_EXCEPTIONS"
    PARTIAL_WITH_MATERIAL_RESIDUAL = "PARTIAL_WITH_MATERIAL_RESIDUAL"
    UNANSWERED = "UNANSWERED"
    UNKNOWN = "UNKNOWN"


class ResidualGapError(ValueError):
    pass


@dataclass(frozen=True)
class BurdenCategory:
    category_id: str
    name: str
    original_annual_burden: Decimal
    question_ids: tuple[str, ...]
    intervention_chapters: tuple[int, ...]
    residual_status: ResidualStatus
    observed_lab_evidence: str
    modeled_remaining_burden: Decimal
    administration_burden: Decimal
    support_obligation: str | None
    uncertainty_note: str
    evidence_classifications: tuple[EvidenceCategory, ...]
    rationale: str
    custom_software_relevance: CustomSoftwareRelevance
    observed_reduction_ratio: Decimal | None = None

    @property
    def calculated_remaining_burden(self) -> Decimal | None:
        if self.observed_reduction_ratio is None:
            return None
        return self.original_annual_burden * (Decimal("1") - self.observed_reduction_ratio)


@dataclass(frozen=True)
class ResidualGapInventory:
    customer_name: str
    original_annual_burden: Decimal
    original_recoverable_value: Decimal
    categories: tuple[BurdenCategory, ...]


@dataclass(frozen=True)
class ResidualGapAnalysis:
    original_annual_burden: Decimal
    residual_operational_burden: Decimal
    new_administration_burden: Decimal
    combined_post_configuration_burden: Decimal
    modeled_burden_reduction: Decimal
    modeled_burden_reduction_ratio: Decimal
    original_recoverable_value: Decimal
    status_counts: dict[ResidualStatus, int]
    largest_residuals: tuple[BurdenCategory, ...]
    question_residuals: dict[str, QuestionResidualStatus]


def _money(raw: Any, field: str) -> Decimal:
    try:
        value = Decimal(str(raw))
    except Exception as exc:
        raise ResidualGapError(f"invalid {field}") from exc
    if value < 0:
        raise ResidualGapError(f"{field} cannot be negative")
    return value


def residual_gaps_from_dict(data: dict[str, Any]) -> ResidualGapInventory:
    if not isinstance(data, dict) or not isinstance(data.get("categories"), list):
        raise ResidualGapError("residual-gap root and categories must be structured")
    valid_questions = {q.question_id for q in load_questions().questions}
    categories = []
    seen = set()
    for raw in data["categories"]:
        identifier = raw.get("category_id", "")
        if not identifier or identifier in seen:
            raise ResidualGapError(f"duplicate or missing burden category ID: {identifier}")
        seen.add(identifier)
        try:
            status = ResidualStatus(raw["residual_status"].replace("_", " "))
            relevance = CustomSoftwareRelevance(raw["custom_software_relevance"])
            evidence = tuple(EvidenceCategory(x) for x in raw["evidence_classifications"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ResidualGapError(f"{identifier}: invalid classification") from exc
        if not evidence:
            raise ResidualGapError(f"{identifier}: missing evidence classification")
        questions = tuple(raw.get("question_ids", ()))
        missing_questions = set(questions) - valid_questions
        if missing_questions:
            raise ResidualGapError(f"{identifier}: nonexistent Chapter 2 questions: {sorted(missing_questions)}")
        chapters = tuple(raw.get("intervention_chapters", ()))
        if set(chapters) - VALID_INTERVENTION_CHAPTERS:
            raise ResidualGapError(f"{identifier}: nonexistent intervention chapter")
        original = _money(raw.get("original_annual_burden"), "original burden")
        remaining = _money(raw.get("modeled_remaining_burden"), "remaining burden")
        administration = _money(raw.get("administration_burden", "0"), "administration burden")
        ratio_raw = raw.get("observed_reduction_ratio")
        ratio = _money(ratio_raw, "reduction ratio") if ratio_raw is not None else None
        if ratio is not None and ratio > 1:
            raise ResidualGapError(f"{identifier}: reduction ratio outside [0, 1]")
        support = raw.get("support_obligation")
        if remaining > original and not (administration or support):
            raise ResidualGapError(f"{identifier}: remaining burden exceeds original")
        if ratio is not None and remaining != original * (1 - ratio):
            raise ResidualGapError(f"{identifier}: remaining burden does not apply observed ratio")
        if status is ResidualStatus.ELIMINATED and remaining != 0:
            raise ResidualGapError(f"{identifier}: ELIMINATED must have zero residual burden")
        if status is ResidualStatus.UNCHANGED and remaining != original:
            raise ResidualGapError(f"{identifier}: UNCHANGED has unexplained reduction")
        if not str(raw.get("rationale", "")).strip():
            raise ResidualGapError(f"{identifier}: missing rationale")
        if not str(raw.get("observed_lab_evidence", "")).strip():
            raise ResidualGapError(f"{identifier}: missing observed evidence")
        categories.append(BurdenCategory(
            identifier, str(raw.get("name", "")).strip(), original, questions, chapters, status,
            raw["observed_lab_evidence"], remaining, administration, support,
            str(raw.get("uncertainty_note", "")), evidence, raw["rationale"], relevance, ratio,
        ))
    declared = _money(data.get("original_annual_burden"), "declared original burden")
    if declared != EXPECTED_ORIGINAL_BURDEN or sum((x.original_annual_burden for x in categories), Decimal()) != declared:
        raise ResidualGapError("original burden categories must sum exactly to $111,020.00")
    recoverable = _money(data.get("original_recoverable_value"), "recoverable value")
    if recoverable != ORIGINAL_RECOVERABLE_VALUE:
        raise ResidualGapError("original recoverable value must remain $51,513.80")
    return ResidualGapInventory(str(data.get("customer_name", "")), declared, recoverable, tuple(categories))


def load_residual_gaps(path: str | Path = DEFAULT_RESIDUAL_GAPS_PATH) -> ResidualGapInventory:
    try:
        with Path(path).open(encoding="utf-8") as source:
            return residual_gaps_from_dict(json.load(source))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResidualGapError(f"Could not load residual gaps {path}: {exc}") from exc


load_burden_inventory = load_residual_gaps


def analyze_residual_gaps(inventory: ResidualGapInventory | None = None) -> ResidualGapAnalysis:
    inventory = inventory or load_residual_gaps()
    residual = sum((x.modeled_remaining_burden for x in inventory.categories), Decimal())
    admin = sum((x.administration_burden for x in inventory.categories), Decimal())
    combined = residual + admin
    reduction = inventory.original_annual_burden - combined
    counts = Counter(x.residual_status for x in inventory.categories)
    ranked = tuple(sorted((x for x in inventory.categories if x.modeled_remaining_burden > 0),
                          key=lambda x: (-x.modeled_remaining_burden, x.category_id)))
    question_residuals = {}
    for question in load_questions().questions:
        related = [x for x in inventory.categories if question.question_id in x.question_ids]
        if not related:
            value = QuestionResidualStatus.UNKNOWN
        elif any(x.residual_status is ResidualStatus.UNKNOWN for x in related):
            value = QuestionResidualStatus.UNKNOWN
        elif any(x.residual_status is ResidualStatus.UNCHANGED for x in related):
            value = QuestionResidualStatus.UNANSWERED
        elif sum((x.modeled_remaining_burden for x in related), Decimal()) >= Decimal("7000"):
            value = QuestionResidualStatus.PARTIAL_WITH_MATERIAL_RESIDUAL
        elif any(x.modeled_remaining_burden for x in related):
            value = QuestionResidualStatus.ANSWERED_WITH_RESIDUAL_EXCEPTIONS
        else:
            value = QuestionResidualStatus.ANSWERED_WITH_LOW_RESIDUAL_BURDEN
        question_residuals[question.question_id] = value
    return ResidualGapAnalysis(inventory.original_annual_burden, residual, admin, combined,
        reduction, reduction / inventory.original_annual_burden, inventory.original_recoverable_value,
        {status: counts[status] for status in ResidualStatus}, ranked, question_residuals)


analyze_burden_inventory = analyze_residual_gaps
