"""Chapter 17: one deterministic cross-channel reconciliation edge.

The module deliberately has no persistence or integration framework.  It accepts
copies of already-exported evidence and returns an exception record; source
systems remain authoritative.
"""
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from .evidence import EvidenceCategory
from .questions import load_questions
from .weak_native_coverage import AnswerStatus, GapClassification, load_weak_native_coverage


class CustomEdgeError(ValueError):
    """An edge contract or experiment violated its narrow boundary."""


class CustomResult(StrEnum):
    RECONCILED = "RECONCILED"
    EXCEPTION = "EXCEPTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNRESOLVED_IDENTITY = "UNRESOLVED_IDENTITY"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class EdgeDecision(StrEnum):
    EDGE_JUSTIFIED_FOR_FURTHER_ECONOMIC_TEST = "EDGE_JUSTIFIED_FOR_FURTHER_ECONOMIC_TEST"
    EDGE_TECHNICALLY_USEFUL_BUT_ECONOMICALLY_WEAK = "EDGE_TECHNICALLY_USEFUL_BUT_ECONOMICALLY_WEAK"
    EDGE_TOO_BROAD = "EDGE_TOO_BROAD"
    EDGE_NOT_NEEDED = "EDGE_NOT_NEEDED"
    EDGE_BLOCKED_BY_MISSING_EVIDENCE = "EDGE_BLOCKED_BY_MISSING_EVIDENCE"
    CUSTOM_EDGE_NOT_JUSTIFIED = "CUSTOM_EDGE_NOT_JUSTIFIED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CustomEdgeDefinition:
    edge_id: str
    name: str
    residual_gap_id: str
    affected_question_ids: tuple[str, ...]
    input_evidence: tuple[str, ...]
    output_evidence: tuple[str, ...]
    ownership_boundary: str
    excluded_responsibilities: tuple[str, ...]
    failure_behavior: str
    support_implications: tuple[str, ...]
    evidence_classification: EvidenceCategory
    scope: GapClassification = GapClassification.BOUNDED
    rule_version: str = "JRO-XC-1.0"


@dataclass(frozen=True)
class EdgeInput:
    record_id: str
    area: str
    source_systems: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    canonical_order_id: str | None
    canonical_sku: str | None
    fulfillment_store: str | None
    order_state: str | None
    return_or_cancellation_state: str | None
    inventory_movement: int | None
    expected_inventory_movement: int | None
    accounting_evidence: bool = True
    historical_compatible: bool = True


@dataclass(frozen=True)
class EdgeOutcome:
    record_id: str
    result: CustomResult
    source_systems: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    canonical_ids: tuple[str, ...]
    rule_version: str
    input_evidence_used: tuple[str, ...]
    rationale: str
    area: str


@dataclass(frozen=True)
class EffortCategory:
    name: str
    hours: Decimal


@dataclass(frozen=True)
class CustomEdgeAnalysis:
    definition: CustomEdgeDefinition
    inputs: tuple[EdgeInput, ...]
    outcomes: tuple[EdgeOutcome, ...]
    counts: Mapping[CustomResult, int]
    manual_review_before_custom: int
    manual_review_after_custom: int
    custom_edge_manual_review_reduction_ratio: Decimal
    before_question_statuses: Mapping[str, AnswerStatus]
    after_question_statuses: Mapping[str, AnswerStatus]
    modeled_burden_before_custom: Decimal
    modeled_burden_after_custom: Decimal
    modeled_incremental_burden_reduction: Decimal
    effort: tuple[EffortCategory, ...]
    modeled_custom_edge_setup_cost: Decimal
    annual_custom_edge_support_hours: Decimal
    annual_custom_edge_support_cost: Decimal
    simple_custom_edge_payback_years: Decimal | None
    decision: EdgeDecision
    decision_rationale: str
    configured_workaround_layers: tuple[str, ...]
    custom_workaround_layers: tuple[str, ...]
    configured_owned: tuple[str, ...]
    custom_added_ownership: tuple[str, ...]
    overall_lab_verdict: str = "UNTESTED"


DEFAULT_DEFINITION = CustomEdgeDefinition(
    "edge-cross-channel-exception", "James River cross-channel exception reconciliation",
    "cross-channel-exception-rule", ("ECOM-01", "ECOM-02"),
    ("online order export", "fulfillment-store mapping", "canonical SKU",
     "return/cancellation state", "inventory movement evidence"),
    tuple(x.value for x in CustomResult),
    "Consumes exports and emits exception evidence only; POS, inventory, and e-commerce remain authoritative.",
    ("POS runtime", "inventory runtime", "purchasing", "accounting", "transfers",
     "e-commerce runtime", "historical migration", "dashboarding", "general integration"),
    "Fail closed to insufficient evidence, unresolved identity, or out of scope; never mutate sources.",
    ("rule changes", "test maintenance", "schema compatibility", "deployment/runtime ownership", "defect investigation"),
    EvidenceCategory.OBSERVED_IMPLEMENTATION_STRUCTURE,
)


def validate_definition(definition: CustomEdgeDefinition = DEFAULT_DEFINITION) -> None:
    scenario = load_weak_native_coverage()
    gaps = {g["gap_id"]: g for g in scenario.residual_gaps}
    questions = {q.question_id for q in load_questions().questions}
    if definition.residual_gap_id not in gaps:
        raise CustomEdgeError("nonexistent Chapter 16 residual gap")
    if not definition.affected_question_ids or not set(definition.affected_question_ids) <= questions:
        raise CustomEdgeError("nonexistent business-question IDs")
    if set(definition.affected_question_ids) != set(gaps[definition.residual_gap_id]["question_ids"]):
        raise CustomEdgeError("custom edge claiming unrelated question coverage")
    if not definition.input_evidence: raise CustomEdgeError("missing input contract")
    if not definition.output_evidence: raise CustomEdgeError("missing output contract")
    try: outputs = {CustomResult(x) for x in definition.output_evidence}
    except ValueError as exc: raise CustomEdgeError("unknown custom result") from exc
    if outputs != set(CustomResult): raise CustomEdgeError("incomplete output contract")
    if not definition.ownership_boundary.strip(): raise CustomEdgeError("missing ownership boundary")
    if not definition.excluded_responsibilities: raise CustomEdgeError("empty excluded-responsibility list")
    if definition.scope is GapClassification.BOUNDED and gaps[definition.residual_gap_id]["classification"] is not GapClassification.BOUNDED:
        raise CustomEdgeError("broad residual classified as bounded")


def reconcile(record: EdgeInput, definition: CustomEdgeDefinition = DEFAULT_DEFINITION) -> EdgeOutcome:
    validate_definition(definition)
    original = tuple(record.__dict__.items())
    used = tuple(f"{name}={value}" for name, value in original if name not in {"record_id"})
    canonical = tuple(x for x in (record.canonical_order_id, record.canonical_sku, record.fulfillment_store) if x)
    if record.area not in {"cross-channel", "ecommerce"}:
        result, rationale = CustomResult.OUT_OF_SCOPE, f"{record.area} belongs to an excluded workflow."
    elif not record.accounting_evidence:
        result, rationale = CustomResult.OUT_OF_SCOPE, "Accounting linkage is explicitly excluded; no accounting evidence is fabricated."
    elif not record.historical_compatible:
        result, rationale = CustomResult.OUT_OF_SCOPE, "Broad acquired-store historical incompatibility requires migration or standardization."
    elif not record.canonical_sku or not record.canonical_order_id:
        result, rationale = CustomResult.UNRESOLVED_IDENTITY, "Canonical order or SKU identity is unresolved; the rule does not guess."
    elif any(x is None for x in (record.fulfillment_store, record.order_state,
                                  record.return_or_cancellation_state,
                                  record.inventory_movement, record.expected_inventory_movement)):
        result, rationale = CustomResult.INSUFFICIENT_EVIDENCE, "A required exported state or inventory movement is missing; the rule fails closed."
    elif record.inventory_movement == record.expected_inventory_movement:
        result, rationale = CustomResult.RECONCILED, "The company-specific expected movement agrees with exported fulfillment and order evidence."
    else:
        result, rationale = CustomResult.EXCEPTION, "Evidence is sufficient, but observed inventory movement disagrees with the company-specific expected movement."
    if tuple(record.__dict__.items()) != original:
        raise CustomEdgeError("custom edge modifying authoritative source records")
    outcome = EdgeOutcome(record.record_id, result, record.source_systems, record.source_record_ids,
                          canonical, definition.rule_version, used, rationale, record.area)
    validate_outcome(record, outcome)
    return outcome


def validate_outcome(record: EdgeInput, outcome: EdgeOutcome) -> None:
    """Reject fabricated resolution, lost provenance, or authoritative mutation claims."""
    try:
        CustomResult(outcome.result)
    except ValueError as exc:
        raise CustomEdgeError("unknown custom result") from exc
    required = (record.fulfillment_store, record.order_state,
                record.return_or_cancellation_state, record.inventory_movement,
                record.expected_inventory_movement)
    if outcome.result is CustomResult.RECONCILED and (not record.canonical_order_id
            or not record.canonical_sku or any(x is None for x in required)):
        raise CustomEdgeError("custom rule claiming to resolve missing evidence")
    if outcome.source_systems != record.source_systems or outcome.source_record_ids != record.source_record_ids:
        raise CustomEdgeError("custom edge modifying authoritative source records")
    if not outcome.rule_version or not outcome.input_evidence_used or not outcome.rationale:
        raise CustomEdgeError("custom result missing provenance")


def fixture_inputs() -> tuple[EdgeInput, ...]:
    def row(identifier, area="cross-channel", sku="SKU-100", actual=-1, expected=-1, **kw):
        values=dict(record_id=identifier, area=area, source_systems=("WebCart", "RiverPOS", "Inventory"),
          source_record_ids=(f"WEB-{identifier}", f"POS-{identifier}", f"INV-{identifier}"),
          canonical_order_id=f"ORDER-{identifier}", canonical_sku=sku, fulfillment_store="STORE-03",
          order_state="FULFILLED", return_or_cancellation_state="NONE", inventory_movement=actual,
          expected_inventory_movement=expected)
        values.update(kw); return EdgeInput(**values)
    return (row("CLEAN-1"), row("CLEAN-2", actual=1, expected=1), row("CLEAN-3", actual=0, expected=0),
            row("TRUE-X", actual=0, expected=-1), row("MISSING", inventory_movement=None),
            row("AMBIG", sku=None), row("ACCOUNT", accounting_evidence=False),
            row("PURCHASE", area="purchasing"), row("ACQUIRED", historical_compatible=False))


def calculate_payback(setup_cost: Decimal, reduction: Decimal, support_cost: Decimal) -> Decimal | None:
    for name, value in (("setup cost", setup_cost), ("burden reduction", reduction), ("support cost", support_cost)):
        if value < 0: raise CustomEdgeError(f"negative {name}")
    denominator = reduction - support_cost
    return setup_cost / denominator if denominator > 0 else None


def run_custom_edge(definition: CustomEdgeDefinition = DEFAULT_DEFINITION,
                    records: tuple[EdgeInput, ...] | None = None,
                    hourly_rate: Decimal = Decimal("125"),
                    support_rate: Decimal = Decimal("100")) -> CustomEdgeAnalysis:
    validate_definition(definition)
    if hourly_rate < 0 or support_rate < 0: raise CustomEdgeError("negative modeled cost")
    records = records or fixture_inputs(); outcomes = tuple(reconcile(x, definition) for x in records)
    counts = Counter(x.result for x in outcomes); before = len(records)
    after = before - counts[CustomResult.RECONCILED]
    ratio = (Decimal(before-after) / Decimal(before)) if before else Decimal()
    burden_before = next(g["modeled_burden"] for g in load_weak_native_coverage().residual_gaps
                         if g["gap_id"] == definition.residual_gap_id)
    burden_after = burden_before * (Decimal(1)-ratio)
    effort = tuple(EffortCategory(n, Decimal(h)) for n,h in (("discovery/refinement",12),("implementation",24),
      ("tests",20),("integration with existing lab outputs",10),("documentation",8),
      ("deployment/operationalization assumption",8),("contingency",8)))
    if any(x.hours < 0 for x in effort): raise CustomEdgeError("negative modeled effort")
    setup = sum((x.hours for x in effort), Decimal()) * hourly_rate
    support_hours = Decimal("30"); support = support_hours * support_rate
    reduction = burden_before-burden_after; payback=calculate_payback(setup,reduction,support)
    before_q={q["question_id"]:q["weak_status"] for q in load_weak_native_coverage().questions
              if q["question_id"] in definition.affected_question_ids}
    after_q={q:AnswerStatus.PARTIALLY_ANSWERED for q in definition.affected_question_ids}
    decision = (EdgeDecision.EDGE_JUSTIFIED_FOR_FURTHER_ECONOMIC_TEST if ratio>0 and payback is not None
                else EdgeDecision.EDGE_TECHNICALLY_USEFUL_BUT_ECONOMICALLY_WEAK if ratio>0
                else EdgeDecision.EDGE_NOT_NEEDED)
    rationale = "Scope is bounded, three deterministic manual reviews are removed, true exceptions remain, and ownership adds only one rule and its failure path."
    return CustomEdgeAnalysis(definition, records, outcomes, MappingProxyType({x:counts[x] for x in CustomResult}),
      before,after,ratio,MappingProxyType(before_q),MappingProxyType(after_q),burden_before,burden_after,reduction,
      effort,setup,support_hours,support,payback,decision,rationale,
      ("export","mapping","automation","BI","manual review"),
      ("export","mapping","narrow rule","existing BI/automation","manual review for residuals"),
      ("mappings","reports","automations","configuration"),
      ("one custom rule/component","its tests","runtime/deployment assumption","its failure path"))


run_custom_edge_experiment = run_custom_edge
