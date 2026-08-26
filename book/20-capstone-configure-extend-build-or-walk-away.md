# Chapter 20 — Capstone: Configure, Extend, Build, or Walk Away?

## 1. The hypothesis

The cookbook's **BUY / CONFIGURE** verdict was a MODELED ALTERNATIVE ASSUMPTION, not an observed result. The completed synthetic lab's verdict is **INVESTIGATE**; therefore the hypothesis is **WEAKENED**. This does not mean configuration failed. It means the evidence does not support committing to any single intervention before discovery.

Run the synthesis:

```bash
python -m retail_configuration_lab capstone
```

## 2–6. What the intervention ladder accomplished

Identity configuration removed synthetic false exceptions while retaining ambiguity and true disagreement. Native reports answered a meaningful subset of Chapter 2 questions; the native e-commerce connector reduced manual reconciliation; purchasing, receiving, returns, and transfers turned records into explicit outcomes. Automation removed deterministic handling but introduced failure and support paths. BI improved visibility without manufacturing missing source evidence. Process change eliminated process-caused exceptions, not technical gaps.

These are **OBSERVED LAB RESULTS** on synthetic fixtures. Dollar and labor effects remain **MODELED ASSUMPTIONS**.

## 7–8. What still hurt and what it costs to own

Chapter 11 retained broad operational, administration, support, and unknown burden. The valuable remaining problem is reliable cross-system exception evidence—especially cross-channel, inventory, transfer, return, and accounting evidence. Chapter 12 showed configuration support is manageable, not free: mappings, reports, automation failures, vendor/schema changes, and platform cash costs recur.

## 9–12. Scaling and platform shape

**STANDARDIZED GROWTH:** Store #7 reused most structure, required no new code path, and added bounded mapping/configuration and support work.

**FRAGMENTED ACQUISITION:** Store #8 had much lower reuse, ambiguous identities, another platform family, process gaps, and unknown cross-channel behavior. Standardize first and consider migration rather than making permanent integration the default.

The **STRONG NATIVE SUITE** makes configuration more plausible and custom less relevant. **WEAK NATIVE COVERAGE** creates workaround dependence and broad technical gaps. Thus native-coverage dependence is HIGH: the base conclusion is not portable without capability discovery.

## 13–15. Extend, build, and economics

Chapter 17 proved one narrow cross-channel rule technically useful and worthy of economic testing. It did not prove that edge is the best purchase. Chapter 18 showed full custom answers materially more modeled questions and lowers operational residual, but assumes broad adapter, runtime, reliability, and support ownership; it still cannot fabricate missing accounting evidence.

Chapter 19 is reused, not recomputed. **BUY / CONFIGURE leads first-year net benefit; FULL CUSTOM leads three-year net benefit.** No option is dominated, and the modeled sensitivities preserve the three-year leader. Because the time horizons disagree, Chapter 19 classifies economics as **ECONOMICS_TOO_CLOSE**. The strict economic evidence therefore does not justify silently selecting configuration, the edge, or full custom.

## 16. Final decision gates

| Gate | Result | Interpretation |
|---|---|---|
| Existing capability sufficiency | MODERATE | Meaningful, incomplete question coverage |
| Residual materiality | BROAD_MATERIAL | More remains than the single bounded edge |
| Support burden | MANAGEABLE | Benefit remains, with recurring ownership |
| Standardized scaling | STRONG_REUSE | Store #7 reused structure |
| Fragmentation sensitivity | HIGH | Store #8 materially degraded reuse |
| Native-coverage sensitivity | HIGH_DEPENDENCE | Strong and weak suites change the shape |
| Narrow custom value | JUSTIFIED | Technically useful for further economic test |
| Full custom value | MATERIAL_INCREMENT | More modeled value with broad ownership |
| Economics | TOO_CLOSE | First- and three-year leaders differ |

The rules are ordered and inspectable, not weighted. Robust configuration plus immaterial residual would yield BUY / CONFIGURE. A bounded justified edge plus config-edge economic leadership would yield NARROW CUSTOM EDGE. Here, broad residuals and split economic leadership yield **INVESTIGATE**.

## 17–18. Verdict and remaining material problem

**FINAL VERDICT: INVESTIGATE.** The original BUY / CONFIGURE hypothesis is **WEAKENED**.

The remaining valuable problem is not “replace retail systems.” It is producing reliable, sufficiently fresh, provenance-bearing cross-system exception evidence where source platforms and processes leave gaps. Discovery must determine whether that problem is broad, one bounded edge, or mostly standardization.

## 19. Custom-software boundary

### WHAT CUSTOM SOFTWARE SHOULD OWN

No material custom ownership is authorized under INVESTIGATE. If discovery validates the Chapter 17 residual, custom may own only one deterministic exception rule, its transformation/provenance, fail-closed behavior, and output into an existing workflow.

### WHAT CUSTOM SOFTWARE SHOULD NOT OWN

POS or inventory runtime, purchasing, returns, accounting, broad synchronization, source truth, or the dashboard platform. The ecosystem remains authoritative.

## Final architecture

```text
AUTHORITATIVE SYSTEMS
        ↓
IDENTITY GOVERNANCE
        ↓
NATIVE CONFIGURATION → NATIVE INTEGRATIONS
        ↓
AUTOMATION → BI / EXCEPTION VISIBILITY
        ↓
PROCESS OWNERSHIP
        ↓
[DISCOVERY-GATED NARROW CUSTOM EDGE]
        ↓
HUMAN JUDGMENT FOR TRUE EXCEPTIONS
```

## 20. Discovery requirements

Verify identifiers, authoritative systems, supported native integrations, unanswered Chapter 2 questions, actual manual/admin/support burden, standardized versus acquisition-driven growth, fragmentation, materiality of the bounded residual, accounting evidence access, process versus software causes, migration preference, real licensing, API limits, volumes, labor rates, historical quality, and change-management cost. The structured checklist is in `data/final_verdict.json`.

## 21–22. What the lab proved—and did not prove

It proved deterministic synthetic behavior and repository structure. It showed configuration, native integration, automation, BI, and process change can remove substantial routine work; standardization improves reuse; a narrow edge can add value; and full custom expands ownership. It did **not** validate a real vendor, customer, API, volume, price, support load, or ROI.

**TECHNICALLY POSSIBLE** is not **ECONOMICALLY JUSTIFIED**. **ECONOMICALLY ATTRACTIVE IN THE SYNTHETIC MODEL** is not **VALIDATED WITH A REAL CUSTOMER**.

Good solutions engineering is not maximizing engineering. It finds the smallest reliable intervention that captures enough value:

```text
BUSINESS QUESTION → EXISTING CAPABILITY → STANDARDIZE → CONFIGURE
→ NATIVE INTEGRATE → AUTOMATE → REPORT → CHANGE PROCESS
→ MEASURE RESIDUAL → CUSTOM EDGE ONLY IF MATERIAL → COMPARE ECONOMICS
→ CONFIGURE, EXTEND, BUILD, STANDARDIZE, INVESTIGATE, OR WALK AWAY
```
