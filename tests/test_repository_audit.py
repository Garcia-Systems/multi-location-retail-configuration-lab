"""Publication-level regression checks across the completed Chapters 0--20."""

from contextlib import redirect_stdout
from decimal import Decimal
from io import StringIO
from pathlib import Path

from retail_configuration_lab.cli import main
from retail_configuration_lab.economics import analyze_economics
from retail_configuration_lab.full_custom_counterfactual import (
    load_full_custom_counterfactual,
)


PRIMARY_COMMANDS = (
    "baseline",
    "capabilities",
    "questions",
    "identity",
    "native-reporting",
    "ecommerce-reconciliation",
    "purchasing",
    "returns-transfers",
    "automation",
    "bi-reporting",
    "process-change",
    "residual-gaps",
    "support-surface",
    "add-store",
    "acquired-store",
    "strong-native-suite",
    "weak-native-coverage",
    "custom-edge",
    "full-custom-counterfactual",
    "economics",
    "capstone",
)


def _run(command: str) -> str:
    output = StringIO()
    with redirect_stdout(output):
        assert main([command]) == 0
    return output.getvalue()


def test_full_cli_chain_is_successful_deterministic_and_order_independent():
    """Every public chapter command must be safe to compose in either order."""
    forward = {command: _run(command) for command in PRIMARY_COMMANDS}
    reverse = {command: _run(command) for command in reversed(PRIMARY_COMMANDS)}

    assert forward == reverse
    for chapter, command in enumerate(PRIMARY_COMMANDS):
        assert f"Chapter {chapter}" in forward[command]


def test_historical_and_provider_side_invariants_remain_exact():
    analysis = analyze_economics()
    counterfactual = load_full_custom_counterfactual()
    full_custom = next(
        option for option in analysis.options if option.option_id == "full-custom"
    )

    assert analysis.original_annual_burden == Decimal("111020.00")
    assert analysis.original_recoverable_value == Decimal("51513.80")
    assert full_custom.setup_implementation_cash_cost == Decimal("62000.00")
    assert full_custom.annual_platform_cash_cost == Decimal("15000.00")
    assert counterfactual.engineering_hours == Decimal("378")
    assert counterfactual.direct_delivery_cost == Decimal("32440.00")
    # Provider delivery cost is evidence about delivery economics, not buyer cost.
    assert counterfactual.direct_delivery_cost not in (
        full_custom.setup_cost,
        full_custom.total_first_year_economic_cost,
    )


def test_readme_lists_every_command_and_continuous_chapter_file():
    root = Path(__file__).parents[1]
    readme = (root / "README.md").read_text()

    for chapter, command in enumerate(PRIMARY_COMMANDS):
        assert f"python -m retail_configuration_lab {command}" in readme
        chapter_files = tuple((root / "book").glob(f"{chapter:02d}-*.md"))
        assert len(chapter_files) == 1
        assert f"({chapter_files[0].relative_to(root)})" in readme

    assert not tuple((root / "book").glob("21-*.md"))
