# GENESIS Phase 2: Sparse Event-Driven AGI

**Branch:** agi/sparse-event-driven-v1
**Start date:** 2026-08-08
**Status:** Design phase — awaiting Opus consultation

---

## Vision Statement

Build a brain-inspired AGI substrate on home hardware by exploiting the
principles that make biological brains computationally powerful at ~20W:

1. **Sparse coding** — only 1-10% of units active at any moment
2. **Event-driven computation** — units compute only when they fire
3. **Local connectivity** — each unit connects to ~10⁴ neighbors, not all
4. **In-memory analog computation** — synapses compute where they store
5. **Metabolic accounting** — every operation costs energy; death is real

## Phase 1 Lessons Applied

From the ICBINB paper (`paper/icbinb-2026-v1`):
- Learning fails under (cost × mortality) interaction
- Cost alone doesn't suppress; mortality alone doesn't prevent
- Buffering (decoupled plasticity budget) is the mechanism-matched fix
- Loss-of-plasticity (Dohare 2024) is a separate phenomenon from economy-side suppression

Phase 2 architecture must:
- Maintain sparsity at inference AND learning time
- Buffer plasticity energy from survival energy
- Avoid loss-of-plasticity through architectural design (not just reinitialization)

## Hypothesis to Test

> "A sparse, event-driven, locally-connected substrate with metabolic
> buffering can achieve continual in-lifetime learning on home hardware
> (~10¹² FLOPS), closing the effective compute gap from 10⁶-10⁸× (dense)
> to 10²-10⁴×."

## Key Open Questions

1. What is the minimum network size for emergent cognition?
2. Which local learning rule is both biologically plausible and effective?
3. How to handle credit assignment without backprop?
4. What neuromodulatory signals are necessary?
5. How to prevent catastrophic forgetting in sparse architecture?

## Pending

- [ ] Opus strategic consultation
- [ ] Architecture selection
- [ ] First substrate prototype
- [ ] Benchmark definition