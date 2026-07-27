# tests/clusy/qwen — Clusy AI Agent Work Products

This directory contains all experiments, analyses, patches, and notebooks
generated during the GENESIS hyper-critical AGI review sessions
(2026-07-23 Exp 30 ablation; 2026-07-25 session 7 / Exp 87 metabolic-ceiling evolution).

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
├── exp87_metabolic_ceiling/
│   ├── run_evolution.py                      ← Driver: real survival/reproduction evolution, A/B STDP_TARGET
│   ├── plot_metabolic_ceiling.py             ← 4-panel metabolic-ceiling figure + PARAM-drift heatmap
│   ├── results/
│   │   ├── stdp_target_0.json                ← Per-tick metrics, STDP_TARGET=0 (3 seeds x 150 snapshots)
│   │   └── stdp_target_1.json                ← Per-tick metrics, STDP_TARGET=1 (3 seeds x 150 snapshots)
│   └── figures/
│       ├── metabolic_ceiling.png             ← idle cost vs income quantum, brain bloat, comprehension, refugium
│       └── param_drift.png                   ← PARAM-gene total-drift heatmap (mutational bias)
├── session9_lumpsum_reward/
│   ├── run_evolution.py                      ← Driver (Exp-87-based): lump-sum ceiling test, K sweep, frac_net_pos
│   ├── probe_lump.py                         ← Clean diagnostic: per-tick run-length distribution + lump payments
│   └── results/
│       ├── session9_sweep_summary.json       ← K∈{2,4,8} × DEPLETE{0,1} sweep summary
│       └── exp87_stdp_target_0.json          ← Per-condition metric series
├── patches/
│   ├── homeostatic_stdp.py                   ← @njit Homeostatic STDP code
│   ├── cam.py                                ← @njit CAM read/write code
│   ├── numba_verification.py                 ← Numba compilation test (both upgrades)
│   ├── integration_spec.md                   ← Exact insertion points in engine files
│   └── apply_patches.py                      ← Automated patching script
├── curriculum/
│   └── hard_wm_design.md                     ← Hardened Working Memory curriculum design
└── notes/
    ├── exp30_three_way_verdict.md            ← Final three-way verdict
    ├── exp87_metabolic_ceiling_verdict.md    ← Exp 87 verdict: the ceiling nullifies selection
    └── session9_lumpsum_reward_verdict.md    ← Session 9 verdict: lump-sum implemented, ceiling holds (honest null)
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


---

## Exp 87 — Metabolic-Ceiling Evolution (session 7, 2026-07-25)

**Question:** does letting STRUCTURE evolve under the existing grounded income pressure
produce Rule-7 emergent efficiency (brains shrinking toward the income budget), and do the
PARAM genes then drift adaptively? Driver `run_evolution.py` (NO kernel change, NO income/cost
scaling; real survival + real reproduction via the engine's `mutate_dna` on the FULL genome;
architecture-derived seed energy; contiguous 00_Graded scroll; A/B STDP_TARGET; 3 seeds x 30 000 ticks).

| Hypothesis | Verdict | Evidence |
|------------|---------|----------|
| H1: Rule-7 efficiency (idle cost falls toward 256) | **REJECTED** | idle cost ROSE: arm0 414→2387, arm1 385→1619; brains bloated (n_neurons 65→~183 / →~113) |
| H2: adaptive PARAM drift | **NEUTRAL** | per-seed SD ≈ 0 → mutational bias (refugium-dominated), not adaptive tuning |
| H3: STDP_TARGET raises comprehension | **NOT supported** | correct/tick peaked ~129 (founders) then collapsed to ~3 in BOTH arms |
| Rule-14 check | **VIOLATION** | refugium fired ~11% / ~10% of ticks (> 5% threshold): population on life support |

**Measured economics of the seeded ancestor (65 neurons / 93 synapses):** pure-idle cost
**436 cycles/tick** > income quantum **256 cycles/tick** (CELL_STATES = 2^8); fraction of
net-positive ticks = **0.000** in every condition (even 250/250 correct on pure-repeat content).

**Verdict:** the metabolic ceiling is DYNAMICAL — when idle cost exceeds the income quantum the
income gradient is flat at zero and **selection is nullified** (no organism earns positive net
income, so cheaper brains are not favoured; the refugium's mutational growth bias dominates).
Letting structure evolve is INSUFFICIENT while the ceiling binds. Next frontier (no rigged
mechanics): re-ground the INCOME side — income ∝ measured Shannon information gain (Free Energy
Principle), or re-derive the income quantum as a measured work quantity — subject to the Rule 21.4
tuning test. See `notes/exp87_metabolic_ceiling_verdict.md` and `Docs/Result.md` Experiment 87.
