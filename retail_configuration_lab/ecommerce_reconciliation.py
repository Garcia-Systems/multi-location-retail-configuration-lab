"""Chapter 5's narrow, configuration-driven native connector simulation.

The connector capabilities are MODELED ALTERNATIVE ASSUMPTIONS.  Counts and
classifications produced by this deterministic simulation are OBSERVED LAB
RESULTS; neither is a claim about a commercial product.
"""

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Any

from .capabilities import load_inventory
from .evidence import EvidenceCategory
from .identity import IdentityConfiguration, IdentityType, MappingStatus, load_identity_configuration
from .native_reporting import QuestionResult


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONNECTOR_PATH = ROOT / "config" / "integrations" / "ecommerce_store_native.json"
DEFAULT_ORDERS_PATH = ROOT / "data" / "ecommerce" / "orders.json"


class EcommerceValidationError(ValueError):
    """Raised when connector configuration or synthetic evidence is unsafe."""


class OrderStatus(StrEnum):
    PLACED = "PLACED"
    ALLOCATED = "ALLOCATED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"
    PARTIALLY_RETURNED = "PARTIALLY_RETURNED"


class ReconciliationResult(StrEnum):
    RECONCILED = "RECONCILED"
    PARTIALLY_RECONCILED = "PARTIALLY_RECONCILED"
    EXCEPTION = "EXCEPTION"
    UNRESOLVED_IDENTITY = "UNRESOLVED_IDENTITY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ConnectorConfiguration:
    connector_id: str
    source_system: str
    target_systems: tuple[str, ...]
    enabled: bool
    order_rule: str
    canonical_prefix: str
    store_reference_prefix: str
    channel_source_id: str
    canonical_channel_id: str
    fulfillment_store_mapping: dict[str, str]
    supported_statuses: tuple[OrderStatus, ...]
    cancellation_rule: str
    return_rule: str
    cross_store_return_rule: str
    inventory_effect_rules: dict[str, str]
    synchronization_mode: str
    acknowledgement_rule: str
    evidence_classification: EvidenceCategory

    def canonical_order_id(self, source_order_id: str) -> str:
        prefix = "WEB-"
        if self.order_rule != "PREFIX_NUMERIC_SUFFIX" or not source_order_id.startswith(prefix):
            raise EcommerceValidationError(f"Order ID does not satisfy configured rule: {source_order_id}")
        suffix = source_order_id.removeprefix(prefix)
        if not suffix.isdigit():
            raise EcommerceValidationError(f"Order ID lacks numeric suffix: {source_order_id}")
        return self.canonical_prefix + suffix


@dataclass(frozen=True)
class OrderLine:
    source_sku: str
    sku_system: str
    quantity: int
    marked_resolved: bool


@dataclass(frozen=True)
class OnlineOrder:
    online_order_id: str
    provenance: str
    status: OrderStatus
    channel_source_id: str
    fulfillment_store_source_id: str
    store_reference: str | None
    store_evidence_store_id: str | None
    lines: tuple[OrderLine, ...]
    inventory_effect: int | None
    acknowledgement: str
    cancellation_stage: str | None = None
    reservation_released: bool | None = None
    return_store_source_id: str | None = None


@dataclass(frozen=True)
class OrderReconciliation:
    order: OnlineOrder
    canonical_order_id: str
    canonical_channel_id: str | None
    canonical_store_id: str | None
    canonical_skus: tuple[str, ...]
    expected_inventory_effect: int | None
    result: ReconciliationResult
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class QuestionImpact:
    question_id: str
    status: QuestionResult
    reason: str


@dataclass(frozen=True)
class BeforeMetrics:
    orders_requiring_manual_reconciliation: int
    manual_identity_lookups: int
    records_lacking_direct_order_linkage: int
    apparent_exceptions: int
    true_exceptions: int


@dataclass(frozen=True)
class EcommerceExperimentResult:
    outcomes: tuple[OrderReconciliation, ...]
    before: BeforeMetrics
    question_impacts: tuple[QuestionImpact, ...]

    @property
    def count_by_result(self) -> Counter[ReconciliationResult]:
        return Counter(item.result for item in self.outcomes)

    @property
    def total_orders(self) -> int:
        return len(self.outcomes)

    @property
    def automatically_linked_orders(self) -> int:
        return sum(item.canonical_store_id is not None and bool(item.canonical_skus)
                   for item in self.outcomes)

    @property
    def orders_requiring_manual_reconciliation_after(self) -> int:
        return sum(item.result is not ReconciliationResult.RECONCILED for item in self.outcomes)

    @property
    def manual_reconciliation_reduction_ratio(self) -> float:
        before = self.before.orders_requiring_manual_reconciliation
        return ((before - self.orders_requiring_manual_reconciliation_after) / before
                if before else 0.0)

    @property
    def native_reconciliation_rate(self) -> float:
        evaluable = sum(item.result in {ReconciliationResult.RECONCILED,
                                       ReconciliationResult.PARTIALLY_RECONCILED,
                                       ReconciliationResult.EXCEPTION}
                        for item in self.outcomes)
        return self.count_by_result[ReconciliationResult.RECONCILED] / evaluable if evaluable else 0.0


def _object(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise EcommerceValidationError(f"{key} must be an object")
    return value


def connector_from_dict(raw: dict[str, Any], identity: IdentityConfiguration | None = None) -> ConnectorConfiguration:
    """Validate the connector contract against Chapters 1 and 3."""
    identity = identity or load_identity_configuration()
    systems = {system.identifier for system in load_inventory().systems}
    source, targets = raw.get("source_system"), raw.get("target_systems")
    if source not in systems or not isinstance(targets, list) or not targets or set(targets) - systems:
        raise EcommerceValidationError("Connector references nonexistent systems")
    order_map, channel, sku_dependency = (_object(raw, "order_id_mapping"),
                                           _object(raw, "channel_mapping"),
                                           _object(raw, "sku_identity_dependency"))
    allowed_order_rules = {"PREFIX_NUMERIC_SUFFIX"}
    if order_map.get("rule") not in allowed_order_rules:
        raise EcommerceValidationError("Unsupported connector rule")
    channel_ids = {item.canonical_id for item in identity.identities[IdentityType.CHANNEL]}
    if channel.get("canonical_channel_id") not in channel_ids:
        raise EcommerceValidationError("Connector references invalid canonical channel")
    resolved_channel = identity.resolve(IdentityType.CHANNEL, "RiverCommerce", channel.get("source_identifier", ""))
    if resolved_channel.canonical_id != channel.get("canonical_channel_id"):
        raise EcommerceValidationError("Channel source mapping disagrees with canonical identity")
    stores = {item.canonical_id for item in identity.identities[IdentityType.STORE]}
    fulfillment = _object(raw, "fulfillment_store_mapping")
    if any(store not in stores for store in fulfillment.values()):
        raise EcommerceValidationError("Fulfillment map references nonexistent store")
    if sku_dependency != {"identity_type": "SKU", "require_confirmed_mapping": True}:
        raise EcommerceValidationError("Unsupported SKU identity dependency")
    try:
        statuses = tuple(OrderStatus(value) for value in raw.get("supported_order_statuses", []))
        evidence = EvidenceCategory(raw.get("evidence_classification"))
    except ValueError as exc:
        raise EcommerceValidationError("Invalid connector status or evidence classification") from exc
    if set(statuses) != set(OrderStatus):
        raise EcommerceValidationError("Connector must explicitly configure the supported status vocabulary")
    cancellation, returns, effects = (_object(raw, "cancellation_handling"),
                                      _object(raw, "return_handling"),
                                      _object(raw, "inventory_effect_rules"))
    if cancellation.get("rule") != "NO_EFFECT_OR_RELEASE" or cancellation.get("after_allocation_effect") != "RELEASE_RESERVATION":
        raise EcommerceValidationError("Invalid cancellation rule")
    if returns.get("rule") != "INCREMENT_SELLABLE_AT_ORIGINAL_STORE" or returns.get("cross_store") not in {"PARTIAL", "EXCEPTION"}:
        raise EcommerceValidationError("Invalid return rule")
    supported_effects = {"FULFILLED": "DECREMENT_FULFILLED_QUANTITY", "CANCELLED": "NO_NET_DECREMENT",
                         "RETURNED": "INCREMENT_RETURNED_QUANTITY", "PARTIALLY_RETURNED": "INCREMENT_RETURNED_QUANTITY"}
    if effects != supported_effects:
        raise EcommerceValidationError("Unsupported connector inventory-effect rule")
    if raw.get("synchronization_mode") != "ORDER_EVENTS_TO_STORE_ECOSYSTEM" or raw.get("connector_acknowledgement") != "REQUIRED":
        raise EcommerceValidationError("Unsupported connector rule")
    required_text = (raw.get("connector_id"), order_map.get("canonical_prefix"),
                     order_map.get("store_reference_prefix"))
    if not all(isinstance(value, str) and value for value in required_text) or not isinstance(raw.get("enabled"), bool):
        raise EcommerceValidationError("Connector identity, prefixes, and enabled status are required")
    return ConnectorConfiguration(raw["connector_id"], source, tuple(targets), raw["enabled"],
        order_map["rule"], order_map["canonical_prefix"], order_map["store_reference_prefix"],
        channel["source_identifier"], channel["canonical_channel_id"], dict(fulfillment), statuses,
        cancellation["rule"], returns["rule"], returns["cross_store"], dict(effects),
        raw["synchronization_mode"], raw["connector_acknowledgement"], evidence)


def load_connector_configuration(path: str | Path = DEFAULT_CONNECTOR_PATH) -> ConnectorConfiguration:
    with Path(path).open(encoding="utf-8") as source:
        return connector_from_dict(json.load(source))


def orders_from_dict(raw: dict[str, Any], connector: ConnectorConfiguration,
                     identity: IdentityConfiguration | None = None) -> tuple[OnlineOrder, ...]:
    identity = identity or load_identity_configuration()
    rows = raw.get("orders")
    if not isinstance(rows, list):
        raise EcommerceValidationError("orders must be a list")
    orders: list[OnlineOrder] = []
    seen: set[str] = set()
    valid_skus = {item.canonical_id for item in identity.identities[IdentityType.SKU]}
    for row in rows:
        order_id = row.get("online_order_id")
        if not isinstance(order_id, str) or order_id in seen:
            raise EcommerceValidationError("Missing or duplicate online order ID")
        seen.add(order_id); connector.canonical_order_id(order_id)
        if not isinstance(row.get("provenance"), str) or not row["provenance"].strip():
            raise EcommerceValidationError(f"{order_id}: missing order provenance")
        try:
            status = OrderStatus(row.get("status"))
        except ValueError as exc:
            raise EcommerceValidationError(f"{order_id}: invalid order status") from exc
        if status not in connector.supported_statuses:
            raise EcommerceValidationError(f"{order_id}: unsupported order status")
        lines: list[OrderLine] = []
        for line in row.get("lines", []):
            quantity = line.get("quantity")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
                raise EcommerceValidationError(f"{order_id}: impossible line quantity")
            resolved = line.get("resolved")
            resolution = identity.resolve(IdentityType.SKU, line.get("sku_system", ""), line.get("source_sku", ""))
            if resolved is True and (resolution.status is not MappingStatus.CONFIRMED or resolution.canonical_id not in valid_skus):
                raise EcommerceValidationError(f"{order_id}: resolved line references invalid SKU")
            lines.append(OrderLine(line.get("source_sku", ""), line.get("sku_system", ""), quantity, resolved is True))
        if not lines:
            raise EcommerceValidationError(f"{order_id}: order requires lines")
        effect = row.get("inventory_effect")
        if effect is not None and (isinstance(effect, bool) or not isinstance(effect, int) or abs(effect) > sum(x.quantity for x in lines)):
            raise EcommerceValidationError(f"{order_id}: inventory effect has impossible quantity")
        orders.append(OnlineOrder(order_id, row["provenance"], status, row.get("channel_source_id", ""),
            row.get("fulfillment_store_source_id", ""), row.get("store_reference"),
            row.get("store_evidence_store_id"), tuple(lines), effect, row.get("acknowledgement", ""),
            row.get("cancellation_stage"), row.get("reservation_released"), row.get("return_store_source_id")))
    return tuple(orders)


def load_orders(path: str | Path = DEFAULT_ORDERS_PATH,
                connector: ConnectorConfiguration | None = None) -> tuple[OnlineOrder, ...]:
    connector = connector or load_connector_configuration()
    with Path(path).open(encoding="utf-8") as source:
        return orders_from_dict(json.load(source), connector)


def reconcile_order(order: OnlineOrder, connector: ConnectorConfiguration,
                    identity: IdentityConfiguration | None = None) -> OrderReconciliation:
    identity = identity or load_identity_configuration()
    canonical_order = connector.canonical_order_id(order.online_order_id)
    channel = identity.resolve(IdentityType.CHANNEL, "RiverCommerce", order.channel_source_id)
    canonical_store = connector.fulfillment_store_mapping.get(order.fulfillment_store_source_id)
    sku_resolutions = [identity.resolve(IdentityType.SKU, line.sku_system, line.source_sku) for line in order.lines]
    canonical_skus = tuple(item.canonical_id for item in sku_resolutions if item.status is MappingStatus.CONFIRMED and item.canonical_id)
    identity_reasons: list[str] = []
    if channel.status is not MappingStatus.CONFIRMED or channel.canonical_id != connector.canonical_channel_id:
        identity_reasons.append("channel identity is unresolved")
    if canonical_store is None:
        identity_reasons.append("fulfillment-store identity is unresolved; no geography inference was used")
    if len(canonical_skus) != len(order.lines):
        identity_reasons.append("one or more SKU identities are unknown or ambiguous")
    quantity = sum(line.quantity for line in order.lines)
    expected: int | None
    if order.status is OrderStatus.FULFILLED:
        expected = -quantity
    elif order.status is OrderStatus.CANCELLED:
        expected = 0
    elif order.status in {OrderStatus.RETURNED, OrderStatus.PARTIALLY_RETURNED}:
        expected = quantity
    else:
        expected = None
    if identity_reasons:
        result, reasons = ReconciliationResult.UNRESOLVED_IDENTITY, identity_reasons
    elif expected is None or order.inventory_effect is None or not order.store_evidence_store_id:
        result, reasons = ReconciliationResult.UNKNOWN, ["modeled evidence is insufficient to compare inventory"]
    else:
        reasons = []
        if order.store_evidence_store_id != canonical_store:
            reasons.append("store evidence disagrees with configured fulfillment store")
        if order.inventory_effect != expected:
            reasons.append("observed inventory quantity disagrees with configured effect")
        if order.status is OrderStatus.CANCELLED and order.cancellation_stage == "AFTER_ALLOCATION" and order.reservation_released is not True:
            reasons.append("allocated inventory reservation was not released")
        cross_store = (order.status in {OrderStatus.RETURNED, OrderStatus.PARTIALLY_RETURNED}
                       and order.return_store_source_id != order.fulfillment_store_source_id)
        if cross_store:
            result = (ReconciliationResult.PARTIALLY_RECONCILED
                      if connector.cross_store_return_rule == "PARTIAL" and not reasons
                      else ReconciliationResult.EXCEPTION)
            reasons.append("cross-store return coverage is incomplete")
        elif reasons:
            result = ReconciliationResult.EXCEPTION
        elif order.acknowledgement != "ACKNOWLEDGED":
            result, reasons = ReconciliationResult.EXCEPTION, ["connector acknowledgement was not successful"]
        else:
            result = ReconciliationResult.RECONCILED
    return OrderReconciliation(order, canonical_order, channel.canonical_id, canonical_store,
                               canonical_skus, expected, result, tuple(reasons))


QUESTION_IMPACTS = (
    QuestionImpact("SAL-02", QuestionResult.ANSWERED, "Online channel remains canonical and distinct from fulfillment location; Chapter 4 does not regress."),
    QuestionImpact("ECOM-01", QuestionResult.ANSWERED, "Configured linkage identifies both reconciled and identity-blocked fulfillment records."),
    QuestionImpact("ECOM-02", QuestionResult.PARTIALLY_ANSWERED, "Cancellation effects reconcile, but cross-store return coverage remains incomplete."),
    QuestionImpact("RET-01", QuestionResult.PARTIALLY_ANSWERED, "Online transaction and inventory evidence link; accounting and broader return coverage remain outside Chapter 5."),
)


def run_ecommerce_reconciliation(connector: ConnectorConfiguration | None = None,
                                 orders: tuple[OnlineOrder, ...] | None = None) -> EcommerceExperimentResult:
    connector = connector or load_connector_configuration()
    orders = orders or load_orders(connector=connector)
    outcomes = tuple(reconcile_order(order, connector) for order in orders)
    true_exceptions = sum(item.result is ReconciliationResult.EXCEPTION for item in outcomes)
    before = BeforeMetrics(len(orders), len(orders), len(orders),
                           sum(item.result is not ReconciliationResult.RECONCILED for item in outcomes),
                           true_exceptions)
    return EcommerceExperimentResult(outcomes, before, QUESTION_IMPACTS)
