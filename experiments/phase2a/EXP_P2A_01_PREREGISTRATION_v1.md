# Exp-P2A-01: Three-Factor STDP with Eligibility Traces Rescues Learning Under Metabolic Constraint

**Status:** PRE-REGISTERED (locked before execution)
**Date:** 2026-08-08
**Branch:** agi/sparse-event-driven-v1
**Version:** v1 (locked)
**Fills:** R3 (Buffering Rescue) slot in Paper_Draft_v3.md
**Implements:** D5 hardware prediction mechanism (CPU simulation)
**Related:** OPUS_STRATEGIC_ASSESSMENT_v1.md

---

## 1. Hypothesis

**H1 (Primary):** A three-factor STDP rule with eligibility traces (e-prop, Bellec et al. 2020),
combined with a decoupled plasticity power pool, will produce statistically significant
in-lifetime learning under the (cost, mortality) quadrant — where Phase 1 showed collapse
across five mechanism families.

**H0 (Null):** No arm exceeds the matched NOLEARN ablation by the pre-registered bar.

---

## 2. Substrate

- **Network:** Event-driven LIF (Lava 0.10, CPU simulation)
- **Architecture:** Source → Dense → LIF → Sink
- **Validated config:** weight=3, vth=20, connectivity=10%, dv=0.3, du=0.3
- **Sparsity:** 7.27% (biological range 1-10%) ✓
- **Amplification:** 1.47x ✓
- **Energy:** Rule 21, Loihi reference 23.6 pJ/spike (Davies et al. 2018)
- **Note:** CPU simulation for algorithm validation; D5 hardware prediction
  remains for silicon confirmation.

---

## 3. Task

**TF1 byte-stream remap** (same task family as Phase 1):
- Predict next byte to earn energy; death at zero reserves (absorbing state)
- 20,000-tick lifetimes
- Learnable to ~78-79% by error-driven readout (Phase 1 baseline)

---

## 4. Experimental Arms (3, pre-registered)

| Arm | Rule | Plasticity Pool | Expected |
|-----|------|-----------------|----------|
| **A1** | Three-factor STDP + eligibility traces (e-prop) | Decoupled (buffered) | LEARNS |
| **A2** | NOLEARN ablation (matched) | N/A | NULL (baseline) |
| **A3** | Old STDP3C (Phase 1 rule) | Coupled (survival budget) | NULL (control) |

**Key contrasts:**
- A1 vs A2: does learning happen at all?
- A1 vs A3: does the mechanism-matched fix beat the old rule?

---

## 5. Design

- **Seeds:** n = 24 per arm (Opus requirement for permutation test power)
- **Economy:** (cost=1, mortality=1) — the collapse quadrant from Phase 1
- **Buffering (A1 only):** Decoupled plasticity pool with fixed budget,
  separate from survival cash-flow (D5 mechanism)
- **Eligibility trace (A1 only):** per-synapse trace, decay τ_e
- **Neuromodulator (A1 only):** M(t) gated by plasticity pool availability

---

## 6. Metrics (pre-registered)

### Primary
- **Gate A delta:** mean accuracy(A1) − mean accuracy(A2), in percentage points
- **Bar:** ≥ +5.00 pp (matches Phase 1 Gate A)

### Secondary
- **Gate B:** A1 > matched ablation (A2), permutation test p < 0.05
- **Gate C:** effect size with 95% CI, per-seed reporting
- **ρ (error-space reduction):** corrected metric from Phase 1 Gate_A_Reconciliation_v1

### Energy
- Total energy per arm (Rule 21)
- Energy-per-percentage-point-gain

---

## 7. Five Pre-Registered Failure Mode Categories

If H1 is null, classify into exactly one:

| Code | Failure Mode | Diagnostic |
|------|--------------|------------|
| **F1** | Insufficient signal: eligibility traces too weak | Check trace magnitudes |
| **F2** | Credit assignment failure: neuromodulator mis-timed | Check M(t) vs reward correlation |
| **F3** | Energy starvation: plasticity pool depleted | Check pool drain rate |
| **F4** | Substrate ceiling: LIF dynamics cannot support task | Test A1 on free-energy quadrant |
| **F5** | Task mismatch: TF1 not learnable by this architecture | Test on known-learnable variant |

**Rule:** If null, run F1-F5 diagnostics BEFORE writing the null result paper.
No post-hoc variants beyond the 3 pre-registered arms.

---

## 8. Hard Stop Rules

- **Max 3 pre-registered variants** (A1, A2, A3)
- **Max 3 months** from execution start to written result
- **If null:** write the null result paper regardless (Rule 16)
- **No p-hacking:** all analyses specified here before execution

---

## 9. Decision Rules

| Outcome | Action |
|---------|--------|
| H1 confirmed (A1 ≥ A2 + 5pp, p<0.05) | Phase 2B (synaptic consolidation); validate D5 on hardware |
| H1 null, F1-F3 (fixable) | ONE pre-registered retry with documented fix |
| H1 null, F4-F5 (fundamental) | Write null result paper immediately |

---

## 10. Provenance Guard

Per Provenance_Trace_F1.md (fabrication incident audit):
- All random seeds logged with timestamp
- All results written to results/ immediately after each run
- No manual editing of result files
- Git commit after every batch of seeds

---

**LOCKED.** No changes after execution begins.
Amendments require a new version (v2) with dated changelog.