# tests/clusy/qwen — Clusy AI Agent Work Products

This directory contains all experiments, analyses, patches, and notebooks
generated during the GENESIS hyper-critical AGI review session (2026-07-23).

## Structure

```
tests/clusy/qwen/
├── README.md                                 ← This file
├── review/
│   └── hyper_critical_review.ipynb           ← Full AGI architecture critique
├── exp30_ablation/
│   ├── run_ablation.py                       ← Driver: Arm A (STDP ON) + Arm B (OFF)
│   ├── plot_ablation.py                      ← A/B comparison plot
│   ├── run_arm_c.py                          ← Driver: Arm C (STDP_COSTONLY)
│   ├── plot_three_way.py                     ← A/B/C three-way comparison plot
│   ├── results/
│   │   ├── arm_A.json                        ← Raw per-tick metrics (STDP ON)
│   │   ├── arm_B.json                        ← Raw per-tick metrics (STDP OFF)
│   │   └── arm_C.json                        ← Raw per-tick metrics (COSTONLY)
│   └── figures/
│       ├── ablation_comparison.png           ← A vs B population + accuracy + energy
│       └── three_way_comparison.png          ← A vs B vs C steady-state summary
├── patches/
│   ├── homeostatic_stdp.py                   ← @njit Homeostatic STDP code
│   ├── cam.py                                ← @njit CAM read/write code
│   ├── numba_verification.py                 ← Numba compilation test (both upgrades)
│   ├── integration_spec.md                   ← Exact insertion points in engine files
│   └── apply_patches.py                      ← Automated patching script
├── curriculum/
│   └── hard_wm_design.md                     ← Hardened Working Memory curriculum design
└── notes/
    └── exp30_three_way_verdict.md            ← Final three-way verdict
```

## Key Findings

| Experiment | Result | Verdict |
|------------|--------|---------|
| Arm A: STDP ON | Pop=373, Acc=43.3% | Learning works but costly |
| Arm B: STDP OFF | Pop=600, Acc=2.9% | No learning, replicators thrive |
| Arm C: COSTONLY | Pop=600, **Acc=56.9%** | Frozen weights PREDICT BETTER |

**STDP is actively harmful.** Frozen weights (Arm C) predict 13.6pp better than
STDP-modified weights (Arm A). Maladaptive weight drift is the root cause.

## Fix Deployed

1. **Homeostatic STDP** (λ=0.01): `w += Δw_STDP − λ(w − w_DNA)`
2. **Compositional Memory (CAM)**: 8-slot per-organism key-value store

Both 100% Numba-safe. Already applied to `neuromorphic_engine.py` + `genesis_lab.py`.
