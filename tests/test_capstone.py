from dataclasses import replace
import subprocess, sys
import pytest

from retail_configuration_lab.capstone import (CapstoneValidationError, FinalVerdict,
    HypothesisEffect, GATE_ENUMS, derive_final_verdict, load_capstone_decision,
    run_capstone, validate_capstone_decision)
from retail_configuration_lab.economics import analyze_economics
from retail_configuration_lab.custom_edge import EdgeDecision, run_custom_edge
from retail_configuration_lab.full_custom_counterfactual import FullCustomResult, load_full_custom_counterfactual
from retail_configuration_lab.add_store import load_store7_experiment
from retail_configuration_lab.acquired_store import load_acquired_store_experiment
from retail_configuration_lab.strong_native_suite import load_strong_native_suite
from retail_configuration_lab.weak_native_coverage import load_weak_native_coverage


def test_capstone_loads_and_is_deterministic():
    assert run_capstone() == run_capstone()

def test_original_and_final_vocabulary():
    d=run_capstone(); assert d.original_verdict == "BUY / CONFIGURE"; assert d.final_verdict in FinalVerdict

def test_all_gates_are_populated():
    d=run_capstone(); assert set(d.gates)==set(GATE_ENUMS); assert all(d.gates.values())

def test_chapter_19_is_reused():
    d=run_capstone(); e=analyze_economics()
    assert d.first_year_leader==e.rankings["highest_first_year_net_benefit"].option_id
    assert d.three_year_leader==e.rankings["highest_three_year_net_benefit"].option_id

def test_chapters_17_and_18_are_reused():
    assert run_custom_edge().decision is EdgeDecision.EDGE_JUSTIFIED_FOR_FURTHER_ECONOMIC_TEST
    assert load_full_custom_counterfactual().result is FullCustomResult.FULL_CUSTOM_ADDS_MATERIAL_VALUE
    assert run_capstone().gates["narrow_custom_value"]=="JUSTIFIED"

def test_scenario_sources_are_reused():
    d=run_capstone(); assert load_store7_experiment().structural_reuse_ratio > load_acquired_store_experiment().structural_reuse_ratio
    assert load_strong_native_suite().total_questions and load_weak_native_coverage().questions
    assert set(d.scenario_results)=={"base_configured_ecosystem","strong_native_suite","weak_native_coverage","standardized_store_7","fragmented_store_8"}

def test_decision_has_required_explanation():
    d=run_capstone(); assert d.rationales and d.remaining_material_problem and d.custom_software_boundary
    assert d.discovery_conditions and d.remaining_unknowns and d.confidence_qualifier

def test_invalid_gate_and_unsupported_verdict_are_rejected():
    d=load_capstone_decision(); bad=dict(d.gates); bad["economics"]="MAGIC"
    with pytest.raises(CapstoneValidationError): validate_capstone_decision(replace(d,gates=bad))
    with pytest.raises(ValueError): FinalVerdict("FULL CUSTOM")

def test_buy_configure_requires_noncontradictory_gates():
    d=load_capstone_decision()
    with pytest.raises(CapstoneValidationError): validate_capstone_decision(replace(d,final_verdict=FinalVerdict.BUY_CONFIGURE,hypothesis_effect=HypothesisEffect.STRENGTHENED))

def test_edge_requires_justified_bounded_gap():
    d=load_capstone_decision(); bad=dict(d.gates); bad["narrow_custom_value"]="NOT_NEEDED"
    with pytest.raises(CapstoneValidationError): validate_capstone_decision(replace(d,gates=bad,final_verdict=FinalVerdict.NARROW_CUSTOM_EDGE,hypothesis_effect=HypothesisEffect.QUALIFIED))

def test_one_off_and_no_deal_require_supporting_evidence():
    d=load_capstone_decision()
    for verdict in (FinalVerdict.ONE_OFF_CUSTOM_PROJECT,FinalVerdict.NO_DEAL):
        with pytest.raises(CapstoneValidationError): validate_capstone_decision(replace(d,final_verdict=verdict))

def test_hypothesis_effect_and_evidence_categories():
    d=run_capstone(); assert d.hypothesis_effect is HypothesisEffect.WEAKENED
    assert set(d.evidence_categories)=={"observed_lab_results","modeled_assumptions","modeled_alternative_assumptions","unknown_discovery_required"}

def test_cli_capstone_content():
    p=subprocess.run([sys.executable,"-m","retail_configuration_lab","capstone"],text=True,capture_output=True)
    assert p.returncode==0
    for text in ("Original cookbook verdict","BUY / CONFIGURE","Final lab verdict","Effect on original hypothesis","Chapter 19 economic leader","Remaining material problem","Discovery required","Custom software boundary","FINAL VERDICT:"):
        assert text in p.stdout
