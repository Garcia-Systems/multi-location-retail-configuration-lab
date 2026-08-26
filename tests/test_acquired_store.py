import json
from pathlib import Path
import subprocess
import sys

import pytest

from retail_configuration_lab.acquired_store import (
    DATA_PATH, STORE8_ID, AcquisitionResponse, AcquisitionValidationError,
    CompatibilityFit, load_acquired_store_experiment, recommend_response,
)


def test_identity_and_eight_store_scope_preserve_store7_control():
    x = load_acquired_store_experiment()
    assert x.store_id == STORE8_ID and len(x.store_ids) == 8
    assert x.store_ids[-2:] == ("JRO-STORE-007", STORE8_ID)
    assert x.store7_structural_reuse_ratio == pytest.approx(.70)


def test_fragmented_systems_and_capability_evidence_are_explicit():
    x = load_acquired_store_experiment()
    assert x.pos_system["id"] == "RidgePOS"
    assert x.inventory_system["id"] == "RidgeInventory"
    assert x.pos_system["capabilities"]["api"] == "UNKNOWN"


def test_mapping_outcomes_never_guess():
    x = load_acquired_store_experiment()
    assert x.mapping("BLTS-M-BL").resolved_canonical_sku == "JRO-1042-BLU-M"
    assert x.mapping("1042").resolved_canonical_sku is None
    assert len(x.mapping("1042").canonical_matches) == 2
    assert x.mapping("OLD-BLUE").kind == "UNMAPPED"
    assert x.mapping("SHEN-001").kind == "LOCAL_ONLY"
    assert x.mapping("BLTS-M-BL-2").kind == "APPARENT_DUPLICATE"
    assert "1042" in x.mapping("OLD-BLUE").historical_aliases


def test_return_and_transfer_fragmentation_stays_visible():
    x = load_acquired_store_experiment(); ret = x.raw["returns"][0]; transfer = x.raw["transfers"][0]
    assert ret["reason"] is None and ret["original_transaction"] is None
    assert ret["damaged_as_adjustment"] and not ret["cross_store_supported"]
    assert transfer["quantity_received"] is None and transfer["manually_edited"]
    assert x.raw["standardization"]["transfer_manual_after"] < x.raw["standardization"]["transfer_manual_before"]


def test_process_gap_is_distinct_and_standardization_cannot_fill_technical_gap():
    x = load_acquired_store_experiment()
    assert x.count_fit(CompatibilityFit.PROCESS_GAP) == 3
    assert x.count_fit(CompatibilityFit.TECHNICAL_GAP) == 1
    assert x.raw["standardization"]["residual_technical_gaps"] == 1


def test_open_scenario_tension_and_unknown_are_retained():
    x = load_acquired_store_experiment()
    assert x.count_fit(CompatibilityFit.MIGRATION_CANDIDATE) >= 1
    assert x.raw["custom_candidates"][0]["bounded"]
    assert x.count_fit(CompatibilityFit.UNKNOWN) >= 1
    assert x.raw["module_scenario"]["closes_gap"] is False


def test_scaling_and_fragmentation_metrics_use_compatible_denominator():
    x = load_acquired_store_experiment()
    assert x.structural_reuse_ratio == pytest.approx(5 / 20)
    assert x.fragmentation_reuse_delta == pytest.approx(.70 - .25)
    assert x.structural_reuse_ratio < x.store7_structural_reuse_ratio
    assert x.technical_gap_new_capability_ratio == pytest.approx(4 / 20)


def test_support_growth_and_question_degradation_are_visible():
    x = load_acquired_store_experiment()
    assert x.additional_support_surface_items == 6
    assert "second POS mapping maintenance" in x.raw["support_obligations"]
    assert "NOT_ANSWERED" in x.raw["question_coverage"].values()
    assert "UNKNOWN" in x.raw["question_coverage"].values()


def test_primary_response_comes_from_transparent_rule():
    decision = recommend_response(load_acquired_store_experiment())
    assert decision.primary_response is AcquisitionResponse.STANDARDIZE_FIRST
    assert AcquisitionResponse.MIGRATE_SYSTEM in decision.considered_responses
    assert "Identity and process gaps" in decision.rationale


@pytest.mark.parametrize(("mutation", "message"), [
    (lambda raw: raw["sku_mappings"].append(dict(raw["sku_mappings"][0])), "duplicate acquired-store mapping"),
    (lambda raw: raw["sku_mappings"][0].update(source_system="MissingSystem"), "invalid local source system reference"),
])
def test_unsafe_mapping_configuration_is_rejected(tmp_path: Path, mutation, message):
    raw = json.loads(DATA_PATH.read_text()); mutation(raw)
    path = tmp_path / "bad.json"; path.write_text(json.dumps(raw))
    with pytest.raises(AcquisitionValidationError, match=message):
        load_acquired_store_experiment(path)


def test_cli_acquired_store_traces_comparison_and_verdict():
    done = subprocess.run([sys.executable, "-m", "retail_configuration_lab", "acquired-store"], capture_output=True, text=True)
    assert done.returncode == 0
    for value in ("Store #7 structural reuse ratio", "Store #8 structural reuse ratio",
                  "Fragmentation reuse delta", "AMBIGUOUS", "DO NOT GUESS", "Unmapped identities",
                  "Primary response: STANDARDIZE_FIRST", "Current lab verdict: UNTESTED"):
        assert value in done.stdout
