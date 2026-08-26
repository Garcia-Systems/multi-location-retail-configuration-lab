# Chapter 10 — Process Change Experiment

Not every visible residual asks for software. Good software paired with a bad process can make the bad process **consistently visible**. A solutions engineer should therefore ask whether capability is absent, or whether behavior, governance, or ownership is inconsistent, before automating anything.

```text
EXCEPTION → ROOT CAUSE → CAPABILITY / PROCESS / GOVERNANCE / OWNERSHIP
          → CHANGE PROCESS WHERE APPROPRIATE → RE-RUN THE SAME SCENARIO
```

## Declarative rules, not another technology layer

Chapter 10 adds process rules and before/after fixtures—no workflow engine, integration, report, dataset, API, store, service, or automatic acknowledgement. The rules define the trigger, owner, required behavior, completion, and escalation. They are **MODELED ASSUMPTIONS**; their stored structure is **OBSERVED IMPLEMENTATION STRUCTURE**. The modeled POS reason field and other fictional existing capabilities remain **MODELED ALTERNATIVE ASSUMPTIONS**.

The intervention vocabulary—`CONFIGURATION`, `NATIVE_INTEGRATION`, `AUTOMATION`, `BI`, and `PROCESS_CHANGE`—makes process change a first-class solutions-engineering choice, not a fallback and not a weighted contest.

## Five operational experiments

1. **Inconsistent receiving.** When goods arrive, the receiving store verifies the PO, counts goods, posts the receipt, records discrepancies, and closes only when complete. A delayed/unlinked receipt is escalated at shift end. The same Chapter 6 reconciliation changes from missing to reconciled.
2. **Return-reason discipline.** A completed return is not operationally complete until it has an allowed reason. Chapter 7, rather than new enforcement software, classifies the same return again.
3. **Transfer closure ownership.** The sender owns accurate `SENT` evidence, the receiver owns physical verification and `RECEIVED` acknowledgement, and Central Inventory owns aged review. A human must verify arrival; acknowledgement is deliberately not automated.
4. **Mapping governance.** An Inventory Data Steward maintains the approved canonical artifact before activation where practical, reviews ambiguity, and rejects undocumented local aliases as truth. This is governance over Chapter 6's existing supplier-item mapping—not an MDM application.
5. **Purposeful spreadsheets.** Managers use the configured Chapter 9 briefing directly where it answers the question. A spreadsheet remains acceptable for a documented residual purpose. The experiment removes duplicate workflow, not tools by ideology, while leaving underlying report evidence unchanged.

Ownership and escalation matter because visibility without a resolver does not remove burden.

## Before and after, through existing logic

The experiment holds each underlying reference stable and changes synthetic operational behavior. Receiving is replayed through Chapter 6; return reason and transfer acknowledgement through Chapter 7; governed mapping through the existing purchasing identity resolution; and report evidence through Chapter 9. This avoids a separate fake outcome calculator.

The deterministic run observes five noncompliant events before and none after. Six operational exceptions become one: four process/ownership exceptions (including redundant assembly) and one data-governance exception are eliminated, while the accounting-evidence technical gap remains. Process-caused exceptions fall from four to zero (a 100% synthetic reduction). Manual steps fall from twelve to two (an 83.33% synthetic reduction). These ratios are **OBSERVED LAB RESULTS** only inside the fixtures and have no success threshold.

Potential delayed-receiving follow-up, reason correction, transfer closure, mapping cleanup, duplicate assembly, and unclear-ownership burden remains a **MODELED ASSUMPTION**. Applying a fixture ratio to real hours or dollars would be modeled extrapolation—not observed savings.

## What disappears—and what does not

```text
BAD PROCESS + GOOD SOFTWARE
        ↓
CONSISTENTLY VISIBLE BAD PROCESS

GOOD PROCESS + EXISTING SOFTWARE
        ↓
SOME "SOFTWARE PROBLEMS" DISAPPEAR

GOOD PROCESS + MISSING TECHNICAL CAPABILITY
        ↓
TECHNICAL GAP STILL EXISTS
```

Process change can eliminate avoidable bad records, delayed steps, duplicate work, and unclear ownership. It cannot create a missing platform capability, missing accounting evidence, or unsupported integration behavior. Accordingly, `FIN-01` remains only partially answered. `PUR-01`, `RET-02`, `TRN-01`, and `MGT-01` retain their evidence coverage; `INV-03` stays conservative. Fewer exceptions alone never makes a question answered.

Run the experiment:

```bash
python -m retail_configuration_lab process-change
```

> The lab observed that changing synthetic operational behavior eliminated some exceptions without adding software. It did not prove that real organizations would achieve the same compliance or labor reduction.

This proves only that process behavior can explain some synthetic residuals and creates clear before/after root-cause evidence for later analysis. It does not prove adoption, sustained compliance, real labor reduction, support economics, or that process fixes every gap. Accounting evidence remains unavailable, and the current lab verdict remains **UNTESTED**.

The next chapter may formally ask what still hurts. This chapter does not perform that residual classification.
