# Exp-P2A-01: Three-Factor STDP with Eligibility Traces (v2 — Amendment)

**Status:** AMENDED (v1 → v2)
**Date of amendment:** 2026-08-08
**Reason for amendment:** v1 task (binary next-bit prediction) was IID random
  (autocorrelation lag=1 = -0.022), making it unlearnable by ANY model.
  This was a design error, not a method failure.

**Change log (v1 → v2):**
- Section 3 (Task): Changed from "binary next-bit prediction" to "delayed copy"
- Section 5 (Design): Pattern length now explicitly k=5 ticks
- Section 6 (Metrics): Same bars (+5pp, p<0.05) applied to new task
- All other sections (arms, seeds, hard stops, failure modes): UNCHANGED

---

## 3. Task (AMENDED)

**Delayed copy (k=5 ticks):**
- Input: binary stream x[t]
- Target: y[t] = x[t-k] where k=5
- Rationale: directly tests eligibility trace survival over k ticks
- Learnability: structured signal with autocorrelation at lag=5
- Reference: standard e-prop sanity-check task (Bellec et al. 2020)

**Why this task:**
1. Isolates the credit-assignment mechanism (trace must survive k ticks)
2. Has known learnable signal (autocorr at lag k ≠ 0)
3. Simple enough that failure = implementation bug, not theory failure
4. Stepping stone to temporal XOR (Bellec 2020 benchmark) and TF1 remap

---

## 4. Experimental Arms (UNCHANGED)

| Arm | Rule | Plasticity Pool | Expected |
|-----|------|-----------------|----------|
| **A1** | Three-factor STDP + eligibility traces (e-prop) | Decoupled (buffered) | LEARNS |
| **A2** | NOLEARN ablation (matched) | N/A | NULL (baseline, ~50%) |
| **A3** | Old STDP3C (Phase 1 rule) | Coupled (survival budget) | NULL or WEAK |

---

## 6. Metrics (UNCHANGED bars)

### Primary
- **Gate A1 delta:** mean accuracy(A1) − mean accuracy(A2), in percentage points
- **Bar:** ≥ +5.00 pp

### Secondary
- **Gate B:** permutation test p < 0.05
- **Gate C:** effect size with 95% CI
- **Sanity check:** A2 must be at chance (~50%) on delayed copy task

### Baseline expectation
- Random prediction on delayed copy: 50% (binary task)
- A1 target: ≥ 55% (Gate A)
- A2 target: ~50% (sanity check — confirms task setup)

---

## 9. Decision Rules (updated for v2)

| Outcome | Action |
|---------|--------|
| A1 ≥ 55%, A2 ≈ 50%, p<0.05 | Phase 2B: temporal XOR benchmark |
| A1 ≈ A2 ≈ 50% | Debug e-prop implementation (F1-F3 diagnostics) |
| A1 > 50% but A1 ≈ A3 | Buffering doesn't help (D5 falsified on CPU) |
| A1 > 55% and A3 ≈ 50% | ✅ D5 prediction confirmed — proceed to hardware validation |

---

## Amendment justification

Per OPUS_STRATEGIC_ASSESSMENT_v1.md guidance:
> "If bitstream is random IID, accuracy=50% is the best possible answer
> from any model — not a sign of learning failure, but of irreducible entropy."

This amendment corrects a task design error, not a hypothesis change.
Hypothesis H1 remains unchanged; only the experimental task changed.

---

**v2 LOCKED.** Further amendments require v3 with dated changelog.