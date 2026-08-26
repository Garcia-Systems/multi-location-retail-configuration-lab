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
python -m retail_configuration_lab --help
```

The baseline command loads `data/baseline_case.json`, validates its evidence labels and values, and reconstructs the modeled economics using `Decimal` arithmetic. It deliberately reports unfavorable results, including negative first-year buyer surplus, without imposing a made-up benchmark.

## Chapter index

1. [Chapter 0 — The BUY / CONFIGURE Hypothesis](book/00-buy-configure-hypothesis.md) — establishes the synthetic baseline; status **UNTESTED**.

No later chapter is implemented yet. The roadmap is to test current capabilities, configuration, native integrations, automation, BI/reporting, and process change; measure residual burden; and consider a narrow custom edge only if the evidence justifies it. The next task is capability inventory—not integration code.

