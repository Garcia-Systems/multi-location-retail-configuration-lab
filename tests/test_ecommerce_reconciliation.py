import copy
import json
import subprocess
import sys

import pytest

from retail_configuration_lab.ecommerce_reconciliation import (
    DEFAULT_CONNECTOR_PATH, DEFAULT_ORDERS_PATH, EcommerceValidationError,
    ReconciliationResult, connector_from_dict, load_connector_configuration,
    load_orders, orders_from_dict, reconcile_order, run_ecommerce_reconciliation,
)
from retail_configuration_lab.identity import load_identity_configuration
from retail_configuration_lab.native_reporting import QuestionResult


def connector_raw():
    return json.loads(DEFAULT_CONNECTOR_PATH.read_text())


def orders_raw():
    return json.loads(DEFAULT_ORDERS_PATH.read_text())


def outcome(order_id):
    result = run_ecommerce_reconciliation()
    return next(item for item in result.outcomes if item.order.online_order_id == order_id)


def test_native_connector_configuration_loads_and_systems_and_channel_resolve():
    connector = load_connector_configuration()
    assert connector.enabled
    assert connector.source_system == "rivercommerce"
    assert set(connector.target_systems) == {"riverpos", "riverstock", "riverreturns"}
    assert connector.canonical_channel_id == "JRO-CHANNEL-ECOM"


def test_valid_fulfillment_store_mapping_resolves():
    assert load_connector_configuration().fulfillment_store_mapping["fulfillment_yorktown"] == "JRO-STORE-003"


def test_invalid_store_mapping_is_rejected():
    raw = connector_raw()
    raw["fulfillment_store_mapping"]["bad"] = "JRO-STORE-999"
    with pytest.raises(EcommerceValidationError, match="nonexistent store"):
        connector_from_dict(raw)


@pytest.mark.parametrize("order_id", ["WEB-100184", "WEB-100185", "WEB-100186", "WEB-100187", "WEB-100188"])
def test_normal_fulfillment_cancellation_paths_and_original_return_reconcile(order_id):
    assert outcome(order_id).result is ReconciliationResult.RECONCILED


def test_fulfilled_quantity_mismatch_remains_exception():
    item = outcome("WEB-100192")
    assert item.result is ReconciliationResult.EXCEPTION
    assert item.expected_inventory_effect == -2 and item.order.inventory_effect == -1


@pytest.mark.parametrize("order_id", ["WEB-100190", "WEB-100191"])
def test_unknown_store_or_sku_becomes_unresolved_identity(order_id):
    assert outcome(order_id).result is ReconciliationResult.UNRESOLVED_IDENTITY


def test_channel_remains_distinct_from_fulfillment_store():
    item = outcome("WEB-100184")
    assert item.canonical_channel_id == "JRO-CHANNEL-ECOM"
    assert item.canonical_store_id == "JRO-STORE-003"
    assert item.canonical_channel_id != item.canonical_store_id


def test_incorrect_cancellation_effect_is_exception():
    assert outcome("WEB-100194").result is ReconciliationResult.EXCEPTION


def test_cross_store_return_is_partial():
    assert outcome("WEB-100189").result is ReconciliationResult.PARTIALLY_RECONCILED


def test_connector_acknowledgement_failure_is_surfaced():
    item = outcome("WEB-100193")
    assert item.result is ReconciliationResult.EXCEPTION
    assert "acknowledgement" in item.reasons[0]


def test_before_after_metrics_and_rates_match_fixture():
    result = run_ecommerce_reconciliation()
    assert result.before.orders_requiring_manual_reconciliation == 12
    assert result.orders_requiring_manual_reconciliation_after == 7
    assert result.automatically_linked_orders == 10
    assert result.manual_reconciliation_reduction_ratio == pytest.approx(5 / 12)
    assert result.native_reconciliation_rate == pytest.approx(5 / 9)


def test_relevant_chapter_two_question_coverage_updates_without_regression():
    impacts = {item.question_id: item.status for item in run_ecommerce_reconciliation().question_impacts}
    assert impacts == {"SAL-02": QuestionResult.ANSWERED, "ECOM-01": QuestionResult.ANSWERED,
                       "ECOM-02": QuestionResult.PARTIALLY_ANSWERED,
                       "RET-01": QuestionResult.PARTIALLY_ANSWERED}


@pytest.mark.parametrize("mutation, message", [
    (lambda x: x.update(source_system="not-real"), "nonexistent systems"),
    (lambda x: x["channel_mapping"].update(canonical_channel_id="BAD"), "invalid canonical channel"),
    (lambda x: x["order_id_mapping"].update(rule="MAGIC"), "Unsupported connector rule"),
    (lambda x: x["cancellation_handling"].update(rule="IGNORE"), "Invalid cancellation rule"),
    (lambda x: x["return_handling"].update(rule="ANYWHERE"), "Invalid return rule"),
])
def test_invalid_connector_contract_is_rejected(mutation, message):
    raw = connector_raw(); mutation(raw)
    with pytest.raises(EcommerceValidationError, match=message):
        connector_from_dict(raw)


def test_duplicate_ids_missing_provenance_invalid_status_and_impossible_effect_rejected():
    connector = load_connector_configuration(); identity = load_identity_configuration()
    for mutate, message in [
        (lambda raw: raw["orders"].append(copy.deepcopy(raw["orders"][0])), "duplicate"),
        (lambda raw: raw["orders"][0].update(provenance=""), "provenance"),
        (lambda raw: raw["orders"][0].update(status="SHIPPED"), "status"),
        (lambda raw: raw["orders"][0].update(inventory_effect=-99), "impossible"),
        (lambda raw: raw["orders"][0]["lines"][0].update(source_sku="BAD"), "invalid SKU"),
    ]:
        raw = orders_raw(); mutate(raw)
        with pytest.raises(EcommerceValidationError, match=message):
            orders_from_dict(raw, connector, identity)


def test_cli_ecommerce_reconciliation_output():
    result = subprocess.run([sys.executable, "-m", "retail_configuration_lab", "ecommerce-reconciliation"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert "Before native integration" in result.stdout and "After native integration" in result.stdout
    assert "RESULT\nRECONCILED" in result.stdout
    assert "TRUE OPERATIONAL EXCEPTION" in result.stdout
    assert "Current lab verdict: UNTESTED" in result.stdout
