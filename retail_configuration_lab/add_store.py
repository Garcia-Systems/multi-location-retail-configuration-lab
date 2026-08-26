"""Chapter 13: a bounded, deterministic standardized-store onboarding experiment."""

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path

from .evidence import EvidenceCategory
from .identity import IdentityType, load_identity_configuration

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "store7_onboarding.json"
STORE7_ID = "JRO-STORE-007"


class OnboardingValidationError(ValueError):
    """Raised when onboarding configuration is unsafe or internally inconsistent."""


class TaskClassification(StrEnum):
    REUSED_UNCHANGED = "REUSED_UNCHANGED"
    REUSED_WITH_STORE_CONFIGURATION = "REUSED_WITH_STORE_CONFIGURATION"
    NEW_MAPPING = "NEW_MAPPING"
    NEW_CONFIGURATION = "NEW_CONFIGURATION"
    NEW_CAPABILITY_REQUIRED = "NEW_CAPABILITY_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OnboardingTask:
    task_id: str
    category: str
    description: str
    required: bool
    configuration_artifact: str
    classification: TaskClassification
    reused_unchanged: bool
    configured_from_template: bool
    new_store_specific_value: bool
    validation_result: str
    dependency: str
    support_implication: str
    evidence_classification: EvidenceCategory


@dataclass(frozen=True)
class Store7Experiment:
    before_store_ids: tuple[str, ...]
    after_store_ids: tuple[str, ...]
    source_mappings: dict[str, str]
    store_groups: dict[str, tuple[str, ...]]
    assortment: tuple[str, ...]
    excluded_skus: tuple[str, ...]
    tasks: tuple[OnboardingTask, ...]
    transactions: tuple[dict, ...]
    growth: dict[str, tuple[int, int]]
    issue_trace: dict[str, str]

    @property
    def applicable_tasks(self) -> tuple[OnboardingTask, ...]:
        return tuple(t for t in self.tasks if t.required and t.classification is not TaskClassification.NOT_APPLICABLE)

    def count(self, classification: TaskClassification) -> int:
        return sum(t.classification is classification for t in self.applicable_tasks)

    @property
    def total_onboarding_tasks(self) -> int:
        return len(self.applicable_tasks)

    @property
    def structural_reuse_ratio(self) -> float:
        denominator = self.total_onboarding_tasks
        reused = self.count(TaskClassification.REUSED_UNCHANGED) + self.count(TaskClassification.REUSED_WITH_STORE_CONFIGURATION)
        return reused / denominator if denominator else 0.0

    @property
    def new_capability_ratio(self) -> float:
        return self.count(TaskClassification.NEW_CAPABILITY_REQUIRED) / self.total_onboarding_tasks if self.total_onboarding_tasks else 0.0


def load_store7_experiment(path: Path | str = DATA_PATH) -> Store7Experiment:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    identity = load_identity_configuration()
    before = tuple(x.canonical_id for x in identity.identities[IdentityType.STORE])
    store = raw.get("store", {})
    if store.get("canonical_id") in before:
        raise OnboardingValidationError("duplicate canonical Store #7 ID")
    if store.get("canonical_id") != STORE7_ID:
        raise OnboardingValidationError("Store #7 canonical identity must exist before it is referenced")
    after = before + (STORE7_ID,)
    if len(after) != len(set(after)) or len(after) != 7:
        raise OnboardingValidationError("Store #7 added multiple times or hard-coded six-store invariant")

    mappings = store.get("source_mappings", {})
    existing_keys = {(m.source_system, m.source_identifier) for m in identity.mappings if m.identity_type is IdentityType.STORE}
    if not mappings or any((system, source) in existing_keys for system, source in mappings.items()):
        raise OnboardingValidationError("duplicate source store mapping")
    groups = {k: tuple(v) for k, v in raw.get("store_groups", {}).items()}
    if ("ALL_STORES" not in groups or tuple(groups["ALL_STORES"]) != after
            or len(groups["ALL_STORES"]) != len(set(groups["ALL_STORES"]))):
        raise OnboardingValidationError("invalid store group membership")
    if any(member not in after for members in groups.values() for member in members):
        raise OnboardingValidationError("store group references nonexistent identity")

    sku_ids = {x.canonical_id for x in identity.identities[IdentityType.SKU]}
    assortment = tuple(raw.get("assortment", {}).get("carried_skus", []))
    excluded = tuple(raw.get("assortment", {}).get("excluded_skus", []))
    if not assortment or not excluded or (set(assortment) | set(excluded)) - sku_ids:
        raise OnboardingValidationError("Store #7 transaction or assortment references nonexistent SKU")
    if set(assortment) & set(excluded):
        raise OnboardingValidationError("SKU cannot be both carried and excluded")
    if raw.get("fulfillment_store") != STORE7_ID:
        raise OnboardingValidationError("invalid fulfillment-store configuration")
    if raw.get("purchasing_destination") != STORE7_ID:
        raise OnboardingValidationError("invalid purchasing destination")
    if not raw.get("process_owner"):
        raise OnboardingValidationError("missing required process ownership")

    artifacts = set(raw.get("configuration_artifacts", []))
    tasks = []
    for row in raw.get("tasks", []):
        try:
            classification = TaskClassification(row["classification"])
            evidence = EvidenceCategory(row["evidence_classification"])
        except (KeyError, ValueError) as exc:
            raise OnboardingValidationError("invalid task classification or evidence") from exc
        if row.get("configuration_artifact") not in artifacts:
            raise OnboardingValidationError("onboarding task references nonexistent configuration artifact")
        tasks.append(OnboardingTask(
            row["task_id"], row["category"], row["description"], row["required"],
            row["configuration_artifact"], classification, row["reused_unchanged"],
            row["configured_from_template"], row["new_store_specific_value"],
            row["validation_result"], row["dependency"], row["support_implication"], evidence,
        ))
    if len({t.task_id for t in tasks}) != len(tasks):
        raise OnboardingValidationError("duplicate onboarding task ID")

    transactions = tuple(raw.get("transactions", []))
    for tx in transactions:
        if tx.get("sku") not in sku_ids:
            raise OnboardingValidationError("Store #7 transaction references nonexistent SKU")
        if tx.get("kind") == "TRANSFER" and tx.get("from_store") == tx.get("to_store"):
            raise OnboardingValidationError("transfer cannot use the same sending and receiving store")
    growth = {key: tuple(value) for key, value in raw["growth"].items()}
    return Store7Experiment(before, after, mappings, groups, assortment, excluded, tuple(tasks), transactions, growth, raw["issue_trace"])
