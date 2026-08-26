# Chapter 0 — The BUY / CONFIGURE Hypothesis

James River Outfitters is a synthetic, centrally owned regional retailer: six physical stores, one e-commerce channel, a mostly shared merchandise catalog with local assortment variation, and central operations, purchasing, inventory, finance, and e-commerce responsibilities. It is not a real customer, and this chapter makes no claims about real software vendors.

## The fictional opportunity

Operational fragmentation here means that work crosses store POS, inventory, purchasing, transfers, e-commerce, returns, scheduling, accounting, spreadsheets and exports, reconciliation, and central management reporting. The modeled workflow follows goods and information from supplier and purchase order through receiving, inventory, sale, return or transfer or adjustment, reconciliation, and management reporting. Chapter 0 describes that boundary; it does not fix it.

The original fictional analysis assigned a **$111,020.00 annual current-state burden** and **$51,513.80 recoverable annual value**. Its custom-software hypothesis assigned a $62,000.00 implementation price, $15,000.00 annual fee, 378 engineering hours, and $32,440.00 direct delivery cost. These numbers reconstruct an alternative, not a quote, measurement, or forecast.

## Two competing hypotheses

One hypothesis is that custom software can recover the modeled value by joining fragmented operations. The competing buy/configure hypothesis says a fictional existing alternative adequately meets the need at materially lower cost or risk. That sentence led the earlier cookbook to the verdict **BUY / CONFIGURE**.

It is also a **MODELED ALTERNATIVE ASSUMPTION**. Repeating it cannot make it evidence. In particular, lower modeled cost does not demonstrate configuration coverage, operational adoption, data quality, or a reduction in residual burden.

The lab therefore attempts to falsify rather than protect the verdict. It asks:

1. Can configuration genuinely solve enough of the problem to deserve the BUY / CONFIGURE verdict?
2. If configuration does not solve everything, what economically meaningful residual problem remains?

Until later executable work answers those questions, the distinction is mandatory:

```text
ORIGINAL MODELED VERDICT
BUY / CONFIGURE

CURRENT LAB VERDICT
UNTESTED
```

## Reconstruct the baseline

From the repository root, run:

```bash
python -m retail_configuration_lab baseline
```

The program loads the structured synthetic case and calculates recoverable-value ratio, first-year cash cost and buyer surplus, recurring-year buyer surplus, simple first-year coverage, and direct delivery contribution before recurring support. The last figure is **not a complete accounting profit calculation**, and the coverage ratio has no invented “good” threshold.

### MODELED ASSUMPTIONS

The case's burden, recoverable value, prices, fee, engineering effort, delivery cost, business workflow, and fictional alternative reasoning are inputs. The custom first-year buyer surplus is negative under those inputs; the lab exposes rather than hides that outcome. A calculation from assumptions remains conditional on them.

### OBSERVED LAB RESULTS

At this stage execution demonstrates only that:

- the synthetic case loads and passes explicit structural validation;
- decimal calculations are deterministic;
- the original modeled economics can be reconstructed; and
- the laboratory begins with an **UNTESTED** verdict.

It does **not** demonstrate that configuration is effective, that a fictional product has any particular capability, that staff will adopt a process, or that BUY / CONFIGURE is preferable. Those claims need evidence from later experiments. Chapter 0 establishes the experiment and nothing more.

The next move is not to build an integration:

> Before changing or building anything, inventory what the existing systems are already capable of doing.
