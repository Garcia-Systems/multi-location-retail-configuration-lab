"""Load, validate, and analyze Chapter 2's synthetic business questions."""

from collections import Counter
from dataclasses import dataclass
import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from .capabilities import CapabilityInventory, load_inventory
from .evidence import EvidenceCategory
from .models import (
    FreshnessRequirement, QuestionCoverageStatus, QuestionScope, QuestionType,
)

DEFAULT_QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "business_questions.json"

FRESHNESS_DEFINITIONS = {
    FreshnessRequirement.REAL_TIME: "Available as the event occurs when delay prevents the action.",
    FreshnessRequirement.NEAR_REAL_TIME: "Available within minutes, not necessarily synchronously.",
    FreshnessRequirement.DAILY: "Available once per completed operating day.",
    FreshnessRequirement.WEEKLY: "Available once per management week.",
    FreshnessRequirement.PERIOD_CLOSE: "Available for the accounting close timetable.",
    FreshnessRequirement.ON_DEMAND: "Available when an authorized operator requests it.",
}


class BusinessQuestionError(ValueError):
    """Raised when a question fixture violates its evidence contract."""


@dataclass(frozen=True)
class StakeholderRole:
    name: str
    responsibilities: tuple[str, ...]


@dataclass(frozen=True)
class BusinessQuestion:
    question_id: str
    business_area: str
    question_text: str
    primary_owner: str
    decision_action: str
    required_evidence: tuple[str, ...]
    freshness: FreshnessRequirement
    scope: QuestionScope
    importance_rationale: str
    evidence_category: EvidenceCategory
    question_type: QuestionType
    coverage_status: QuestionCoverageStatus
    related_capability_ids: tuple[str, ...] = ()
    known_limitations: tuple[str, ...] = ()
    unresolved_discovery_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class BusinessQuestionInventory:
    customer_name: str
    roles: tuple[StakeholderRole, ...]
    questions: tuple[BusinessQuestion, ...]


@dataclass(frozen=True)
class BusinessQuestionAnalysis:
    total_business_questions: int
    count_by_business_area: dict[str, int]
    count_by_question_type: dict[QuestionType, int]
    count_by_freshness: dict[FreshnessRequirement, int]
    count_by_coverage_status: dict[QuestionCoverageStatus, int]
    direct_capability_paths: int
    multiple_capabilities_required: int
    no_known_capability: int
    unknown_coverage: int
    quality_failures: tuple[str, ...]


def _text(raw: dict[str, Any], key: str, context: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BusinessQuestionError(f"{context}: missing or empty {key}")
    return value.strip()


def _strings(raw: dict[str, Any], key: str, context: str, *, required: bool) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list) or (required and not value):
        qualifier = "nonempty " if required else ""
        raise BusinessQuestionError(f"{context}: {key} must be a {qualifier}list of strings")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise BusinessQuestionError(f"{context}: {key} must contain nonempty strings")
    return tuple(item.strip() for item in value)


def _enum(enum_type: type, raw: dict[str, Any], key: str, context: str):
    value = _text(raw, key, context)
    try:
        return enum_type(value)
    except ValueError as exc:
        raise BusinessQuestionError(f"{context}: invalid {key} {value}") from exc


def questions_from_dict(
    data: dict[str, Any], capability_inventory: CapabilityInventory | None = None,
) -> BusinessQuestionInventory:
    """Construct validated questions and resolve every Chapter 1 reference."""
    if not isinstance(data, dict):
        raise BusinessQuestionError("Business-question root must be an object")
    capabilities = capability_inventory or load_inventory()
    capability_ids = {item.capability.identifier for item in capabilities.assessments}
    raw_roles, raw_questions = data.get("stakeholder_roles"), data.get("business_questions")
    if not isinstance(raw_roles, list) or not raw_roles:
        raise BusinessQuestionError("stakeholder_roles must be a nonempty list")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise BusinessQuestionError("business_questions must be a nonempty list")

    roles: list[StakeholderRole] = []
    role_names: set[str] = set()
    for raw in raw_roles:
        if not isinstance(raw, dict):
            raise BusinessQuestionError("stakeholder role must be an object")
        name = _text(raw, "name", "stakeholder role")
        if name in role_names:
            raise BusinessQuestionError(f"duplicate stakeholder role: {name}")
        role_names.add(name)
        roles.append(StakeholderRole(name, _strings(raw, "responsibilities", name, required=True)))

    questions: list[BusinessQuestion] = []
    question_ids: set[str] = set()
    for raw in raw_questions:
        if not isinstance(raw, dict):
            raise BusinessQuestionError("business question must be an object")
        identifier = _text(raw, "question_id", "business question")
        if identifier in question_ids:
            raise BusinessQuestionError(f"duplicate question ID: {identifier}")
        question_ids.add(identifier)
        owner = _text(raw, "primary_owner", identifier)
        if owner not in role_names:
            raise BusinessQuestionError(f"{identifier}: unknown primary_owner {owner}")
        related = _strings(raw, "related_capability_ids", identifier, required=False)
        missing = sorted(set(related) - capability_ids)
        if missing:
            raise BusinessQuestionError(
                f"{identifier}: nonexistent Chapter 1 capability: {', '.join(missing)}"
            )
        coverage = _enum(QuestionCoverageStatus, raw, "coverage_status", identifier)
        if coverage is QuestionCoverageStatus.DIRECT and not related:
            raise BusinessQuestionError(f"{identifier}: DIRECT coverage requires a related capability")
        if coverage is QuestionCoverageStatus.MULTIPLE_CAPABILITIES_REQUIRED and len(related) < 2:
            raise BusinessQuestionError(
                f"{identifier}: MULTIPLE_CAPABILITIES_REQUIRED requires at least two capabilities"
            )
        if coverage is QuestionCoverageStatus.NO_KNOWN_CAPABILITY and related:
            raise BusinessQuestionError(
                f"{identifier}: NO_KNOWN_CAPABILITY cannot claim related capabilities"
            )
        questions.append(BusinessQuestion(
            identifier, _text(raw, "business_area", identifier),
            _text(raw, "question_text", identifier), owner,
            _text(raw, "decision_action", identifier),
            _strings(raw, "required_evidence", identifier, required=True),
            _enum(FreshnessRequirement, raw, "freshness", identifier),
            _enum(QuestionScope, raw, "scope", identifier),
            _text(raw, "importance_rationale", identifier),
            _enum(EvidenceCategory, raw, "evidence_category", identifier),
            _enum(QuestionType, raw, "question_type", identifier), coverage, related,
            _strings(raw, "known_limitations", identifier, required=False),
            _strings(raw, "unresolved_discovery_notes", identifier, required=False),
        ))
    return BusinessQuestionInventory(
        _text(data, "customer_name", "business-question inventory"), tuple(roles), tuple(questions)
    )


def load_questions(path: str | Path = DEFAULT_QUESTIONS_PATH) -> BusinessQuestionInventory:
    try:
        with Path(path).open(encoding="utf-8") as source:
            raw = json.load(source)
    except (OSError, JSONDecodeError) as exc:
        raise BusinessQuestionError(f"Could not load business questions {path}: {exc}") from exc
    return questions_from_dict(raw)


def analyze_questions(inventory: BusinessQuestionInventory) -> BusinessQuestionAnalysis:
    """Return deterministic counts; no score or verdict is inferred."""
    areas = Counter(item.business_area for item in inventory.questions)
    types = Counter(item.question_type for item in inventory.questions)
    freshness = Counter(item.freshness for item in inventory.questions)
    coverage = Counter(item.coverage_status for item in inventory.questions)
    failures = tuple(
        item.question_id for item in inventory.questions
        if not (item.primary_owner and item.decision_action and item.required_evidence
                and item.freshness and item.scope and item.importance_rationale)
    )
    return BusinessQuestionAnalysis(
        len(inventory.questions), dict(sorted(areas.items())),
        {value: types[value] for value in QuestionType},
        {value: freshness[value] for value in FreshnessRequirement},
        {value: coverage[value] for value in QuestionCoverageStatus},
        coverage[QuestionCoverageStatus.DIRECT],
        coverage[QuestionCoverageStatus.MULTIPLE_CAPABILITIES_REQUIRED],
        coverage[QuestionCoverageStatus.NO_KNOWN_CAPABILITY],
        coverage[QuestionCoverageStatus.UNKNOWN], failures,
    )
