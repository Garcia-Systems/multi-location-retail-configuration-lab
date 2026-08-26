# Chapter 16 — Weak Native Coverage Scenario

> **This is a synthetic sensitivity scenario. It does not describe the capabilities or economics of any real retail software product.**

Chapter 15 asked how configuration-first behaves with unusually strong native coverage. This chapter holds the business questions constant and tests the opposite boundary: useful store sales, inventory, purchasing, and returns functions remain, but cross-system semantics are weak. Run it with:

```bash
python -m retail_configuration_lab weak-native-coverage
```

## Supported is not export-only

A supported store-sales report can answer its question from native operational meaning. An export proves only that fields can leave a system. The fictional weak matrix therefore preserves supported sales by store and SKU, on-hand inventory, purchase orders, and store returns while classifying cross-channel, transfer, and accounting linkage as exports, automation possibilities, gaps, or unknowns. Every capability and price is a **MODELED ALTERNATIVE ASSUMPTION**.

## Configuration sprawl and workaround chains

```text
NO NATIVE E-COMMERCE / STORE RECONCILIATION
  → scheduled export → store mapping → SKU mapping → automation
  → BI reconciliation view → manual review

NO TRANSFER RECONCILIATION
  → transfer export → location mapping → BI exception view → manual closure
```

These `WorkaroundLayer`-like fixture records are **OBSERVED IMPLEMENTATION STRUCTURE**. The count measures structural obligations, not human effort. Exports, mappings, automation, BI, and review can form a useful control, but also a change-sensitive system of configuration.

Automation moves exports, checks missing records, and raises alerts. It cannot infer a reliable receiving acknowledgement or prove physical receipt. BI consolidates available evidence; it cannot create accounting transaction linkage or missing return meaning. Thus **more reporting is not more source truth**.

## Questions and burden

The experiment deterministically re-evaluates all Chapter 2 IDs for base, strong, and weak scenarios. Basic store sales remains answered; cross-channel, transfer, accounting, and management questions degrade or depend on workarounds. The dependency ratio is the number of the 13 explicitly evaluated cross-system/BI-relevant question IDs touched by at least one workaround divided by 13. It has no success threshold.

The economic preview keeps modeled setup cost separate and calculates only:

```text
annual post-configuration cost
= annual platform cash + annual support/admin + residual operational burden
```

Setup assumptions explicitly cover exports, mappings, automation, BI, validation, and process change; they are not inferred from object counts. Residual operational, administration, support, unknown, and exception-review burdens remain visible. A lower fictional subscription therefore does not establish lower cost.

## Residuals and response

The strongest **BOUNDED** residual is cross-channel exception reconciliation: order and POS exports plus mappings are clear inputs, a defined exception record is the output, and two e-commerce questions bound its ownership surface. This is the Chapter 17 candidate—not an implementation.

The accounting/operational linkage residual is **BROAD** across sales, returns, and purchasing. Physical transfer acknowledgement is **PROCESS**; workaround maintenance is **ADMINISTRATION**; return-reason export consistency is **UNKNOWN**. Broad gaps should not be disguised as a small custom edge: migration, standardization, or investigation may be more coherent.

The transparent ordered rule selects `STANDARDIZE_FIRST` when a broad workflow gap coexists with permanent support/admin cost at least as high as platform cash cost. Other modeled facts could select configure plus automation, a narrow custom edge, investigate, migrate, a one-off project, or no deal. Coverage is not a score and the scenario response does not alter the lab verdict.

```text
CONFIGURATION-FIRST works best when underlying products expose useful capabilities

WEAK NATIVE COVERAGE
  ↓
EXPORTS → MAPPINGS → AUTOMATIONS → BI WORKAROUNDS → MANUAL REVIEW
  ↓
CONFIGURATION CAN BECOME ITS OWN COMPLEX SYSTEM

CONFIGURATION SPRAWL ≠ FULL CUSTOM IS AUTOMATICALLY BETTER
```

**Overall lab verdict: UNTESTED.** We now have a candidate for the narrowest possible custom intervention. The next experiment is to implement only that edge and see whether it earns its ownership cost. Chapter 17 is not implemented here.
