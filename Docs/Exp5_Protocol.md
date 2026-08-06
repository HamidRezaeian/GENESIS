# Experiment 5 Protocol: Metabolic Cost Threshold Scan

**Protocol ID:** `EXP5_COST_THRESHOLD_SCAN_v1`  
**Pre-registration Date:** 2026-08-06  
**Status:** Pre-registered (Committed prior to implementation/execution)  

---

## 1. Objective & Hypothesis

Following Exp 4b's finding that the Reservoir + NLMS substrate achieves **+21.04 pp** accuracy when metabolic costs are zeroed (`FREE_ENERGY=1`), Exp 5 maps the precise metabolic cost threshold $\theta^* \in [0, 1]$ where in-lifetime learning transitions from net-affordable to metabolically suppressed.

---

## 2. Experimental Architecture & Flag Specification

- **Substrate & Readout:** `GENESIS_RESERVOIR_PER_ORG=1` (per-organism echo-state reservoir + linear LMS readout, identical to Exp 103b/4b).
- **New Engine Flag:** `GENESIS_COST_FACTOR=\theta` (float in `[0.0, 1.0]`, default `1.0`).
  - Scales ONLY the plasticity metabolic ATP charge operations (`CYCLES_PER_STDP_UPDATE` etc.) by factor $\theta$.
  - $\theta = 0.0$: Equivalent to `FREE_ENERGY=1` (zero metabolic cost for plasticity updates).
  - $\theta = 1.0$: Full Rule 21 physical cost model.
  - Default value `1.0` guarantees byte-identical regression safety when unset.
- **Death Floor:** `GENESIS_NO_DEATH=1` fixed across ALL arms. This isolates the learning suppression caused by metabolic expenditure from population-collapse artifacts.

---

## 3. Provenance Table (Rule 16 / Rule 17 Compliance)

| Parameter / Flag | Value | Source / Rationale |
|---|---|---|
| `GENESIS_RESERVOIR_PER_ORG` | `1` | Pre-registered Exp 103b / 4b architecture |
| `GENESIS_COST_FACTOR` | `\theta \in \{0.0, 0.1, 0.25, 0.5, 0.75, 1.0\}` | Linear-scaled metabolic multiplier |
| `GENESIS_NO_DEATH` | `1` | Isolates learning capability from death-at-zero |
| `RESERVOIR_SIZE` | `256` | Pre-registered Exp 103 standard |
| `RESERVOIR_SPARSITY` | `0.1` | Pre-registered Exp 103 standard |
| `RESERVOIR_TAU` | `20.0` | Pre-registered Exp 103 standard |
| `READOUT_LR` | `0.01` (LEARN) / `0.0` (NOLEARN) | Pre-registered Exp 103b standard |

---

## 4. Full Run Protocol

- **Cohort Size:** 60 organisms (frozen population, no births/deaths).
- **Duration:** 2000 ticks per seed.
- **Reporting Period:** Every 200 ticks.
- **Seeds:** `[0, 1, 2, 3]` (4 seeds).
- **Arm Matrix:**
  - **LEARN Arm (`READOUT_LR=0.01`):** Tested across all 6 scan points $\theta \in \{0.0, 0.1, 0.25, 0.5, 0.75, 1.0\}$.
  - **NOLEARN Control (`READOUT_LR=0.0`):** Tested at $\theta \in \{0.0, 0.5, 1.0\}$.

---

## 5. Binding Evaluation Criteria & Metrics

1. **In-Lifetime Learning Delta ($\Delta(\theta)$):**
   $$\Delta(\theta) = \text{Late Acc}(\theta) - \text{Early Acc}(\theta)$$
   where Early Acc is mean accuracy over ticks 1-600 and Late Acc is mean accuracy over ticks 1400-2000.
2. **Critical Threshold Estimate ($\theta^*$):**
   $$\theta^* = \max \{\theta \in \text{Scan Points} \mid \Delta(\theta) > +5.0\text{ pp}\}$$
3. **Monotonicity Check:** $\Delta(\theta)$ must be non-increasing with respect to $\theta$ (allowing $\pm 2.0\text{ pp}$ noise).
4. **Energy Sanity Check:** Mean colony energy must monotonically decrease as $\theta$ increases (verifying real physical cost impact).

---

## 6. Pre-registered Failure Modes

- **Flat Failure (No Transition):** $\Delta(\theta)$ remains flat across all $\theta \in [0.0, 1.0]$. Indicates cost effect is all-or-nothing binary or unwired.
- **Contradiction Failure:** $\Delta(1.0) > +5.0\text{ pp}$ under full cost. Contradicts Exp 103b live results; requires immediate audit.
