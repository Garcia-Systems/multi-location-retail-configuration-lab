# Chapter 6 — Purchasing and Inventory Configuration

Procurement reconciliation should begin with identity and configuration, not a new procurement application. The experiment asks which purchasing questions existing fictional capabilities could answer after coherent configuration:

```text
PURCHASING QUESTION → CAPABILITY → IDENTITY → OWNERSHIP / STATUS RULES
                    → RECEIVING → EXCEPTIONS → HUMAN ATTENTION
```

The RiverBuy/RiverStock/RiverBooks capabilities discussed here are **MODELED ALTERNATIVE ASSUMPTIONS**, not claims about commercial products. The JSON crosswalks, rules, and fixtures are **OBSERVED IMPLEMENTATION STRUCTURE**. Deterministic classifications and counts are **OBSERVED LAB RESULT**.

## Three identities, not one

`JRO-SUPPLIER-014` identifies Blue Ridge Textiles. `BR-1042` identifies that supplier's catalog item. `JRO-1042-BLU-M` identifies James River Outfitters' canonical SKU. Therefore:

```text
SUPPLIER ≠ SUPPLIER ITEM ≠ CANONICAL SKU
```

The configured mapping relates these identities without overwriting source identifiers or provenance. A missing mapping remains missing; `BR-AMBIG`, with two candidates, is not guessed.

Purchase orders also preserve distinct references. RiverBuy `PO-82451`, RiverStock receipt reference `RCV-PO-82451`, accounting reference `BUY-82451`, and canonical `JRO-PO-82451` are linked by explicit prefix rules. The canonical ID does not erase any source evidence.

## Ownership, status, and replenishment

Every PO owns an intended canonical destination store. Receipt aliases such as `RVA-WH` map to a canonical location for comparison, but a receipt mapped to `JRO-STORE-004` is not reassigned to a PO destined for `JRO-STORE-002`; it is a location exception.

PO status (`DRAFT`, `OPEN`, `PARTIALLY_RECEIVED`, `RECEIVED`, `CANCELLED`, `CLOSED`) describes the order lifecycle. Receiving status (`NOT_RECEIVED`, `PARTIALLY_RECEIVED`, `FULLY_RECEIVED`, `OVER_RECEIVED`, `REJECTED`, `UNKNOWN`) describes physical evidence separately. Classification compares ordered and received quantities rather than inferring receipt state from PO status.

The configured taxonomy—`CORE`, `SEASONAL`, `LOCAL_ASSORTMENT`, and `NON_REPLENISHING`—adds operational context only. It does not forecast demand or assign artificial severity. A CORE discrepancy can be discussed differently from a non-replenishing item without changing the observed variance.

## Before and after

```text
BEFORE
supplier aliases + item aliases + PO references + store identifiers + statuses
        ↓
manual reconciliation

AFTER CONFIGURATION
canonical supplier + supplier-item mapping + canonical PO linkage
+ canonical store + explicit receiving rules
        ↓
routine cases reconcile + real exceptions stand out
```

Run the deterministic experiment:

```bash
python -m retail_configuration_lab purchasing
```

Before configuration, all 10 PO/receipt links require manual matching. After configuration, three require manual matching, a **70% purchasing manual reconciliation reduction ratio**. Two of eight evaluable lines fully reconcile, a **25% PO-line reconciliation rate**. These ratios have no imposed success threshold.

The clean `PO-82451` fixture is an identity-only false exception: PO item `BR-1042` and receipt item `1042` map to `JRO-1042-BLU-M`; eight ordered and eight received at Richmond reconcile. Other fixtures deliberately retain one partial receipt, one over-receipt, one missing receipt, one wrong-location receipt, one cancelled-PO receipt, two unresolved identities (missing and ambiguous), and one inventory-effect disagreement.

## Inventory and accounting boundaries

A valid receipt predicts an increase in the destination store's on-hand inventory. One clean fixture records that increase. Another has a structurally correct five-unit receipt but only a three-unit inventory effect, so purchasing linkage succeeds while the inventory exception remains visible.

The PO and receipt retain accounting references, but Chapter 6 does not inspect postings. `JRO-PO-82451` therefore carries `EXTERNAL EVIDENCE REQUIRED`; no accounting posting or agreement is fabricated.

## Business-question impact

The experiment marks `PUR-01` and `PUR-02` **ANSWERED** because its bounded exception queue identifies purchasing attention and receiving discrepancies. `INV-03` is **PARTIALLY ANSWERED** because supplier-item defects can be separated from observed inventory effects, not every inventory discrepancy. `FIN-01` remains **PARTIALLY ANSWERED** because identifiers are retained while accounting evidence remains external.

An 80-hour annual purchasing burden shown by the CLI is a **MODELED ASSUMPTION** only. Applying a synthetic ratio to it would be modeled extrapolation, not observed effort or dollars.

Quantity discrepancies, wrong-store and cancelled-PO receipts, missing and ambiguous mappings, inventory-effect disagreement, and missing accounting evidence remain unresolved. Supplier receipts are distinguished from store transfer receipts, but returns and transfer reconciliation belong to Chapter 7 and are not implemented here.

> The lab observed that configuration reduced synthetic purchasing and receiving reconciliation work. It did not observe real retailer labor savings or prove equivalent capabilities in any commercial product.

The current lab verdict remains **UNTESTED**.
