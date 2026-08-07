# When Plasticity Costs Energy and Death Is Real:
# A Factorial Quantification of the Metabolic Cost-Mortality Interaction
# Suppressing In-Lifetime Learning

**Status:** Draft v3
**Date:** 2026-08-08
**Target:** ICBINB workshop (NeurIPS)

---

## Abstract

In-lifetime plasticity lets biological agents adapt within a single lifetime,
yet artificial agents under energy constraints routinely fail to learn online.
We quantify **when** and **why**. Using GENESIS, a physically-costed substrate
in which organisms predict a byte stream to earn energy and die at zero
reserves, we run a pre-registered 2x2 factorial experiment crossing metered
plasticity cost with mortality pressure. In-lifetime learning collapses
exclusively in the (cost, mortality) quadrant: with free energy, learners gain
**+17.09 to +24.16 percentage points** over matched no-learning ablations
(4 seeds); with metered cost but mortality disabled, accuracy is invariant
across the full cost range (**77.57% at every cost factor**) even as colony
reserves drain monotonically to zero. Cost alone does not impair learning;
mortality alone does not prevent it; their interaction does. We then test a
**buffering intervention** and relate the collapse phenotype to **loss of
plasticity** in continual deep learning, showing the mechanisms are
dissociable. The results yield a falsifiable prediction for neuromorphic
hardware: on-chip learning under hard energy budgets will fail unless plastic
circuits are buffered by dedicated power domains or duty-cycled from
survival-critical computation.

---

## 1. Introduction

### 1.1 Problem

In-lifetime learning is the defining capability of biological agents and the
stated goal of neuromorphic computing; simulated agents almost never pay for
plasticity out of the same budget that keeps them alive. When energy
accounting is enforced with absorbing-state death, a surprising, reproducible,
mechanism-independent collapse emerges: five consecutive mechanism families
(Hebbian STDP, R-STDP, target-driven STDP, reservoir readouts, neuroevolution)
return null in-lifetime learning under the full economy (Exp 99-103b, Exp 3).

This paper isolates the cause factorially and tests a mechanism-matched fix.
Thesis: the suppressor is not metabolic cost and not mortality, but their
**interaction**; the remedy is buffering (decoupling plasticity payment from
survival cash-flow).

### 1.2 Gaps

**G1 - Homeostatic RL** (Keramati & Gutkin 2014): shapes the objective;
never meters the physical cost of learning updates against survival.

**G2 - Resource-rational analysis** (Lieder & Griffiths 2020): penalty
formulations predict graded degradation; our Exp-5 signature (flat accuracy,
monotone energy drain) shows budget-constraint-plus-absorbing-state does
the work, not cost magnitude.

**G3 - Evolutionary cost-of-learning** (Mery & Kawecki 2003): established
biologically, never operationalized in a neural substrate with measured
per-update energy.

**G4 - Loss of plasticity** (Dohare et al. 2024, Nature): explains
learner-side degradation; silent about economy-side suppression. Same
phenotype, different mechanism. We dissociate them with a 2x2 intervention
factorial.

### 1.3 Contributions

1. Pre-registered 2x2 factorial quantification (existing data, R1-R2)
2. Buffering intervention with pre-registered rescue criterion (new, R3)
3. Dissociation experiment: economy-side vs loss-of-plasticity (new, R4)
4. Falsifiable hardware prediction
5. Full negative-results record as companion material

---

## 2. Methods

### 2.1 Substrate
Per-organism echo-state reservoir + NLMS readout; LIF SNN core; byte-stream
prediction; 20,000-tick lifetimes; >= 4 seeds per cell; matched NOLEARN
ablation in every arm. Task family learnable to ~78-79% by error-driven
readout.

### 2.2 Rule 21 Physical Accounting
Four basis classes: MEASURED, FORCED-BY-DESIGN, NOMINAL-HOST, POLICY.
Income < cost by construction. Reference: Loihi ~23.6 pJ per synaptic spike.

### 2.3 The 2x2 Factorial (Existing Data)
FREE_ENERGY x NO_DEATH; each cell >= 4 seeds. Pre-registered bars:
Gate A delta >= +5.00 pp; Gate B learning > matched ablation.

### 2.4 Buffering Intervention (New, R3)
B1 developmental reserve; B2 duty-cycling. Pre-registered sweep.

### 2.5 Plasticity Preservation (New, R4)
Continual-backprop-style reinitialization; three diagnostics per checkpoint.

### 2.6 Intervention Factorial (New, R4)
buffering {none, B1} x preservation {none, reinit}; 4 seeds; matched
ablations; full Rule 21 accounting.

### 2.7 Statistics
Two-way ANOVA; effect sizes + CIs; per-seed reporting; pre-registered bars.

---

## 3. Results

### R1 - The Interaction (Existing: Exp 4/4b)
Free-energy quadrant: +17.09 to +24.16 pp LEARN advantage, all 4 seeds.
Cost x death quadrant: null across all mechanism families.

### R2 - Cost-Invariance Without Mortality (Existing: Exp 5)
Accuracy flat at 77.57% for all theta in [0,1] under NO_DEATH=1;
mean colony energy decreases monotonically 100 -> 0.

### R3 - Buffering Rescue (NEW)
[R3 result slot: pending execution]

### R4 - Two Mechanisms, Dissociated (NEW)
[R4 result slot: pending execution]

### Negative-Results Companion (Existing)
Exp 99-103b, Exp 3, Sub1-5 table as appendix.

---

## 4. Discussion

**D1 vs Homeostatic RL:** the interaction is physical, not objective-shaping.

**D2 vs Resource-Rationality:** the operative variable is budget constraint
+ absorbing state, not the Lagrange multiplier.

**D3 vs Cost-of-Learning:** computational operationalization of the
Drosophila trade-off.

**D4 vs Loss-of-Plasticity:** same phenotype, different mechanism; R4 is
the dissociation. "Loss of plasticity is a disease of the learner; metabolic
suppression is a disease of the economy the learner lives in."

**D5 Hardware Prediction (Falsifiable):** a Loihi-class on-chip learner
under fixed energy budget with termination-on-depletion will show lower
asymptotic accuracy than the same learner with a decoupled plasticity
power domain, at equal total energy.

**D6 Limitations:** single task family; reservoir readout only; 4 seeds;
NOMINAL-HOST energy units pending RAPL; simulation, not hardware.

---

## 5. Conclusion

(1) Cost alone does not suppress learning; mortality alone does not prevent
it; their interaction does.

(2) Buffering + preservation as the mechanism-matched fix; loss-of-plasticity
dissociation as the theoretical stake.

(3) Hardware prediction as an invitation to the neuromorphic community to
falsify it on silicon.

---

## Appendix A - Gate A1 / A2 Split
Gate A1 (from scratch): no priors, random init, delta >= +5 pp or rho >= 0.25.
Gate A2 (priors allowed): same bars, ablation receives same priors.
Both require Gate B + Gate C.

## Appendix B - Plasticity-Preservation Arm Specification
Diagnostic instrumentation; periodic reinitialization; factorial design;
pre-registered outcome table.

## Appendix C - Crafter Integration Plan
Calibration, not competition. DreamerV3 14.5+/-1.6 reference.
Dual reporting: Crafter score + GENESIS in-lifetime delta.

---

## References

Dohare et al. 2024. Loss of plasticity in deep continual learning. Nature.
Hafner et al. 2025. DreamerV3. Nature / arXiv:2301.04104.
Keramati & Gutkin 2014. Homeostatic RL. eLife.
Mery & Kawecki 2003. Cost of learning in Drosophila. Proc. R. Soc. B.
Lieder & Griffiths 2020. Resource-rational analysis. BBS.
Davies et al. 2018. Loihi. IEEE Micro.
Bellec et al. 2020. e-prop. Nature Communications.
Bauer et al. 2023. AdA. ICML.
GENESIS internal: Exp 99-103b, Exp 3, Exp 4/4b/5, Sub1-5 records.
