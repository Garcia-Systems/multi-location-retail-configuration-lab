# Chapter 14 — Acquired Store Stress Test

Chapter 13 was a control: Store #7 used the same platforms, identities, processes, and reporting structure. Chapter 14 deliberately breaks those reuse assumptions with **James River Outfitters — Shenandoah Acquisition**, canonical identity `JRO-STORE-008`. It is newly acquired, fictional, and not yet standardized.

```text
STANDARDIZED STORE #7                 FRAGMENTED STORE #8
same platform and process             RidgePOS + RidgeInventory + RidgeSheets
        ↓                                      ↓
high structural reuse                 mapping, module, migration, and edge pressure
```

Run the deterministic experiment:

```bash
python -m retail_configuration_lab acquired-store
```

## Fragmentation as received

The fictional RidgePOS has CSV sales and return exports, a local SKU and category field, but its API/change behavior is unknown. RidgeInventory exports on-hand, adjustments, and receiving evidence without James River identities. RidgeSheets is not an application: it is a structured fixture representing manually maintained transfer exports. These are **MODELED ALTERNATIVE ASSUMPTIONS**, not vendor claims.

Identity is the primary stress point. `BLTS-M-BL` maps cleanly—but still needs a governed new mapping—to `JRO-1042-BLU-M`. The reused code `1042` has multiple possible canonical matches and is never guessed. `OLD-BLUE` is unmapped. `SHEN-001` is local-only merchandise awaiting a merchandising decision. `BLTS-M-BL-2` merely looks like a duplicate and is not automatically merged. Historical aliases, reused codes, incomplete supplier context, and inconsistent categories separate **current-state mappable data** from **historical data requiring cleanup**. Perfect backfill is not assumed.

Return semantics also differ: the fixture lacks reason and original-transaction evidence, rejects cross-store handling, and represents damage as an adjustment. Configuration reports these violations rather than silently claiming compliance. Transfer rows contain free-text locations, inconsistent identities, missing receipt acknowledgement, and edited status.

Ten compatibility dimensions remain explicit—identity, reporting, e-commerce, purchasing, returns, transfers, automation, BI, process, and support—and use a compact fit vocabulary. They are not collapsed into a complexity score. At eight-store scope, sales, inventory, transfers, and management briefing are partial; returns are not answered; purchasing is unknown.

## Bounded standardization first

The experiment assigns the canonical store identity, accepts only clean SKU/category/location/supplier aliases, controls the current transfer template, and requires current-period return reasons where possible. It neither rewrites history nor forces ambiguous identities. Current transfers improve and one clean SKU resolves; historical ambiguity, local-only merchandise, and the notification technical gap remain.

This distinction matters: inconsistent transfer locations are a **process gap**; a missing source capability is a **technical gap**. Standardization can repair the former but cannot manufacture the latter.

## Keep multiple responses open

The modeled configured-module path is deliberately narrow:

```text
RidgePOS daily CSV
        ↓
configured sales/category/store import
        ↓
canonical reporting layer
```

It makes sales reporting reusable with configuration but does not become a generalized adapter. The migration counterfactual records fictional setup, cleanup, and training hours and the prospect of reduced platform diversity; it does not perform a migration. RidgeInventory is a migration candidate because retaining it creates a second export, mapping, training, and schema-change surface.

A historical identifier resolver is recorded as a possible bounded custom edge because missing context prevents deterministic resolution of reused aliases. It affects store-sales and return questions. It is **not implemented**, and its existence does not make custom software the primary response. It is an input to Chapter 17.

The transparent decision order asks whether bounded standardization demonstrably improves identity/process gaps, whether a configured module closes the material remainder, whether one bounded technical edge remains, whether broad permanent duplication favors migration, whether value warrants work, or whether discovery is insufficient. In this fixture, bounded standardization is the first action while migration and a narrow edge remain live later choices.

## Structural and support effects

Store #7 retains its 70% structural reuse control. Store #8 reuses 5 of 20 compatible structural items (25%), producing a 45 percentage-point `fragmentation_reuse_delta`. Store #8 also exposes mappings, blocked/unknown work, and technical/new-capability structure separately. These are **OBSERVED LAB RESULTS** from synthetic fixtures, not time or cost estimates.

Keeping the acquired family creates six incremental obligations: second-POS mappings, a second inventory export, historical aliases, transfer normalization, acquired-user support, and another schema-change exposure. Under Chapter 11's residual framing, current identity burden can reduce, historical cleanup remains, platform support increases, mapping moves into administration, and cross-channel evidence remains unknown. Migration/setup, cleanup, training, and recurring economic effects remain **MODELED ASSUMPTIONS**; this is not Chapter 19 economics.

```text
STANDARDIZATION → HIGH REUSE → CONFIGURATION COMPETES WELL

FRAGMENTATION → MORE MAPPINGS + MORE UNKNOWNs + MORE SUPPORT DIVERSITY
              + MORE TECHNICAL EDGES → CONFIGURATION ECONOMICS WEAKEN

FRAGMENTATION ≠ AUTOMATIC CUSTOM SOFTWARE
STANDARDIZE / MIGRATE / DEFER may be rational responses.
```

> The lab observes how a deliberately fragmented synthetic acquired store reduces reuse and increases configuration/support diversity. It does not measure real acquisition integration cost or establish what any commercial platform can support.

The next chapters test platform-capability extremes. They are not implemented here. **Current lab verdict: UNTESTED.**
