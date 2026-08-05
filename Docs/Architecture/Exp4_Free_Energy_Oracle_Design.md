# Option 4 — Exp 4: Free-Energy Oracle Probe Design

**Status:** DESIGN — Awaiting Approval. Design-doc only. **NO implementation, NO experiment, NO PR, NO merge until explicitly approved.**  
**Date:** 2026-08-05  
**Branch:** `feature/exp4-free-energy-oracle`  
**Parent decision:** `Docs/Decision/Final_Pivot_Decision.md` (2026-08-05) — incorporating critical review feedback to isolate substrate capabilities from economy pressure prior to PATH A execution.  
**Predecessor results:** Exp 101 (R-STDP, NULL — self-silencing), Exp 102 (STDP_TARGET, NULL), Exp 103 (shared reservoir readout, STATIC ONLY: +10.35pp), Exp 103b (per-organism reservoir readout, NULL_OR_DEGRADED: +21.31pp), Exp 3 (neuroevolution, NULL — extinction cycles).  

---

## 0. Executive Summary & Critical Motivation

### The Prime Suspect: Substrate vs. Economy Confound

Across all five falsified experiments (101, 102, 103, 103b, 3), every tested mechanism evaluated neural learning rules inside the full GENESIS thermodynamic economy (Rule 21 metabolic costing, cycle-pool constraints, and death-at-zero energy depletion). 

However, **Exp 103 and Exp 103b demonstrated a massive +10.35pp to +21.31pp static representation advantage over NOLEARN controls**, establishing definitively that the SNN-on-RAM substrate **can represent and retain** task structures.

Critical review feedback identified that all five nulls confounded three distinct layers:
1. **Substrate physics** (spiking LIF neurons, RAM ring topology, pointer saccades).
2. **Learning rule** (local Hebbian STDP, R-STDP, reservoir LMS readouts).
3. **Economic pressure** (metabolic cycle depletion, starvation death at $E \le 0$, life-support refugium intervention).

The **economy is the prime suspect** suppressing in-run learning acquisition. Before committing 5–7 sessions to PATH A (PyTorch autograd backend migration), **Exp 4 isolates the substrate from the economy** by relaxing metabolic constraints and evaluating learning under an unconstrained Free-Energy Oracle.

---

## 1. Architecture & Integration Spec

### 1.1 Unchanged Substrate & Learning Rule
- **Substrate Physics**: Existing SNN-on-RAM kernel (`world_tick_numba` in `src/neuromorphic_engine.py` and `src/genesis_lab.py`). Spiking LIF dynamics, global heap allocation, pointer-based text patch walking, and CAM memory arrays remain **100% untouched**.
- **Learning Mechanism**: Uses the existing reservoir + online LMS readout architecture from Exp 103/103b. **Zero changes** to neural or synaptic update equations.

### 1.2 Modified Economy & Oracle Parameters
Three environment flags relax thermodynamic and economic constraints:

1. **`GENESIS_FREE_ENERGY=1`**:
   - Zero metabolic costs for synaptic updates and neuron evaluations (`CYCLES_PER_STDP_UPDATE = 0`, `CYCLES_PER_SYNAPSE_READ = 0`).
   - Organisms do not pay ATP burn for cognitive or plastic operations.
2. **`GENESIS_NO_DEATH=1`**:
   - Eliminates starvation death at $E \le 0$. Energy floor is clamped at zero ($E \ge 0$).
   - Organisms never die, preventing population collapse, extinction cycles, or refugium (Rule 14) life-support artifact interference.
3. **`GENESIS_SUPERVISED_TEACHER=1`**:
   - Provides a global directional error teacher directly to the readout layer on every prediction step.
   - Bypasses local baseline-dependent or zero-sum reward gates (eliminating the Exp 101 self-silencing failure mode).

### 1.3 Minimal Integration & Default-Path Hygiene
- All three parameters land as optional, explicit environment flags (`GENESIS_FREE_ENERGY`, `GENESIS_NO_DEATH`, `GENESIS_SUPERVISED_TEACHER`).
- **Byte-Identity Invariant**: When all three flags are `0` (default), the kernel execution path is 100% byte-identical to the certified baseline.
- `src/compile_fingerprint.py` registers the new flags in `ENV_NAME_MAP` so Numba JIT caches are correctly isolated without stale kernel collisions.

---

## 2. Task & Probe Specification

**Protocol:** `EXP4_FREE_ENERGY_ORACLE_v1` (to be pre-registered in `Docs/Exp4_Protocol.md` prior to probe execution).

| Parameter | Specification |
|---|---|
| **Task** | Next-byte prediction over contiguous Books text patch (500-byte patch, standard saccade-driven walking) |
| **Cohort** | Frozen cohort of **60 organisms** (no reproduction, no starvation death, energy clamped) |
| **Duration** | **1,000 world ticks** (fast feasibility probe only) |
| **Seeds** | **4 seeds (`0, 1, 2, 3`)**, pre-pinned before run execution |
| **Arms** | **LEARN** (`READOUT_LR > 0` under Free-Energy Oracle) vs. **NOLEARN** (`READOUT_LR = 0`, identical network & initial weights) |
| **Windows** | Early = ticks 1–250, Late = ticks 751–1000 |
| **Metric** | Cohort-mean 8-bit accuracy, in-run gain $\Delta(\text{LEARN}) = \text{late} - \text{early}$ |

---

## 3. Success Criteria (Binding)

Both criteria must be met across the 4-seed mean:

1. **In-Run Acquisition**: $\Delta(\text{LEARN}) = \text{late} - \text{early} > \mathbf{+5.0\text{ pp}}$.
2. **Learning Separability**: $\Delta(\text{LEARN}) > \Delta(\text{NOLEARN}) + \mathbf{3.0\text{ pp}}$ (separating learning from environmental drift).

**Interpretation**: If BOTH criteria pass, **the economy (metabolic costing and death dynamics) is confirmed as the killer of in-lifetime learning**. The substrate itself is proven capable of in-lifetime acquisition when unconstrained by energy depletion.

---

## 4. Failure Criteria & Ultimate Kill Clause

### 4.1 Probe Failure
If either success criterion fails (or if the run collapses/undetermined), the hypothesis that economy alone suppressed learning is **falsified**.

### 4.2 Universal Kill Clause (Binding)
If Exp 4 fails AND Path A (differentiable plasticity oracle) fails (or is bypassed):
- **PATH B3 executes immediately**: Archive the repository with an honest, fully auditable negative conclusion (`Docs/Decision/Substrate_Limits_Acceptance.md`).
- Downgrade Rule-18-A/B finish line, correct README/ARD claims, and cease all further substrate hopping.

---

## 5. Rationale & Scientific Value

1. **High Efficiency**: Exp 4 probe runs in ~hours vs. ~days required for full PyTorch backend autograd integration (Path A).
2. **Confound Isolation**: Cleanly decouples substrate physics from economic/thermodynamic constraints.
3. **Directly Tests Prime Suspect**: Tests the top hypothesis raised in critical review before major codebase refactoring.

---

## 6. Rule 21 & Cost Accounting Alignment

- **No Invented Cost Measurements**: Exp 4 uses the existing Rule 21 physical cost model infrastructure.
- Instead of adding new un-derived cost constants, Exp 4 simply relaxes metabolic constraints via explicit env flags (`FREE_ENERGY=1`).
- All cost tracking ledgers remain active in telemetry for auditability.

---

## 7. Timeline & Staged Execution Plan

Total duration: **3 sessions**.

| Stage | Task | Session | Output |
|---|---|---|---|
| **S1 (Current)** | Architecture & Design | Session 1 | `Docs/Architecture/Exp4_Free_Energy_Oracle_Design.md` (this doc) committed & pushed |
| **S2** | Implementation & Harness | Session 2 | Flag plumbing in `neuromorphic_engine.py` & `genesis_lab.py`, fingerprinting, parity regression test |
| **S3** | Probe Execution & Verdict | Session 3 | 1,000-tick probe (`experiments/exp4_free_energy_probe.py`), raw JSON artifacts, verdict in `Docs/Result.md` |

---

*Recorded 2026-08-05 on branch `feature/exp4-free-energy-oracle`. Design doc only. Awaiting explicit approval to proceed.*
