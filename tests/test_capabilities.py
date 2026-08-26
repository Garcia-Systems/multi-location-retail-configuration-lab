import copy
import json

import pytest

from retail_configuration_lab.capabilities import (
    DEFAULT_INVENTORY_PATH, CapabilityInventoryError, analyze_inventory,
    inventory_from_dict, load_inventory,
)
from retail_configuration_lab.cli import main
from retail_configuration_lab.models import CapabilityStatus


def raw_inventory():
    return json.loads(DEFAULT_INVENTORY_PATH.read_text(encoding="utf-8"))


def test_inventory_loads_and_all_system_references_resolve():
    inventory = load_inventory()
    system_ids = {system.identifier for system in inventory.systems}
    assert inventory.customer_name == "James River Outfitters"
    assert len(system_ids) == 11
    assert all(item.primary_system in system_ids for item in inventory.assessments)


def test_all_seven_statuses_are_valid_and_represented():
    assert {item.status for item in load_inventory().assessments} == set(CapabilityStatus)


@pytest.mark.parametrize("collection,id_key,error", [
    ("systems", "id", "duplicate system identifier"),
    ("capability_assessments", "capability_id", "duplicate capability identifier"),
])
def test_duplicate_identifiers_are_rejected(collection, id_key, error):
    raw = raw_inventory()
    duplicate = copy.deepcopy(raw[collection][0])
    duplicate[id_key] = raw[collection][0][id_key]
    raw[collection].append(duplicate)
    with pytest.raises(CapabilityInventoryError, match=error):
        inventory_from_dict(raw)


def test_unknown_requires_discovery_note():
    raw = raw_inventory()
    item = next(x for x in raw["capability_assessments"] if x["status"] == "UNKNOWN")
    del item["discovery_note"]
    with pytest.raises(CapabilityInventoryError, match="UNKNOWN requires a discovery note"):
        inventory_from_dict(raw)


@pytest.mark.parametrize("status", [
    "SUPPORTED_WITH_CONFIGURATION", "SUPPORTED_WITH_NATIVE_INTEGRATION",
])
def test_dependency_statuses_require_dependency(status):
    raw = raw_inventory()
    item = next(x for x in raw["capability_assessments"] if x["status"] == status)
    del item["dependency"]
    with pytest.raises(CapabilityInventoryError, match="requires a dependency"):
        inventory_from_dict(raw)


def test_expected_counts_and_non_custom_path_exclusions():
    result = analyze_inventory(load_inventory())
    assert result.total_capabilities == 51
    assert result.count_by_status == {
        CapabilityStatus.SUPPORTED: 19,
        CapabilityStatus.SUPPORTED_WITH_CONFIGURATION: 10,
        CapabilityStatus.SUPPORTED_WITH_NATIVE_INTEGRATION: 6,
        CapabilityStatus.EXPORT_ONLY: 6,
        CapabilityStatus.AUTOMATION_POSSIBLE: 5,
        CapabilityStatus.GAP: 2,
        CapabilityStatus.UNKNOWN: 3,
    }
    assert result.potentially_addressable_without_custom_software == 46
    assert result.potentially_addressable_without_custom_software == (
        result.total_capabilities - result.explicit_gaps - result.explicit_unknowns
    )


def test_cli_output_includes_statuses_and_caution(capsys):
    assert main(["capabilities"]) == 0
    output = capsys.readouterr().out
    for status in CapabilityStatus:
        assert status.value.replace("_", " ") + ":" in output
    assert "does not prove business value or implementation success" in output


def test_area_filter_only_filters_matrix_rows(capsys):
    assert main(["capabilities", "--area", "inventory"]) == 0
    output = capsys.readouterr().out
    matrix = output.split("Capability matrix (filtered rows)", 1)[1]
    assert "Inventory     On-hand quantity by store" in matrix
    assert "Sales by store" not in matrix
    assert "Total capabilities: 51" in output


def test_status_filter_only_filters_matrix_rows(capsys):
    assert main(["capabilities", "--status", "GAP"]) == 0
    matrix = capsys.readouterr().out.split("Capability matrix (filtered rows)", 1)[1]
    assert " GAP" in matrix
    assert " SUPPORTED\n" not in matrix
