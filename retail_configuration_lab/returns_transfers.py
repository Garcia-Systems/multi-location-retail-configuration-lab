"""Chapter 7 configuration-driven return and transfer reconciliation."""

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
import re
from typing import Any

from .identity import IdentityType, load_identity_configuration
from .native_reporting import QuestionResult

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "returns_transfers"
DATA = ROOT / "data" / "returns_transfers" / "records.json"


class ReturnsTransfersValidationError(ValueError):
    """The fixture is malformed, rather than valid incomplete operating evidence."""


class ReturnStatus(StrEnum):
    INITIATED = "INITIATED"
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class TransferStatus(StrEnum):
    CREATED = "CREATED"
    SENT = "SENT"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class ReturnResult(StrEnum):
    RECONCILED = "RECONCILED"
    CROSS_STORE_RECONCILED = "CROSS_STORE_RECONCILED"
    MISSING_ORIGINAL_REFERENCE = "MISSING_ORIGINAL_REFERENCE"
    UNRESOLVED_IDENTITY = "UNRESOLVED_IDENTITY"
    MISSING_REASON = "MISSING_REASON"
    INVENTORY_EFFECT_EXCEPTION = "INVENTORY_EFFECT_EXCEPTION"
    PARTIALLY_RECONCILED = "PARTIALLY_RECONCILED"
    UNKNOWN = "UNKNOWN"


class TransferResult(StrEnum):
    RECONCILED = "RECONCILED"
    MISSING_RECEIPT = "MISSING_RECEIPT"
    PARTIAL_RECEIPT = "PARTIAL_RECEIPT"
    OVER_RECEIPT = "OVER_RECEIPT"
    LOCATION_EXCEPTION = "LOCATION_EXCEPTION"
    CANCELLED_TRANSFER_MOVEMENT = "CANCELLED_TRANSFER_MOVEMENT"
    UNRESOLVED_IDENTITY = "UNRESOLVED_IDENTITY"
    INVENTORY_EFFECT_EXCEPTION = "INVENTORY_EFFECT_EXCEPTION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ReturnsTransfersConfiguration:
    return_rules: dict[str, Any]
    transfer_rules: dict[str, Any]


@dataclass(frozen=True)
class ReturnRecord:
    return_id: str; source_system: str; original_reference: str | None
    original_channel: str; return_channel: str; original_sale_store: str | None
    return_store: str; canonical_sku: str | None; quantity: int; reason: str | None
    status: ReturnStatus; inventory_effect: int; provenance: str


@dataclass(frozen=True)
class TransferRecord:
    transfer_id: str; source_system: str; sending_store: str; receiving_store: str
    expected_receiving_store: str; canonical_sku: str | None
    quantity_sent: int; quantity_received: int; sent_status: bool
    sent_timestamp: str | None; received_status: bool; received_timestamp: str | None
    status: TransferStatus; sender_inventory_effect: int
    receiver_inventory_effect: int; provenance: str


@dataclass(frozen=True)
class ReturnOutcome:
    record: ReturnRecord; result: ReturnResult; expected_inventory_effect: int
    accounting_evidence: bool = False


@dataclass(frozen=True)
class TransferOutcome:
    record: TransferRecord; result: TransferResult


@dataclass(frozen=True)
class QuestionImpact:
    question_id: str; status: QuestionResult; reason: str


@dataclass(frozen=True)
class ReturnsTransfersExperiment:
    return_outcomes: tuple[ReturnOutcome, ...]
    transfer_outcomes: tuple[TransferOutcome, ...]
    before: dict[str, int]
    question_impacts: tuple[QuestionImpact, ...]

    @property
    def return_counts(self): return Counter(x.result for x in self.return_outcomes)
    @property
    def transfer_counts(self): return Counter(x.result for x in self.transfer_outcomes)
    @property
    def total_returns(self): return len(self.return_outcomes)
    @property
    def total_transfers(self): return len(self.transfer_outcomes)
    @property
    def reconciled_returns(self):
        return self.return_counts[ReturnResult.RECONCILED] + self.return_counts[ReturnResult.CROSS_STORE_RECONCILED]
    @property
    def reconciled_transfers(self): return self.transfer_counts[TransferResult.RECONCILED]
    @property
    def manual_reviews_after(self):
        return self.total_returns + self.total_transfers - self.reconciled_returns - self.reconciled_transfers
    @property
    def return_reconciliation_rate(self):
        """Fully reconciled returns divided by all structurally valid return fixtures."""
        return self.reconciled_returns / self.total_returns if self.total_returns else 0.0
    @property
    def transfer_reconciliation_rate(self):
        """Fully reconciled transfers divided by all structurally valid transfer fixtures."""
        return self.reconciled_transfers / self.total_transfers if self.total_transfers else 0.0
    @property
    def manual_return_transfer_review_reduction_ratio(self):
        before = self.before["manual_return_transfer_reviews"]
        return (before - self.manual_reviews_after) / before if before else 0.0


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def load_returns_transfers_configuration(directory: Path = CONFIG) -> ReturnsTransfersConfiguration:
    returns = _load(directory / "return_rules.json")
    transfers = _load(directory / "transfer_rules.json")
    if set(returns.get("valid_statuses", ())) != {x.value for x in ReturnStatus}:
        raise ReturnsTransfersValidationError("invalid return status configuration")
    if not returns.get("valid_reasons") or not set(returns.get("reason_required_for_statuses", ())) <= set(returns["valid_statuses"]):
        raise ReturnsTransfersValidationError("invalid return reason configuration")
    if set(transfers.get("valid_statuses", ())) != {x.value for x in TransferStatus}:
        raise ReturnsTransfersValidationError("invalid transfer status configuration")
    if transfers.get("inventory_effect_at_send") != "NEGATIVE_SENT_QUANTITY" or transfers.get("inventory_effect_at_receipt") != "POSITIVE_RECEIVED_QUANTITY":
        raise ReturnsTransfersValidationError("impossible configured inventory effect")
    return ReturnsTransfersConfiguration(returns, transfers)


def load_returns_transfers_records(path: Path = DATA, configuration: ReturnsTransfersConfiguration | None = None):
    config = configuration or load_returns_transfers_configuration()
    raw = _load(path)
    identity = load_identity_configuration()
    stores = {x.canonical_id for x in identity.identities[IdentityType.STORE]}
    skus = {x.canonical_id for x in identity.identities[IdentityType.SKU]}
    returns, return_ids = [], set()
    for row in raw.get("returns", ()):
        if row.get("return_id") in return_ids: raise ReturnsTransfersValidationError("duplicate return ID")
        return_ids.add(row.get("return_id"))
        try: status = ReturnStatus(row.get("status"))
        except ValueError as exc: raise ReturnsTransfersValidationError("invalid return status") from exc
        reason = row.get("reason")
        if reason is not None and reason not in config.return_rules["valid_reasons"]: raise ReturnsTransfersValidationError("invalid return reason")
        if not isinstance(row.get("quantity"), int) or row["quantity"] < 0: raise ReturnsTransfersValidationError("negative or invalid return quantity")
        if row.get("return_store") not in stores or (row.get("original_sale_store") is not None and row["original_sale_store"] not in stores): raise ReturnsTransfersValidationError("return references nonexistent store")
        if row.get("canonical_sku") is not None and row["canonical_sku"] not in skus: raise ReturnsTransfersValidationError("resolved return SKU references nonexistent canonical SKU")
        reference = row.get("original_reference")
        if reference is not None and not re.fullmatch(r"(?:POS|ORD)-\d+", reference): raise ReturnsTransfersValidationError("malformed original transaction reference")
        if not row.get("provenance"): raise ReturnsTransfersValidationError("missing return provenance")
        returns.append(ReturnRecord(row["return_id"], row["source_system"], reference, row["original_channel"], row["return_channel"], row.get("original_sale_store"), row["return_store"], row.get("canonical_sku"), row["quantity"], reason, status, row["inventory_effect"], row["provenance"]))
    transfers, transfer_ids = [], set()
    for row in raw.get("transfers", ()):
        if row.get("transfer_id") in transfer_ids: raise ReturnsTransfersValidationError("duplicate transfer ID")
        transfer_ids.add(row.get("transfer_id"))
        if row.get("sending_store") == row.get("receiving_store"): raise ReturnsTransfersValidationError("transfer locations must differ")
        if not {row.get("sending_store"), row.get("receiving_store"), row.get("expected_receiving_store")} <= stores: raise ReturnsTransfersValidationError("transfer references nonexistent store")
        try: status = TransferStatus(row.get("status"))
        except ValueError as exc: raise ReturnsTransfersValidationError("invalid transfer status") from exc
        if any(not isinstance(row.get(name), int) or row[name] < 0 for name in ("quantity_sent", "quantity_received")): raise ReturnsTransfersValidationError("negative or invalid transfer quantity")
        if row.get("canonical_sku") is not None and row["canonical_sku"] not in skus: raise ReturnsTransfersValidationError("resolved transfer SKU references nonexistent canonical SKU")
        if not row.get("provenance"): raise ReturnsTransfersValidationError("missing transfer provenance")
        if row.get("sender_inventory_effect", 1) > 0 or row.get("receiver_inventory_effect", -1) < 0: raise ReturnsTransfersValidationError("impossible transfer inventory effect")
        transfers.append(TransferRecord(row["transfer_id"], row["source_system"], row["sending_store"], row["receiving_store"], row["expected_receiving_store"], row.get("canonical_sku"), row["quantity_sent"], row["quantity_received"], row["sent_status"], row.get("sent_timestamp"), row["received_status"], row.get("received_timestamp"), status, row["sender_inventory_effect"], row["receiver_inventory_effect"], row["provenance"]))
    return tuple(returns), tuple(transfers), raw["before"]


def run_returns_transfers_experiment(configuration: ReturnsTransfersConfiguration | None = None, path: Path = DATA):
    config = configuration or load_returns_transfers_configuration()
    returns, transfers, before = load_returns_transfers_records(path, config)
    return_outcomes = []
    for record in returns:
        expected = 0 if record.reason in config.return_rules["non_restockable_reasons"] else record.quantity
        if record.canonical_sku is None: result = ReturnResult.UNRESOLVED_IDENTITY
        elif record.original_reference is None: result = ReturnResult.MISSING_ORIGINAL_REFERENCE
        elif record.status.value in config.return_rules["reason_required_for_statuses"] and record.reason is None: result = ReturnResult.MISSING_REASON
        elif record.inventory_effect != expected: result = ReturnResult.INVENTORY_EFFECT_EXCEPTION
        elif record.status is not ReturnStatus.COMPLETED: result = ReturnResult.PARTIALLY_RECONCILED if record.status is not ReturnStatus.UNKNOWN else ReturnResult.UNKNOWN
        elif record.original_sale_store is not None and record.original_sale_store != record.return_store: result = ReturnResult.CROSS_STORE_RECONCILED
        else: result = ReturnResult.RECONCILED
        return_outcomes.append(ReturnOutcome(record, result, expected))
    transfer_outcomes = []
    for record in transfers:
        if record.canonical_sku is None: result = TransferResult.UNRESOLVED_IDENTITY
        elif record.status is TransferStatus.CANCELLED and (record.sender_inventory_effect or record.receiver_inventory_effect): result = TransferResult.CANCELLED_TRANSFER_MOVEMENT
        elif record.receiving_store != record.expected_receiving_store: result = TransferResult.LOCATION_EXCEPTION
        elif not record.received_status or record.quantity_received == 0: result = TransferResult.MISSING_RECEIPT
        elif record.quantity_received < record.quantity_sent: result = TransferResult.PARTIAL_RECEIPT
        elif record.quantity_received > record.quantity_sent: result = TransferResult.OVER_RECEIPT
        elif record.sender_inventory_effect != -record.quantity_sent or record.receiver_inventory_effect != record.quantity_received: result = TransferResult.INVENTORY_EFFECT_EXCEPTION
        elif record.status is TransferStatus.UNKNOWN: result = TransferResult.UNKNOWN
        else: result = TransferResult.RECONCILED
        transfer_outcomes.append(TransferOutcome(record, result))
    impacts = (
        QuestionImpact("TRN-01", QuestionResult.ANSWERED, "Separate sent and receipt evidence identifies missing receipts."),
        QuestionImpact("TRN-02", QuestionResult.ANSWERED, "Sent and received quantities classify partial and over-receipts."),
        QuestionImpact("RET-01", QuestionResult.PARTIALLY_ANSWERED, "Transaction and inventory evidence is classified; accounting remains outside scope."),
        QuestionImpact("RET-02", QuestionResult.ANSWERED, "Configured reason requirements expose missing reason data."),
        QuestionImpact("INV-02", QuestionResult.PARTIALLY_ANSWERED, "Return and transfer effects are visible, without general adjustment controls."),
        QuestionImpact("FIN-01", QuestionResult.NOT_ANSWERED, "No accounting evidence is created by this experiment."),
    )
    return ReturnsTransfersExperiment(tuple(return_outcomes), tuple(transfer_outcomes), before, impacts)
