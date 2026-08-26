# Chapter 2 — Define the Business Questions

Chapter 1 asked what the fictional ecosystem theoretically can do. That feature inventory is useful, but a system capability is not a business question. Chapter 2 deliberately steps away from systems and asks: **What does James River Outfitters actually need to know or act on?**

> A dashboard is not a requirement. A report is not a requirement. An integration is not a requirement. The operational question comes first.

```text
CHAPTER 1
What can the ecosystem theoretically do?
        ↓
CHAPTER 2
What does the business actually need to know or act on?
        ↓
LATER CHAPTERS
Can configuration make the existing capabilities answer those questions?
```

## Start with action, not features

“What reports can RiverPOS produce?” invites a tour of functionality. “Which store/SKU inventory mismatches remain unresolved at the end of the daily operating period?” establishes a testable need. The inventory question enables an action—investigate material discrepancies—and specifies evidence, freshness, owner, and scope.

```text
BUSINESS QUESTION
        ↓
DECISION OR ACTION
        ↓
REQUIRED EVIDENCE
        ↓
ACCEPTABLE FRESHNESS
        ↓
OWNER
        ↓
ONLY THEN: MAP TO EXISTING CAPABILITIES
```

The synthetic model uses five compact types: **DESCRIPTIVE** asks what happened, **EXCEPTION** asks what needs attention, **RECONCILIATION** asks which records disagree, **DECISION** identifies an operational choice, and **CONTROL** asks whether a required process happened. A question without a decision, action, control, or management purpose is rejected.

> The smallest useful question often produces a smaller and cheaper solution.

## Fictional operational owners

These are roles, not named people or claims about a real retailer:

- **Central Operations Manager** prioritizes cross-store exceptions and coordinates follow-up.
- **Inventory Manager** investigates stock discrepancies and adjustment or transfer exceptions.
- **Purchasing Manager** reviews purchase, receipt, and supplier exceptions.
- **Finance / Accounting** reconciles operational evidence and manages close controls.
- **E-Commerce Operations** resolves fulfillment, cancellation, and online-return effects.
- **Store Manager** acts on local sales, returns, receiving, and transfer exceptions.

The roles intentionally form a small responsibility vocabulary, not an organization chart.

## The evidence contract

Every question identifies the minimum fields later experiments would need. `TRN-01`, for example, asks which transfers were sent but not received and requires transfer ID, both stores, sent and received timestamps/statuses, SKU, and quantity. `ECOM-01` requires online order ID, channel, fulfillment location, order status, SKU, and quantity. These definitions do **not** create transfer or order datasets and do not perform reconciliation. They provide a contract against which later configuration can be tested.

Scope is equally explicit: a question can cover one or all stores, cross-store operations, an e-commerce channel, cross-channel activity, purchasing, or the enterprise. The reader need not guess scope from prose.

## Fresh enough for the action

The vocabulary is `REAL_TIME`, `NEAR_REAL_TIME`, `DAILY`, `WEEKLY`, `PERIOD_CLOSE`, and `ON_DEMAND`. Real-time is not automatically desirable. Transfer exceptions and stock effects are modeled as daily needs; a central exception briefing is weekly; accounting reconciliation is needed at period close; sales-by-store inquiry is on demand. Faster evidence may cost more without improving the decision.

## Coverage is a hypothesis

A question can have a `DIRECT`, `PARTIAL`, `MULTIPLE_CAPABILITIES_REQUIRED`, `NO_KNOWN_CAPABILITY`, or `UNKNOWN` relationship to Chapter 1. `SAL-01` needs store, SKU, and period capabilities together. `RET-01` needs transaction, inventory, return-accounting, and reconciliation evidence. `INV-03` remains unknown because identity reliability is deliberately untested.

`DIRECT` does not mean solved. It means only that the modeled inventory suggests a plausible direct path. Configuration, data quality, workflow behavior, and implementation still could fail. Conversely, no known capability does not justify custom software automatically. A later response might be process change, configuration, automation, BI, a revised requirement, acceptance of residual burden, or—only when justified—a custom edge.

## Execute the model

```bash
python -m retail_configuration_lab questions
python -m retail_configuration_lab questions --area inventory
python -m retail_configuration_lab questions --coverage NO_KNOWN_CAPABILITY
python -m retail_configuration_lab questions --owner "Inventory Manager"
python -m retail_configuration_lab questions --id INV-01
```

Execution validates identifiers, owners, actions, evidence fields, controlled vocabularies, coverage rules, and Chapter 1 references. It deterministically counts questions by area, type, freshness, and coverage. That successful validation and counting is an **OBSERVED LAB RESULT**; the JSON definitions and mappings are **OBSERVED IMPLEMENTATION STRUCTURE**. The fictional requirements themselves are **MODELED ASSUMPTION**, while their Chapter 1 mappings rely on **MODELED ALTERNATIVE ASSUMPTIONS**.

## What remains untested

No report, dashboard, integration, automation, reconciliation engine, or configuration has been built. The chapter does not establish evidence quality, validate workflows, or solve store/SKU/channel identity. It does not prove that any question can actually be answered. Chapter 3's identity experiment is deliberately not implemented. The current lab verdict remains **UNTESTED**.
