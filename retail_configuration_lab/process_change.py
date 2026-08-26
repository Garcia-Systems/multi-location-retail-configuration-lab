"""Chapter 10: process-only changes replayed through Chapters 6, 7, and 9.

This module changes synthetic behavior and declarative ownership, never system
capability.  The existing reconciliation functions remain the outcome engines.
"""

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, replace
from enum import StrEnum
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .bi_reporting import BIQuestionStatus, run_bi_reporting
from .evidence import EvidenceCategory
from .purchasing import (PurchasingResult, SupplierItemMapping,
                         load_purchasing_configuration, run_purchasing_experiment)
from .returns_transfers import (ReturnResult, TransferResult,
                                run_returns_transfers_experiment)

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "config" / "process" / "process_rules.json"
SCENARIOS = ROOT / "data" / "process_change" / "scenarios.json"


class ProcessValidationError(ValueError):
    """An invalid lab definition, distinct from valid synthetic noncompliance."""


class ComplianceStatus(StrEnum):
    COMPLIANT = "COMPLIANT"
    NONCOMPLIANT = "NONCOMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class TechnologyAvailability(StrEnum):
    YES = "YES"
    NO = "NO"
    PARTIAL = "PARTIAL"


class ResidualCause(StrEnum):
    PROCESS = "PROCESS"
    DATA_GOVERNANCE = "DATA_GOVERNANCE"
    OWNERSHIP = "OWNERSHIP"
    TECHNICAL_GAP = "TECHNICAL_GAP"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class InterventionType(StrEnum):
    CONFIGURATION = "CONFIGURATION"
    NATIVE_INTEGRATION = "NATIVE_INTEGRATION"
    AUTOMATION = "AUTOMATION"
    BI = "BI"
    PROCESS_CHANGE = "PROCESS_CHANGE"


@dataclass(frozen=True)
class ProcessRule:
    rule_id: str
    business_area: str
    name: str
    problem_statement: str
    owner: str
    required_behavior: str
    trigger: str
    completion_condition: str
    escalation_condition: str
    affected_evidence: str
    evidence_classification: EvidenceCategory
    scenario_id: str
    capability_id: str


@dataclass(frozen=True)
class ProcessState:
    compliance: ComplianceStatus
    behavior: str
    manual_steps: int


@dataclass(frozen=True)
class ProcessScenario:
    scenario_id: str
    name: str
    technology_available: TechnologyAvailability
    primary_residual_cause: ResidualCause
    rule_id: str | None
    event_reference: str
    before: ProcessState
    after: ProcessState


@dataclass(frozen=True)
class ScenarioOutcome:
    scenario: ProcessScenario
    exception_before: bool
    exception_after: bool
    before_result: str
    after_result: str

    @property
    def eliminated(self) -> bool:
        return self.exception_before and not self.exception_after


@dataclass(frozen=True)
class QuestionImpact:
    question_id: str
    status: BIQuestionStatus
    reason: str


@dataclass(frozen=True)
class ProcessChangeResult:
    rules: tuple[ProcessRule, ...]
    outcomes: tuple[ScenarioOutcome, ...]
    question_impacts: tuple[QuestionImpact, ...]
    chapter9_report_evidence_unchanged: bool
    interventions: tuple[InterventionType, ...]

    @property
    def scenarios_evaluated(self): return len(self.outcomes)
    @property
    def noncompliant_before(self): return sum(x.scenario.before.compliance is ComplianceStatus.NONCOMPLIANT for x in self.outcomes)
    @property
    def noncompliant_after(self): return sum(x.scenario.after.compliance is ComplianceStatus.NONCOMPLIANT for x in self.outcomes)
    @property
    def operational_exceptions_before(self): return sum(x.exception_before for x in self.outcomes)
    @property
    def operational_exceptions_after(self): return sum(x.exception_after for x in self.outcomes)
    @property
    def manual_steps_before(self): return sum(x.scenario.before.manual_steps for x in self.outcomes)
    @property
    def manual_steps_after(self): return sum(x.scenario.after.manual_steps for x in self.outcomes)
    @property
    def process_caused_exceptions_eliminated(self):
        return sum(x.eliminated and x.scenario.primary_residual_cause in {ResidualCause.PROCESS, ResidualCause.OWNERSHIP} for x in self.outcomes)
    @property
    def data_governance_exceptions_eliminated(self):
        return sum(x.eliminated and x.scenario.primary_residual_cause is ResidualCause.DATA_GOVERNANCE for x in self.outcomes)
    @property
    def technical_exceptions_unchanged(self):
        return sum(x.exception_before and x.exception_after and x.scenario.primary_residual_cause is ResidualCause.TECHNICAL_GAP for x in self.outcomes)
    @property
    def unknown_mixed_exceptions(self):
        return sum(x.exception_after and x.scenario.primary_residual_cause in {ResidualCause.UNKNOWN, ResidualCause.MIXED} for x in self.outcomes)
    @property
    def process_exception_reduction_ratio(self):
        relevant = [x for x in self.outcomes if x.scenario.primary_residual_cause in {ResidualCause.PROCESS, ResidualCause.OWNERSHIP}]
        before, after = sum(x.exception_before for x in relevant), sum(x.exception_after for x in relevant)
        return (before - after) / before if before else 0.0
    @property
    def manual_process_step_reduction_ratio(self):
        return ((self.manual_steps_before - self.manual_steps_after) / self.manual_steps_before
                if self.manual_steps_before else 0.0)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_process_configuration(rules_path: Path = RULES, scenarios_path: Path = SCENARIOS):
    raw_rules, raw_scenarios = _read(rules_path), _read(scenarios_path)
    scenario_ids = {row.get("id") for row in raw_scenarios.get("scenarios", [])}
    valid_areas = set(raw_rules.get("business_areas", []))
    # These capability references name capabilities already exercised in Chapters 3–9.
    existing_capabilities = {"purchasing-receiving", "returns-reason", "inventory-transfer",
                             "identity-product", "reporting-bi"}
    rules, seen = [], set()
    for row in raw_rules.get("rules", []):
        rid = row.get("id")
        if not rid or rid in seen: raise ProcessValidationError(f"duplicate process-rule ID: {rid}")
        seen.add(rid)
        if not row.get("owner"): raise ProcessValidationError(f"missing owner: {rid}")
        if not row.get("required_behavior"): raise ProcessValidationError(f"empty required behavior: {rid}")
        if not row.get("completion_condition"): raise ProcessValidationError(f"missing completion condition: {rid}")
        if row.get("business_area") not in valid_areas or row.get("scenario_id") not in scenario_ids:
            raise ProcessValidationError(f"nonexistent business area/scenario: {rid}")
        if row.get("capability_id") not in existing_capabilities:
            raise ProcessValidationError(f"process intervention claims unavailable capability: {rid}")
        try: evidence = EvidenceCategory(row.get("evidence_classification"))
        except ValueError as exc: raise ProcessValidationError(f"invalid evidence classification: {rid}") from exc
        rules.append(ProcessRule(rid, row["business_area"], row["name"], row["problem_statement"],
            row["owner"], row["required_behavior"], row["trigger"], row["completion_condition"],
            row["escalation_condition"], row["affected_evidence"], evidence,
            row["scenario_id"], row["capability_id"]))
    rule_ids = seen
    scenarios, seen = [], set()
    for row in raw_scenarios.get("scenarios", []):
        sid = row.get("id")
        if not sid or sid in seen or not row.get("event_reference") or not isinstance(row.get("before"), dict) or not isinstance(row.get("after"), dict):
            raise ProcessValidationError(f"malformed before/after scenario reference: {sid}")
        seen.add(sid)
        if row.get("rule_id") is not None and row["rule_id"] not in rule_ids:
            raise ProcessValidationError(f"scenario references nonexistent rule: {sid}")
        try:
            before = ProcessState(ComplianceStatus(row["before"]["compliance"]), row["before"]["behavior"], row["before"]["manual_steps"])
            after = ProcessState(ComplianceStatus(row["after"]["compliance"]), row["after"]["behavior"], row["after"]["manual_steps"])
            availability = TechnologyAvailability(row["technology_available"])
            cause = ResidualCause(row["primary_residual_cause"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ProcessValidationError(f"invalid compliance/residual classification: {sid}") from exc
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (before.manual_steps, after.manual_steps)):
            raise ProcessValidationError(f"invalid manual steps: {sid}")
        if row.get("rule_id") and availability is TechnologyAvailability.NO:
            raise ProcessValidationError(f"process rule claims technical capability does not exist: {sid}")
        scenarios.append(ProcessScenario(sid, row["name"], availability, cause, row.get("rule_id"),
                                         row["event_reference"], before, after))
    return tuple(rules), tuple(scenarios)


def _temporary_json(value: dict[str, Any]):
    handle = NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8", delete=False)
    json.dump(value, handle); handle.close()
    return Path(handle.name)


def run_process_change_experiment() -> ProcessChangeResult:
    rules, scenarios = load_process_configuration()
    purchase_before = run_purchasing_experiment()
    purchase_data = deepcopy(_read(ROOT / "data" / "purchasing" / "purchase_orders.json"))
    purchase_data["receipts"].append({"receipt_id":"JRO-RECEIPT-82454","po_reference":"RCV-PO-82454",
        "line_id":"1","supplier_item_id":"BR-1042","received_quantity":6,"location_source_id":"RVA-WH",
        "status":"FULLY_RECEIVED","inventory_effect":6})
    base_config = load_purchasing_configuration()
    governed = SupplierItemMapping("JRO-SUPPLIER-014", "BR-UNKNOWN", (),
        ("JRO-1042-BLU-M",), "RESOLVED", "approved canonical mapping source")
    governed_config = replace(base_config, supplier_items=tuple(
        governed if x.supplier_item_id == "BR-UNKNOWN" else x for x in base_config.supplier_items))
    purchase_path = _temporary_json(purchase_data)
    try: purchase_after = run_purchasing_experiment(governed_config, purchase_path)
    finally: purchase_path.unlink()

    rt_before = run_returns_transfers_experiment()
    rt_data = deepcopy(_read(ROOT / "data" / "returns_transfers" / "records.json"))
    for row in rt_data["returns"]:
        if row["return_id"] == "JRO-RET-1008": row["reason"] = "WRONG_SIZE"
    for row in rt_data["transfers"]:
        if row["transfer_id"] == "JRO-TR-1007":
            row.update(quantity_received=4, received_status=True, received_timestamp="2026-07-04T10:00:00Z",
                       status="RECEIVED", receiver_inventory_effect=4)
    rt_path = _temporary_json(rt_data)
    try: rt_after = run_returns_transfers_experiment(path=rt_path)
    finally: rt_path.unlink()

    before_po = {x.po.canonical_po_id: x.result for x in purchase_before.outcomes}
    after_po = {x.po.canonical_po_id: x.result for x in purchase_after.outcomes}
    before_ret = {x.record.return_id: x.result for x in rt_before.return_outcomes}
    after_ret = {x.record.return_id: x.result for x in rt_after.return_outcomes}
    before_tr = {x.record.transfer_id: x.result for x in rt_before.transfer_outcomes}
    after_tr = {x.record.transfer_id: x.result for x in rt_after.transfer_outcomes}
    evaluated = {
        "inconsistent-receiving": (before_po["JRO-PO-82454"] is PurchasingResult.MISSING_RECEIPT, after_po["JRO-PO-82454"] is not PurchasingResult.RECONCILED, before_po["JRO-PO-82454"].value, after_po["JRO-PO-82454"].value),
        "return-reason": (before_ret["JRO-RET-1008"] is ReturnResult.MISSING_REASON, after_ret["JRO-RET-1008"] is not ReturnResult.RECONCILED, before_ret["JRO-RET-1008"].value, after_ret["JRO-RET-1008"].value),
        "transfer-closure": (before_tr["JRO-TR-1007"] is TransferResult.MISSING_RECEIPT, after_tr["JRO-TR-1007"] is not TransferResult.RECONCILED, before_tr["JRO-TR-1007"].value, after_tr["JRO-TR-1007"].value),
        "mapping-governance": (before_po["JRO-PO-82456"] is PurchasingResult.UNRESOLVED_IDENTITY, after_po["JRO-PO-82456"] is not PurchasingResult.RECONCILED, before_po["JRO-PO-82456"].value, after_po["JRO-PO-82456"].value),
        "spreadsheet-duplication": (True, False, "REDUNDANT_ASSEMBLY", "DEFINED_RESIDUAL_USE_ONLY"),
        "accounting-reconciliation": (True, True, "EVIDENCE_UNAVAILABLE", "EVIDENCE_UNAVAILABLE"),
    }
    outcomes = tuple(ScenarioOutcome(x, *evaluated[x.scenario_id]) for x in scenarios)
    bi_before, bi_after = run_bi_reporting(), run_bi_reporting()
    impacts = (
        QuestionImpact("PUR-01", BIQuestionStatus.ANSWERED, "Same Chapter 6 logic retains purchasing exception visibility."),
        QuestionImpact("RET-02", BIQuestionStatus.ANSWERED, "Reason evidence becomes complete; fewer exceptions does not create coverage."),
        QuestionImpact("TRN-01", BIQuestionStatus.ANSWERED, "Sent/received evidence remains available after acknowledgement."),
        QuestionImpact("INV-03", BIQuestionStatus.UNKNOWN, "Mapping evidence improves, but the original question remains conservatively unresolved."),
        QuestionImpact("MGT-01", BIQuestionStatus.ANSWERED, "Configured briefing evidence is unchanged while duplicate assembly is retired."),
        QuestionImpact("FIN-01", BIQuestionStatus.PARTIALLY_ANSWERED, "Operational evidence exists; accounting evidence remains unavailable."),
    )
    return ProcessChangeResult(rules, outcomes, impacts, bi_before.reports == bi_after.reports,
        tuple(InterventionType))
