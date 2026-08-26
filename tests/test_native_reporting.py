from decimal import Decimal
import subprocess
import sys

from retail_configuration_lab.native_reporting import (
    QuestionResult, load_reporting_configuration, reporting_period_contains,
    run_native_reporting,
)


def test_configuration_and_six_store_group():
    config = load_reporting_configuration()
    assert len(config.reports) == 5
    assert len(config.store_groups["ALL_STORES"]) == 6
    assert config.category_for("RiverPOS", "Clothing") == "APPAREL"
    assert config.category_for("RiverPOS", "Apparel") == "APPAREL"


def test_period_and_sales_metrics_are_deterministic():
    config = load_reporting_configuration()
    assert reporting_period_contains("2026-01-15T00:00:00-05:00", "2026-01-15", config)
    assert not reporting_period_contains("2026-01-16T00:00:00-05:00", "2026-01-15", config)
    rows = run_native_reporting(config).reports["store-sales"]
    first = rows[0]
    assert first["gross_sales"] == Decimal("100.00")
    assert first["returns"] == Decimal("50.00")
    assert first["net_sales"] == Decimal("50.00")
    assert first["units_sold"] == 1


def test_configured_dimensions_inventory_and_question_coverage():
    result = run_native_reporting()
    assert {r["common_category"] for r in result.reports["sales-category"]} == {"APPAREL"}
    assert all(r["canonical_sku"].startswith("JRO-") for r in result.reports["sku-activity"])
    assert result.reports["inventory-snapshot"][0]["on_hand_quantity"] == 8
    assert result.reports["inventory-adjustments"][0]["adjustment"] == -2
    statuses = {q.after_configuration for q in result.questions}
    assert statuses == set(QuestionResult)
    assert result.native_question_answer_rate == 1 / 5
    returns = next(q for q in result.questions if q.question_id == "RET-01")
    assert returns.after_configuration is QuestionResult.NOT_ANSWERED


def test_native_reporting_cli():
    completed = subprocess.run([sys.executable, "-m", "retail_configuration_lab", "native-reporting"],
                               capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert "Question coverage" in completed.stdout
    assert "STORE SALES SUMMARY" in completed.stdout
    assert "Current lab verdict: UNTESTED" in completed.stdout
