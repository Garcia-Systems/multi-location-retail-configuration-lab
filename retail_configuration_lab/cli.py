"""Terminal interface for the executable textbook."""

import argparse
from decimal import Decimal
from typing import Sequence

from .baseline import assess, load_baseline
from .capabilities import analyze_inventory, load_inventory
from .models import CapabilityStatus


def _money(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def baseline_report() -> str:
    case = load_baseline()
    result = assess(case)
    lines = [
        case.customer_name,
        "Chapter 0 — The BUY / CONFIGURE Hypothesis", "",
        f"Original modeled verdict: {case.original_verdict}",
        f"Current lab verdict: {case.current_lab_verdict}", "",
        f"Annual current-state burden: {_money(case.annual_current_state_burden)}",
        f"Recoverable annual value: {_money(case.recoverable_annual_value)}",
        f"Recoverable-value ratio: {result.recoverable_value_ratio:.2%}", "",
        f"Custom implementation price: {_money(case.custom_implementation_price)}",
        f"Custom annual fee: {_money(case.custom_annual_recurring_fee)}",
        f"Custom first-year customer cash cost: {_money(result.custom_first_year_customer_cash_cost)}",
        f"Custom first-year buyer surplus: {_money(result.custom_first_year_buyer_surplus)}",
        f"Custom recurring-year buyer surplus: {_money(result.custom_recurring_year_buyer_surplus)}",
        f"Simple first-year coverage ratio: {result.simple_first_year_coverage_ratio:.2f}", "",
        f"Modeled engineering effort: {case.modeled_engineering_hours:g} hours",
        f"Modeled direct delivery cost: {_money(case.modeled_direct_delivery_cost)}",
        "Direct delivery contribution before recurring support: "
        f"{_money(result.direct_delivery_contribution_before_recurring_support)}",
        "  (not a complete accounting profit calculation)", "",
        "Experimental question:", case.experiment_questions[0],
    ]
    return "\n".join(lines)


def _status_label(status: CapabilityStatus) -> str:
    return status.value.replace("_", " ")


def capabilities_report(area: str | None = None, status: str | None = None) -> str:
    """Render unfiltered analysis followed by a optionally filtered matrix."""
    inventory = load_inventory()
    analysis = analyze_inventory(inventory)
    selected_status = CapabilityStatus(status.upper().replace(" ", "_")) if status else None
    rows = [item for item in inventory.assessments
            if (area is None or item.capability.business_area.casefold() == area.casefold())
            and (selected_status is None or item.status is selected_status)]
    lines = [
        inventory.customer_name,
        "Chapter 1 — Inventory What Already Exists", "",
        f"Total capabilities: {analysis.total_capabilities}", "",
        "Capability status summary:",
    ]
    lines.extend(f"{_status_label(item)}: {analysis.count_by_status[item]}"
                 for item in CapabilityStatus)
    lines.extend([
        "", f"Explicit gaps: {analysis.explicit_gaps}",
        f"Explicit unknowns: {analysis.explicit_unknowns}",
        "Potential non-custom paths worth testing: "
        f"{analysis.potentially_addressable_without_custom_software}",
        "  (a plausible path worth testing; not proof that a business problem is solved)", "",
        "Important:",
        "Capability inventory does not prove business value or implementation success.",
        "CAPABILITY EXISTS is not the same as CAPABILITY SOLVES BUSINESS QUESTION.", "",
        "Capability matrix" + (" (filtered rows)" if area or status else ""),
        f"{'AREA':<13} {'CAPABILITY':<38} {'SYSTEM':<16} STATUS",
        "-" * 92,
    ])
    system_names = {item.identifier: item.name for item in inventory.systems}
    for item in rows:
        lines.append(f"{item.capability.business_area:<13} {item.capability.name:<38} "
                     f"{system_names[item.primary_system]:<16} {_status_label(item.status)}")
        lines.append(f"  Rationale: {item.rationale}")
        if item.dependency:
            lines.append(f"  Dependency: {item.dependency}")
        if item.discovery_note:
            lines.append(f"  Discovery: {item.discovery_note}")
    if not rows:
        lines.append("No capability rows match the requested filters.")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the synthetic retail configuration lab.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("baseline", help="print the Chapter 0 baseline assessment")
    capabilities = subparsers.add_parser(
        "capabilities", help="print the Chapter 1 fictional capability inventory"
    )
    capabilities.add_argument("--area", help="show matrix rows for one business area")
    capabilities.add_argument(
        "--status", choices=[status.value for status in CapabilityStatus],
        help="show matrix rows for one capability status",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "baseline":
        print(baseline_report())
    elif args.command == "capabilities":
        print(capabilities_report(args.area, args.status))
    return 0
