# Exp 30 Three-Way Verdict: STDP Is Actively Harmful

## Final Numbers (steady-state, last 25% of 200k ticks)

| Metric | A: STDP ON | B: STDP OFF | C: COSTONLY | Delta (C − A) |
|--------|:----------:|:-----------:|:-----------:|:--------------:|
| Population | 373.2 | 600.0 | **599.6** | +226.4 (+60.7%) |
| Accuracy | 43.3% | 2.9% | **56.9%** | **+13.6 pp** |
| Energy/org | 13.2M | 14.9M | **5.6M** | −7.6M (−57.6%) |
| Extinctions | 0 | 0 | 0 | — |

## Diagnosis

```
H1 (energy overhead):     FALSIFIED ─── Arm C ≈ Arm B pop (+0.1%)
H2 (weight drift):        CONFIRMED ── Arm C > Arm A accuracy (+13.6 pp)
```

## Three Verdicts

| Question | Answer |
|----------|--------|
| Does STDP enable learning? | YES (43.3% > 2.9%) |
| Is STDP economically viable? | NO (373 < 600) |
| Is weight drift the problem? | YES (Arm C frozen beats Arm A learned) |
| Should we rip out STDP? | NO — fix it with homeostatic anchoring |

## The Fix

**Homeostatic STDP** — add a restoring force toward DNA-decoded birth weight:

```
w += Δw_STDP − λ(w − w_DNA)   (λ = 0.01)
```

This prevents runaway drift while preserving local adaptation.

**Compositional Memory (CAM)** — per-organism 8-slot non-leaky key-value store,
providing the substrate for working memory that the current leaky membrane cannot.
