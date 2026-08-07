# Re-Score Aggregate Summary — Corrected Gate A (Amendment v1)

**Protocol:** `SUBSTRATE_4_LEARNING_CURVE_v1`  
**Script:** `experiments/rescore_learning_curve_v1.py`  
**Git SHA at re-score:** `e4c4db77eaa2ffac7322375658283315bc287a98`  
**Status:** RE-ANALYSIS of existing artifacts under the pre-registered amendment `Docs/Architecture/SUBSTRATE_4_LEARNING_CURVE_v1.md`. Originals untouched (Rule 8); all outputs are NEW files. n=4 existing seeds per artifact — diagnostic only; confirmatory claims require fresh seeds 100–107 to n ≥ 8 (amendment D8).

Corrected Gate A screen (frozen): **T** = OLS slope of window accuracy, 95% CI > 0 (D3); **M** = error-space relative reduction ρ = (E0−E1)/E0 ≥ 0.25 with CI > 0 (D4; for the novel-switch artifact M uses ρ_B per D6); **B** = LEARN−NOLEARN paired late gap, 95% CI > 0 (D7). Decision table: amendment §4.

## 1. Decision table — one row per artifact (binding)

| Artifact | Task | Ticks | Δ (late−early), pp [95% CI] | Slope, pp/1k ticks [95% CI] | ρ (M stat) [95% CI] | Gate B gap, pp [95% CI] | T | M | B | F flags | Verdict | Confirmatory |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sub3_summary | static | 2000 | +2.118 [+0.024, +4.212] | +1.425 [-0.206, +3.056] | +0.119 [+0.011, +0.227] | +17.691 [+16.653, +18.729] | ✗ | ✗ | ✓ | F2F3 | **STATIC_ONLY_F3** | no |
| sub4_summary | static | 2000 | +3.455 [+0.213, +6.697] | +2.270 [+0.107, +4.432] | +0.202 [+0.050, +0.353] | +37.188 [+35.055, +39.320] | ✓ | ✗ | ✓ | — | **REAL_BUT_NEGLIGIBLE_F2** | no |
| sub4_20k_summary | static | 20000 | +3.698 [+3.039, +4.357] | +0.091 [+0.025, +0.156] | +0.268 [+0.234, +0.301] | +39.965 [+36.468, +43.462] | ✓ | ✓ | ✓ | — | **GATE_A_SCREEN_PASS_CORRECTED** | **YES — fresh seeds 100–107** |
| sub4_nonstationary_summary | nonstationary | 20000 | +3.125 [-0.033, +6.283] | +0.096 [-0.099, +0.290] | +0.095 [+0.000, +0.191] | +21.476 [+16.517, +26.434] | ✗ | ✗ | ✓ | F1F2F3 | **STATIC_ONLY_F3** | no |
| sub4_novel_summary | novel_switch | 20000 | +7.170 [+4.714, +9.627] | +0.366 [+0.247, +0.485] | +0.060 [-0.170, +0.290] | +25.729 [+23.199, +28.259] | ✓ | ✗ | ✓ | — | **REAL_BUT_NEGLIGIBLE_F2** | no |
| sub5_summary | static | 2000 | +0.156 [-1.146, +1.459] | +0.516 [-0.464, +1.496] | +0.020 [-0.135, +0.174] | +42.222 [+39.140, +45.304] | ✗ | ✗ | ✓ | F1F2F3 | **STATIC_ONLY_F3** | no |
| exp103_full | static | 20000 | +0.104 [-0.107, +0.315] | +0.005 [-0.004, +0.013] | +0.005 [-0.005, +0.014] | +10.351 [-2.150, +22.852] | ✗ | ✗ | ✗ | F1F2F4 | **NULL** | no |
| exp103b_full | static | 20000 | -0.243 [-1.636, +1.150] | +0.009 [-0.042, +0.061] | -0.012 [-0.077, +0.053] | +21.788 [+19.565, +24.012] | ✗ | ✗ | ✓ | F1F2F3 | **STATIC_ONLY_F3** | no |

Verdict legend (amendment §4): `GATE_A_SCREEN_PASS_CORRECTED` → substrate viability re-opened, confirmatory run required; `REAL_BUT_NEGLIGIBLE_F2` → rise real but ρ < 25%, Paper v2 conclusion stands; `STATIC_ONLY_F3` → in-lifetime-learning claim withdrawn for the artifact (Exp 103 pattern); `NULL` → remains Gate-A-negative; `INSTRUMENT_SUSPECT_F4` → Rule 20 audit before any claim.

## 2. D5 — within-phase re-learning (non-stationary artifact)

**sub4_nonstationary_summary** — post-switch phases only; delta_p = mean(last 2 windows of phase) - first window of phase; per-seed mean over phases:

| seed | LEARN re-learning Δ, pp | NOLEARN Δ, pp |
|---|---|---|
| 0 | +5.903 | +1.319 |
| 1 | +5.417 | -1.354 |
| 2 | +4.722 | +1.181 |
| 3 | +6.806 | +0.208 |

- LEARN across seeds: +5.712 [+4.319, +7.105] pp, t = 13.05, permutation p ≈ 0.1243 (MC)
- NOLEARN across seeds: +0.339 [-1.622, +2.299] pp
- Robustness (pre-registered): all-phases +4.850 [+4.357, +5.343] pp; last-window-only +5.972 [+4.607, +7.338] pp

## 3. D6 — novel-sequence transfer (A→B)

**sub4_novel_summary** — A_late = mean last 3 A-windows; B0 = first B window; B_late = mean last 3 B-windows; rho_B under the D4 bar:

| seed | A_late | B0 | B_late | retention, pp | ρ_B | gap_B, pp |
|---|---|---|---|---|---|---|
| 0 | 76.53 | 69.58 | 75.28 | -6.945 | 0.1872 | +24.028 |
| 1 | 74.86 | 77.29 | 74.44 | +2.431 | -0.1254 | +25.764 |
| 2 | 73.47 | 71.46 | 76.04 | -2.014 | 0.1606 | +27.847 |
| 3 | 73.54 | 72.71 | 73.19 | -0.833 | 0.0178 | +25.278 |

- retention: -1.840 [-8.026, +4.345] pp (≤ 0 expected; catastrophic-interference reference)
- ρ_B: +0.060 [-0.170, +0.290] (bar: ≥ 0.25)
- gap_B (paired, Gate B continuity): +25.729 [+23.199, +28.259] pp

## 4. Worked-example validation & aggregate cross-check

Amendment §3.3 worked example: sub4-20k ρ from published aggregates = 26.79% (E0 = 13.8021, E1 = 10.1042). Binding per-seed recomputation below; discrepancies are the expected Jensen gap between an aggregate-of-means and a mean-of-ratios and are documented, not smoothed over.

| Artifact | ρ from published aggregates | ρ per-seed mean (binding) | abs discrepancy |
|---|---|---|---|
| sub3_summary | 12.09% | 11.87% | 0.22pp |
| sub4_summary | 20.84% | 20.16% | 0.68pp |
| sub4_20k_summary | 26.79% | 26.78% | 0.02pp |
| sub4_nonstationary_summary | 9.64% | 9.55% | 0.09pp |
| sub5_summary | 1.89% | 1.96% | 0.06pp |
| exp103_full | 0.25% | 0.47% | 0.22pp |

## 5. Confirmatory-run requirements (amendment D8)

Artifacts passing the corrected Gate A screen: **sub4_20k_summary**.
Per D8, a confirmatory run is REQUIRED before any viability claim: fresh seeds 100–107 (as many as needed for n ≥ 8 total, minimum 4), original driver protocol IDs unchanged, NOLEARN arm re-run on the same fresh seeds for pairing, result-cache reuse disabled (Exp 96→97 anti-winner's-curse precedent).

## 6. What this re-scoring does NOT change

- Exp 99's SNN-on-RAM substrate falsification stands (independent, executed kill criterion).
- `Ascent.md` §2 / Rule 18 finish line unchanged; the staged pilot (`SUBSTRATE_4_STAGED_PILOT_v1`) remains the only instrument for the 5M question.
- All verdicts here are re-analysis of n=4 seeds — diagnostic, not confirmatory (Rule 3). Historical `gate_a_pass`/`verdict` fields in the source artifacts remain as recorded under the retired proxy.
