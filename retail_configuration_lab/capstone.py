"""Chapter 20: a transparent synthesis of Chapters 0--19."""
from dataclasses import dataclass, replace
from enum import StrEnum
import json
from pathlib import Path

from .economics import analyze_economics
from .custom_edge import EdgeDecision, run_custom_edge
from .full_custom_counterfactual import FullCustomResult, load_full_custom_counterfactual
from .add_store import load_store7_experiment
from .acquired_store import load_acquired_store_experiment
from .strong_native_suite import load_strong_native_suite
from .weak_native_coverage import load_weak_native_coverage

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "final_verdict.json"

class CapstoneValidationError(ValueError): pass
class FinalVerdict(StrEnum):
    BUY_CONFIGURE="BUY / CONFIGURE"; CONFIGURE_AUTOMATION="CONFIGURE + AUTOMATION"
    NARROW_CUSTOM_EDGE="NARROW CUSTOM EDGE"; PROMISING="PROMISING — VALIDATE IN DISCOVERY"
    STANDARDIZE_FIRST="STANDARDIZE FIRST"; INVESTIGATE="INVESTIGATE"
    ONE_OFF_CUSTOM_PROJECT="ONE-OFF CUSTOM PROJECT"; NO_DEAL="NO DEAL"
class HypothesisEffect(StrEnum):
    STRENGTHENED="STRENGTHENED"; WEAKENED="WEAKENED"; QUALIFIED="QUALIFIED"; UNCHANGED="UNCHANGED"; INCONCLUSIVE="INCONCLUSIVE"

GATE_ENUMS={
 "existing_capability_sufficiency":{"STRONG","MODERATE","WEAK","UNKNOWN"},
 "residual_materiality":{"IMMATERIAL","BOUNDED_MATERIAL","BROAD_MATERIAL","UNKNOWN"},
 "support_burden":{"LOW","MANAGEABLE","MATERIAL","EXCESSIVE","UNKNOWN"},
 "scaling":{"STRONG_REUSE","CONDITIONAL_REUSE","WEAK_REUSE","UNKNOWN"},
 "fragmentation_sensitivity":{"LOW","MODERATE","HIGH","UNKNOWN"},
 "native_coverage_sensitivity":{"LOW_DEPENDENCE","MODERATE_DEPENDENCE","HIGH_DEPENDENCE","UNKNOWN"},
 "narrow_custom_value":{"NOT_NEEDED","ECONOMICALLY_WEAK","JUSTIFIED","TOO_BROAD","BLOCKED","UNKNOWN"},
 "full_custom_value":{"MATERIAL_INCREMENT","LIMITED_INCREMENT","DUPLICATIVE","TOO_BROAD","SOURCE_LIMITED","UNKNOWN"},
 "economics":{"ROBUST","SENSITIVITY_DEPENDENT","TOO_CLOSE","UNFAVORABLE","UNKNOWN"},
}

@dataclass(frozen=True)
class CapstoneDecision:
    original_cookbook_verdict: str; final_verdict: FinalVerdict; hypothesis_effect: HypothesisEffect
    gates: dict[str,str]; rationales: dict[str,str]; remaining_unknowns: tuple[str,...]
    discovery_conditions: tuple[str,...]; custom_software_should_own: tuple[str,...]
    custom_software_should_not_own: tuple[str,...]; evidence_categories: dict[str,tuple[str,...]]
    evidence_references: tuple[str,...]; economic_leader: str; first_year_leader: str
    three_year_leader: str; remaining_material_problem: str; confidence_qualifier: str
    scenario_results: dict[str,str]
    @property
    def original_verdict(self): return self.original_cookbook_verdict
    @property
    def custom_software_boundary(self):
        return {"should_own":self.custom_software_should_own,"should_not_own":self.custom_software_should_not_own}
    @property
    def rationale(self): return self.rationales

def hypothesis_effect_for(original: str, final: FinalVerdict) -> HypothesisEffect:
    if original == "BUY / CONFIGURE" and final is FinalVerdict.BUY_CONFIGURE: return HypothesisEffect.STRENGTHENED
    if original == "BUY / CONFIGURE" and final in {FinalVerdict.NARROW_CUSTOM_EDGE,FinalVerdict.CONFIGURE_AUTOMATION}: return HypothesisEffect.QUALIFIED
    if original == "BUY / CONFIGURE" and final in {FinalVerdict.INVESTIGATE,FinalVerdict.NO_DEAL,FinalVerdict.STANDARDIZE_FIRST,FinalVerdict.ONE_OFF_CUSTOM_PROJECT}: return HypothesisEffect.WEAKENED
    if final is FinalVerdict.PROMISING: return HypothesisEffect.INCONCLUSIVE
    return HypothesisEffect.UNCHANGED

def derive_final_verdict(g: dict[str,str], economic_leader: str, *, broad_customer_specific=False, blocking_gate=False) -> FinalVerdict:
    """Ordered rules, not a score: contradictions deliberately stop strong claims."""
    if g["economics"] == "UNFAVORABLE": return FinalVerdict.NO_DEAL
    if g["fragmentation_sensitivity"] == "HIGH" and g["scaling"] == "WEAK_REUSE": return FinalVerdict.STANDARDIZE_FIRST
    if broad_customer_specific and g["full_custom_value"] == "MATERIAL_INCREMENT": return FinalVerdict.ONE_OFF_CUSTOM_PROJECT
    if (g["existing_capability_sufficiency"] == "STRONG" and g["residual_materiality"] == "IMMATERIAL"
        and g["support_burden"] in {"LOW","MANAGEABLE"} and g["economics"] == "ROBUST" and not blocking_gate): return FinalVerdict.BUY_CONFIGURE
    if (g["existing_capability_sufficiency"] in {"STRONG","MODERATE"} and g["residual_materiality"] == "BOUNDED_MATERIAL"
        and g["narrow_custom_value"] == "JUSTIFIED" and g["full_custom_value"] in {"LIMITED_INCREMENT","TOO_BROAD"}
        and economic_leader == "configure-narrow-edge"): return FinalVerdict.NARROW_CUSTOM_EDGE
    if g["economics"] in {"TOO_CLOSE","SENSITIVITY_DEPENDENT","UNKNOWN"}: return FinalVerdict.INVESTIGATE
    if g["narrow_custom_value"] in {"NOT_NEEDED","ECONOMICALLY_WEAK"}: return FinalVerdict.CONFIGURE_AUTOMATION
    return FinalVerdict.PROMISING

def validate_capstone_decision(d: CapstoneDecision) -> None:
    if not d.original_cookbook_verdict: raise CapstoneValidationError("missing original verdict")
    if not isinstance(d.final_verdict, FinalVerdict): raise CapstoneValidationError("unsupported final verdict")
    if set(d.gates) != set(GATE_ENUMS): raise CapstoneValidationError("missing gate result")
    if any(d.gates[k] not in allowed for k,allowed in GATE_ENUMS.items()): raise CapstoneValidationError("invalid gate enum")
    if not d.rationales or any(not str(x).strip() for x in d.rationales.values()): raise CapstoneValidationError("missing rationale")
    if not d.remaining_unknowns or not d.discovery_conditions: raise CapstoneValidationError("missing discovery unknowns")
    if not d.evidence_references or any(not Path(__file__).resolve().parents[1].joinpath(x).exists() for x in d.evidence_references): raise CapstoneValidationError("missing evidence references")
    option_ids={x.option_id for x in analyze_economics().options}
    if d.economic_leader not in option_ids or d.first_year_leader not in option_ids or d.three_year_leader not in option_ids: raise CapstoneValidationError("economic leader reference does not exist")
    expected=derive_final_verdict(d.gates,d.economic_leader)
    if d.final_verdict is not expected: raise CapstoneValidationError("final verdict inconsistent with decision logic")
    if d.final_verdict is FinalVerdict.NARROW_CUSTOM_EDGE and d.gates["narrow_custom_value"] != "JUSTIFIED": raise CapstoneValidationError("edge is not bounded and justified")
    if d.final_verdict is FinalVerdict.BUY_CONFIGURE and d.gates["residual_materiality"] != "IMMATERIAL": raise CapstoneValidationError("material unresolved gap contradicts BUY / CONFIGURE")
    if d.final_verdict is FinalVerdict.NO_DEAL and d.gates["economics"] != "UNFAVORABLE": raise CapstoneValidationError("favorable economics contradict NO DEAL")
    if d.hypothesis_effect is not hypothesis_effect_for(d.original_cookbook_verdict,d.final_verdict): raise CapstoneValidationError("incorrect hypothesis effect")
    if set(d.evidence_categories)!={"observed_lab_results","modeled_assumptions","modeled_alternative_assumptions","unknown_discovery_required"}: raise CapstoneValidationError("evidence categories are mixed or incomplete")

def load_capstone_decision(path: Path|str=DATA_PATH) -> CapstoneDecision:
    raw=json.loads(Path(path).read_text())
    try:
        d=CapstoneDecision(raw["original_verdict"],FinalVerdict(raw["final_verdict"]),HypothesisEffect(raw["hypothesis_effect"]),raw["gates"],raw["rationales"],tuple(raw["remaining_unknowns"]),tuple(raw["discovery_requirements"]),tuple(raw["custom_boundary"]["should_own"]),tuple(raw["custom_boundary"]["should_not_own"]),{k:tuple(v) for k,v in raw["evidence_inventory"].items()},tuple(raw["evidence_references"]),raw["economic_leader"],raw["first_year_leader"],raw["three_year_leader"],raw["remaining_material_problem"],raw["confidence_qualifier"],raw["scenario_results"])
    except (KeyError,ValueError,TypeError) as e: raise CapstoneValidationError("invalid final verdict artifact") from e
    validate_capstone_decision(d); return d

def run_capstone(path: Path|str=DATA_PATH) -> CapstoneDecision:
    d=load_capstone_decision(path); economics=analyze_economics(); edge=run_custom_edge(); full=load_full_custom_counterfactual()
    if d.first_year_leader != economics.rankings["highest_first_year_net_benefit"].option_id or d.three_year_leader != economics.rankings["highest_three_year_net_benefit"].option_id: raise CapstoneValidationError("Chapter 19 result not reused")
    if d.gates["narrow_custom_value"]=="JUSTIFIED" and edge.decision is not EdgeDecision.EDGE_JUSTIFIED_FOR_FURTHER_ECONOMIC_TEST: raise CapstoneValidationError("Chapter 17 result not reused")
    if d.gates["full_custom_value"]=="MATERIAL_INCREMENT" and full.result is not FullCustomResult.FULL_CUSTOM_ADDS_MATERIAL_VALUE: raise CapstoneValidationError("Chapter 18 result not reused")
    # Loading these sources ensures their validated structures remain prerequisites.
    load_store7_experiment(); load_acquired_store_experiment(); load_strong_native_suite(); load_weak_native_coverage()
    return d

load_final_verdict=load_capstone_decision
