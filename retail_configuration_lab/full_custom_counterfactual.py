"""Chapter 18: a model of broad custom integration, not an implementation of it."""
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from .baseline import load_baseline
from .custom_edge import run_custom_edge
from .evidence import EvidenceCategory
from .questions import load_questions
from .weak_native_coverage import AnswerStatus, load_weak_native_coverage


class CounterfactualValidationError(ValueError):
    pass


class ReuseClassification(StrEnum):
    GENERIC_REUSABLE = "GENERIC_REUSABLE"
    DOMAIN_REUSABLE = "DOMAIN_REUSABLE"
    CUSTOMER_CONFIGURED = "CUSTOMER_CONFIGURED"
    CUSTOMER_SPECIFIC = "CUSTOMER_SPECIFIC"
    UNKNOWN = "UNKNOWN"


class OwnershipClassification(StrEnum):
    VENDOR_OWNED = "VENDOR_OWNED"
    CONFIGURATION_OWNED = "CONFIGURATION_OWNED"
    CUSTOM_CODE_OWNED = "CUSTOM_CODE_OWNED"
    PROCESS_OWNED = "PROCESS_OWNED"
    SHARED = "SHARED"
    UNKNOWN = "UNKNOWN"


class ReliabilityRequirement(StrEnum):
    REQUIRED = "REQUIRED"
    NOT_REQUIRED = "NOT_REQUIRED"
    UNKNOWN = "UNKNOWN"


class FullCustomResult(StrEnum):
    FULL_CUSTOM_ADDS_MATERIAL_VALUE = "FULL_CUSTOM_ADDS_MATERIAL_VALUE"
    FULL_CUSTOM_ADDS_LIMITED_INCREMENTAL_VALUE = "FULL_CUSTOM_ADDS_LIMITED_INCREMENTAL_VALUE"
    FULL_CUSTOM_IS_DUPLICATIVE = "FULL_CUSTOM_IS_DUPLICATIVE"
    FULL_CUSTOM_TOO_BROAD_FOR_RESIDUAL = "FULL_CUSTOM_TOO_BROAD_FOR_RESIDUAL"
    FULL_CUSTOM_BLOCKED_BY_SOURCE_LIMITS = "FULL_CUSTOM_BLOCKED_BY_SOURCE_LIMITS"
    INVESTIGATE = "INVESTIGATE"
    UNKNOWN = "UNKNOWN"


SOURCE_SYSTEMS = frozenset({"pos", "inventory", "purchasing", "e-commerce", "accounting", "scheduling/exports"})
AUTHORITATIVE_SYSTEMS = MappingProxyType({
    "sales": "pos", "inventory": "inventory", "purchase orders": "purchasing",
    "online orders": "e-commerce", "accounting": "accounting",
})


@dataclass(frozen=True)
class CustomComponent:
    component_id: str
    name: str
    responsibility: str
    upstream_systems: tuple[str, ...]
    downstream_consumers: tuple[str, ...]
    authoritative: bool
    customer_specific: bool
    reuse: ReuseClassification
    runtime_ownership_required: bool
    observability_required: bool
    support_responsibility: str
    test_surface: str
    evidence_classification: EvidenceCategory = EvidenceCategory.MODELED_ALTERNATIVE_ASSUMPTION


@dataclass(frozen=True)
class Responsibility:
    name: str
    ownership: OwnershipClassification


@dataclass(frozen=True)
class ReliabilityCapability:
    name: str
    requirement: ReliabilityRequirement
    rationale: str


@dataclass(frozen=True)
class Allocation:
    name: str
    amount: Decimal


@dataclass(frozen=True)
class QuestionComparison:
    question_id: str
    question: str
    configuration_status: AnswerStatus
    full_custom_status: AnswerStatus
    required_source_evidence_available: bool
    rationale: str


@dataclass(frozen=True)
class BurdenComparison:
    residual_operational: Decimal
    administration: Decimal
    support: Decimal
    unknown: Decimal

    @property
    def total(self) -> Decimal:
        return self.residual_operational + self.administration + self.support + self.unknown


@dataclass(frozen=True)
class FullCustomCounterfactual:
    original_scope: tuple[str, ...]
    components: tuple[CustomComponent, ...]
    configuration_responsibilities: tuple[Responsibility, ...]
    full_custom_responsibilities: tuple[Responsibility, ...]
    reliability: tuple[ReliabilityCapability, ...]
    effort_allocation: tuple[Allocation, ...]
    delivery_cost_allocation: tuple[Allocation, ...]
    support_allocation: tuple[Allocation, ...]
    implementation_price: Decimal
    annual_customer_fee: Decimal
    question_coverage: tuple[QuestionComparison, ...]
    configuration_burden: BurdenComparison
    full_custom_burden: BurdenComparison
    result: FullCustomResult
    result_rationale: str
    overall_lab_verdict: str = "UNTESTED"

    @property
    def engineering_hours(self): return sum((x.amount for x in self.effort_allocation), Decimal())
    @property
    def direct_delivery_cost(self): return sum((x.amount for x in self.delivery_cost_allocation), Decimal())
    @property
    def modeled_full_custom_support_hours(self): return sum((x.amount for x in self.support_allocation), Decimal())
    @property
    def modeled_full_custom_support_cost(self): return self.modeled_full_custom_support_hours * Decimal("100")
    @property
    def configuration_answered_questions(self): return sum(x.configuration_status is AnswerStatus.ANSWERED for x in self.question_coverage)
    @property
    def full_custom_answered_questions(self): return sum(x.full_custom_status is AnswerStatus.ANSWERED for x in self.question_coverage)
    @property
    def incremental_question_gain_full_custom(self): return self.full_custom_answered_questions-self.configuration_answered_questions
    @property
    def incremental_modeled_burden_reduction_full_custom(self): return self.configuration_burden.residual_operational-self.full_custom_burden.residual_operational
    @property
    def configuration_custom_ownership_count(self): return sum(x.ownership is OwnershipClassification.CUSTOM_CODE_OWNED for x in self.configuration_responsibilities)
    @property
    def full_custom_ownership_count(self): return sum(x.ownership in {OwnershipClassification.CUSTOM_CODE_OWNED, OwnershipClassification.SHARED} for x in self.full_custom_responsibilities)
    @property
    def incremental_custom_ownership_count(self): return self.full_custom_ownership_count-self.configuration_custom_ownership_count
    @property
    def adapter_count(self): return sum(x.component_id.startswith("adapter-") for x in self.components)
    @property
    def customer_specific_component_count(self): return sum(x.customer_specific for x in self.components)
    @property
    def adapters_required(self): return tuple(x for x in self.components if x.component_id.startswith("adapter-"))
    @property
    def reconciliation_domains(self): return tuple(x for x in self.components if x.component_id.startswith("reconcile-"))
    @property
    def runtime_capabilities(self): return self.reliability
    @property
    def support_obligations(self): return tuple(x.name for x in self.support_allocation)
    @property
    def ownership_surface(self): return self.full_custom_responsibilities
    @property
    def custom_ownership_expansion(self): return (self.configuration_custom_ownership_count, self.full_custom_ownership_count)


def _component(identifier, name, responsibility, upstream=(), downstream=("canonical layer",), reuse=ReuseClassification.DOMAIN_REUSABLE, customer=False, runtime=True, observe=True):
    return CustomComponent(identifier, name, responsibility, tuple(upstream), tuple(downstream), False,
                           customer, reuse, runtime, observe, "provider maintains failures and changes",
                           "contracts, transformations, failures, and regression fixtures")


def component_inventory() -> tuple[CustomComponent, ...]:
    adapters = tuple(_component(f"adapter-{key}", name, "ingest / validate / transform / map", (key,)) for key, name in (
        ("pos", "POS adapter"), ("inventory", "Inventory adapter"), ("purchasing", "Purchasing adapter"),
        ("e-commerce", "E-commerce adapter"), ("accounting", "Accounting adapter"),
        ("scheduling/exports", "Scheduling/export adapter")))
    canonical = _component("canonical-identity", "Canonical identity and reference layer",
        "map store, SKU/product/variant, supplier, channel, order, PO, and transfer identity",
        SOURCE_SYSTEMS, ("reconciliation rules",), ReuseClassification.CUSTOMER_CONFIGURED, True)
    reconciliations = tuple(_component(f"reconcile-{key}", name, responsibility, (), ("exception model",),
        ReuseClassification.CUSTOMER_CONFIGURED, key in {"returns", "transfers"}) for key,name,responsibility in (
        ("sales", "Sales/channel reconciliation", "compare sales and channels"),
        ("inventory", "Inventory reconciliation", "compare expected and recorded stock"),
        ("purchasing", "Purchasing/receiving reconciliation", "compare POs and receipts"),
        ("returns", "Returns reconciliation", "apply local return semantics"),
        ("transfers", "Transfers reconciliation", "apply acquired-store and local transfer semantics"),
        ("accounting", "Accounting comparison", "compare operational and available ledger evidence")))
    remaining = (
        _component("exceptions", "Custom exception model", "classify unresolved identity, missing records, quantity/state mismatch, unsupported scenarios, and validation failure", (), ("briefing",), ReuseClassification.CUSTOMER_SPECIFIC, True),
        _component("runtime-scheduler", "Ingestion/execution scheduling", "schedule executions and preserve provenance", runtime=True),
        _component("runtime-reliability", "Retry, replay, and idempotency", "prevent duplicate effects and permit controlled recovery", runtime=True),
        _component("runtime-observability", "Logging, monitoring, and alerting", "make failures visible and actionable", runtime=True),
        _component("runtime-operations", "Deployment and operational support", "own releases, dependencies, vendor changes, escalation, and recovery", runtime=True),
        _component("report-briefing", "Management exception briefing", "apply James River materiality, ownership, and briefing rules", (), (), ReuseClassification.CUSTOMER_SPECIFIC, True),
        _component("report-feed", "Cross-system reporting feed", "publish reconciled records and exception provenance", (), (), ReuseClassification.DOMAIN_REUSABLE),
    )
    return adapters + (canonical,) + reconciliations + remaining


def load_full_custom_counterfactual() -> FullCustomCounterfactual:
    weak, edge, baseline = load_weak_native_coverage(), run_custom_edge(), load_baseline()
    config_status = {q["question_id"]: q["weak_status"] for q in weak.questions}
    config_status.update(edge.after_question_statuses)
    # Accounting detail is unavailable; missing return reasons remain process-caused.
    exceptions = {"FIN-01": AnswerStatus.NOT_ANSWERED, "INV-02": AnswerStatus.UNKNOWN,
                  "RET-02": AnswerStatus.PARTIALLY_ANSWERED}
    question_text = {q.question_id:q.question_text for q in load_questions().questions}
    coverage = tuple(QuestionComparison(qid, question_text[qid], status,
        exceptions.get(qid, AnswerStatus.ANSWERED), qid != "FIN-01",
        "Required records are modeled available." if qid != "FIN-01" else "Required accounting detail does not exist in modeled source evidence; custom code cannot fabricate it.")
        for qid,status in config_status.items())
    config_resp = tuple(Responsibility(*x) for x in (
        ("POS runtime",OwnershipClassification.VENDOR_OWNED), ("identity configuration",OwnershipClassification.CONFIGURATION_OWNED),
        ("native reporting",OwnershipClassification.VENDOR_OWNED), ("native connector configuration",OwnershipClassification.CONFIGURATION_OWNED),
        ("purchasing configuration",OwnershipClassification.CONFIGURATION_OWNED), ("returns/transfers rules",OwnershipClassification.CONFIGURATION_OWNED),
        ("automation",OwnershipClassification.SHARED), ("BI",OwnershipClassification.SHARED),
        ("receiving and return procedures",OwnershipClassification.PROCESS_OWNED), ("narrow reconciliation edge",OwnershipClassification.CUSTOM_CODE_OWNED)))
    components = component_inventory()
    full_resp = tuple(Responsibility(c.name, OwnershipClassification.CUSTOM_CODE_OWNED) for c in components) + (
        Responsibility("source-system runtime and truth", OwnershipClassification.VENDOR_OWNED),
        Responsibility("process compliance and physical receipt", OwnershipClassification.PROCESS_OWNED))
    reliability = tuple(ReliabilityCapability(n, ReliabilityRequirement.REQUIRED, r) for n,r in (
        ("idempotency","scheduled and replayed records must not duplicate results"), ("retry","transient source failures require bounded retry"),
        ("replay","operators need controlled recovery"), ("acknowledgements","ingestion needs durable completion evidence"),
        ("reconciliation","the system's purpose is cross-source comparison"), ("logging","support needs provenance and failure history"),
        ("alerting","unattended failures require escalation"), ("monitoring","provider owns runtime health")))
    effort = tuple(Allocation(n,Decimal(h)) for n,h in (("discovery/workflows",40),("source adapters",82),("canonical mappings",42),("reconciliation rules",62),("reliability/runtime",48),("reporting",22),("testing",38),("deployment/operations setup",16),("documentation/training",12),("contingency",16)))
    costs = tuple(Allocation(n,Decimal(v)) for n,v in (("engineering delivery","27000"),("operations setup","2440"),("documentation/training","1000"),("contingency","2000")))
    support = tuple(Allocation(n,Decimal(h)) for n,h in (("adapter/vendor changes",36),("monitoring and triage",30),("failures/replay",24),("deployments/dependencies",20),("custom rules",18),("user escalation",16)))
    config_burden = BurdenComparison(weak.residual_operational_burden-edge.modeled_incremental_burden_reduction,
                                    weak.administration_burden, edge.annual_custom_edge_support_cost, weak.unknown_burden)
    full_burden = BurdenComparison(Decimal("18000"),Decimal("12000"),Decimal("14400"),Decimal("6400"))
    scenario = FullCustomCounterfactual(tuple(baseline.system_categories),components,config_resp,full_resp,reliability,
        effort,costs,support,baseline.custom_implementation_price,baseline.custom_annual_recurring_fee,
        coverage,config_burden,full_burden,FullCustomResult.FULL_CUSTOM_ADDS_MATERIAL_VALUE,
        "Full custom answers materially more modeled questions and reduces operational burden, while expanding custom ownership across adapters, reconciliation, and runtime; source and process limits remain.")
    validate_counterfactual(scenario)
    return scenario


def derive_result(s: FullCustomCounterfactual) -> tuple[FullCustomResult, str]:
    """Apply named conditions; deliberately no score or economic success threshold."""
    missing_source = any(not q.required_source_evidence_available for q in s.question_coverage)
    if s.incremental_question_gain_full_custom > 1 and s.incremental_modeled_burden_reduction_full_custom > 0:
        return FullCustomResult.FULL_CUSTOM_ADDS_MATERIAL_VALUE, (
            "Full custom answers materially more modeled questions and reduces operational burden, "
            "while expanding custom ownership across adapters, reconciliation, and runtime; source and process limits remain.")
    if s.incremental_custom_ownership_count > 0 and (s.incremental_question_gain_full_custom == 1 or s.incremental_modeled_burden_reduction_full_custom > 0):
        return FullCustomResult.FULL_CUSTOM_ADDS_LIMITED_INCREMENTAL_VALUE, "Ownership expands, but modeled improvement is limited."
    if missing_source and s.incremental_question_gain_full_custom == 0:
        return FullCustomResult.FULL_CUSTOM_BLOCKED_BY_SOURCE_LIMITS, "Missing source evidence blocks incremental question coverage."
    if s.incremental_custom_ownership_count > 0 and s.incremental_question_gain_full_custom == 0:
        return FullCustomResult.FULL_CUSTOM_IS_DUPLICATIVE, "Ownership expands without incremental question coverage."
    return FullCustomResult.INVESTIGATE, "The explicit coverage, burden, and ownership conditions are inconclusive."


def validate_counterfactual(s: FullCustomCounterfactual) -> None:
    ids=[x.component_id for x in s.components]
    if len(ids)!=len(set(ids)): raise CounterfactualValidationError("duplicate full-custom component IDs")
    for c in s.components:
        try: ReuseClassification(c.reuse); EvidenceCategory(c.evidence_classification)
        except ValueError as exc: raise CounterfactualValidationError("invalid reuse classification") from exc
        if not set(c.upstream_systems)<=SOURCE_SYSTEMS: raise CounterfactualValidationError("nonexistent source system")
        if c.authoritative: raise CounterfactualValidationError("full custom replacing authoritative systems")
    for r in s.configuration_responsibilities+s.full_custom_responsibilities:
        try: OwnershipClassification(r.ownership)
        except ValueError as exc: raise CounterfactualValidationError("invalid ownership classification") from exc
    if any(x.amount<0 for x in s.effort_allocation+s.delivery_cost_allocation+s.support_allocation):
        raise CounterfactualValidationError("negative modeled hours/costs")
    if s.engineering_hours != Decimal("378"): raise CounterfactualValidationError("effort allocation must sum to 378")
    if s.direct_delivery_cost != Decimal("32440"): raise CounterfactualValidationError("delivery cost allocation must sum to 32440")
    for q in s.question_coverage:
        if q.full_custom_status is AnswerStatus.ANSWERED and not q.required_source_evidence_available:
            raise CounterfactualValidationError("question marked answered without required source evidence")
    edge=run_custom_edge()
    expected=load_weak_native_coverage().residual_operational_burden-edge.modeled_incremental_burden_reduction
    if s.configuration_burden.residual_operational != expected or s.configuration_custom_ownership_count != 1:
        raise CounterfactualValidationError("configuration-first comparison baseline inconsistent with Chapter 17")
    if not s.result_rationale.strip(): raise CounterfactualValidationError("chapter result without rationale")
    derived,_=derive_result(s)
    if s.result is not derived: raise CounterfactualValidationError("chapter result inconsistent with transparent rules")


run_full_custom_counterfactual = load_full_custom_counterfactual
