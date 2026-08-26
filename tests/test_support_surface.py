import copy
import json
from decimal import Decimal

import pytest

from retail_configuration_lab.cli import main, support_surface_report
from retail_configuration_lab.questions import load_questions
from retail_configuration_lab.support_surface import (
    DEFAULT_SUPPORT_SURFACE_PATH, FrequencyModel, SupportCategory, SupportSurfaceError,
    analyze_support_surface, load_support_inventory, support_inventory_from_dict,
)


def raw_inventory():
    return json.loads(DEFAULT_SUPPORT_SURFACE_PATH.read_text())


def test_inventory_categories_dependencies_and_unique_ids():
    inventory = load_support_inventory()
    assert len({x.obligation_id for x in inventory.obligations}) == len(inventory.obligations) == 10
    assert {x.category for x in inventory.obligations} == set(SupportCategory)
    assert all(x.source_dependency for x in inventory.obligations)


@pytest.mark.parametrize("field", [
    "modeled_incidents_per_year", "modeled_hours_per_incident", "modeled_hourly_cost",
])
def test_negative_labor_input_fails(field):
    raw = raw_inventory(); raw["obligations"][0][field] = "-1"
    with pytest.raises(SupportSurfaceError): support_inventory_from_dict(raw)


def test_exact_support_economics_and_no_double_counting():
    inventory = load_support_inventory(); analysis = analyze_support_surface(inventory)
    assert all(x.annual_effort_hours == x.annual_modeled_effort for x in inventory.obligations)
    assert all(x.annual_support_cost == x.annual_modeled_cost for x in inventory.obligations)
    assert analysis.annual_support_labor_hours == Decimal("99.00")
    assert analysis.annual_support_labor_cost == Decimal("4800.00")
    assert analysis.annual_platform_cash_cost == Decimal("9000.00")
    assert analysis.annual_total_configuration_support_cost == Decimal("13800.00")
    assert inventory.replaces_chapter11_admin_estimate
    assert analysis.annual_total_configuration_support_cost != analysis.chapter11_new_administration_burden + Decimal("13800.00")
    assert analysis.support_cost_as_share_of_modeled_burden_reduction == Decimal("13800") / Decimal("54700")
    assert analysis.net_modeled_burden_reduction_after_support == Decimal("40900.00")


def test_required_obligations_and_prior_failure_evidence_exist():
    inventory=load_support_inventory(); categories={x.category for x in inventory.obligations}
    assert {SupportCategory.MAPPING_MAINTENANCE, SupportCategory.AUTOMATION_FAILURE_HANDLING,
        SupportCategory.BI_REPORT_MAINTENANCE, SupportCategory.ROLE_ACCESS_ADMINISTRATION,
        SupportCategory.VENDOR_SCHEMA_CONFIGURATION_CHANGES,
        SupportCategory.STORE_ONBOARDING_SUPPORT_PREPARATION} <= categories
    assert any(x.evidence_classification.value == "OBSERVED IMPLEMENTATION STRUCTURE" for x in inventory.obligations)
    assert any(x.evidence_classification.value == "OBSERVED LAB RESULT" for x in inventory.obligations)


def test_support_analysis_does_not_mutate_question_coverage():
    before=tuple((x.question_id,x.coverage_status) for x in load_questions().questions)
    analyze_support_surface()
    assert tuple((x.question_id,x.coverage_status) for x in load_questions().questions) == before


def test_invalid_frequency_dependency_platform_cost_and_reconciliation_fail():
    for mutation in ("frequency", "dependency", "platform", "double_count"):
        raw=copy.deepcopy(raw_inventory())
        if mutation == "frequency": raw["obligations"][0]["frequency_model"]="DAILY"
        elif mutation == "dependency": raw["obligations"][0]["source_dependency"]="config/nope.json"
        elif mutation == "platform": raw["platform_costs"][0]["annual_cost"]="-1"
        else: raw["replaces_chapter11_admin_estimate"]=False
        with pytest.raises(SupportSurfaceError): support_inventory_from_dict(raw)


def test_calculation_mismatches_and_duplicate_ids_fail():
    for field,value in (("annual_modeled_effort","999"),("annual_modeled_cost","999")):
        raw=raw_inventory(); raw["obligations"][0][field]=value
        with pytest.raises(SupportSurfaceError): support_inventory_from_dict(raw)
    raw=raw_inventory(); raw["obligations"][1]["obligation_id"]=raw["obligations"][0]["obligation_id"]
    with pytest.raises(SupportSurfaceError): support_inventory_from_dict(raw)


def test_cli_support_surface(capsys):
    assert main(["support-surface"]) == 0
    output=capsys.readouterr().out
    assert "Annual support labor cost" in output and "Annual platform cash cost" in output
    assert "OBLIGATION" in output and "configuration updated" in output
    assert "Current lab verdict: UNTESTED" in output
