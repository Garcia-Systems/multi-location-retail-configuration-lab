# Chapter 7 — Returns and Transfers

James River Outfitters remains fictional. This chapter asks how much synthetic return and transfer reconciliation can be achieved with identities, status rules, native transaction behavior, and explicit process semantics. Existing operational systems remain authoritative: the Python code evaluates configured evidence; it is not a return application, transfer application, integration service, or accounting system.

## Different business events

```text
RETURN                         TRANSFER
original sale                  store A inventory
        ↓                              ↓
customer gives goods back      internal location movement
        ↓                              ↓
financial + inventory effects  store B inventory
```

A return reverses part of a customer-facing event and may cross a channel or store. A transfer moves inventory that the company already owns. Neither should be hidden under a generic adjustment label. Chapter 7 builds directly on Chapter 3 identities, Chapter 5 order linkage, and Chapter 6 inventory-effect semantics.

## Configured semantics

The files in `config/returns_transfers/` are **OBSERVED IMPLEMENTATION STRUCTURE**. They encode the **MODELED ALTERNATIVE ASSUMPTIONS** that the fictional POS supports cross-store returns, its ecosystem supports online returns and reason rules, and the fictional inventory platform exposes sent and received transfer evidence. They make no claim about a commercial vendor.

Return configuration supplies a compact status vocabulary, valid reason codes, a completed-return reason requirement, channel/location support, and expected restock effects. `DEFECTIVE` and `DAMAGED` are configured as non-restockable without introducing a disposition workflow. The return record preserves the original transaction, original channel, return channel, original sale store, return store, SKU, quantity, reason, status, effect, source, and provenance. It intentionally contains no refund or accounting model.

Original sale and return location answer different questions. In the clean cross-store fixture, the original sale remains `JRO-STORE-002`, the return remains `JRO-STORE-005`, and the `+1` effect belongs to store 005. The sale is never rewritten. An online sale returned in a store likewise retains `JRO-CHANNEL-ONLINE` as its original channel and `JRO-CHANNEL-STORE` as its return channel.

Transfer configuration says that sent evidence does not imply receipt. A normal movement decrements the sender by sent quantity and increments the receiver by received quantity. Closure requires receiver evidence and equal quantities; a `RECEIVED` label alone cannot override quantity or inventory evidence. Sender, receiver, timestamps, statuses, quantities, effects, source, SKU, and provenance remain separate.

## Deterministic scenarios and validation

The synthetic return fixtures cover original-store, cross-store, e-commerce, fulfillment-store, and different-store returns; valid and missing transaction linkage; unresolved SKU; missing reason; inventory mismatch; and an incomplete state. Transfer fixtures cover complete, missing, partial, excess, wrong-location, unresolved-SKU, cancelled-movement, correct effects, absent receiver increment, and received-but-effect-mismatched cases.

Structural validation rejects duplicate IDs, invalid statuses or supplied reasons, negative quantities, nonexistent stores, falsely resolved SKUs, malformed transaction references, missing provenance, same-location transfers, and impossible effect direction. By contrast, a missing original reference, missing reason, unknown mapping, or absent receipt is valid-but-incomplete operational evidence. It is classified rather than discarded.

## Before and after configuration

Before configuration, the modeled fixture requires 20 manual return/transfer reviews, including six transaction lookups and ten transfer closure checks. Raw IDs, inconsistent status meanings, optional reasons, inconsistent online references, confused sale/return locations, and manual closure produce apparent exceptions.

After applying canonical identities and the configured rules, five of ten returns and two of ten transfers reconcile fully. Thirteen records retain a reason for manual review, producing a synthetic manual-review reduction ratio of 35%. The return reconciliation rate is 50% and the transfer reconciliation rate is 20%; each denominator is all ten structurally valid records of its type. These are **OBSERVED LAB RESULTS**, not thresholds or projections of retailer performance.

The clean cross-store return reconciles while preserving both locations. Missing reason, missing reference, unresolved identity, partial state, and effect mismatch remain visible. Transfers separately expose two missing receipts, one partial receipt, one over-receipt, one wrong location, one cancelled movement, one unresolved identity, and one true inventory-effect exception. In the true exception, status is `RECEIVED` and both quantities are five, but the receiver effect is only `+3`.

```text
RAW RETURN / TRANSFER RECORDS
        ↓
INCONSISTENT IDENTITY + STATUS SEMANTICS
        ↓
MANUAL INTERPRETATION

CONFIGURED IDENTITY
+ CONFIGURED STATUS RULES
+ CONFIGURED INVENTORY EFFECTS
        ↓
ROUTINE CASES CLASSIFIED
        ↓
TRUE EXCEPTIONS SURFACE
```

## Chapter 2 impact

Existing IDs are reused. `TRN-01` (sent but not received) and `TRN-02` (quantity disagreement) become `ANSWERED`. `RET-02` becomes `ANSWERED` because missing reasons are detectable. `RET-01` is only `PARTIALLY_ANSWERED`: operational transaction and inventory evidence is available, but accounting is absent. `INV-02` is partial because these effects do not create general adjustment controls. `FIN-01` remains `NOT_ANSWERED`; the lab fabricates no accounting evidence.

## Detection, correction, and scope

```text
SYSTEM CAN DETECT:
missing return reason

SYSTEM CANNOT GUARANTEE:
employee records the reason correctly
```

Detection is not correction. Missing reason data is a deliberate process/data-quality residual suitable for a later process experiment. Location, quantity, inventory, and missing-control exceptions similarly remain operational work. Manual return lookup, cross-store reconciliation, reason follow-up, transfer closure, quantity investigation, and inventory movement investigation are **MODELED ASSUMPTION** burden categories. No modeled hour or dollar reduction is an observed saving.

Run the experiment with:

```bash
python -m retail_configuration_lab returns-transfers
```

The output includes clean return and transfer traces, a cross-store return, missing reason, missing receipt, partial receipt, and true effect exception. It does not schedule exports, send alerts, trigger workflows, build BI, reconcile accounting, or implement Chapter 8 automation.

> The lab observed deterministic improvements in synthetic return and transfer reconciliation after configuration. It did not observe real retailer labor savings or establish the capabilities of any real commercial platform.

The current lab verdict remains **UNTESTED**. Major experiments remain.
