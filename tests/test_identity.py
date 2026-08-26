import subprocess
import sys

import pytest

from retail_configuration_lab.identity import (
    IdentityType, MappingStatus, load_identity_configuration, run_identity_experiment,
)


@pytest.fixture(scope="module")
def config():
    return load_identity_configuration()


def test_all_six_domains_load_and_relationships_remain_distinct(config):
    assert set(config.identities) == set(IdentityType)
    sku = config.identities[IdentityType.SKU][0]
    variant = config.identities[IdentityType.VARIANT][0]
    assert sku.canonical_id != sku.product_id != sku.variant_id
    assert variant.product_id == sku.product_id


@pytest.mark.parametrize(("kind", "system", "source", "expected"), [
    (IdentityType.STORE, "RiverStock", "STORE_1", "JRO-STORE-001"),
    (IdentityType.SKU, "RiverStock", "1042", "JRO-1042-BLU-M"),
    (IdentityType.SUPPLIER, "RiverBooks", "VENDOR-281", "JRO-SUPPLIER-014"),
    (IdentityType.CHANNEL, "RiverBooks", "ECOM", "JRO-CHANNEL-ECOM"),
])
def test_confirmed_domain_mappings(config, kind, system, source, expected):
    resolved = config.resolve(kind, system, source)
    assert resolved.canonical_id == expected
    assert resolved.status is MappingStatus.CONFIRMED
    assert resolved.source_identifier == source
    assert resolved.provenance


def test_unknown_is_not_guessed(config):
    result = config.resolve(IdentityType.STORE, "RiverPOS", "NOT-A-STORE")
    assert result.status is MappingStatus.UNMAPPED
    assert result.canonical_id is None


def test_ambiguous_and_conflicting_evidence_remain_unresolved(config):
    ambiguous = config.resolve("SKU", "Spreadsheet", "SHIRT-M")
    conflict = config.resolve("SUPPLIER", "Spreadsheet", "BR-TG")
    assert ambiguous.status is MappingStatus.AMBIGUOUS and ambiguous.canonical_id is None
    assert len(ambiguous.candidate_canonical_ids) == 2
    assert conflict.status is MappingStatus.CONFLICT and conflict.canonical_id is None


def test_experiment_preserves_true_exceptions_and_removes_false_ones():
    result = run_identity_experiment()
    assert result.raw_comparisons == 9
    assert result.raw_direct_matches == 1
    assert result.raw_apparent_mismatches == 8
    assert result.canonical_matches == 6
    assert result.false_exceptions_eliminated == 3
    assert result.true_operational_exceptions_remaining == 2
    assert result.ambiguous_identities == result.unmapped_identities == result.conflicts == 1
    assert result.pre_standardization_identity_driven_false_exceptions == 6
    assert result.false_exception_elimination_ratio == 0.5
    classes = {outcome.classification for outcome in result.outcomes}
    assert "FALSE_EXCEPTION_ELIMINATED" in classes
    assert "TRUE_OPERATIONAL_EXCEPTION" in classes
    assert {"INV-01", "ECOM-01", "TRN-01", "RET-01", "PUR-02", "FIN-01"} <= set(
        result.relevant_chapter_2_questions_affected
    )


def test_identity_cli_sections_and_examples():
    completed = subprocess.run(
        [sys.executable, "-m", "retail_configuration_lab", "identity"],
        check=False, capture_output=True, text=True,
    )
    assert completed.returncode == 0
    assert "Before standardization" in completed.stdout
    assert "After configured identity mapping" in completed.stdout
    assert "ELIMINATED FALSE EXCEPTION" in completed.stdout
    assert "TRUE EXCEPTION REMAINS" in completed.stdout
    assert "Current lab verdict: UNTESTED" in completed.stdout
