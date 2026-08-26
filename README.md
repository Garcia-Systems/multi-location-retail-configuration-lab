# Multi-Location Retail Configuration Lab

> An executable solutions-engineering lab that tests whether configuration, native integrations, automation, BI, and process change can solve a multi-location retailer’s operational problems before custom software is justified.

This compact Python textbook tests a configuration-first method against a wholly synthetic opportunity. **James River Outfitters is fictional**, and every business detail, financial quantity, and alternative capability is a modeled assumption unless deterministic execution labels it otherwise. No real customer or commercial vendor is represented.

## Purpose and completed status

The earlier fictional cookbook verdict was **BUY / CONFIGURE**: it assumed that an existing alternative adequately met the need at materially lower cost or risk. The final lab verdict is **INVESTIGATE** and the original hypothesis is **WEAKENED**.

> The original BUY / CONFIGURE verdict is an input hypothesis, not a conclusion of this executable lab.

The central question is: **Can configuration genuinely solve enough of the problem to deserve the BUY / CONFIGURE verdict?** If not, what economically meaningful residual remains?

## Architecture and configuration-first principle

The textbook is deliberately file-backed and stateless: immutable Python value objects load synthetic JSON fixtures and configuration, chapter functions derive results, and one CLI exposes the complete experiment. It does not require a database or implement the Chapter 18 counterfactual architecture. The intervention order is the architectural boundary, not merely a reading order:

```text
BUSINESS PROBLEM
        ↓
CURRENT PRODUCT CAPABILITIES
        ↓
CONFIGURATION
        ↓
NATIVE INTEGRATIONS
        ↓
AUTOMATION
        ↓
BI / REPORTING
        ↓
PROCESS CHANGE
        ↓
RESIDUAL GAP
        ↓
CUSTOM EDGE ONLY IF JUSTIFIED
```

## Evidence vocabulary

- **MODELED ASSUMPTION** — a fictional quantity or claim used in the analysis.
- **OBSERVED LAB RESULT** — behavior demonstrated by deterministic synthetic execution.
- **OBSERVED IMPLEMENTATION STRUCTURE** — repository artifacts such as configuration, mappings, fixtures, rules, reports, or scenarios; not automatically measured labor.
- **SENSITIVITY ASSUMPTION** — a hypothetical changed value used to test economics.
- **MODELED ALTERNATIVE ASSUMPTION** — fictional capability, cost, limitation, or behavior assigned to a buy/configure alternative, never a claim about a real vendor.

## Install and run

Python 3.12 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m retail_configuration_lab baseline
python -m retail_configuration_lab capabilities
python -m retail_configuration_lab questions
python -m retail_configuration_lab identity
python -m retail_configuration_lab native-reporting
python -m retail_configuration_lab ecommerce-reconciliation
python -m retail_configuration_lab purchasing
python -m retail_configuration_lab returns-transfers
python -m retail_configuration_lab automation
python -m retail_configuration_lab bi-reporting
python -m retail_configuration_lab process-change
python -m retail_configuration_lab residual-gaps
python -m retail_configuration_lab support-surface
python -m retail_configuration_lab add-store
python -m retail_configuration_lab acquired-store
python -m retail_configuration_lab strong-native-suite
python -m retail_configuration_lab weak-native-coverage
python -m retail_configuration_lab custom-edge
python -m retail_configuration_lab full-custom-counterfactual
python -m retail_configuration_lab economics
python -m retail_configuration_lab capstone
python -m retail_configuration_lab --help
```

The baseline command loads `data/baseline_case.json`, validates its evidence labels and values, and reconstructs the modeled economics using `Decimal` arithmetic. It deliberately reports unfavorable results, including negative first-year buyer surplus, without imposing a made-up benchmark.

## Chapter index

1. [Chapter 0 — The BUY / CONFIGURE Hypothesis](book/00-buy-configure-hypothesis.md) — establishes the synthetic baseline; status **UNTESTED**.
2. [Chapter 1 — Inventory What Already Exists](book/01-inventory-what-already-exists.md) — classifies the fictional ecosystem without validating the hypothesis.
3. [Chapter 2 — Define the Business Questions](book/02-define-the-business-questions.md) — defines actionable questions and diagnostic capability-coverage hypotheses.
4. [Chapter 3 — Standardize Retail Identity](book/03-standardize-retail-identity.md) — tests configured identity mappings against synthetic false and true exceptions.
5. [Chapter 4 — Configure Native Multi-Store Reporting](book/04-configure-native-multi-store-reporting.md) — measures which questions configured synthetic POS/inventory reports can answer.
6. [Chapter 5 — Configure E-Commerce and Store Reconciliation](book/05-configure-ecommerce-store-reconciliation.md) — tests a fictional supported connector against order, identity, cancellation, return, and inventory evidence.
7. [Chapter 6 — Purchasing and Inventory Configuration](book/06-purchasing-and-inventory-configuration.md) — tests configured supplier-item, PO, location, receipt, replenishment, and inventory-effect rules.
8. [Chapter 7 — Returns and Transfers](book/07-returns-and-transfers.md) — tests configured return linkage, location, reason, transfer status, quantity, and inventory-effect rules while preserving true exceptions.
9. [Chapter 8 — Automation Layer](book/08-automation-layer.md) — automates narrow deterministic handoffs and alerts while preserving exceptions for human judgment.
10. [Chapter 9 — BI / Reporting Configuration](book/09-bi-reporting-configuration.md) — configures RiverBI views over existing evidence and measures management-question coverage without repairing source exceptions.
11. [Chapter 10 — Process Change Experiment](book/10-process-change-experiment.md) — changes synthetic operating behavior and replays existing reconciliation logic without adding technology.
12. [Chapter 11 — What Still Hurts?](book/11-what-still-hurts.md) — reconciles the original burden and classifies the modeled operational, administrative, support, technical, and unknown residuals.
13. [Chapter 12 — Configuration Support Surface](book/12-configuration-support-surface.md) — inventories recurring administration and support, separates labor from fictional platform cash cost, and reconciles Chapter 11 without double counting.
14. [Chapter 13 — Add Store #7](book/13-add-store-7.md) — executes standardized growth and measures reused structure, new mappings, configuration, and capability growth.
15. [Chapter 14 — Acquired Store Stress Test](book/14-acquired-store-stress-test.md) — contrasts standardized growth with a fragmented synthetic acquisition and keeps standardization, configuration, migration, a narrow edge, and deferral open.
16. [Chapter 15 — Strong Native Suite Scenario](book/15-strong-native-suite-scenario.md) — tests whether broad fictional native coverage reduces the remaining custom need enough to justify configuration despite higher cash cost, migration, administration, and dependency.
17. [Chapter 16 — Weak Native Coverage Scenario](book/16-weak-native-coverage-scenario.md) — measures workaround sprawl, degraded question coverage, and bounded versus broad residuals when native semantics are weak.
18. [Chapter 17 — The Narrow Custom Edge](book/17-the-narrow-custom-edge.md) — tests one deterministic cross-channel exception rule against the best configured alternative while preserving authoritative systems and explicit scope refusal.
19. [Chapter 18 — Full Custom Counterfactual](book/18-full-custom-counterfactual.md) — models broad adapter, reconciliation, reliability, and support ownership against configuration plus the narrow edge.
20. [Chapter 19 — Economics After Configuration](book/19-economics-after-configuration.md) — compares transparent modeled buyer setup, ownership, residual burden, risk, payback, and three-year economics.
21. [Chapter 20 — Capstone: Configure, Extend, Build, or Walk Away?](book/20-capstone-configure-extend-build-or-walk-away.md) — synthesizes all gates, economics, ownership boundaries, and discovery requirements into the final verdict.

The Chapter 1 command loads and validates the structured inventory, reports unfiltered counts, and prints a capability matrix. Optional `--area` and `--status` filters narrow only the displayed matrix rows.

## Final result and study path

- **Original cookbook verdict:** BUY / CONFIGURE
- **Final lab verdict:** INVESTIGATE
- **Effect on original hypothesis:** WEAKENED

Chapter 19 splits the economic result: BUY / CONFIGURE leads first-year net benefit while FULL CUSTOM leads three-year net benefit, so economics are TOO CLOSE. Configuration achieves meaningful coverage with manageable support and strong standardized Store #7 reuse, but broad residuals, Store #8 fragmentation, and high native-platform dependence prevent a commitment before discovery.

```text
BUSINESS QUESTION → EXISTING CAPABILITY → STANDARDIZE → CONFIGURE
→ NATIVE INTEGRATE → AUTOMATE → REPORT → CHANGE PROCESS
→ MEASURE RESIDUAL → CUSTOM EDGE ONLY IF MATERIAL → COMPARE ECONOMICS
→ CONFIGURE / EXTEND / BUILD / STANDARDIZE / INVESTIGATE / WALK AWAY
```

### Custom-software boundary

No material custom ownership is currently authorized. If discovery validates the bounded Chapter 17 residual, custom may own only its deterministic exception rule, provenance, fail-closed transformation, and workflow output. It should not own POS, inventory, purchasing, returns, accounting, broad synchronization, or dashboards.

### Scaling and scenario lesson

Store #7 demonstrates strong reuse under standardized growth. Fragmented Store #8 demonstrates that acquisitions may require standardization or migration before integration. Strong native coverage makes configuration more plausible; weak native coverage creates workaround sprawl and broad gaps.

### Discovery checklist and remaining unknowns

Verify identifier standardization; authoritative systems; supported integrations; unanswered Chapter 2 questions; actual manual and support burden; growth/acquisition shape; platform fragmentation; bounded-gap materiality; accounting evidence; process causes; migration preference; real volumes, labor, licensing, API behavior, historical quality, and change-management cost. The executable structured checklist is `data/final_verdict.json`.

### Recommended study path

Read Chapters 0–2 for the hypothesis and evidence contracts; 3–10 for the intervention ladder; 11–12 for residual/support ownership; 13–16 for scaling and platform sensitivity; 17–19 for custom boundaries and economics; then run Chapter 20 for the decision.

The final conclusion is a synthetic lab result, not a sales promise. Run `python -m retail_configuration_lab capstone` for its evidence chain. Chapters 0–19 retain historical `UNTESTED` text where they describe the state at that point in the experiment.
