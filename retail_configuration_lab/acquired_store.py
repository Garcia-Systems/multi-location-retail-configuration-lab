"""Chapter 14's synthetic fragmentation experiment (not an integration framework)."""

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path

from .add_store import load_store7_experiment
from .models import CapabilityStatus

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "acquired_store.json"
STORE8_ID = "JRO-STORE-008"


class AcquisitionValidationError(ValueError):
    pass


class CompatibilityFit(StrEnum):
    REUSABLE = "REUSABLE"
    REUSABLE_WITH_CONFIGURATION = "REUSABLE_WITH_CONFIGURATION"
    REQUIRES_NEW_MAPPING = "REQUIRES_NEW_MAPPING"
    REQUIRES_NEW_MODULE = "REQUIRES_NEW_MODULE"
    TECHNICAL_GAP = "TECHNICAL_GAP"
    PROCESS_GAP = "PROCESS_GAP"
    MIGRATION_CANDIDATE = "MIGRATION_CANDIDATE"
    UNKNOWN = "UNKNOWN"


class AcquisitionResponse(StrEnum):
    STANDARDIZE_FIRST = "STANDARDIZE_FIRST"
    CONFIGURE_NEW_MODULE = "CONFIGURE_NEW_MODULE"
    NARROW_CUSTOM_EDGE = "NARROW_CUSTOM_EDGE"
    MIGRATE_SYSTEM = "MIGRATE_SYSTEM"
    NO_INTEGRATION_YET = "NO_INTEGRATION_YET"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SkuMapping:
    local_sku: str
    source_system: str
    canonical_matches: tuple[str, ...]
    kind: str
    historical_aliases: tuple[str, ...]

    @property
    def resolved_canonical_sku(self) -> str | None:
        return self.canonical_matches[0] if self.kind == "CLEAN" and len(self.canonical_matches) == 1 else None


@dataclass(frozen=True)
class CompatibilityAssessment:
    area: str
    fit: CompatibilityFit
    rationale: str


@dataclass(frozen=True)
class AcquisitionDecision:
    primary_response: AcquisitionResponse
    rationale: str
    considered_responses: tuple[AcquisitionResponse, ...]


@dataclass(frozen=True)
class AcquiredStoreExperiment:
    raw: dict
    systems: tuple[dict, ...]
    sku_mappings: tuple[SkuMapping, ...]
    compatibility: tuple[CompatibilityAssessment, ...]

    @property
    def store_id(self): return self.raw["store"]["canonical_id"]
    @property
    def store_name(self): return self.raw["store"]["name"]
    @property
    def store_ids(self): return load_store7_experiment().after_store_ids + (self.store_id,)
    @property
    def pos_system(self): return next(x for x in self.systems if x["kind"] == "POS")
    @property
    def inventory_system(self): return next(x for x in self.systems if x["kind"] == "INVENTORY")
    @property
    def structural_reuse_ratio(self): return self.raw["structure"]["reused_items"] / self.raw["structure"]["total_items"]
    @property
    def store7_structural_reuse_ratio(self): return load_store7_experiment().structural_reuse_ratio
    @property
    def fragmentation_reuse_delta(self): return self.store7_structural_reuse_ratio - self.structural_reuse_ratio
    @property
    def technical_gap_new_capability_ratio(self): return self.raw["structure"]["technical_gap_or_new_capability_items"] / self.raw["structure"]["total_items"]
    @property
    def additional_support_surface_items(self): return len(self.raw["support_obligations"])
    def mapping(self, local_sku): return next((x for x in self.sku_mappings if x.local_sku == local_sku), None)
    def count_fit(self, fit): return sum(x.fit is fit for x in self.compatibility)


def recommend_response(experiment: AcquiredStoreExperiment) -> AcquisitionDecision:
    """Apply ordered, inspectable rules; counts are evidence, not a weighted score."""
    process_identity = sum(x.fit in (CompatibilityFit.PROCESS_GAP, CompatibilityFit.REQUIRES_NEW_MAPPING) for x in experiment.compatibility)
    improved = experiment.raw["standardization"]["resolved_mappings"] > 0 and experiment.raw["standardization"]["transfer_manual_after"] < experiment.raw["standardization"]["transfer_manual_before"]
    migration = any(x.fit is CompatibilityFit.MIGRATION_CANDIDATE for x in experiment.compatibility)
    custom = any(x["bounded"] for x in experiment.raw["custom_candidates"])
    module_closes = experiment.raw["module_scenario"]["closes_gap"]
    considered = tuple(r for r, yes in ((AcquisitionResponse.STANDARDIZE_FIRST, process_identity and improved), (AcquisitionResponse.CONFIGURE_NEW_MODULE, module_closes), (AcquisitionResponse.NARROW_CUSTOM_EDGE, custom), (AcquisitionResponse.MIGRATE_SYSTEM, migration)) if yes)
    if process_identity and improved:
        return AcquisitionDecision(AcquisitionResponse.STANDARDIZE_FIRST, "Identity and process gaps measurably improve through bounded current-state standardization; reassess migration, module, and bounded edge evidence afterward.", considered)
    if module_closes: return AcquisitionDecision(AcquisitionResponse.CONFIGURE_NEW_MODULE, "The bounded supported module closes the remaining material gap.", considered)
    if custom: return AcquisitionDecision(AcquisitionResponse.NARROW_CUSTOM_EDGE, "One bounded material technical edge remains after configuration.", considered)
    if migration: return AcquisitionDecision(AcquisitionResponse.MIGRATE_SYSTEM, "Broad duplicated support and low reuse make migration a modeled candidate.", considered)
    if not experiment.raw["question_coverage"]: return AcquisitionDecision(AcquisitionResponse.NO_INTEGRATION_YET, "No demonstrated question value justifies integration yet.", considered)
    return AcquisitionDecision(AcquisitionResponse.UNKNOWN, "Discovery evidence is insufficient.", considered)


def load_acquired_store_experiment(path: Path | str = DATA_PATH) -> AcquiredStoreExperiment:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("store", {}).get("canonical_id") != STORE8_ID: raise AcquisitionValidationError("invalid acquired-store canonical identity")
    if STORE8_ID in load_store7_experiment().after_store_ids: raise AcquisitionValidationError("duplicate acquired-store identity")
    systems = tuple(raw.get("systems", ())); ids = {x.get("id") for x in systems}
    if len(ids) != len(systems) or None in ids: raise AcquisitionValidationError("duplicate or missing source system")
    for system in systems:
        for status in system.get("capabilities", {}).values():
            try: CapabilityStatus(status)
            except ValueError as exc: raise AcquisitionValidationError("invalid capability status") from exc
    mappings = tuple(SkuMapping(x["local_sku"], x["source_system"], tuple(x["canonical_matches"]), x["kind"], tuple(x.get("historical_aliases", ()))) for x in raw.get("sku_mappings", ()))
    if len({x.local_sku for x in mappings}) != len(mappings): raise AcquisitionValidationError("duplicate acquired-store mapping")
    if any(x.source_system not in ids for x in mappings): raise AcquisitionValidationError("invalid local source system reference")
    if any(x.kind == "AMBIGUOUS" and len(x.canonical_matches) < 2 for x in mappings): raise AcquisitionValidationError("ambiguous mapping requires alternatives")
    assessments = tuple(CompatibilityAssessment(a, CompatibilityFit(f), r) for a, f, r in raw.get("compatibility", ()))
    required = {"identity", "reporting", "e-commerce", "purchasing", "returns", "transfers", "automation", "BI", "process", "support"}
    if {x.area for x in assessments} != required: raise AcquisitionValidationError("compatibility dimensions incomplete")
    return AcquiredStoreExperiment(raw, systems, mappings, assessments)


run_acquired_store_experiment = load_acquired_store_experiment
