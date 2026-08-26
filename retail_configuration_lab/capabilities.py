"""Load, validate, and count the fictional Chapter 1 capability inventory."""

from collections import Counter
from dataclasses import dataclass
import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from .evidence import EvidenceCategory
from .models import CapabilityStatus

DEFAULT_INVENTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "capability_inventory.json"


class CapabilityInventoryError(ValueError):
    """Raised when the inventory is structurally or semantically invalid."""


@dataclass(frozen=True)
class System:
    identifier: str
    name: str
    category: str
    authoritative_responsibility: str
    major_capabilities: tuple[str, ...]
    known_limitations: tuple[str, ...]
    evidence_category: EvidenceCategory


@dataclass(frozen=True)
class Capability:
    identifier: str
    business_area: str
    name: str


@dataclass(frozen=True)
class CapabilityAssessment:
    capability: Capability
    primary_system: str
    status: CapabilityStatus
    rationale: str
    evidence_category: EvidenceCategory
    dependency: str | None = None
    discovery_note: str | None = None


@dataclass(frozen=True)
class CapabilityInventory:
    customer_name: str
    systems: tuple[System, ...]
    assessments: tuple[CapabilityAssessment, ...]


@dataclass(frozen=True)
class CapabilityAnalysis:
    total_capabilities: int
    count_by_status: dict[CapabilityStatus, int]
    count_by_business_area: dict[str, int]
    explicit_unknowns: int
    explicit_gaps: int
    potentially_addressable_without_custom_software: int


def _text(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CapabilityInventoryError(f"{context}: missing or empty {key}")
    return value.strip()


def _string_list(data: dict[str, Any], key: str, context: str) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        raise CapabilityInventoryError(f"{context}: {key} must be a nonempty list of strings")
    return tuple(item.strip() for item in value)


def _evidence(data: dict[str, Any], context: str) -> EvidenceCategory:
    raw = _text(data, "evidence_category", context)
    try:
        return EvidenceCategory(raw)
    except ValueError as exc:
        raise CapabilityInventoryError(f"{context}: invalid evidence category {raw}") from exc


def inventory_from_dict(data: dict[str, Any]) -> CapabilityInventory:
    """Validate raw structured inventory data and construct immutable models."""
    if not isinstance(data, dict):
        raise CapabilityInventoryError("Inventory root must be an object")
    raw_systems = data.get("systems")
    raw_assessments = data.get("capability_assessments")
    if not isinstance(raw_systems, list) or not isinstance(raw_assessments, list):
        raise CapabilityInventoryError("systems and capability_assessments must be lists")

    systems: list[System] = []
    system_ids: set[str] = set()
    for raw in raw_systems:
        if not isinstance(raw, dict):
            raise CapabilityInventoryError("system records must be objects")
        identifier = _text(raw, "id", "system")
        if identifier in system_ids:
            raise CapabilityInventoryError(f"duplicate system identifier: {identifier}")
        system_ids.add(identifier)
        systems.append(System(identifier, _text(raw, "name", identifier),
                              _text(raw, "category", identifier),
                              _text(raw, "authoritative_responsibility", identifier),
                              _string_list(raw, "major_capabilities", identifier),
                              _string_list(raw, "known_limitations", identifier),
                              _evidence(raw, identifier)))

    assessments: list[CapabilityAssessment] = []
    capability_ids: set[str] = set()
    for raw in raw_assessments:
        if not isinstance(raw, dict):
            raise CapabilityInventoryError("capability assessments must be objects")
        identifier = _text(raw, "capability_id", "capability")
        if identifier in capability_ids:
            raise CapabilityInventoryError(f"duplicate capability identifier: {identifier}")
        capability_ids.add(identifier)
        primary_system = _text(raw, "primary_system", identifier)
        if primary_system not in system_ids:
            raise CapabilityInventoryError(
                f"{identifier}: nonexistent primary system {primary_system}"
            )
        raw_status = _text(raw, "status", identifier)
        try:
            status = CapabilityStatus(raw_status)
        except ValueError as exc:
            raise CapabilityInventoryError(f"{identifier}: invalid capability status {raw_status}") from exc
        dependency = raw.get("dependency")
        discovery_note = raw.get("discovery_note")
        if status in (CapabilityStatus.SUPPORTED_WITH_CONFIGURATION,
                      CapabilityStatus.SUPPORTED_WITH_NATIVE_INTEGRATION):
            if not isinstance(dependency, str) or not dependency.strip():
                raise CapabilityInventoryError(f"{identifier}: {status.value} requires a dependency")
        if status is CapabilityStatus.UNKNOWN:
            if not isinstance(discovery_note, str) or not discovery_note.strip():
                raise CapabilityInventoryError(f"{identifier}: UNKNOWN requires a discovery note")
        capability = Capability(identifier, _text(raw, "business_area", identifier),
                                _text(raw, "name", identifier))
        assessments.append(CapabilityAssessment(
            capability, primary_system, status, _text(raw, "rationale", identifier),
            _evidence(raw, identifier), dependency.strip() if isinstance(dependency, str) else None,
            discovery_note.strip() if isinstance(discovery_note, str) else None,
        ))
    return CapabilityInventory(_text(data, "customer_name", "inventory"),
                               tuple(systems), tuple(assessments))


def load_inventory(path: str | Path = DEFAULT_INVENTORY_PATH) -> CapabilityInventory:
    try:
        with Path(path).open(encoding="utf-8") as source:
            raw = json.load(source)
    except (OSError, JSONDecodeError) as exc:
        raise CapabilityInventoryError(f"Could not load capability inventory {path}: {exc}") from exc
    return inventory_from_dict(raw)


NON_CUSTOM_PATH_STATUSES = frozenset({
    CapabilityStatus.SUPPORTED,
    CapabilityStatus.SUPPORTED_WITH_CONFIGURATION,
    CapabilityStatus.SUPPORTED_WITH_NATIVE_INTEGRATION,
    CapabilityStatus.EXPORT_ONLY,
    CapabilityStatus.AUTOMATION_POSSIBLE,
})


def analyze_inventory(inventory: CapabilityInventory) -> CapabilityAnalysis:
    statuses = Counter(item.status for item in inventory.assessments)
    areas = Counter(item.capability.business_area for item in inventory.assessments)
    return CapabilityAnalysis(
        len(inventory.assessments),
        {status: statuses[status] for status in CapabilityStatus},
        dict(sorted(areas.items())),
        statuses[CapabilityStatus.UNKNOWN], statuses[CapabilityStatus.GAP],
        sum(statuses[status] for status in NON_CUSTOM_PATH_STATUSES),
    )
