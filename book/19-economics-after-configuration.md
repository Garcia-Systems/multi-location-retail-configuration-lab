# Chapter 19 — Economics After Configuration

Sticker price is not an economic comparison. This chapter rejects **CUSTOM COSTS $62K / CONFIGURATION COSTS LESS / THEREFORE CONFIGURATION WINS**. Instead it asks what each option costs, what burden it leaves, what support it creates, and what risk it owns—then compares the whole economic system.

> **Every financial result in this chapter is modeled. The executable lab provides structure and sensitivity, not observed customer ROI.**

```text
OPTION
  ↓
SETUP + RECURRING CASH + ADMINISTRATION + SUPPORT
      + RESIDUAL BURDEN + RISK
  ↓
TOTAL ECONOMIC EFFECT

DO NOTHING vs BUY / CONFIGURE vs CONFIGURE + AUTOMATION
vs CONFIGURE + NARROW CUSTOM EDGE vs FULL CUSTOM
```

Run the deterministic comparison:

```bash
python -m retail_configuration_lab economics
```

## Buyer economics, not provider economics

The primary ledger contains what James River pays or bears: implementation, incremental subscription cash, internal administration and support, residual operations, and risk. Provider direct delivery cost, contribution, and delivery support are a different ledger. In particular, full custom's modeled $15,000 annual fee includes vendor runtime support; provider support labor is not charged to the buyer a second time.

## The explicit model

Setup cash and internal setup labor are one-time and remain visible. Annual recurring cash, administration, configuration support, custom-code support, residual operational burden, and a fixed annual risk allowance remain separate. The Chapter 12 support inventory replaces the Chapter 11 provisional administration estimate: it is reconciled into administration and support rather than added twice.

Annual gross burden reduction is original burden minus residual burden. Annual net benefit before setup subtracts incremental recurring cash, administration, support, and risk. First-year net benefit then subtracts setup. Recurring-year net benefit omits setup. Simple payback is setup divided by positive annual net benefit before setup; otherwise it is unavailable. Three-year net benefit is three undiscounted annual net benefits before setup minus setup. No discount rate, IRR, optimizer, or probability model is introduced.

The $51,513.80 original recoverable annual value is a commercial guardrail, not a synonym for gross burden reduction. Captured recoverable value is modeled separately by burden-category coverage. The CLI flags when annual net benefit exceeds that ceiling rather than silently treating every avoided burden dollar as commercially recoverable.

## Ownership, risk, and alternatives

DO NOTHING retains scaling exposure. BUY / CONFIGURE owns vendor dependency and configuration drift. Automation adds failure handling and configuration sprawl. The narrow edge adds bounded runtime ownership. Full custom adds broad adapter, runtime, and vendor-change ownership. These are modeled annual allowances with explicit rationales—not opaque risk scores, and no risk type is universally worst.

The configured buy scope includes identity, native reporting and integrations, purchasing, returns/transfers, process changes, and BI; it excludes Chapter 8 automation. Automation is added in the next path. The narrow edge builds on that configured/automated path without inheriting full-custom pricing. Full custom preserves the Chapter 0 $62,000 buyer price and $15,000 fee.

## Dominance, sensitivity, and break-even thinking

Economic dominance uses only setup, annual ownership cost, and residual burden: another option must be no worse on all three and strictly better on at least one. It does not smuggle qualitative judgments into a score. Separate rankings show first-year cost, first- and three-year net benefit, payback, residual burden, and ownership/support cost; different winners are legitimate.

Sensitivity cases independently test high configuration support, worse configured residual burden, lower narrow-edge value, and higher full-custom buyer support. They never mutate base assumptions. Break-even thinking can then ask how much extra support an option can absorb, what burden reduction an edge needs to repay setup, or what full-custom price would equal another option's three-year benefit. The cheapest platform can be expensive once labor and residual burden are included; likewise, the lowest residual burden is not automatically the best deal when setup and ownership are high.

## What remains

Chapter 19 produces a chapter-specific economic result, not the project verdict. Chapter 20 must synthesize capability and question coverage, identity/configuration, integrations, automation, BI, process change, residual burden, support, scaling, fragmentation, native-coverage scenarios, narrow custom, full custom, and these economics.

**Overall lab verdict: UNTESTED**
