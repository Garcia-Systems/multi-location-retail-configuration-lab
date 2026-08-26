"""Terminal interface for the executable textbook."""

import argparse
from decimal import Decimal
from typing import Sequence

from .baseline import assess, load_baseline
from .capabilities import analyze_inventory, load_inventory
from .models import CapabilityStatus
from .models import QuestionCoverageStatus, QuestionType
from .questions import analyze_questions, load_questions


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


def questions_report(
    area: str | None = None, coverage: str | None = None,
    owner: str | None = None, question_id: str | None = None,
) -> str:
    """Render full analysis and a filtered question inventory or one-question trace."""
    inventory = load_questions()
    analysis = analyze_questions(inventory)
    selected_coverage = QuestionCoverageStatus(coverage) if coverage else None
    rows = [item for item in inventory.questions
            if (area is None or item.business_area.casefold() == area.casefold())
            and (selected_coverage is None or item.coverage_status is selected_coverage)
            and (owner is None or item.primary_owner.casefold() == owner.casefold())
            and (question_id is None or item.question_id.casefold() == question_id.casefold())]
    lines = [
        inventory.customer_name,
        "Chapter 2 — Define the Business Questions", "",
        f"Business questions: {analysis.total_business_questions}", "", "By type:",
    ]
    lines.extend(f"{kind.value}: {analysis.count_by_question_type[kind]}" for kind in QuestionType)
    lines.extend(["", "Coverage hypothesis:"])
    lines.extend(
        f"{status.value.replace('_', ' ')}: {analysis.count_by_coverage_status[status]}"
        for status in QuestionCoverageStatus
    )
    lines.extend([
        "", "Capability coverage is a hypothesis derived from modeled inventory. "
        "It is not evidence that the business question has been solved.",
        "DIRECT does not mean SOLVED.", "", "Current lab verdict: UNTESTED", "",
    ])
    if question_id:
        lines.append("Question trace")
        if not rows:
            lines.append("No question matches the requested ID and filters.")
        for item in rows:
            lines.extend([
                "BUSINESS QUESTION", item.question_text, "        ↓", "OWNER", item.primary_owner,
                "        ↓", "DECISION / ACTION", item.decision_action, "        ↓",
                "REQUIRED EVIDENCE", *[f"- {field}" for field in item.required_evidence],
                "        ↓", "FRESHNESS", item.freshness.value, "        ↓",
                "RELATED CAPABILITIES", ", ".join(item.related_capability_ids) or "None known",
                "        ↓", "COVERAGE HYPOTHESIS", item.coverage_status.value.replace("_", " "),
            ])
        return "\n".join(lines)
    lines.extend([
        "Question inventory" + (" (filtered questions)" if area or coverage or owner else ""),
        f"{'ID':<9} {'OWNER':<28} QUESTION", "-" * 100,
    ])
    for item in rows:
        lines.extend([
            f"{item.question_id:<9} {item.primary_owner:<28} {item.question_text}", "",
            f"Type: {item.question_type.value}", f"Freshness: {item.freshness.value}",
            f"Scope: {item.scope.value.replace('_', ' ')}", f"Action: {item.decision_action}",
            f"Coverage: {item.coverage_status.value.replace('_', ' ')}",
            "Capabilities: " + (", ".join(item.related_capability_ids) or "None known"), "",
        ])
    if not rows:
        lines.append("No business questions match the requested filters.")
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
    questions = subparsers.add_parser(
        "questions", help="print the Chapter 2 fictional business questions"
    )
    questions.add_argument("--area", help="show questions for one business area")
    questions.add_argument("--coverage", choices=[item.value for item in QuestionCoverageStatus])
    questions.add_argument("--owner", help="show questions assigned to one primary owner")
    questions.add_argument("--id", dest="question_id", help="trace one business question")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "baseline":
        print(baseline_report())
    elif args.command == "capabilities":
        print(capabilities_report(args.area, args.status))
    elif args.command == "questions":
        print(questions_report(args.area, args.coverage, args.owner, args.question_id))
    return 0
