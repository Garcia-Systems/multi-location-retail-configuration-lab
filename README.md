# Multi-Location Retail Configuration Lab

> An executable solutions-engineering lab that tests whether configuration, native integrations, automation, BI, and process change can solve a multi-location retailer’s operational problems before custom software is justified.

This compact Python textbook tests a configuration-first method against a wholly synthetic opportunity. **James River Outfitters is fictional**, and every business detail, financial quantity, and alternative capability is a modeled assumption unless deterministic execution labels it otherwise. No real customer or commercial vendor is represented.

## Starting hypothesis

The earlier fictional cookbook verdict was **BUY / CONFIGURE**: it assumed that an existing alternative adequately met the need at materially lower cost or risk. The current lab status is **UNTESTED**.

> The original BUY / CONFIGURE verdict is an input hypothesis, not a conclusion of this executable lab.

The central question is: **Can configuration genuinely solve enough of the problem to deserve the BUY / CONFIGURE verdict?** If not, what economically meaningful residual remains?

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

The Chapter 1 command loads and validates the structured inventory, reports unfiltered counts, and prints a capability matrix. Optional `--area` and `--status` filters narrow only the displayed matrix rows.

## Study path

```text
BUY / CONFIGURE hypothesis
        ↓
Capability inventory
        ↓
Business questions
        ↓
Identity standardization
        ↓
Native multi-store reporting
        ↓
Native e-commerce/store reconciliation
        ↓
Purchasing and inventory configuration
        ↓
Measure routine reconciliation removed
        ↓
Next:
Returns and transfers
```

The current lab verdict remains **UNTESTED**. Chapter 6 observes synthetic purchasing-reconciliation results, but does not observe real retailer savings or prove that BUY / CONFIGURE works. Returns/transfers and later experiments are not implemented.
