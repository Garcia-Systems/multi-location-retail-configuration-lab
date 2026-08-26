from decimal import Decimal
import json

import pytest

from retail_configuration_lab.cli import main
from retail_configuration_lab.residual_gaps import (
    ORIGINAL_RECOVERABLE_VALUE, ResidualGapError, ResidualStatus,
    analyze_residual_gaps, load_residual_gaps, residual_gaps_from_dict,
)


def _raw():
    with open("data/residual_gaps.json", encoding="utf-8") as source:
        return json.load(source)


def test_inventory_reconciles_original_baseline_and_recoverable_boundary():
    inventory = load_residual_gaps()
    assert sum((x.original_annual_burden for x in inventory.categories), Decimal()) == Decimal("111020.00")
    assert inventory.original_recoverable_value == ORIGINAL_RECOVERABLE_VALUE == Decimal("51513.80")


def test_negative_burden_is_rejected():
    raw = _raw(); raw["categories"][0]["original_annual_burden"] = "-1"
    with pytest.raises(ResidualGapError, match="negative"):
        residual_gaps_from_dict(raw)


def test_invalid_status_is_rejected():
    raw = _raw(); raw["categories"][0]["residual_status"] = "SOLVED"
    with pytest.raises(ResidualGapError, match="classification"):
        residual_gaps_from_dict(raw)


def test_all_six_statuses_are_meaningfully_present():
    statuses = {x.residual_status for x in load_residual_gaps().categories}
    assert statuses == set(ResidualStatus)
    assert sum(x.residual_status is ResidualStatus.REDUCED for x in load_residual_gaps().categories) > 1


def test_ratio_drives_modeled_remaining_burden():
    identity = next(x for x in load_residual_gaps().categories if x.category_id == "identity-reconciliation")
    assert identity.calculated_remaining_burden == identity.modeled_remaining_burden == Decimal("2000.0000")


def test_totals_keep_administration_separate_and_reduction_modeled():
    result = analyze_residual_gaps()
    assert result.residual_operational_burden == Decimal("50920.00")
    assert result.new_administration_burden == Decimal("5400.00")
    assert result.combined_post_configuration_burden == Decimal("56320.00")
    assert result.modeled_burden_reduction == Decimal("54700.00")
    assert result.modeled_burden_reduction_ratio == Decimal("54700") / Decimal("111020")
    assert result.modeled_burden_reduction != result.original_recoverable_value


def test_accounting_support_and_unknown_remain_visible():
    categories = {x.category_id: x for x in load_residual_gaps().categories}
    assert categories["accounting-reconciliation"].residual_status is ResidualStatus.UNCHANGED
    assert categories["automation-failure-handling"].residual_status is ResidualStatus.NEW_SUPPORT_OBLIGATION
    assert categories["automation-failure-handling"].support_obligation
    assert categories["other-operational-exceptions"].residual_status is ResidualStatus.UNKNOWN


def test_question_references_and_ranking_are_deterministic():
    result = analyze_residual_gaps()
    assert result.question_residuals
    assert [x.category_id for x in result.largest_residuals[:3]] == [
        "accounting-reconciliation", "other-operational-exceptions", "inventory-mismatch-investigation"
    ]


def test_duplicate_and_bad_reference_validation():
    duplicate = _raw(); duplicate["categories"][1]["category_id"] = duplicate["categories"][0]["category_id"]
    with pytest.raises(ResidualGapError, match="duplicate"):
        residual_gaps_from_dict(duplicate)
    bad = _raw(); bad["categories"][0]["question_ids"] = ["NOPE-99"]
    with pytest.raises(ResidualGapError, match="nonexistent Chapter 2"):
        residual_gaps_from_dict(bad)


def test_cli_includes_economics_statuses_and_untested(capsys):
    assert main(["residual-gaps"]) == 0
    output = capsys.readouterr().out
    assert "Original annual burden: $111,020.00" in output
    assert "Combined post-configuration burden: $56,320.00" in output
    assert "Accounting reconciliation" in output and "UNCHANGED" in output
    assert "Current lab verdict: UNTESTED" in output
    for status in ResidualStatus:
        assert status.value in output
