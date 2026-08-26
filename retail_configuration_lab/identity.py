"""Chapter 3's bounded, configuration-driven identity experiment."""

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Any

from .evidence import EvidenceCategory


CONFIG_DIRECTORY = Path(__file__).resolve().parents[1] / "config" / "identity"


class IdentityValidationError(ValueError):
    """Raised when an identity configuration would permit unsafe resolution."""


class IdentityType(StrEnum):
    STORE = "STORE"
    PRODUCT = "PRODUCT"
    VARIANT = "VARIANT"
    SKU = "SKU"
    SUPPLIER = "SUPPLIER"
    CHANNEL = "CHANNEL"


class MappingStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    AMBIGUOUS = "AMBIGUOUS"
    UNMAPPED = "UNMAPPED"
    CONFLICT = "CONFLICT"


class IdentityReadiness(StrEnum):
    READY = "READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    BLOCKED = "BLOCKED"
    NOT_IDENTITY_DEPENDENT = "NOT_IDENTITY_DEPENDENT"


@dataclass(frozen=True)
class CanonicalIdentity:
    canonical_id: str
    identity_type: IdentityType
    description: str
    product_id: str | None = None
    variant_id: str | None = None


@dataclass(frozen=True)
class IdentityMapping:
    identity_type: IdentityType
    source_system: str
    source_identifier: str
    status: MappingStatus
    canonical_ids: tuple[str, ...]
    provenance: str
    evidence_classification: EvidenceCategory
    source_description: str | None = None
    source_identifier_kind: str | None = None

    @property
    def canonical_id(self) -> str | None:
        return self.canonical_ids[0] if len(self.canonical_ids) == 1 else None


@dataclass(frozen=True)
class ResolvedIdentity:
    """Resolution result that deliberately preserves source provenance."""
    identity_type: IdentityType
    source_system: str
    source_identifier: str
    canonical_id: str | None
    status: MappingStatus
    provenance: str | None
    evidence_classification: EvidenceCategory | None
    candidate_canonical_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdentityConfiguration:
    identities: dict[IdentityType, tuple[CanonicalIdentity, ...]]
    mappings: tuple[IdentityMapping, ...]

    def resolve(self, identity_type: IdentityType | str, source_system: str,
                source_identifier: str) -> ResolvedIdentity:
        kind = IdentityType(str(identity_type).upper())
        matches = [m for m in self.mappings if m.identity_type is kind
                   and m.source_system == source_system
                   and m.source_identifier == source_identifier]
        if not matches:
            return ResolvedIdentity(kind, source_system, source_identifier, None,
                                    MappingStatus.UNMAPPED, None, None)
        mapping = matches[0]
        return ResolvedIdentity(
            kind, source_system, source_identifier, mapping.canonical_id,
            mapping.status, mapping.provenance, mapping.evidence_classification,
            mapping.canonical_ids,
        )


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IdentityValidationError(f"{field} must be a nonempty string")
    return value


def load_identity_configuration(directory: Path | str = CONFIG_DIRECTORY) -> IdentityConfiguration:
    """Load and cross-validate the six identity-domain configuration artifacts."""
    directory = Path(directory)
    identities: dict[IdentityType, tuple[CanonicalIdentity, ...]] = {}
    mappings: list[IdentityMapping] = []
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        try:
            kind = IdentityType(data.get("identity_type"))
        except ValueError as exc:
            raise IdentityValidationError(f"Invalid identity type in {path.name}") from exc
        if kind in identities:
            raise IdentityValidationError(f"Duplicate identity domain: {kind}")
        domain: list[CanonicalIdentity] = []
        seen_ids: set[str] = set()
        for row in data.get("canonical_identities", []):
            canonical_id = _required_text(row.get("canonical_id"), "canonical_id")
            if canonical_id in seen_ids:
                raise IdentityValidationError(f"Duplicate canonical ID in {kind}: {canonical_id}")
            seen_ids.add(canonical_id)
            domain.append(CanonicalIdentity(
                canonical_id, kind, _required_text(row.get("description"), "description"),
                row.get("product_id"), row.get("variant_id"),
            ))
        identities[kind] = tuple(domain)
        for row in data.get("mappings", []):
            source_system = _required_text(row.get("source_system"), "source_system")
            source_identifier = _required_text(row.get("source_identifier"), "source_identifier")
            provenance = _required_text(row.get("provenance"), "provenance")
            try:
                status = MappingStatus(row.get("status"))
            except ValueError as exc:
                raise IdentityValidationError("Invalid mapping status") from exc
            try:
                evidence = EvidenceCategory(row.get("evidence_classification"))
            except ValueError as exc:
                raise IdentityValidationError("Missing or invalid evidence classification") from exc
            candidates = row.get("canonical_ids")
            if candidates is None and row.get("canonical_id") is not None:
                candidates = [row["canonical_id"]]
            if not isinstance(candidates, list) or not candidates or not all(
                    isinstance(item, str) and item for item in candidates):
                raise IdentityValidationError("A configured mapping needs canonical identity evidence")
            mappings.append(IdentityMapping(
                kind, source_system, source_identifier, status, tuple(candidates), provenance,
                evidence, row.get("source_description"), row.get("source_identifier_kind"),
            ))
    missing = set(IdentityType) - set(identities)
    if missing:
        raise IdentityValidationError(f"Missing identity domains: {', '.join(sorted(missing))}")
    all_ids = {kind: {item.canonical_id for item in rows} for kind, rows in identities.items()}
    keys: dict[tuple[IdentityType, str, str], tuple[str, ...]] = {}
    for mapping in mappings:
        for candidate in mapping.canonical_ids:
            if candidate not in all_ids[mapping.identity_type]:
                raise IdentityValidationError(f"Mapping references nonexistent canonical ID: {candidate}")
        key = (mapping.identity_type, mapping.source_system, mapping.source_identifier)
        if key in keys and keys[key] != mapping.canonical_ids:
            raise IdentityValidationError("Duplicate source mapping points to incompatible identities")
        keys[key] = mapping.canonical_ids
        if mapping.identity_type is IdentityType.PRODUCT and mapping.source_identifier_kind == "SUPPLIER_ITEM":
            raise IdentityValidationError("Supplier item identity cannot be a canonical product mapping")
    for variant in identities[IdentityType.VARIANT]:
        if not variant.product_id or variant.product_id not in all_ids[IdentityType.PRODUCT]:
            raise IdentityValidationError(f"Variant has invalid product relationship: {variant.canonical_id}")
    variants = {item.canonical_id: item for item in identities[IdentityType.VARIANT]}
    for sku in identities[IdentityType.SKU]:
        if not sku.product_id or sku.product_id not in all_ids[IdentityType.PRODUCT] or not sku.variant_id \
                or sku.variant_id not in variants or variants[sku.variant_id].product_id != sku.product_id:
            raise IdentityValidationError(f"SKU has invalid product/variant relationships: {sku.canonical_id}")
    return IdentityConfiguration(identities, tuple(mappings))


def resolve_identity(configuration: IdentityConfiguration, identity_type: IdentityType | str,
                     source_system: str, source_identifier: str) -> ResolvedIdentity:
    return configuration.resolve(identity_type, source_system, source_identifier)


@dataclass(frozen=True)
class Comparison:
    label: str
    identity_type: IdentityType
    left_system: str
    left_identifier: str
    left_value: int
    right_system: str
    right_identifier: str
    right_value: int


@dataclass(frozen=True)
class ComparisonOutcome:
    comparison: Comparison
    left: ResolvedIdentity
    right: ResolvedIdentity
    classification: str
    canonical_id: str | None


@dataclass(frozen=True)
class QuestionIdentityImpact:
    question_id: str
    readiness: IdentityReadiness
    reason: str


@dataclass(frozen=True)
class BurdenCategory:
    category: str
    annual_hours: int
    evidence_classification: EvidenceCategory = EvidenceCategory.MODELED_ASSUMPTION


@dataclass(frozen=True)
class IdentityExperimentResult:
    raw_comparisons: int
    raw_direct_matches: int
    raw_apparent_mismatches: int
    mappings_applied: int
    canonical_matches: int
    false_exceptions_eliminated: int
    pre_standardization_identity_driven_false_exceptions: int
    true_operational_exceptions_remaining: int
    ambiguous_identities: int
    unmapped_identities: int
    conflicts: int
    outcomes: tuple[ComparisonOutcome, ...]
    question_impacts: tuple[QuestionIdentityImpact, ...]
    burden_categories: tuple[BurdenCategory, ...]

    @property
    def false_exception_elimination_ratio(self) -> float:
        denominator = self.pre_standardization_identity_driven_false_exceptions
        return self.false_exceptions_eliminated / denominator if denominator else 0.0

    @property
    def relevant_chapter_2_questions_affected(self) -> tuple[str, ...]:
        return tuple(item.question_id for item in self.question_impacts
                     if item.readiness is not IdentityReadiness.NOT_IDENTITY_DEPENDENT)


COMPARISONS = (
    Comparison("matching trail-shirt stock", IdentityType.SKU, "RiverPOS", "SKU-1042", 8, "RiverStock", "1042", 8),
    Comparison("real hiking-pant shortage", IdentityType.SKU, "RiverPOS", "SKU-1055", 6, "RiverStock", "1055", 4),
    Comparison("Williamsburg fulfillment", IdentityType.STORE, "RiverPOS", "WBG-01", 12, "RiverCommerce", "fulfillment_williamsburg", 12),
    Comparison("supplier payable", IdentityType.SUPPLIER, "RiverBuy", "SUP-014", 320, "RiverBooks", "VENDOR-281", 320),
    Comparison("e-commerce return total", IdentityType.CHANNEL, "RiverCommerce", "WEB", 3, "RiverBooks", "ECOM", 2),
    Comparison("already shared commerce SKU", IdentityType.SKU, "RiverCommerce", "JRO-1042-BLU-M", 5, "RiverCommerce", "JRO-1042-BLU-M", 5),
    Comparison("ambiguous legacy item", IdentityType.SKU, "Spreadsheet", "SHIRT-M", 2, "RiverStock", "1042", 2),
    Comparison("unknown pop-up location", IdentityType.STORE, "RiverPOS", "POPUP-9", 1, "RiverStock", "STORE_1", 1),
    Comparison("contradictory supplier label", IdentityType.SUPPLIER, "Spreadsheet", "BR-TG", 1, "RiverBuy", "SUP-014", 1),
)


QUESTION_IMPACTS = (
    QuestionIdentityImpact("INV-01", IdentityReadiness.READY, "Configured store and SKU identity is comparable; quantities may still disagree."),
    QuestionIdentityImpact("INV-03", IdentityReadiness.PARTIALLY_READY, "Confirmed mappings help, while ambiguous and unmapped cases remain."),
    QuestionIdentityImpact("ECOM-01", IdentityReadiness.READY, "Channel and fulfillment-store identities remain distinct and traceable."),
    QuestionIdentityImpact("TRN-01", IdentityReadiness.PARTIALLY_READY, "Known stores resolve, but unknown locations block some transfers."),
    QuestionIdentityImpact("RET-01", IdentityReadiness.READY, "Configured SKU, channel, and store identity can be compared."),
    QuestionIdentityImpact("PUR-02", IdentityReadiness.PARTIALLY_READY, "Supplier mappings resolve except deliberately conflicting evidence."),
    QuestionIdentityImpact("FIN-01", IdentityReadiness.PARTIALLY_READY, "Known supplier and channel identities resolve; operational values can still differ."),
)


BURDEN = (
    BurdenCategory("store identifier reconciliation", 48),
    BurdenCategory("SKU/product mapping reconciliation", 120),
    BurdenCategory("supplier mapping reconciliation", 36),
    BurdenCategory("channel mapping reconciliation", 24),
)


def run_identity_experiment(configuration: IdentityConfiguration | None = None,
                            comparisons: tuple[Comparison, ...] = COMPARISONS) -> IdentityExperimentResult:
    config = configuration or load_identity_configuration()
    outcomes: list[ComparisonOutcome] = []
    mappings_applied = ambiguous = unmapped = conflicts = canonical_matches = eliminated = true = 0
    for comparison in comparisons:
        left = config.resolve(comparison.identity_type, comparison.left_system, comparison.left_identifier)
        right = config.resolve(comparison.identity_type, comparison.right_system, comparison.right_identifier)
        mappings_applied += sum(item.status is MappingStatus.CONFIRMED for item in (left, right))
        statuses = {left.status, right.status}
        if MappingStatus.CONFLICT in statuses:
            classification = "CONFLICT"
            conflicts += 1
        elif MappingStatus.AMBIGUOUS in statuses:
            classification = "AMBIGUOUS"
            ambiguous += 1
        elif MappingStatus.UNMAPPED in statuses:
            classification = "UNMAPPED"
            unmapped += 1
        elif left.canonical_id == right.canonical_id:
            canonical_matches += 1
            if comparison.left_value == comparison.right_value:
                classification = ("DIRECT_MATCH" if comparison.left_identifier == comparison.right_identifier
                                  else "FALSE_EXCEPTION_ELIMINATED")
                eliminated += classification == "FALSE_EXCEPTION_ELIMINATED"
            else:
                classification = "TRUE_OPERATIONAL_EXCEPTION"
                true += 1
        else:
            classification = "DIFFERENT_CANONICAL_IDENTITIES"
        canonical = left.canonical_id if left.canonical_id == right.canonical_id else None
        outcomes.append(ComparisonOutcome(comparison, left, right, classification, canonical))
    direct = sum(row.left_identifier == row.right_identifier for row in comparisons)
    # Equal-valued, raw-ID mismatches are the synthetic identity-driven false-exception population.
    pre_false = sum(row.left_identifier != row.right_identifier and row.left_value == row.right_value
                    and outcome.classification not in {"TRUE_OPERATIONAL_EXCEPTION", "DIFFERENT_CANONICAL_IDENTITIES"}
                    for row, outcome in zip(comparisons, outcomes))
    return IdentityExperimentResult(
        len(comparisons), direct, len(comparisons) - direct, mappings_applied,
        canonical_matches, eliminated, pre_false, true, ambiguous, unmapped, conflicts,
        tuple(outcomes), QUESTION_IMPACTS, BURDEN,
    )
