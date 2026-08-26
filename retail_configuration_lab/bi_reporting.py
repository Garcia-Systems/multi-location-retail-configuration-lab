"""Chapter 9: configured RiverBI views over existing synthetic evidence.

Reconciliation remains owned by Chapters 5–7.  This module only projects and
filters their immutable outcomes; it neither repairs nor writes evidence.
"""

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import json
from pathlib import Path
from typing import Any

from .ecommerce_reconciliation import ReconciliationResult, run_ecommerce_reconciliation
from .models import FreshnessRequirement
from .native_reporting import run_native_reporting
from .purchasing import PurchasingResult, run_purchasing_experiment
from .returns_transfers import ReturnResult, TransferResult, run_returns_transfers_experiment

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIRECTORY = ROOT / "config" / "bi"


class BIValidationError(ValueError):
    pass


class BIQuestionStatus(StrEnum):
    ANSWERED = "ANSWERED"
    PARTIALLY_ANSWERED = "PARTIALLY_ANSWERED"
    NOT_ANSWERED = "NOT_ANSWERED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class BIDataset:
    dataset_id: str
    sources: tuple[str, ...]
    fields: tuple[str, ...]
    canonical_dimensions: tuple[str, ...]
    relationships: tuple[str, ...]


@dataclass(frozen=True)
class BIReport:
    report_id: str
    dataset_id: str
    columns: tuple[str, ...]
    group_by: tuple[str, ...]
    freshness: FreshnessRequirement
    question_ids: tuple[str, ...]
    sections: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoverageTransition:
    question_id: str
    question: str
    before: BIQuestionStatus
    after: BIQuestionStatus


@dataclass(frozen=True)
class BIConfiguration:
    platform: str
    datasets: tuple[BIDataset, ...]
    metrics: tuple[dict[str, Any], ...]
    exception_views: tuple[dict[str, Any], ...]
    reports: tuple[BIReport, ...]
    coverage: tuple[CoverageTransition, ...]
    manual_steps_before: tuple[str, ...]
    manual_steps_after: tuple[str, ...]


@dataclass(frozen=True)
class BIReportingResult:
    configuration: BIConfiguration
    reports: dict[str, tuple[dict[str, Any], ...]]
    question_transitions: tuple[CoverageTransition, ...]
    management_briefing: tuple[dict[str, Any], ...]

    @property
    def configured_datasets_views(self) -> int:
        return len(self.configuration.datasets) + len(self.configuration.exception_views)

    @property
    def count_before(self) -> dict[BIQuestionStatus, int]:
        counts = Counter(x.before for x in self.question_transitions)
        return {status: counts[status] for status in BIQuestionStatus}

    @property
    def count_after(self) -> dict[BIQuestionStatus, int]:
        counts = Counter(x.after for x in self.question_transitions)
        return {status: counts[status] for status in BIQuestionStatus}

    @property
    def questions_improved_by_bi(self) -> tuple[str, ...]:
        rank = {BIQuestionStatus.UNKNOWN: 0, BIQuestionStatus.NOT_ANSWERED: 1,
                BIQuestionStatus.PARTIALLY_ANSWERED: 2, BIQuestionStatus.ANSWERED: 3}
        return tuple(x.question_id for x in self.question_transitions if rank[x.after] > rank[x.before])

    @property
    def bi_question_answer_rate(self) -> float:
        return self.count_after[BIQuestionStatus.ANSWERED] / len(self.question_transitions) if self.question_transitions else 0.0

    @property
    def bi_incremental_question_gain(self) -> int:
        return self.count_after[BIQuestionStatus.ANSWERED] - self.count_before[BIQuestionStatus.ANSWERED]

    @property
    def manual_reporting_steps_before(self) -> int:
        return len(self.configuration.manual_steps_before)

    @property
    def manual_reporting_steps_after(self) -> int:
        return len(self.configuration.manual_steps_after)

    @property
    def manual_reporting_step_reduction_ratio(self) -> float:
        before = self.manual_reporting_steps_before
        return (before - self.manual_reporting_steps_after) / before if before else 0.0

    @property
    def exception_records_surfaced(self) -> int:
        return len(self.management_briefing)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_bi_configuration(directory: Path | str = CONFIG_DIRECTORY) -> BIConfiguration:
    directory = Path(directory)
    ds_raw, metrics_raw, views_raw, reports_raw = (_read(directory / name) for name in
        ("datasets.json", "metrics.json", "exception_views.json", "reports.json"))
    valid_sources = {"chapter4_native_sales", "chapter5_channel_reconciliation",
                     "chapter6_purchasing_reconciliation", "chapter7_returns", "chapter7_transfers"}
    valid_dimensions = {"canonical_store", "canonical_sku", "canonical_product_category",
                        "canonical_channel", "canonical_supplier"}
    datasets, seen = [], set()
    for row in ds_raw.get("datasets", []):
        identifier = row.get("id")
        if not identifier or identifier in seen:
            raise BIValidationError(f"Duplicate dataset ID: {identifier}")
        seen.add(identifier)
        if not row.get("fields") or set(row.get("sources", [])) - valid_sources:
            raise BIValidationError("Dataset references nonexistent upstream source/evidence type")
        if set(row.get("canonical_dimensions", [])) - valid_dimensions:
            raise BIValidationError("Invalid canonical dimension")
        if set(row.get("relationships", [])) - set(row.get("canonical_dimensions", [])):
            raise BIValidationError("Invalid dataset relationship")
        datasets.append(BIDataset(identifier, tuple(row["sources"]), tuple(row["fields"]),
                                  tuple(row["canonical_dimensions"]), tuple(row.get("relationships", []))))
    by_dataset = {x.dataset_id: x for x in datasets}
    question_rows = _read(ROOT / "data" / "business_questions.json")["business_questions"]
    question_text = {q["question_id"]: q["question_text"] for q in question_rows}
    metrics = tuple(metrics_raw.get("metrics", []))
    for metric in metrics:
        dataset = by_dataset.get(metric.get("dataset"))
        if not dataset or metric.get("field") not in dataset.fields:
            raise BIValidationError("Metric references unavailable field")
        if metric.get("question_id") not in question_text:
            raise BIValidationError("Invalid Chapter 2 question reference")
    views, view_ids = tuple(views_raw.get("exception_views", [])), set()
    for view in views:
        if view.get("id") in view_ids or view.get("dataset") not in by_dataset:
            raise BIValidationError("Duplicate view ID or nonexistent dataset")
        view_ids.add(view.get("id")); filt = view.get("filter", {})
        dataset = by_dataset[view["dataset"]]
        if filt.get("operator") not in {"IN", "NOT_IN", "EQUALS"} or filt.get("field") not in dataset.fields or not isinstance(filt.get("values"), list):
            raise BIValidationError("Invalid filter definition")
    reports, report_ids = [], set()
    for row in reports_raw.get("reports", []):
        rid, dataset = row.get("id"), by_dataset.get(row.get("dataset"))
        if not rid or rid in report_ids:
            raise BIValidationError(f"Duplicate report ID: {rid}")
        report_ids.add(rid)
        if not dataset:
            raise BIValidationError("Report references nonexistent dataset")
        if not row.get("columns"):
            raise BIValidationError("Report columns cannot be empty")
        if set(row["columns"]) - set(dataset.fields):
            raise BIValidationError("Report references unavailable field")
        if set(row.get("group_by", [])) - set(dataset.fields):
            raise BIValidationError("Invalid grouping dimension")
        try:
            freshness = FreshnessRequirement(row.get("freshness"))
        except ValueError as exc:
            raise BIValidationError("Invalid freshness") from exc
        if set(row.get("question_ids", [])) - set(question_text):
            raise BIValidationError("Invalid Chapter 2 question reference")
        if set(row.get("sections", [])) - view_ids:
            raise BIValidationError("Report references nonexistent exception view")
        reports.append(BIReport(rid, dataset.dataset_id, tuple(row["columns"]),
                                tuple(row.get("group_by", [])), freshness,
                                tuple(row.get("question_ids", [])), tuple(row.get("sections", []))))
    coverage = []
    for row in reports_raw.get("coverage", []):
        qid = row.get("question_id")
        if qid not in question_text:
            raise BIValidationError("Invalid Chapter 2 question reference")
        try:
            before, after = BIQuestionStatus(row["before"]), BIQuestionStatus(row["after"])
        except (KeyError, ValueError) as exc:
            raise BIValidationError("Invalid coverage status") from exc
        if after is BIQuestionStatus.ANSWERED and not row.get("required_evidence_available"):
            raise BIValidationError("Report claims question is answered when required evidence is absent")
        coverage.append(CoverageTransition(qid, question_text[qid], before, after))
    manual = reports_raw.get("manual_reporting", {})
    return BIConfiguration(ds_raw.get("platform", "RiverBI"), tuple(datasets), metrics, views,
                           tuple(reports), tuple(coverage), tuple(manual.get("before", [])),
                           tuple(manual.get("after", [])))


def _apply_filter(rows: tuple[dict[str, Any], ...], definition: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    filt = definition["filter"]; values = set(filt["values"]); field = filt["field"]
    if filt["operator"] == "IN": return tuple(r for r in rows if r.get(field) in values)
    if filt["operator"] == "NOT_IN": return tuple(r for r in rows if r.get(field) not in values)
    return tuple(r for r in rows if r.get(field) in values)


def run_bi_reporting(configuration: BIConfiguration | None = None) -> BIReportingResult:
    config = configuration or load_bi_configuration()
    native, purchasing = run_native_reporting(), run_purchasing_experiment()
    returns_transfers, ecommerce = run_returns_transfers_experiment(), run_ecommerce_reconciliation()
    sales = tuple({"store": r["store"], "canonical_sku": "ALL", "category": "ALL",
                   "period": "2026-01-15", "gross_sales": r["gross_sales"],
                   "returns": r["returns"], "net_sales": r["net_sales"], "units": r["units_sold"]}
                  for r in native.reports["store-sales"])
    purchase_rows = tuple({"po": x.po.canonical_po_id, "supplier": x.po.supplier_id,
        "destination_store": x.po.destination_store_id, "canonical_sku": x.canonical_sku or "UNRESOLVED",
        "ordered_quantity": x.line.ordered_quantity, "received_quantity": x.receipt.received_quantity if x.receipt else 0,
        "reconciliation_result": x.result.value, "external_accounting_evidence_required": x.accounting_evidence_required}
        for x in purchasing.outcomes)
    return_rows = tuple({"return_id": x.record.return_id, "original_reference": x.record.original_reference,
        "original_channel": x.record.original_channel, "return_store": x.record.return_store,
        "canonical_sku": x.record.canonical_sku or "UNRESOLVED", "reason": x.record.reason or "MISSING",
        "reconciliation_result": x.result.value, "inventory_effect": x.record.inventory_effect}
        for x in returns_transfers.return_outcomes)
    transfer_rows = tuple({"transfer_id": x.record.transfer_id, "sending_store": x.record.sending_store,
        "receiving_store": x.record.receiving_store, "canonical_sku": x.record.canonical_sku or "UNRESOLVED",
        "quantity_sent": x.record.quantity_sent, "quantity_received": x.record.quantity_received,
        "transfer_result": x.result.value} for x in returns_transfers.transfer_outcomes)
    channel_rows = tuple({"online_order": x.order.online_order_id, "channel": x.canonical_channel_id or "UNRESOLVED",
        "fulfillment_store": x.canonical_store_id or "UNRESOLVED",
        "canonical_sku": ", ".join(x.canonical_skus) if x.canonical_skus else "UNRESOLVED",
        "order_status": x.order.status.value, "reconciliation_result": x.result.value,
        "unresolved_issue": None if x.result is ReconciliationResult.RECONCILED else x.result.value}
        for x in ecommerce.outcomes)
    inventory = []
    for row in channel_rows:
        if row["reconciliation_result"] not in {"RECONCILED", "PARTIALLY_RECONCILED"}:
            inventory.append({"exception_id": row["online_order"], "store": row["fulfillment_store"],
                "canonical_sku": row["canonical_sku"], "exception_type": "CHANNEL_INVENTORY_EFFECT",
                "source_evidence": "chapter5_channel_reconciliation", "expected_effect": "per connector rule",
                "observed_effect": "see source outcome", "status": row["reconciliation_result"]})
    for x in returns_transfers.transfer_outcomes:
        if x.result in {TransferResult.INVENTORY_EFFECT_EXCEPTION, TransferResult.MISSING_RECEIPT, TransferResult.PARTIAL_RECEIPT}:
            inventory.append({"exception_id": x.record.transfer_id, "store": x.record.receiving_store,
                "canonical_sku": x.record.canonical_sku or "UNRESOLVED", "exception_type": "TRANSFER_INVENTORY_EFFECT",
                "source_evidence": "chapter7_transfers", "expected_effect": x.record.quantity_sent,
                "observed_effect": x.record.receiver_inventory_effect, "status": x.result.value})
    datasets = {"cross_store_sales": sales, "inventory_exceptions": tuple(inventory),
                "purchasing_exceptions": purchase_rows, "return_exceptions": return_rows,
                "transfer_exceptions": transfer_rows, "channel_reconciliation": channel_rows}
    views = {v["id"]: _apply_filter(datasets[v["dataset"]], v) for v in config.exception_views}
    outputs = {r.report_id: datasets[r.dataset_id] for r in config.reports if not r.sections}
    briefing = tuple({"section": section, **row} for section in next(r for r in config.reports if r.report_id == "management-briefing").sections for row in views[section])
    outputs["management-briefing"] = briefing
    return BIReportingResult(config, outputs, config.coverage, briefing)


assess_bi_reporting = run_bi_reporting
