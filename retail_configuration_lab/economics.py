"""Chapter 19 deterministic buyer economics (never observed customer ROI)."""
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum

from .baseline import load_baseline
from .custom_edge import run_custom_edge
from .evidence import EvidenceCategory
from .full_custom_counterfactual import load_full_custom_counterfactual
from .support_surface import analyze_support_surface


class EconomicValidationError(ValueError): pass


class EconomicResult(StrEnum):
    BUY_CONFIGURE_ECONOMICALLY_STRONGEST="BUY_CONFIGURE_ECONOMICALLY_STRONGEST"
    CONFIGURE_AUTOMATION_ECONOMICALLY_STRONGEST="CONFIGURE_AUTOMATION_ECONOMICALLY_STRONGEST"
    NARROW_CUSTOM_EDGE_ECONOMICALLY_STRONGEST="NARROW_CUSTOM_EDGE_ECONOMICALLY_STRONGEST"
    FULL_CUSTOM_ECONOMICALLY_STRONGEST="FULL_CUSTOM_ECONOMICALLY_STRONGEST"
    NO_INTERVENTION_ECONOMICALLY_STRONGEST="NO_INTERVENTION_ECONOMICALLY_STRONGEST"
    ECONOMICS_TOO_CLOSE="ECONOMICS_TOO_CLOSE"
    ECONOMICS_DEPEND_ON_SENSITIVITY="ECONOMICS_DEPEND_ON_SENSITIVITY"
    UNKNOWN="UNKNOWN"


@dataclass(frozen=True)
class EconomicOption:
    option_id: str; option_name: str
    setup_implementation_cash_cost: Decimal
    internal_setup_labor_cost: Decimal
    annual_platform_cash_cost: Decimal
    annual_support_labor_cost: Decimal
    annual_administration_cost: Decimal
    annual_residual_operational_burden: Decimal
    annual_custom_code_support_cost: Decimal
    annual_risk_allowance: Decimal
    modeled_annual_recoverable_value_captured: Decimal
    component_ids: tuple[str, ...]
    evidence_sources: tuple[str, ...]
    uncertainty_notes: tuple[str, ...]
    evidence_classifications: tuple[EvidenceCategory, ...]
    residual_over_baseline_explanation: str = ""

    @property
    def setup_cost(self): return self.setup_implementation_cash_cost+self.internal_setup_labor_cost
    @property
    def annual_recurring_cash_cost(self): return self.annual_platform_cash_cost
    @property
    def annual_administration_cost_total(self): return self.annual_administration_cost
    @property
    def residual_operational_burden(self): return self.annual_residual_operational_burden
    @property
    def annual_support_cost(self): return self.annual_support_labor_cost+self.annual_custom_code_support_cost
    @property
    def annual_ownership_cost(self):
        return self.annual_platform_cash_cost+self.annual_administration_cost+self.annual_support_cost+self.annual_risk_allowance
    @property
    def annual_gross_burden_reduction(self): return ORIGINAL_ANNUAL_BURDEN-self.annual_residual_operational_burden
    @property
    def annual_net_benefit_before_setup(self): return self.annual_gross_burden_reduction-self.annual_ownership_cost
    @property
    def first_year_net_benefit(self): return self.annual_net_benefit_before_setup-self.setup_cost
    @property
    def recurring_year_net_benefit(self): return self.annual_net_benefit_before_setup
    @property
    def total_first_year_economic_cost(self): return self.setup_cost+self.annual_ownership_cost+self.annual_residual_operational_burden
    @property
    def total_recurring_year_economic_cost(self): return self.annual_ownership_cost+self.annual_residual_operational_burden
    @property
    def three_year_total_cost(self): return self.setup_cost+Decimal(3)*self.total_recurring_year_economic_cost
    @property
    def three_year_net_benefit(self): return Decimal(3)*self.annual_net_benefit_before_setup-self.setup_cost
    @property
    def simple_payback_years(self):
        if self.option_id == "do-nothing" or self.annual_net_benefit_before_setup <= 0: return None
        return self.setup_cost/self.annual_net_benefit_before_setup
    @property
    def recoverable_value_capture_ratio(self):
        return self.modeled_annual_recoverable_value_captured/ORIGINAL_RECOVERABLE_VALUE if ORIGINAL_RECOVERABLE_VALUE else Decimal()
    @property
    def recoverable_value_guardrail_exceeded(self): return self.annual_net_benefit_before_setup > ORIGINAL_RECOVERABLE_VALUE


@dataclass(frozen=True)
class SensitivityScenario:
    scenario_id: str; name: str; option_id: str; field: str; value: Decimal; rationale: str

@dataclass(frozen=True)
class SensitivityOutcome:
    scenario: SensitivityScenario; leader: str; base_leader: str
    @property
    def leader_changed(self): return self.leader != self.base_leader

@dataclass(frozen=True)
class EconomicAnalysis:
    options: tuple[EconomicOption,...]; sensitivities: tuple[SensitivityOutcome,...]
    result: EconomicResult; result_rationale: str; overall_lab_verdict: str="UNTESTED"
    original_annual_burden: Decimal=ORIGINAL_ANNUAL_BURDEN if 'ORIGINAL_ANNUAL_BURDEN' in globals() else Decimal("111020.00")
    original_recoverable_value: Decimal=ORIGINAL_RECOVERABLE_VALUE if 'ORIGINAL_RECOVERABLE_VALUE' in globals() else Decimal("51513.80")
    @property
    def rankings(self):
        positive=[x for x in self.options if x.simple_payback_years is not None]
        return {"lowest_first_year_economic_cost":min(self.options,key=lambda x:(x.total_first_year_economic_cost,x.option_id)),
                "highest_first_year_net_benefit":max(self.options,key=lambda x:(x.first_year_net_benefit,x.option_id)),
                "highest_three_year_net_benefit":max(self.options,key=lambda x:(x.three_year_net_benefit,x.option_id)),
                "shortest_positive_payback":min(positive,key=lambda x:(x.simple_payback_years,x.option_id)) if positive else None,
                "lowest_residual_burden":min(self.options,key=lambda x:(x.annual_residual_operational_burden,x.option_id)),
                "lowest_annual_ownership_support_cost":min(self.options,key=lambda x:(x.annual_ownership_cost,x.option_id))}
    @property
    def dominated_options(self): return dominance_analysis(self.options)


ORIGINAL_ANNUAL_BURDEN=Decimal("111020.00")
ORIGINAL_RECOVERABLE_VALUE=Decimal("51513.80")

def _option(identifier,name,setup,platform,admin,support,residual,custom_support,risk,captured,components,sources,notes):
    d=lambda x: Decimal(str(x))
    return EconomicOption(identifier,name,d(setup),Decimal(),d(platform),d(support),d(admin),d(residual),d(custom_support),d(risk),d(captured),tuple(components),tuple(sources),tuple(notes),(EvidenceCategory.MODELED_ASSUMPTION,EvidenceCategory.OBSERVED_IMPLEMENTATION_STRUCTURE))

def load_economic_options() -> tuple[EconomicOption,...]:
    baseline=load_baseline(); support=analyze_support_surface(); edge=run_custom_edge(); full=load_full_custom_counterfactual()
    # BI is core to configured scope. Chapter 12's $9k cash includes BI/automation; $4.8k labor is
    # split here into $1.8k administration and $3k support, replacing (not adding to) Ch. 11 admin.
    options=(
      _option("do-nothing","DO NOTHING",0,0,0,0,baseline.annual_current_state_burden,0,5000,0,
              ("current-state-risk",),("data/baseline_case.json",),("Risk models continued scaling exposure; existing SaaS is outside the incremental decision.",)),
      _option("buy-configure","BUY / CONFIGURE",18000,6000,1800,2400,58000,0,2500,Decimal("36059.66"),
              ("native-modules","configuration-admin","configuration-support","vendor-risk"),("book/11-what-still-hurts.md","data/support_surface.json"),("BI is included; Chapter 8 automation is excluded.",)),
      _option("configure-automation","CONFIGURE + AUTOMATION",25000,support.annual_platform_cash_cost,1800,3000,support.residual_operational_burden,0,3500,Decimal("43786.73"),
              ("platform-cash","configuration-admin","configuration-support","automation-risk"),("data/support_surface.json","data/residual_gaps.json"),("Chapter 12 labor is reconciled between admin and support.",)),
      _option("configure-narrow-edge","CONFIGURE + NARROW CUSTOM EDGE",Decimal("25000")+edge.modeled_custom_edge_setup_cost,support.annual_platform_cash_cost,1800,3000,support.residual_operational_burden-edge.modeled_incremental_burden_reduction,edge.annual_custom_edge_support_cost,4500,Decimal("47220.99"),
              ("platform-cash","configuration-admin","configuration-support","edge-support","edge-risk"),("data/support_surface.json","retail_configuration_lab/custom_edge.py"),("Bounded edge support is separate from configuration support.",)),
      _option("full-custom","FULL CUSTOM",full.implementation_price,full.annual_customer_fee,3000,2400,full.full_custom_burden.residual_operational,0,8000,Decimal("48998.11"),
              ("annual-vendor-fee","buyer-admin","buyer-support","broad-runtime-risk"),("data/baseline_case.json","retail_configuration_lab/full_custom_counterfactual.py"),("Annual fee includes vendor runtime support; provider's $14,400 delivery support is not charged again.",)),)
    validate_options(options)
    return options

def validate_options(options):
    baseline=load_baseline()
    if baseline.annual_current_state_burden!=ORIGINAL_ANNUAL_BURDEN or baseline.recoverable_annual_value!=ORIGINAL_RECOVERABLE_VALUE: raise EconomicValidationError("Chapter 0 baseline changed")
    ids=[x.option_id for x in options]
    if len(ids)!=len(set(ids)): raise EconomicValidationError("duplicate option IDs")
    for x in options:
        values=(x.setup_implementation_cash_cost,x.internal_setup_labor_cost,x.annual_platform_cash_cost,x.annual_support_labor_cost,x.annual_administration_cost,x.annual_residual_operational_burden,x.annual_custom_code_support_cost,x.annual_risk_allowance)
        if any(v<0 for v in values): raise EconomicValidationError("negative economic cost")
        if x.annual_residual_operational_burden>ORIGINAL_ANNUAL_BURDEN and not x.residual_over_baseline_explanation: raise EconomicValidationError("residual burden above baseline without explanation")
        if len(x.component_ids)!=len(set(x.component_ids)): raise EconomicValidationError("duplicate cost component")
        if not x.evidence_sources or not x.uncertainty_notes: raise EconomicValidationError("missing evidence or uncertainty")
    do=next(x for x in options if x.option_id=="do-nothing")
    full=next(x for x in options if x.option_id=="full-custom")
    if do.setup_cost or do.annual_residual_operational_burden!=ORIGINAL_ANNUAL_BURDEN: raise EconomicValidationError("invalid do-nothing baseline")
    if full.setup_implementation_cash_cost!=Decimal("62000.00"): raise EconomicValidationError("full-custom implementation price must equal $62,000")
    if full.annual_platform_cash_cost!=Decimal("15000.00"): raise EconomicValidationError("full-custom annual fee must equal $15,000")

def dominance_analysis(options):
    result=[]
    for a in options:
        for b in options:
            av=(a.setup_cost,a.annual_ownership_cost,a.annual_residual_operational_burden); bv=(b.setup_cost,b.annual_ownership_cost,b.annual_residual_operational_burden)
            if a is not b and all(y<=x for x,y in zip(av,bv)) and any(y<x for x,y in zip(av,bv)):
                result.append(a.option_name); break
    return tuple(result)

def _leader(options): return max(options,key=lambda x:(x.three_year_net_benefit,x.first_year_net_benefit,x.option_id)).option_id

def sensitivity_definitions():
    return (SensitivityScenario("low-config-support","Low configuration support","configure-automation","annual_support_labor_cost",Decimal("1800"),"Less failure handling."),
            SensitivityScenario("high-config-support","High configuration support","configure-automation","annual_support_labor_cost",Decimal("7000"),"More failure handling."),
            SensitivityScenario("high-residual","High residual burden","configure-automation","annual_residual_operational_burden",Decimal("60000"),"Configured execution underperforms."),
            SensitivityScenario("low-edge-value","Low narrow-edge value","configure-narrow-edge","annual_residual_operational_burden",Decimal("49500"),"The edge captures less burden."),
            SensitivityScenario("high-full-support","High full-custom support","full-custom","annual_support_labor_cost",Decimal("8000"),"Buyer support exceeds base."))

def apply_sensitivity(options,scenario):
    if scenario.option_id not in {x.option_id for x in options}: raise EconomicValidationError("invalid sensitivity reference")
    if scenario.field not in {"annual_support_labor_cost","annual_residual_operational_burden"}: raise EconomicValidationError("invalid sensitivity field")
    changed=tuple(replace(x,**{scenario.field:scenario.value}) if x.option_id==scenario.option_id else x for x in options)
    validate_options(changed); return changed

def analyze_economics() -> EconomicAnalysis:
    options=load_economic_options(); base=_leader(options)
    outcomes=tuple(SensitivityOutcome(s,_leader(apply_sensitivity(options,s)),base) for s in sensitivity_definitions())
    first=max(options,key=lambda x:x.first_year_net_benefit).option_id; three=max(options,key=lambda x:x.three_year_net_benefit).option_id
    if all(x.first_year_net_benefit<0 for x in options if x.option_id!="do-nothing"): result=EconomicResult.NO_INTERVENTION_ECONOMICALLY_STRONGEST
    elif first!=three: result=EconomicResult.ECONOMICS_TOO_CLOSE
    elif any(x.leader_changed for x in outcomes): result=EconomicResult.ECONOMICS_DEPEND_ON_SENSITIVITY
    else: result={"buy-configure":EconomicResult.BUY_CONFIGURE_ECONOMICALLY_STRONGEST,"configure-automation":EconomicResult.CONFIGURE_AUTOMATION_ECONOMICALLY_STRONGEST,"configure-narrow-edge":EconomicResult.NARROW_CUSTOM_EDGE_ECONOMICALLY_STRONGEST,"full-custom":EconomicResult.FULL_CUSTOM_ECONOMICALLY_STRONGEST,"do-nothing":EconomicResult.NO_INTERVENTION_ECONOMICALLY_STRONGEST}.get(first,EconomicResult.UNKNOWN)
    rationale=f"First-year leader is {first}; three-year leader is {three}; sensitivity changes leader: {any(x.leader_changed for x in outcomes)}."
    if not rationale: raise EconomicValidationError("chapter result without rationale")
    return EconomicAnalysis(options,outcomes,result,rationale)

run_economics=analyze_economics
