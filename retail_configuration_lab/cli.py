"""Terminal interface for the executable textbook."""

import argparse
from decimal import Decimal
from typing import Sequence

from .baseline import assess, load_baseline
from .capabilities import analyze_inventory, load_inventory
from .models import CapabilityStatus
from .models import QuestionCoverageStatus, QuestionType
from .questions import analyze_questions, load_questions
from .identity import IdentityType, load_identity_configuration, run_identity_experiment
from .native_reporting import QuestionResult, load_reporting_configuration, run_native_reporting
from .ecommerce_reconciliation import (
    ReconciliationResult, load_connector_configuration, run_ecommerce_reconciliation,
)
from .purchasing import PurchasingResult, run_purchasing_experiment
from .returns_transfers import (
    ReturnResult, TransferResult, run_returns_transfers_experiment,
)
from .automation import ExecutionStatus, run_automation_experiment
from .bi_reporting import BIQuestionStatus, run_bi_reporting
from .process_change import ResidualCause, run_process_change_experiment
from .residual_gaps import ResidualStatus, analyze_residual_gaps, load_residual_gaps
from .support_surface import analyze_support_surface, load_support_inventory


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


def identity_report(show_mappings: bool = False, identity_type: str | None = None) -> str:
    configuration = load_identity_configuration()
    result = run_identity_experiment(configuration)
    lines = [
        "James River Outfitters", "Chapter 3 — Standardize Retail Identity", "",
        "Before standardization", "----------------------",
        f"Raw comparisons: {result.raw_comparisons}",
        f"Direct identity matches: {result.raw_direct_matches}",
        f"Apparent mismatches: {result.raw_apparent_mismatches}", "",
        "After configured identity mapping", "---------------------------------",
        f"Mappings applied: {result.mappings_applied}",
        f"Canonical matches: {result.canonical_matches}",
        f"False exceptions eliminated: {result.false_exceptions_eliminated}",
        f"True operational exceptions remaining: {result.true_operational_exceptions_remaining}",
        f"Ambiguous identities: {result.ambiguous_identities}",
        f"Unmapped identities: {result.unmapped_identities}",
        f"Conflicts: {result.conflicts}", "",
        f"False-exception elimination ratio: {result.false_exception_elimination_ratio:.2%}",
        "  OBSERVED LAB RESULT from synthetic comparisons; no success threshold is imposed.", "",
        "Chapter 2 identity readiness",
    ]
    lines.extend(f"{impact.question_id}: {impact.readiness.value} — {impact.reason}"
                 for impact in result.question_impacts)
    eliminated = next(item for item in result.outcomes
                      if item.classification == "FALSE_EXCEPTION_ELIMINATED")
    true = next(item for item in result.outcomes
                if item.classification == "TRUE_OPERATIONAL_EXCEPTION")
    e = eliminated.comparison
    t = true.comparison
    lines.extend([
        "", "ELIMINATED FALSE EXCEPTION", "",
        f"{e.left_system} {e.identity_type.value}: {e.left_identifier}",
        f"{e.right_system} {e.identity_type.value}: {e.right_identifier}",
        f"Canonical {e.identity_type.value}: {eliminated.canonical_id}", "",
        f"Both systems report quantity: {e.left_value}", "", "Result:",
        "The apparent disagreement was identity-only.", "",
        "TRUE EXCEPTION REMAINS", "",
        f"{t.left_system} {t.identity_type.value}: {t.left_identifier}",
        f"{t.right_system} {t.identity_type.value}: {t.right_identifier}",
        f"Canonical {t.identity_type.value}: {true.canonical_id}", "",
        f"{t.left_system} quantity: {t.left_value}", f"{t.right_system} quantity: {t.right_value}",
        "", "Result:", "Identity is standardized, but quantity still disagrees.", "",
        "Modeled identity-reconciliation burden (MODELED ASSUMPTION)",
    ])
    lines.extend(f"- {item.category}: {item.annual_hours} annual hours" for item in result.burden_categories)
    total_hours = sum(item.annual_hours for item in result.burden_categories)
    lines.extend([
        f"Modeled extrapolation at the synthetic elimination ratio: "
        f"{total_hours * result.false_exception_elimination_ratio:.1f} annual hours",
        "This is not an observed saving at a retailer.", "",
        "Current lab verdict: UNTESTED",
    ])
    if show_mappings:
        selected = IdentityType(identity_type.upper()) if identity_type else None
        lines.extend(["", "Configured mappings (OBSERVED IMPLEMENTATION STRUCTURE)"])
        for mapping in configuration.mappings:
            if selected is None or mapping.identity_type is selected:
                target = ", ".join(mapping.canonical_ids)
                lines.append(f"{mapping.identity_type.value} | {mapping.source_system} | "
                             f"{mapping.source_identifier} -> {target} [{mapping.status.value}]")
    return "\n".join(lines)


def native_reporting_report() -> str:
    configuration = load_reporting_configuration()
    result = run_native_reporting(configuration)
    counts = result.count_by_result
    outside = [q for q in result.questions if q.after_configuration is QuestionResult.NOT_ANSWERED]
    lines = [
        "James River Outfitters", "Chapter 4 — Configure Native Multi-Store Reporting", "",
        f"Configured native reports: {len(configuration.reports)}",
        f"Configuration records used: {result.configuration_records_used}", "",
        "Question coverage", "-----------------",
        f"ANSWERED: {counts[QuestionResult.ANSWERED]}",
        f"PARTIALLY ANSWERED: {counts[QuestionResult.PARTIALLY_ANSWERED]}",
        f"NOT ANSWERED: {counts[QuestionResult.NOT_ANSWERED]}",
        f"UNKNOWN: {counts[QuestionResult.UNKNOWN]}", "",
        f"Native question answer rate: {result.native_question_answer_rate:.2%}",
        "  OBSERVED LAB RESULT from synthetic native reports; no success threshold is imposed.",
        "Improved through configuration: " + (", ".join(result.questions_improved_by_configuration) or "none"), "",
        "Still outside native POS/inventory reporting:",
        *[f"- {q.question_id}: {q.question}" for q in outside], "",
        "Current lab verdict: UNTESTED", "", "STORE SALES SUMMARY", "",
        f"{'Store':<17} {'Gross':>10} {'Returns':>10} {'Net':>10} {'Units':>7}",
    ]
    for row in result.reports["store-sales"]:
        lines.append(f"{row['store']:<17} {_money(row['gross_sales']):>10} {_money(row['returns']):>10} "
                     f"{_money(row['net_sales']):>10} {row['units_sold']:>7}")
    answered = result.questions[0]; failed = next(q for q in result.questions if q.question_id == "RET-01")
    lines.extend(["", "QUESTION", answered.question, "", "REQUIRED EVIDENCE",
                  "- store", "- sales", "- returns", "- period", "", "NATIVE REPORT",
                  "Store Sales Summary", "", "RESULT", answered.after_configuration.value, "",
                  "QUESTION", failed.question, "", "NATIVE EVIDENCE", "POS return activity",
                  "Inventory effect", "", "MISSING", *[f"- {x}" for x in failed.missing], "",
                  "RESULT", failed.after_configuration.value])
    return "\n".join(lines)


def ecommerce_reconciliation_report() -> str:
    connector = load_connector_configuration()
    result = run_ecommerce_reconciliation(connector)
    counts = result.count_by_result
    clean = next(item for item in result.outcomes
                 if item.result is ReconciliationResult.RECONCILED)
    identity_failure = next(item for item in result.outcomes
                            if item.result is ReconciliationResult.UNRESOLVED_IDENTITY
                            and item.canonical_store_id is None)
    quantity_exception = next(item for item in result.outcomes
                              if item.result is ReconciliationResult.EXCEPTION
                              and item.order.inventory_effect != item.expected_inventory_effect)
    lines = [
        "James River Outfitters",
        "Chapter 5 — Configure E-Commerce and Store Reconciliation", "",
        "Before native integration", "-------------------------",
        f"Orders requiring manual reconciliation: {result.before.orders_requiring_manual_reconciliation}",
        f"Manual identity lookups: {result.before.manual_identity_lookups}",
        f"Records lacking direct order linkage: {result.before.records_lacking_direct_order_linkage}",
        f"Apparent exceptions: {result.before.apparent_exceptions}",
        f"True exceptions: {result.before.true_exceptions}", "",
        "After native integration", "------------------------",
        f"Total synthetic online orders: {result.total_orders}",
        f"Automatically linked orders: {result.automatically_linked_orders}",
        f"RECONCILED: {counts[ReconciliationResult.RECONCILED]}",
        f"PARTIALLY RECONCILED: {counts[ReconciliationResult.PARTIALLY_RECONCILED]}",
        f"EXCEPTION: {counts[ReconciliationResult.EXCEPTION]}",
        f"UNRESOLVED IDENTITY: {counts[ReconciliationResult.UNRESOLVED_IDENTITY]}",
        f"UNKNOWN: {counts[ReconciliationResult.UNKNOWN]}",
        f"Orders requiring manual reconciliation: {result.orders_requiring_manual_reconciliation_after}", "",
        f"Manual reconciliation reduction ratio: {result.manual_reconciliation_reduction_ratio:.2%}",
        f"Native reconciliation rate: {result.native_reconciliation_rate:.2%}",
        "  OBSERVED LAB RESULT from deterministic synthetic evidence; no success threshold is imposed.", "",
        "Chapter 2 question impact",
        *[f"{item.question_id}: {item.status.value.replace('_', ' ')} — {item.reason}"
          for item in result.question_impacts], "",
        "Modeled e-commerce reconciliation burden (MODELED ASSUMPTION): 96 annual hours",
        f"Modeled remaining burden (MODELED EXTRAPOLATION): "
        f"{96 * (1 - result.manual_reconciliation_reduction_ratio):.1f} annual hours",
        "This is not observed labor savings.", "", "Current lab verdict: UNTESTED", "",
        "CLEAN RECONCILIATION", "", "ORDER", clean.order.online_order_id, "",
        "CANONICAL ORDER", clean.canonical_order_id, "", "STORE REFERENCE",
        clean.order.store_reference or "MISSING", "", "CHANNEL",
        clean.canonical_channel_id or "UNRESOLVED", "", "FULFILLMENT STORE",
        clean.canonical_store_id or "UNRESOLVED", "", "SKU",
        ", ".join(clean.canonical_skus), "", "RESULT", clean.result.value.replace("_", " "), "",
        "IDENTITY FAILURE", "", "ORDER", identity_failure.order.online_order_id, "",
        "FULFILLMENT STORE SOURCE ID", identity_failure.order.fulfillment_store_source_id, "",
        "CANONICAL STORE", "UNRESOLVED", "", "RESULT",
        identity_failure.result.value.replace("_", " "), "",
        "TRUE OPERATIONAL EXCEPTION", "", "ORDER", quantity_exception.order.online_order_id, "",
        "ORDER QUANTITY", str(sum(line.quantity for line in quantity_exception.order.lines)), "",
        "EXPECTED INVENTORY DECREMENT", str(abs(quantity_exception.expected_inventory_effect or 0)), "",
        "OBSERVED INVENTORY DECREMENT", str(abs(quantity_exception.order.inventory_effect or 0)), "",
        "RESULT", quantity_exception.result.value,
    ]
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
    identity = subparsers.add_parser(
        "identity", help="run the Chapter 3 identity-standardization experiment"
    )
    identity.add_argument("--show-mappings", action="store_true", help="show mapping provenance")
    identity.add_argument("--type", choices=[item.value.lower() for item in IdentityType],
                          help="filter displayed mappings by identity type")
    subparsers.add_parser("native-reporting", help="run the Chapter 4 native reporting experiment")
    subparsers.add_parser("ecommerce-reconciliation", help="run the Chapter 5 native connector experiment")
    subparsers.add_parser("purchasing", help="run the Chapter 6 purchasing configuration experiment")
    subparsers.add_parser("returns-transfers", help="run the Chapter 7 returns/transfers experiment")
    subparsers.add_parser("automation", help="run the Chapter 8 bounded automation experiment")
    bi = subparsers.add_parser("bi-reporting", help="run the Chapter 9 configured BI experiment")
    bi.add_argument("--report", choices=["management-briefing", "transfer-exceptions"],
                    help="show only one compact report after the experiment summary")
    subparsers.add_parser("process-change", help="run the Chapter 10 process-change experiment")
    subparsers.add_parser("residual-gaps", help="run the Chapter 11 residual-gap analysis")
    subparsers.add_parser("support-surface", help="run the Chapter 12 support-surface analysis")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "baseline":
        print(baseline_report())
    elif args.command == "capabilities":
        print(capabilities_report(args.area, args.status))
    elif args.command == "questions":
        print(questions_report(args.area, args.coverage, args.owner, args.question_id))
    elif args.command == "identity":
        print(identity_report(args.show_mappings, args.type))
    elif args.command == "native-reporting":
        print(native_reporting_report())
    elif args.command == "ecommerce-reconciliation":
        print(ecommerce_reconciliation_report())
    elif args.command == "purchasing":
        print(purchasing_report())
    elif args.command == "returns-transfers":
        print(returns_transfers_report())
    elif args.command == "automation":
        print(automation_report())
    elif args.command == "bi-reporting":
        print(bi_reporting_report(args.report))
    elif args.command == "process-change":
        print(process_change_report())
    elif args.command == "residual-gaps":
        print(residual_gaps_report())
    elif args.command == "support-surface":
        print(support_surface_report())
    return 0


def support_surface_report() -> str:
    inventory = load_support_inventory()
    result = analyze_support_surface(inventory)
    lines = [inventory.customer_name, "Chapter 12 — Configuration Support Surface", "",
        "Configured support surface", "--------------------------",
        f"Mappings/configuration artifacts: {result.active_mappings}",
        f"Native integration configurations: {result.native_integration_configurations}",
        f"Automations: {result.automations}", f"Reports/views: {result.configured_reports}",
        f"Support obligations: {len(inventory.obligations)}",
        f"External-platform-dependent obligations: {result.external_platform_obligations}", "",
        "Modeled recurring support", "-------------------------",
        f"Annual support labor hours: {result.annual_support_labor_hours:.2f}",
        f"Annual support labor cost: {_money(result.annual_support_labor_cost)}",
        f"Annual platform cash cost: {_money(result.annual_platform_cash_cost)}",
        f"Annual total configuration support cost: {_money(result.annual_total_configuration_support_cost)}", "",
        f"Chapter 11 residual operational burden: {_money(result.residual_operational_burden)}",
        f"Chapter 11 provisional new administration burden: {_money(result.chapter11_new_administration_burden)}",
        "Reconciliation: Chapter 12 replaces (does not add to) the Chapter 11 provisional administration estimate.",
        f"Chapter 11 modeled burden reduction: {_money(result.chapter11_modeled_burden_reduction)}",
        "Support cost as share of modeled burden reduction: " + (f"{result.support_cost_as_share_of_modeled_burden_reduction:.2%}" if result.support_cost_as_share_of_modeled_burden_reduction is not None else "N/A"),
        f"Modeled net burden reduction after support: {_money(result.net_modeled_burden_reduction_after_support)}",
        "  Educational modeled comparison only; implementation/setup cost and complete deal economics are excluded.", "",
        "Support obligations by category", "-------------------------------"]
    for category in type(inventory.obligations[0].category):
        cost=sum((x.annual_support_cost for x in inventory.obligations if x.category is category),Decimal())
        lines.append(f"{category.value.replace('_',' ').title()}: {_money(cost)}")
    lines += ["", f"{'OBLIGATION':<34} {'INCIDENTS/YR':>12} {'HRS/INCIDENT':>14} {'ANNUAL HRS':>12} {'ANNUAL COST':>13}", "-"*91]
    for item in inventory.obligations:
        lines.append(f"{item.name:<34} {item.modeled_incidents_per_year:>12} {item.modeled_hours_per_incident:>14} {item.annual_effort_hours:>12} {_money(item.annual_support_cost):>13}")
    traces=[
        ("MAPPING MAINTENANCE SCENARIO","new supplier item","Mapping maintenance","configuration updated","CONFIGURATION REMOVED OPERATIONAL WORK; CREATED RECURRING ADMINISTRATION"),
        ("AUTOMATION-FAILURE SUPPORT SCENARIO","retry exhausted","Automation failure handling","human investigation required","Observed prior synthetic failure path; effort remains modeled"),
        ("BI/REPORT MAINTENANCE SCENARIO","new management category","BI/report maintenance","report configuration updated","Question coverage is unchanged; delivery has support risk"),
        ("VENDOR/SCHEMA-CHANGE SCENARIO","fictional export field renamed","Vendor/schema changes","mapping/report rule update; configuration maintenance required","Fictional bounded change, not a real vendor claim")]
    by_name={x.name:x for x in inventory.obligations}
    for title,trigger,name,outcome,note in traces:
        item=by_name[name]; lines += ["",title,"","TRIGGER",trigger,"","OBLIGATION",name,"","MODELED EFFORT",f"{item.modeled_hours_per_incident} hours/incident at {_money(item.modeled_hourly_cost)}/hour","","RESULT",outcome,"",note]
    lines += ["", "Configured support is not a full-custom counterfactual; runtime, deployments, custom adapters, observability, defects, and dependency upgrades are deferred.", "", "Current lab verdict: UNTESTED"]
    return "\n".join(lines)


def residual_gaps_report() -> str:
    inventory = load_residual_gaps()
    result = analyze_residual_gaps(inventory)
    lines = [inventory.customer_name, "Chapter 11 — What Still Hurts?", "",
        f"Original annual burden: {_money(result.original_annual_burden)}", "",
        "Residual burden summary", "-----------------------",
        f"Residual operational burden: {_money(result.residual_operational_burden)}",
        f"New administration burden: {_money(result.new_administration_burden)}",
        f"Combined post-configuration burden: {_money(result.combined_post_configuration_burden)}", "",
        f"Modeled burden reduction: {_money(result.modeled_burden_reduction)}",
        f"Modeled burden reduction ratio: {result.modeled_burden_reduction_ratio:.2%}",
        "  MODELED ASSUMPTION informed by observed synthetic ratios; not observed savings.",
        f"Original recoverable value: {_money(result.original_recoverable_value)}",
        "  Kept separate from modeled burden reduction.", "",
        "Residual status counts", "----------------------"]
    lines.extend(f"{status.value}: {result.status_counts[status]}" for status in ResidualStatus)
    lines.extend(["", "Largest remaining burdens", "-------------------------"])
    lines.extend(f"{number}. {item.name} — {_money(item.modeled_remaining_burden)}"
                 for number, item in enumerate(result.largest_residuals[:5], 1))
    lines.extend(["", "Category table", "--------------",
                  f"{'CATEGORY':<38} {'ORIGINAL':>12}  {'STATUS':<28} {'REMAINING':>12}"])
    for item in inventory.categories:
        lines.append(f"{item.name:<38} {_money(item.original_annual_burden):>12}  "
                     f"{item.residual_status.value:<28} {_money(item.modeled_remaining_burden):>12}")
    identity = next(x for x in inventory.categories if x.category_id == "identity-reconciliation")
    moved = next(x for x in inventory.categories if x.category_id == "identity-maintenance")
    accounting = next(x for x in inventory.categories if x.category_id == "accounting-reconciliation")
    support = next(x for x in inventory.categories if x.category_id == "automation-failure-handling")
    lines.extend(["", "Residual traces", "---------------", "", "CATEGORY", identity.name,
        "", "ORIGINAL MODELED BURDEN", _money(identity.original_annual_burden),
        "", "OBSERVED SYNTHETIC EVIDENCE", identity.observed_lab_evidence,
        "", "RESIDUAL STATUS", identity.residual_status.value,
        "", "MODELED REMAINING BURDEN", _money(identity.modeled_remaining_burden),
        "", "CATEGORY", moved.name, "", "ORIGINAL WORK", "manual reconciliation",
        "", "POST-CONFIGURATION WORK", "mapping administration", "", "RESIDUAL STATUS", moved.residual_status.value,
        "", "CATEGORY", accounting.name, "", "INTERVENTIONS TESTED", "configuration / BI / process change",
        "", "MISSING EVIDENCE", "accounting-side reconciliation data", "", "RESIDUAL STATUS", accounting.residual_status.value,
        "", "CATEGORY", support.name, "", "ORIGINAL BURDEN", "not present as automation support",
        "", "POST-CONFIGURATION", "retry / validation / failure handling required", "", "STATUS", support.residual_status.value,
        "", "Current lab verdict: UNTESTED"])
    return "\n".join(lines)


def process_change_report() -> str:
    result = run_process_change_experiment()
    lines = ["James River Outfitters", "Chapter 10 — Process Change Experiment", "",
        f"Process scenarios evaluated: {result.scenarios_evaluated}", "",
        "Before process change", "---------------------",
        f"Noncompliant events: {result.noncompliant_before}",
        f"Operational exceptions: {result.operational_exceptions_before}",
        f"Manual follow-up steps: {result.manual_steps_before}", "",
        "After process change", "--------------------",
        f"Noncompliant events: {result.noncompliant_after}",
        f"Operational exceptions: {result.operational_exceptions_after}",
        f"Manual follow-up steps: {result.manual_steps_after}", "",
        f"Process-caused exceptions eliminated: {result.process_caused_exceptions_eliminated}",
        f"Data-governance exceptions eliminated: {result.data_governance_exceptions_eliminated}",
        f"Technical exceptions unchanged: {result.technical_exceptions_unchanged}",
        f"Unknown/mixed exceptions: {result.unknown_mixed_exceptions}", "",
        f"Process exception reduction ratio: {result.process_exception_reduction_ratio:.2%}",
        f"Manual process step reduction ratio: {result.manual_process_step_reduction_ratio:.2%}",
        "  OBSERVED LAB RESULT from deterministic synthetic behavior; no success threshold is imposed.", "",
        "PROCESS CHANGE can eliminate avoidable bad records, delayed steps, duplicate work, and unclear ownership.",
        "PROCESS CHANGE cannot create missing platform capability, accounting evidence, or unsupported integration behavior.", "",
        "Chapter 2 question impact"]
    lines.extend(f"{x.question_id}: {x.status.value.replace('_', ' ')} — {x.reason}"
                 for x in result.question_impacts)
    lines.extend(["", "Intervention classes used so far: " + ", ".join(x.value for x in result.interventions),
                  "", "Current lab verdict: UNTESTED"])
    for outcome in result.outcomes:
        scenario = outcome.scenario
        lines.extend(["", "SCENARIO", scenario.name, "", "SYSTEM CAPABILITY",
                      "AVAILABLE" if scenario.technology_available.value == "YES" else "UNAVAILABLE", "",
                      "BEFORE", scenario.before.behavior, "", "AFTER PROCESS CHANGE",
                      scenario.after.behavior, "", "ROOT CAUSE", scenario.primary_residual_cause.value.replace("_", " "), ""])
        if scenario.primary_residual_cause is ResidualCause.TECHNICAL_GAP:
            lines.extend(["PROCESS CHANGE", "applied where relevant", "", "ACCOUNTING EVIDENCE",
                          "still unavailable", "", "RESULT", "UNCHANGED"])
        else:
            label = ("process/data-quality exception eliminated" if scenario.scenario_id == "return-reason"
                     else "missing-receipt exception eliminated" if scenario.scenario_id == "transfer-closure"
                     else "process-caused exception eliminated" if outcome.eliminated
                     else "UNCHANGED")
            lines.extend(["RESULT", label])
    return "\n".join(lines)


def bi_reporting_report(selected_report: str | None = None) -> str:
    result = run_bi_reporting(); before, after = result.count_before, result.count_after
    labels = ((BIQuestionStatus.ANSWERED, "ANSWERED"),
              (BIQuestionStatus.PARTIALLY_ANSWERED, "PARTIALLY ANSWERED"),
              (BIQuestionStatus.NOT_ANSWERED, "NOT ANSWERED"),
              (BIQuestionStatus.UNKNOWN, "UNKNOWN"))
    lines = ["James River Outfitters", "Chapter 9 — BI / Reporting Configuration", "",
        f"Configured datasets/views: {result.configured_datasets_views}",
        f"Configured reports: {len(result.configuration.reports)}", "",
        "Question coverage before BI", "---------------------------",
        *[f"{label}: {before[status]}" for status, label in labels], "",
        "Question coverage after BI", "--------------------------",
        *[f"{label}: {after[status]}" for status, label in labels], "",
        "Questions improved by BI: " + ", ".join(result.questions_improved_by_bi),
        f"BI question answer rate: {result.bi_question_answer_rate:.2%}",
        f"Incremental questions answered: {result.bi_incremental_question_gain}",
        f"Exception records surfaced in management briefing: {result.exception_records_surfaced}", "",
        f"Manual reporting steps before: {result.manual_reporting_steps_before}",
        f"Manual reporting steps after: {result.manual_reporting_steps_after}",
        f"Manual reporting step reduction ratio: {result.manual_reporting_step_reduction_ratio:.2%}",
        "  Assembly/presentation work only; investigation remains.", "",
        "QUESTION", "Which purchase orders or receipts require purchasing attention?", "",
        "BEFORE BI", "evidence exists in purchasing reconciliation output", "",
        "AFTER BI", "configured exception view surfaces open purchasing exceptions", "",
        "RESULT", "ANSWERED", "", "QUESTION",
        "Which operational sales, return, or purchasing records fail to reconcile with accounting evidence?", "",
        "BI INPUT", "operational exception evidence available", "", "ACCOUNTING EVIDENCE",
        "not available", "", "RESULT", "PARTIALLY ANSWERED", "",
        "Current lab verdict: UNTESTED", "", "Central Management Exception Briefing",
        "======================================"]
    rows = (result.reports["transfer-status-report"] if selected_report == "transfer-exceptions"
            else result.management_briefing)
    for row in rows:
        reference = row.get("transfer_id") or row.get("po") or row.get("return_id") or row.get("online_order") or row.get("exception_id")
        status = row.get("transfer_result") or row.get("reconciliation_result") or row.get("status")
        if selected_report == "transfer-exceptions" and status == "RECONCILED": continue
        lines.append(f"{row.get('section', 'transfer')} | {reference} | {status} | SKU: {row.get('canonical_sku', 'UNRESOLVED')}")
    lines += ["", "TRANSFER", "JRO-TR-1007", "", "RESULT", "MISSING RECEIPT", "",
              "BI EFFECT", "visible in management briefing", "", "OPERATIONAL EFFECT", "unchanged", "",
              "REPORTING organizes and presents reconciliation results.",
              "RECONCILIATION determines whether evidence agrees.",
              "VISIBLE EXCEPTION != RESOLVED EXCEPTION"]
    return "\n".join(lines)


def automation_report() -> str:
    result=run_automation_experiment(); counts=result.counts
    transfer=next(x for x in result.executions if x.automation_id=="missing-transfer-receipt-alert" and x.status is ExecutionStatus.SUCCEEDED)
    blocked=next(x for x in result.executions if x.status is ExecutionStatus.BLOCKED_BY_VALIDATION)
    retry=next(x for x in result.executions if x.automation_id=="scheduled-export-movement")
    exhausted=next(x for x in result.executions if x.status is ExecutionStatus.RETRY_EXHAUSTED)
    duplicate=next(x for x in result.executions if x.status is ExecutionStatus.DUPLICATE_SUPPRESSED)
    return "\n".join([
        "James River Outfitters","Chapter 8 — Automation Layer","",
        f"Configured automations: {len(result.configuration.automations)}","",
        "Before automation","-----------------",f"Recurring manual steps: {result.configuration.manual_steps_before}","",
        "After automation","----------------",f"SUCCEEDED: {counts[ExecutionStatus.SUCCEEDED]}",f"FAILED: {counts[ExecutionStatus.FAILED]}",f"RETRY EXHAUSTED: {counts[ExecutionStatus.RETRY_EXHAUSTED]}",f"BLOCKED BY VALIDATION: {counts[ExecutionStatus.BLOCKED_BY_VALIDATION]}",f"Duplicates suppressed: {counts[ExecutionStatus.DUPLICATE_SUPPRESSED]}",f"Alerts generated: {len(result.alerts)}",f"Validations run: 1",f"Reconciliation triggers: {result.reconciliation_runs}",f"Report distributions: {len(result.distributions)}",f"Residual manual intervention: {result.configuration.manual_steps_after}","",
        f"Manual-step reduction ratio: {result.manual_step_reduction_ratio:.2%}",f"Automation success rate: {result.automation_success_rate:.2%} (SUCCEEDED / terminal action outcomes)","",
        "Residual operational problems: missing transfer receipt; missing return reason; unresolved mapping; true quantity mismatch; accounting evidence gap; automation failure; retry exhaustion.",
        "Automation removes routine handling; detected exceptions still require human judgment.","",
        "Chapter 2 question impact",*[f"{qid}: {status.value.replace('_',' ')} — {reason}" for qid,status,reason in result.question_impacts],"",
        "Current lab verdict: UNTESTED","",
        "MISSING TRANSFER ALERT","","AUTOMATION",transfer.automation_id,"","TRANSFER",transfer.trigger_reference,"","CONDITION","sent but not received","","ACTION","create alert","","RESULT","SUCCEEDED","",
        "MAPPING VALIDATION BLOCK","","AUTOMATION",blocked.automation_id,"","SOURCE ID",blocked.trigger_reference,"","CANONICAL ID","UNRESOLVED","","RESULT","BLOCKED BY VALIDATION","",
        "RETRY SUCCESS","","ATTEMPT 1","FAILED","","ATTEMPT 2",retry.status.value,"",
        "RETRY EXHAUSTION","","ATTEMPTS",str(exhausted.attempt_count),"","RESULT","RETRY EXHAUSTED","",
        "DUPLICATE SUPPRESSION","","TRIGGER","same source event received again","","RESULT",duplicate.status.value.replace('_',' '),"",
        "DETERMINISTIC ROUTINE WORK","        ↓","AUTOMATED","","REAL OPERATIONAL EXCEPTION","        ↓","STILL REQUIRES HUMAN JUDGMENT"
    ])


def purchasing_report() -> str:
    result=run_purchasing_experiment(); counts=result.counts
    clean=next(x for x in result.outcomes if x.result is PurchasingResult.RECONCILED)
    partial=next(x for x in result.outcomes if x.result is PurchasingResult.PARTIAL_RECEIPT)
    wrong=next(x for x in result.outcomes if x.result is PurchasingResult.LOCATION_EXCEPTION)
    unresolved=next(x for x in result.outcomes if x.result is PurchasingResult.UNRESOLVED_IDENTITY)
    labels=[PurchasingResult.RECONCILED,PurchasingResult.PARTIAL_RECEIPT,PurchasingResult.OVER_RECEIPT,PurchasingResult.MISSING_RECEIPT,PurchasingResult.LOCATION_EXCEPTION,PurchasingResult.CANCELLED_PO_RECEIPT,PurchasingResult.UNRESOLVED_IDENTITY,PurchasingResult.INVENTORY_EFFECT_EXCEPTION]
    lines=["James River Outfitters","Chapter 6 — Purchasing and Inventory Configuration","","Before configuration","--------------------",f"PO/receipt manual matches: {result.before['manual_po_receipt_links']}",f"Supplier item lookups: {result.before['supplier_item_lookups']}",f"Manual location interpretations: {result.before['manual_location_interpretations']}",f"Apparent discrepancies: {result.before['apparent_discrepancies']}","","After configuration","-------------------",f"Total purchase orders: {result.total_purchase_orders}",f"Total PO lines: {result.total_po_lines}",f"Supplier items resolved: {result.supplier_items_resolved}",f"Supplier items unresolved: {result.supplier_items_unresolved}",*[f"{x.value.replace('_',' ')}: {counts[x]}" for x in labels],f"EXTERNAL EVIDENCE REQUIRED: {result.records_requiring_external_accounting_evidence}",f"PO/receipt manual matches: {result.manual_links_after}","",f"Purchasing manual reconciliation reduction ratio: {result.purchasing_manual_reconciliation_reduction_ratio:.2%}",f"PO-line reconciliation rate: {result.po_line_reconciliation_rate:.2%}","OBSERVED LAB RESULT from deterministic synthetic fixtures; no success threshold is imposed.","","Chapter 2 question impact",*[f"{x.question_id}: {x.status.value.replace('_',' ')} — {x.reason}" for x in result.question_impacts],"","Modeled purchasing reconciliation burden (MODELED ASSUMPTION): 80 annual hours","This is not observed labor savings.","","Current lab verdict: UNTESTED",""]
    def trace(title,x):
        return [title,"","PURCHASE ORDER",x.po.canonical_po_id,"","SUPPLIER",x.po.supplier_id,"","SUPPLIER ITEM",x.line.supplier_item_id,"","CANONICAL SKU",x.canonical_sku or "UNRESOLVED","","ORDERED",str(x.line.ordered_quantity),"","RECEIVED",str(x.receipt.received_quantity if x.receipt else 0),"","EXPECTED LOCATION",x.po.destination_store_id,"","ACTUAL RECEIPT LOCATION",x.actual_location or "NONE","","RESULT",x.result.value.replace('_',' '),""]
    lines += trace("CLEAN RECEIPT",clean)+trace("PARTIAL RECEIPT",partial)+trace("WRONG LOCATION",wrong)+trace("UNRESOLVED SUPPLIER ITEM",unresolved)
    return "\n".join(lines)


def returns_transfers_report() -> str:
    result = run_returns_transfers_experiment()
    rc, tc = result.return_counts, result.transfer_counts
    return_labels = (ReturnResult.RECONCILED, ReturnResult.CROSS_STORE_RECONCILED,
        ReturnResult.MISSING_ORIGINAL_REFERENCE, ReturnResult.UNRESOLVED_IDENTITY,
        ReturnResult.MISSING_REASON, ReturnResult.INVENTORY_EFFECT_EXCEPTION,
        ReturnResult.PARTIALLY_RECONCILED, ReturnResult.UNKNOWN)
    transfer_labels = (TransferResult.RECONCILED, TransferResult.MISSING_RECEIPT,
        TransferResult.PARTIAL_RECEIPT, TransferResult.OVER_RECEIPT,
        TransferResult.LOCATION_EXCEPTION, TransferResult.CANCELLED_TRANSFER_MOVEMENT,
        TransferResult.UNRESOLVED_IDENTITY, TransferResult.INVENTORY_EFFECT_EXCEPTION,
        TransferResult.UNKNOWN)
    lines = ["James River Outfitters", "Chapter 7 — Returns and Transfers", "",
        "Before configuration", "--------------------",
        f"Manual return/transfer reviews: {result.before['manual_return_transfer_reviews']}",
        f"Manual transaction lookups: {result.before['manual_transaction_lookups']}",
        f"Manual transfer closure checks: {result.before['manual_transfer_closure_checks']}",
        f"Manual identity interpretations: {result.before['manual_identity_interpretations']}",
        f"Apparent inventory exceptions: {result.before['apparent_inventory_exceptions']}", "",
        "Returns after configuration", "---------------------------",
        f"Total returns: {result.total_returns}",
        *[f"{item.value.replace('_', ' ')}: {rc[item]}" for item in return_labels], "",
        "Transfers after configuration", "-----------------------------",
        f"Total transfers: {result.total_transfers}",
        *[f"{item.value.replace('_', ' ')}: {tc[item]}" for item in transfer_labels], "",
        f"Records requiring manual reconciliation: {result.manual_reviews_after}",
        f"Return reconciliation rate: {result.return_reconciliation_rate:.2%}",
        f"Transfer reconciliation rate: {result.transfer_reconciliation_rate:.2%}",
        f"Manual review reduction ratio: {result.manual_return_transfer_review_reduction_ratio:.2%}",
        "OBSERVED LAB RESULT from deterministic synthetic fixtures; no success threshold is imposed.", "",
        "Chapter 2 question impact",
        *[f"{x.question_id}: {x.status.value.replace('_', ' ')} — {x.reason}" for x in result.question_impacts], "",
        "Modeled return/transfer burden categories (MODELED ASSUMPTION): manual return lookup; cross-store reconciliation; reason follow-up; transfer closure and quantity/inventory investigation.",
        "No modeled reduction is an observed labor or dollar saving.", "",
        "Detection is not correction: configuration detects a missing return reason but cannot guarantee employee compliance.",
        "Accounting reconciliation is outside Chapter 7; no accounting evidence is fabricated.", "",
        "Current lab verdict: UNTESTED", ""]

    def return_trace(title: str, outcome):
        record = outcome.record
        return [title, "", "RETURN", record.return_id, "", "ORIGINAL TRANSACTION",
            record.original_reference or "MISSING", "", "ORIGINAL SALE STORE",
            record.original_sale_store or "ONLINE / NO SALE STORE", "", "RETURN STORE",
            record.return_store, "", "SKU", record.canonical_sku or "UNRESOLVED", "",
            "REASON", record.reason or "MISSING", "", "INVENTORY EFFECT",
            f"{record.inventory_effect:+d} at {record.return_store}", "", "RESULT",
            outcome.result.value.replace("_", " "), ""]

    def transfer_trace(title: str, outcome):
        record = outcome.record
        return [title, "", "TRANSFER", record.transfer_id, "", "FROM", record.sending_store,
            "", "TO", record.receiving_store, "", "SENT", str(record.quantity_sent), "",
            "RECEIVED", str(record.quantity_received), "", "SENDER / RECEIVER EFFECT",
            f"{record.sender_inventory_effect:+d} / {record.receiver_inventory_effect:+d}", "",
            "RESULT", outcome.result.value.replace("_", " "), ""]

    find_return = lambda value: next(x for x in result.return_outcomes if x.result is value)
    find_transfer = lambda value: next(x for x in result.transfer_outcomes if x.result is value)
    lines += return_trace("CLEAN RETURN", find_return(ReturnResult.RECONCILED))
    lines += return_trace("CLEAN CROSS-STORE RETURN", find_return(ReturnResult.CROSS_STORE_RECONCILED))
    lines += return_trace("MISSING RETURN REASON", find_return(ReturnResult.MISSING_REASON))
    lines += transfer_trace("CLEAN TRANSFER", find_transfer(TransferResult.RECONCILED))
    lines += transfer_trace("SENT, NOT RECEIVED", find_transfer(TransferResult.MISSING_RECEIPT))
    lines += transfer_trace("PARTIAL TRANSFER", find_transfer(TransferResult.PARTIAL_RECEIPT))
    lines += transfer_trace("TRUE INVENTORY-EFFECT EXCEPTION", find_transfer(TransferResult.INVENTORY_EFFECT_EXCEPTION))
    return "\n".join(lines)
