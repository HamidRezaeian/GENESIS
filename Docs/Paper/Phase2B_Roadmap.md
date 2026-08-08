# Phase 2B: Toward Biologically-Plausible Continual Learning

## Vision

Build a hierarchical, metabolically-constrained spiking neural network 
that can learn continuously under energy constraints — a necessary 
(though not sufficient) step toward biologically-plausible AGI.

## Motivation

Phase 2A established three key findings:
1. e-prop CAN learn temporal tasks (90.7% accuracy, v24)
2. e-prop is fragile to noise (null result, v25-v27)
3. e-prop tolerates metabolic constraints up to a phase transition (~75%)

Phase 2B addresses: **How do we extend these limits architecturally?**

## Research Questions

- RQ1: Can hierarchical processing extend the metabolic plateau?
- RQ2: Does working memory improve temporal credit assignment?
- RQ3: Can neuromodulatory gating solve the noise robustness problem?
- RQ4: What is the metabolic scaling law for biologically-plausible learning?

## Roadmap

### B1: Hierarchical SNN (Months 1-3)
**Goal:** Test if deeper architectures improve metabolic tolerance.

**Design:**
- 3-layer SNN: 10 input → 100 hidden → 50 hidden → 2 output
- Task: Temporal XOR (same as Phase 2A for comparison)
- Measure: Phase transition threshold vs. network depth

**Hypothesis:** Deeper networks have higher phase transition thresholds 
due to distributed representation.

**Deliverable:** Paper section + code + data

---

### B2: Working Memory Module (Months 4-6)
**Goal:** Test if persistent activity bridges temporal gaps.

**Design:**
- Add a "memory layer" with slow membrane time constants (τ = 200ms)
- Task: Delayed match-to-sample (longer delays than XOR)
- Measure: Accuracy vs. delay length

**Hypothesis:** Working memory enables learning across longer temporal 
gaps without eligibility trace decay.

**Deliverable:** Paper section + code + data

---

### B3: Neuromodulatory Gating (Months 7-9)
**Goal:** Test if surprise-based gating solves noise robustness.

**Design:**
- Implement acetylcholine (ACh) analog as novelty signal
- Gate eligibility updates: only "surprising" inputs create traces
- Task: Temporal XOR with 5% noise (failed in Phase 2A)
- Measure: Accuracy vs. noise level

**Hypothesis:** Neuromodulatory gating restores noise robustness by 
filtering expected (noisy) inputs.

**Deliverable:** Paper section + code + data

---

### B4: Metabolic Scaling Law (Months 10-11)
**Goal:** Derive energy-accuracy scaling relationship.

**Design:**
- Combine B1-B3 architectures
- Sweep network size: 50, 100, 500, 1000 neurons
- Measure: Energy per inference vs. accuracy
- Fit: Power law or exponential scaling

**Hypothesis:** Biologically-plausible learning follows a power law 
scaling similar to metabolic scaling in biological brains.

**Deliverable:** Full Phase 2B paper submission

---

## Success Criteria

Each phase produces:
1. A publishable finding (positive or negative)
2. A working building block (reusable code)
3. A pre-registered hypothesis (Rule 2 compliance)
4. Honest reporting of limitations (Rule 16 compliance)

## Connection to AGI

This roadmap does NOT claim to build AGI. It claims to build 
**necessary components** for biologically-plausible AGI:

- Hierarchical processing ✓ (B1)
- Working memory ✓ (B2)  
- Attention/gating ✓ (B3)
- Metabolic efficiency ✓ (B4)

Whether these components are sufficient for AGI remains an open question.
This project contributes measurement science, not AGI claims.

## Timeline Summary

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| B1 | 3 months | Hierarchical SNN paper |
| B2 | 3 months | Working memory paper |
| B3 | 3 months | Neuromodulation paper |
| B4 | 2 months | Scaling law + full paper |
| **Total** | **~11 months** | **Phase 2B paper** |

## Resources Required

- Compute: Local GPU (existing hardware sufficient for ≤1000 neurons)
- Time: ~10 hours/week for implementation and analysis
- Collaboration: Opus consultation for strategic decisions (established protocol)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| B1 shows no improvement | Medium | Low | Publish null result, pivot to B2 |
| B2 working memory unstable | Medium | Medium | Try alternative architectures (ALIF, LSNN) |
| B3 noise gating fails | Low | High | Fundamental limitation finding (publishable) |
| B4 scaling law unclear | Low | Medium | Report as open question |

## Approval

This roadmap is proposed for Phase 2B. Awaiting user confirmation to proceed.