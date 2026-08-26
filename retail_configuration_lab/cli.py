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
    return 0


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
