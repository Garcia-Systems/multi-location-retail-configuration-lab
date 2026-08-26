# Chapter 13 — Add Store #7

Scaling is a claim until it is executed. This chapter adds the standardized synthetic **James River Outfitters — Richmond West** location (`JRO-STORE-007`) to the configured six-store control environment. It does not introduce the fragmented acquisition conditions reserved for the next experiment.

```bash
python -m retail_configuration_lab add-store
```

## Standardized growth, not copied software

The control assumption is **MODELED ALTERNATIVE ASSUMPTION**: Richmond West uses RiverPOS, RiverStock, RiverBuy, RiverCommerce, RiverFlow, RiverBI, the common merchandise taxonomy, and the existing procedures. The experiment therefore compares `SCALE BY COPYING SOFTWARE` with `SCALE BY ADDING CONFIGURATION TO REUSABLE STRUCTURE`.

The store receives one canonical identity plus source-provenance mappings for RiverPOS `STORE-RW`, RiverStock `STORE_7`, RiverBooks `LOC-RICHMOND-WEST`, and RiverCommerce `fulfillment_richmond_west`. `ALL_STORES` expands from six members to seven; the report definition remains unchanged. Duplicate identity, mapping, membership, or onboarding attempts are rejected.

## Common identity does not mean identical assortment

Richmond West carries the existing `JRO-1042-BLU-M` SKU and does not carry existing `JRO-1055-GRN-L`. No product, variant, SKU, or category is cloned. Assortment is store configuration over the canonical catalog.

## Executed reuse

Compact deterministic evidence exercises a store sale and inventory row, online fulfillment (the channel stays `ONLINE` while fulfillment is Store #7), a purchasing receipt, local and cross-store returns, and transfers in both directions. The existing purchasing, return, transfer, automation, BI, and process-rule structures apply. One outbound transfer is deliberately partial: onboarding validation succeeds while the genuine operational exception remains visible.

Native store/category/inventory reports and management group selection consume the expanded configured scope. RiverFlow's transfer alert, mapping validation, distribution, and reconciliation trigger use the same automation definitions. RiverBI's cross-store sales, inventory, transfer, purchasing, and management-exception views use the canonical store scope. Chapter 2 questions are not redefined: Store #7 supplies new evidence to the same sales, unresolved-transfer, and briefing questions.

## Onboarding inventory and ratios

The fixture evaluates **20 applicable tasks**: 11 `REUSED_UNCHANGED`, 3 `REUSED_WITH_STORE_CONFIGURATION`, 1 `NEW_MAPPING`, 5 `NEW_CONFIGURATION`, and 0 `NEW_CAPABILITY_REQUIRED`, blocked, or unknown final tasks. A missing Store Manager role is preserved in the trace as an initial block, then repaired by copying the existing role template; the task's final classification is new configuration.

Structural reuse is `(REUSED_UNCHANGED + REUSED_WITH_STORE_CONFIGURATION) / all required applicable tasks`; `NOT_APPLICABLE` tasks are excluded and zero is handled safely. Here it is `14 / 20 = 70%`. New-capability ratio is `NEW_CAPABILITY_REQUIRED / applicable tasks`, here `0 / 20 = 0%`. Neither ratio has a success threshold or weighted score.

These are **OBSERVED IMPLEMENTATION STRUCTURE** counts and **OBSERVED LAB RESULT** ratios—not labor measurements. Report definitions remain 5 → 5, automation definitions 6 → 6, BI report definitions 7 → 7, process rules 5 → 5, and new code paths 0 → 0. Configuration and evidence records grow without a Store #7-specific reporting, automation, BI, or reconciliation engine.

## Support and residual onboarding problems

The fixture optionally models $720 of incremental annual identity/access review and exception-volume support as a **MODELED ASSUMPTION**. It does not multiply the whole Chapter 12 surface by `7 / 6`. No implementation hours are inferred from task counts. The initially omitted role assignment demonstrates that standardized does not mean zero work.

> The lab observes which configuration and implementation structures are reused when a standardized seventh synthetic store is added. It does not directly observe real onboarding labor or prove that a commercial retail suite scales the same way.

The narrow result is: **The standardized synthetic store reused most of the configured implementation structure.** It is not `BUY / CONFIGURE CONFIRMED`. Fragmentation has not yet been tested, so the **Current lab verdict: UNTESTED**.
