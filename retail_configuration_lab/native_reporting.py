"""Chapter 4's bounded configuration-driven native reporting experiment.

RiverPOS and RiverStock behavior here is a MODELED ALTERNATIVE ASSUMPTION, not
a statement about any commercial product.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .identity import IdentityConfiguration, IdentityType, MappingStatus, load_identity_configuration

CONFIG_DIRECTORY = Path(__file__).resolve().parents[1] / "config" / "reporting"
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "native_reporting.json"


class ReportingValidationError(ValueError):
    pass


class QuestionResult(StrEnum):
    ANSWERED = "ANSWERED"
    PARTIALLY_ANSWERED = "PARTIALLY_ANSWERED"
    NOT_ANSWERED = "NOT_ANSWERED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ReportDefinition:
    report_id: str
    name: str
    kind: str
    store_group: str
    metrics: tuple[str, ...]
    group_by: tuple[str, ...]
    transaction_types: tuple[str, ...]
    return_treatment: str


@dataclass(frozen=True)
class ReportingConfiguration:
    store_groups: dict[str, tuple[str, ...]]
    common_categories: tuple[str, ...]
    category_mappings: dict[tuple[str, str], str]
    reports: tuple[ReportDefinition, ...]
    metrics: dict[str, str]
    date_boundary: dict[str, Any]
    question_references: tuple[str, ...] = ()

    def category_for(self, source_system: str, source_category: str) -> str:
        try:
            return self.category_mappings[(source_system, source_category)]
        except KeyError as exc:
            raise ReportingValidationError(f"No category mapping for {source_system}:{source_category}") from exc


@dataclass(frozen=True)
class QuestionAssessment:
    question_id: str
    question: str
    before_configuration: QuestionResult
    after_configuration: QuestionResult
    native_report: str | None
    missing: tuple[str, ...] = ()


@dataclass(frozen=True)
class NativeReportingAssessment:
    reports: dict[str, tuple[dict[str, Any], ...]]
    questions: tuple[QuestionAssessment, ...]
    configuration_records_used: int

    @property
    def count_by_result(self) -> dict[QuestionResult, int]:
        return {status: sum(q.after_configuration is status for q in self.questions) for status in QuestionResult}

    @property
    def native_question_answer_rate(self) -> float:
        return self.count_by_result[QuestionResult.ANSWERED] / len(self.questions) if self.questions else 0.0

    @property
    def questions_improved_by_configuration(self) -> tuple[str, ...]:
        return tuple(q.question_id for q in self.questions
                     if q.after_configuration is QuestionResult.ANSWERED
                     and q.before_configuration is not QuestionResult.ANSWERED)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_reporting_configuration(directory: Path | str = CONFIG_DIRECTORY,
                                 identity: IdentityConfiguration | None = None) -> ReportingConfiguration:
    directory, identity = Path(directory), identity or load_identity_configuration()
    groups_data, categories_data, reports_data = (_read(directory / name) for name in
        ("store_groups.json", "categories.json", "native_reports.json"))
    canonical_stores = {x.canonical_id for x in identity.identities[IdentityType.STORE]}
    groups: dict[str, tuple[str, ...]] = {}
    for row in groups_data.get("store_groups", []):
        group_id = row.get("id")
        if not group_id or group_id in groups:
            raise ReportingValidationError(f"Duplicate or empty store-group ID: {group_id}")
        stores = tuple(row.get("store_ids", ()))
        unknown = set(stores) - canonical_stores
        if unknown:
            raise ReportingValidationError(f"Store group references nonexistent canonical store: {sorted(unknown)[0]}")
        groups[group_id] = stores
    categories = tuple(categories_data.get("common_categories", ()))
    mappings = {}
    for row in categories_data.get("mappings", []):
        if row.get("common_category") not in categories:
            raise ReportingValidationError("Category mapping references invalid common category")
        mappings[(row.get("source_system"), row.get("source_category"))] = row["common_category"]
    metrics = reports_data.get("metrics", {})
    definitions, seen = [], set()
    valid_returns = {"SUBTRACT", "EXCLUDE", "NOT_APPLICABLE"}
    for row in reports_data.get("reports", []):
        rid = row.get("id")
        if not rid or rid in seen:
            raise ReportingValidationError(f"Duplicate report ID: {rid}")
        seen.add(rid)
        if row.get("store_group") not in groups:
            raise ReportingValidationError(f"Report references nonexistent store group: {row.get('store_group')}")
        if not row.get("group_by"):
            raise ReportingValidationError("Report grouping dimensions cannot be empty")
        unknown = set(row.get("metrics", ())) - set(metrics) - {"ON_HAND", "ADJUSTMENT_QUANTITY"}
        if unknown:
            raise ReportingValidationError(f"Report references nonexistent metric: {sorted(unknown)[0]}")
        if row.get("return_treatment") not in valid_returns:
            raise ReportingValidationError("Invalid return treatment")
        definitions.append(ReportDefinition(rid, row["name"], row["kind"], row["store_group"],
            tuple(row["metrics"]), tuple(row["group_by"]), tuple(row.get("transaction_types", ())), row["return_treatment"]))
    boundary = reports_data.get("date_boundary", {})
    try:
        ZoneInfo(boundary["business_timezone"])
        time.fromisoformat(boundary["start_time"]); time.fromisoformat(boundary["end_time"])
    except (KeyError, ValueError, ZoneInfoNotFoundError) as exc:
        raise ReportingValidationError("Invalid date boundary") from exc
    if boundary.get("start_inclusive") is not True or boundary.get("end_inclusive") is not False:
        raise ReportingValidationError("Invalid date boundary inclusion behavior")
    question_refs = tuple(reports_data.get("question_references", ()))
    question_data = _read(Path(__file__).resolve().parents[1] / "data" / "business_questions.json")
    supported = {q["question_id"] for q in question_data["business_questions"]}
    if set(question_refs) - supported:
        raise ReportingValidationError("Unsupported question reference")
    return ReportingConfiguration(groups, categories, mappings, tuple(definitions), metrics, boundary, question_refs)


def reporting_period_contains(timestamp: str | datetime, start_date: str,
                              configuration: ReportingConfiguration) -> bool:
    value = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
    if value.tzinfo is None:
        raise ReportingValidationError("Transaction timestamp must include an offset")
    local = value.astimezone(ZoneInfo(configuration.date_boundary["business_timezone"]))
    day = date.fromisoformat(start_date)
    zone = ZoneInfo(configuration.date_boundary["business_timezone"])
    start_clock = time.fromisoformat(configuration.date_boundary["start_time"])
    end_clock = time.fromisoformat(configuration.date_boundary["end_time"])
    lower = datetime.combine(day, start_clock, zone)
    upper_day = day + timedelta(days=1) if end_clock <= start_clock else day
    upper = datetime.combine(upper_day, end_clock, zone)
    return lower <= local < upper


def _canonical_sku(identity: IdentityConfiguration, system: str, source: str) -> str:
    resolved = identity.resolve(IdentityType.SKU, system, source)
    if resolved.status is not MappingStatus.CONFIRMED or not resolved.canonical_id:
        raise ReportingValidationError(f"Record references nonexistent SKU: {source}")
    return resolved.canonical_id


def run_native_reporting(configuration: ReportingConfiguration | None = None,
                         data_path: Path | str = DATA_PATH, period: str = "2026-01-15",
                         identity: IdentityConfiguration | None = None) -> NativeReportingAssessment:
    identity = identity or load_identity_configuration()
    configuration = configuration or load_reporting_configuration(identity=identity)
    data = _read(Path(data_path)); stores = {x.canonical_id for x in identity.identities[IdentityType.STORE]}
    tx = []
    for row in data.get("transactions", []):
        if row.get("store_id") not in stores: raise ReportingValidationError("Transaction references nonexistent store")
        sku = _canonical_sku(identity, "RiverPOS", row.get("source_sku"))
        category = configuration.category_for("RiverPOS", row.get("source_category"))
        if row.get("type") not in {"SALE", "RETURN"}: raise ReportingValidationError("Invalid transaction type")
        if reporting_period_contains(row["timestamp"], period, configuration):
            tx.append({**row, "canonical_sku": sku, "common_category": category, "amount": Decimal(row["amount"])})
    outputs: dict[str, tuple[dict[str, Any], ...]] = {}
    for report in configuration.reports:
        allowed = set(configuration.store_groups[report.store_group])
        if report.kind == "SALES":
            buckets = defaultdict(lambda: {"gross_sales": Decimal("0"), "returns": Decimal("0"), "net_sales": Decimal("0"), "units_sold": 0})
            for row in tx:
                if row["store_id"] not in allowed or row["type"] not in report.transaction_types: continue
                key = tuple(row["store_id"] if x == "store" else row[x] for x in report.group_by)
                b = buckets[key]
                if row["type"] == "SALE": b["gross_sales"] += row["amount"]; b["units_sold"] += row["quantity"]
                elif report.return_treatment == "SUBTRACT": b["returns"] += abs(row["amount"]); b["units_sold"] -= abs(row["quantity"])
                b["net_sales"] = b["gross_sales"] - b["returns"]
            rows = []
            for key, values in sorted(buckets.items()):
                dimensions = {name: value for name, value in zip(report.group_by, key)}
                rows.append({**dimensions, **values})
            outputs[report.report_id] = tuple(rows)
        elif report.kind in {"SNAPSHOT", "ADJUSTMENT"}:
            source_rows = data["inventory" if report.kind == "SNAPSHOT" else "adjustments"]
            rows = []
            for row in source_rows:
                if row["store_id"] not in stores: raise ReportingValidationError("Inventory record references nonexistent store")
                if row["store_id"] in allowed:
                    normalized = {**row, "canonical_sku": _canonical_sku(identity, "RiverStock", row["source_sku"])}
                    if report.kind == "SNAPSHOT": normalized["on_hand_quantity"] = row["on_hand"]
                    else: normalized["adjustment"] = row["quantity"]
                    rows.append(normalized)
            outputs[report.report_id] = tuple(rows)
    questions = (
        QuestionAssessment("SAL-01", "What sold by store during the selected period?", QuestionResult.PARTIALLY_ANSWERED, QuestionResult.ANSWERED, "store-sales"),
        QuestionAssessment("INV-02", "Where do inventory adjustments appear unusual or remain unresolved?", QuestionResult.PARTIALLY_ANSWERED, QuestionResult.PARTIALLY_ANSWERED, "inventory-adjustments", ("agreed unusual threshold", "verified resolution context")),
        QuestionAssessment("RET-01", "Which returns disagree across transaction, inventory, or accounting evidence?", QuestionResult.NOT_ANSWERED, QuestionResult.NOT_ANSWERED, None, ("accounting evidence",)),
        QuestionAssessment("RET-02", "Which returns are missing useful reason information?", QuestionResult.UNKNOWN, QuestionResult.UNKNOWN, None, ("historical reason completeness",)),
        QuestionAssessment("SAL-02", "What sold by channel during the selected period?", QuestionResult.NOT_ANSWERED, QuestionResult.NOT_ANSWERED, None, ("e-commerce channel evidence",)),
    )
    records = len(configuration.store_groups) + len(configuration.category_mappings) + len(configuration.reports) + len(configuration.metrics) + 1
    return NativeReportingAssessment(outputs, questions, records)

# Friendly aliases for small teaching/test clients.
load_native_reporting_configuration = load_reporting_configuration
assess_native_reporting = run_native_reporting
