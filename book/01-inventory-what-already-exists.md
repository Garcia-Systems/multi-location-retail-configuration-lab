# Chapter 1 — Inventory What Already Exists

> Before proposing software, understand what the customer already owns.

Configuration-first discovery begins with inventory, not architecture. A missing answer may reflect an undiscovered feature, an unconfigured identifier, or unavailable evidence—not missing software. Conversely, a feature advertised in our fictional model may be incorrectly configured or irrelevant to management's question. This chapter therefore records uncertainty without designing a solution.

## The fictional landscape

James River Outfitters is a wholly fictional retailer with six stores, one e-commerce channel, a mostly common catalog with local assortment variation, and centralized purchasing, inventory, and finance. Store management and e-commerce operations participate in the same operating model. Every `River*` name below is invented and vendor-neutral; no entry is a claim about a real product.

| Fictional system | Category | Authoritative responsibility |
|---|---|---|
| RiverPOS | Store POS / returns | Store sales transactions and in-store returns |
| RiverStock | Inventory | SKU records, location stock, and adjustments |
| RiverBuy | Purchasing | Suppliers, purchase orders, and receiving |
| RiverCommerce | E-commerce | Online orders, cancellations, and fulfillment routing |
| RiverReturns | Returns | Cross-channel return intake and disposition |
| RiverTransfer | Store transfers | Transfer shipment and receipt workflow |
| RiverBooks | Accounting | General-ledger posting and accounting dimensions |
| RiverSchedule | Scheduling | Store labor schedules and staffing assignments |
| RiverBI | BI / reporting | Configured management reports and delivery |
| RiverFlow | Automation / workflow | Bounded notifications and file movement |
| RiverSheets | Spreadsheets / exports | Analyst-managed structured extracts and mappings |

`data/capability_inventory.json` is the authoritative structured inventory. It also records each system's major modeled capabilities and known limitations. Authority is deliberately divided: being the transaction authority does not make a system the authority for a cross-system business interpretation.

## Seven statuses, not a score

The matrix uses exactly seven classifications. They are categories—not maturity levels—and must not be collapsed into a numeric score.

- **SUPPORTED** — the fictional system provides the capability in the modeled current state, without a capability configuration change.
- **SUPPORTED WITH CONFIGURATION** — the feature exists, but settings, mappings, roles, identifiers, report definitions, or workflow rules must change.
- **SUPPORTED WITH NATIVE INTEGRATION** — a supported built-in connection between fictional systems must be enabled and configured; this is not custom code.
- **EXPORT ONLY** — structured information can be emitted, but the source does not directly satisfy the cross-system need. An export can still be valuable evidence or input to an existing analyst process.
- **AUTOMATION POSSIBLE** — a bounded deterministic workflow appears plausible without a general-purpose custom application. It is an inventory observation, **not implemented or tested automation**.
- **GAP** — no plausible native, configuration, export, or bounded-automation route is exposed by the modeled ecosystem. This strong conclusion is used carefully.
- **UNKNOWN** — available information cannot support classification. It demands a discovery note and remains visible.

`UNKNOWN` is not a softer spelling of `GAP`. A gap is a modeled conclusion about the available routes; an unknown is a limit on present knowledge. Converting the latter to the former would turn missing evidence into a product conclusion.

## Capability matrix

The structured matrix covers sales, inventory, purchasing, e-commerce, transfers, returns, accounting, reporting, and automation. Representative ambiguity includes:

| Area | Capability | Primary system | Status |
|---|---|---|---|
| Sales | Sales by store | RiverPOS | SUPPORTED |
| Sales | Category-level reporting | RiverPOS | SUPPORTED WITH CONFIGURATION |
| Inventory | Available-to-sell quantity | RiverStock | SUPPORTED WITH NATIVE INTEGRATION |
| Purchasing | Purchasing exceptions | RiverBuy | EXPORT ONLY |
| Transfers | Unresolved transfer visibility | RiverFlow | AUTOMATION POSSIBLE |
| Reporting | Cross-system reporting | RiverBI | GAP |
| Returns | Reason code | RiverReturns | UNKNOWN |

Dependencies make configuration and native-connector claims testable later. Unknown rows name the discovery work required. The complete deterministic matrix, including rationale and dependency detail, is printed with:

```bash
python -m retail_configuration_lab capabilities
```

It can be inspected without changing the analysis totals:

```bash
python -m retail_configuration_lab capabilities --area inventory
python -m retail_configuration_lab capabilities --status GAP
```

The raw count called **Potential non-custom paths worth testing** includes `SUPPORTED`, configuration, native integration, export, and automation classifications. It excludes `GAP` and `UNKNOWN`. It is not a score, threshold, or verdict; it answers only how many modeled needs have a plausible non-custom path worth testing if custom development were prohibited today.

## Evidence discipline

The fictional product claims in the matrix are **MODELED ALTERNATIVE ASSUMPTIONS**. Writing a claim into JSON does not make it observed. The JSON file and Python models are **OBSERVED IMPLEMENTATION STRUCTURE**. Successful deterministic loading, validation, classification, filtering, and reporting are **OBSERVED LAB RESULTS**—observations about this lab, not evidence that a fictional product works in production.

The executable inventory rejects duplicate identifiers, missing systems, invalid statuses, empty rationales or evidence, missing configuration or connector dependencies, and unknowns without discovery notes. It demonstrates that the repository can consistently inventory the claims and count their classifications. It does **not** demonstrate correct configuration, connector behavior, useful reports, data quality, workflow adoption, implementation success, or business value.

> The existence of a feature is not the same as solving a business question.

Chapter 1 establishes only **CAPABILITY EXISTS** as a modeled claim. It does not establish **CAPABILITY SOLVES BUSINESS QUESTION**. The original `BUY / CONFIGURE` verdict therefore remains an input hypothesis and the current lab verdict remains `UNTESTED`.

> Now that we know what the fictional ecosystem might be capable of doing, the next task is to define exactly what management needs to know before configuring anything.
