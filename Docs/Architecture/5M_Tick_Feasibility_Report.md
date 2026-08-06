# GENESIS — 5M-Tick Experiment Feasibility Consultation

**Date:** 2026-08-06 · **Repo:** `HamidRezaeian/GENESIS` @ `feature/substrate-pivot`, commit `9dd5837`
**Scope:** Consultation only — no code changes were made.
**Evidence basis:** (M) = measured on 8-core Xeon 2.6 GHz / 8 GB sandbox (home-hardware class), (O) = observed in repo files/results, (A) = arithmetic on measured/observed numbers.

---

## 1. Verdict

| Question | Answer |
|---|---|
| **Is 5M ticks computationally feasible on a home computer?** | **YES — comfortably.** ~18 h wall-clock for the full 4-seed × 2-arm protocol on 8 cores (~5.2 days serial on 1 core). RAM < 2 GB, storage < 3 GB. (M/A) |
| **Is it worth doing?** | **NO.** The learning curve saturates by ~4k ticks; the 2k→20k data already proves deep time adds nothing. 5M ticks would cost ~18 h to re-measure a plateau you have already measured. (O) |
| **Can it satisfy Rule 18 Gate A?** | **NO — mathematically impossible on this metric**, independent of compute. (O/A, §4) |
| **Recommendation** | Do **not** run Substrate 4 to 5M ticks. Treat saturation as a falsification result, run a ≤6 h staged pilot only if confirmation is required, and redirect the compute to substrate iteration. (§6) |

---

## 2. Computational cost (measured, not estimated)

Benchmarked the **actual repo code** (`experiments/sub4_small_transformer.py::run_arm`, unmodified, 60 organisms/tick) on the 8-core sandbox:

| Arm | Ticks/s | ms/tick | Per 5M ticks (A) |
|---|---|---|---|
| LEARN | 77.5 | 12.90 | **17.9 h** per seed |
| NOLEARN | 102.6 | 9.75 | **13.5 h** per seed |

Per-tick cost is O(1) — fixed 16-byte context buffer, fixed 500-byte patch, no state growth (O, code read). A 200-tick measurement therefore extrapolates linearly.

### Wall-clock for the full protocol (4 seeds × LEARN/NOLEARN = 8 runs)

| Horizon | Per LEARN run | Serial (1 core, 8 runs) | Parallel (8 cores, 8 runs) |
|---|---|---|---|
| 20k (current) | 4.3 min | ~30 min | ~4.3 min |
| 100k | 21.5 min | ~2.5 h | ~22 min |
| 500k | 1.8 h | ~12.6 h | ~1.8 h |
| 1M | 3.6 h | ~25.2 h | ~3.6 h |
| 2M | 7.2 h | ~50.4 h | ~7.2 h |
| **5M** | **17.9 h** | **~5.2 days** | **~18 h** |

(A from M rates. A modern i7/Ryzen 7 has ~1.5–2× the per-core speed of this 2.6 GHz Xeon → parallel wall-clock closer to **9–12 h**.)

### Memory / storage / energy

- **Model state:** 25,088 params/agent (O, hand-counted from code: 8192 tok_embed + 512 pos_embed + 4096 attn + 4096 FFN + 8192 head) ≈ 98 KiB fp32 → 60 agents ≈ **5.7 MiB**. Whole run < 0.2 GB RSS; 8 parallel runs < 2 GB. A 16–32 GB home machine is vastly oversized. (A/O)
- **Storage:** window logs every 1,000 ticks → 5,000 records ≈ 0.5 MB/run at 5M. Full-cohort weight snapshots every 100k ticks → 50 × 5.7 MiB ≈ **285 MiB/run**, ~2.3 GB for all 8 runs. Trivial. (A)
- **Energy:** ~18 h × ~90 W ≈ **1.6 kWh** — negligible. (A)

**Note for bookkeeping (O):** the code implements **one** attention block + one FFN (~25k params), while the docstring claims "2 Transformer Blocks … ~10,000 trainable weights". Both statements in the docstring are inaccurate relative to the code.

---

## 3. Scaling behavior: already saturated (observed, not extrapolated)

From the repo's own result files (4 seeds each):

| Run | Ticks | In-lifetime Δ (Gate A needs ≥ +5pp) | Late acc | Gap vs NOLEARN (Gate B needs > 3pp) |
|---|---|---|---|---|
| `sub4_summary.json` | 2k | +3.45pp ❌ | 86.88% | +37.19pp ✅ |
| `sub4_20k_summary.json` | 20k | +3.70pp ❌ | 89.90% | +39.97pp ✅ |
| `sub4_nonstationary_summary.json` | 20k | +3.13pp ❌ | 70.69% | +21.48pp ✅ |
| `sub4_novel_summary.json` | 20k | +2.31pp ❌ | 74.74% | +25.73pp ✅ |

**A 10× increase in ticks (2k→20k) bought +0.24pp of in-lifetime delta and +3.02pp of late accuracy.** The 20k learning curves show why (O): accuracy rises fast to a peak of ~93–95% by **tick ~4,000**, then oscillates around ~90% with ±3pp window-to-window noise through tick 20,000 (e.g. seed 0: 93.75% @4k → 89.58% @20k; the rise is entirely front-loaded).

Projection 20k → 5M (250×): even an aggressive log-linear reading of the endpoint means (+3pp per decade) caps out near the bit-accuracy ceiling and leaves the in-lifetime delta at ~3.7pp. The realistic projection is **no change**: the 4k→20k interior is flat within noise, so ticks 20k→5M sample the same stationary distribution. Expected outcome of a 5M run: late acc ~90–92%, **delta ~3.7pp — Gate A still FAIL**.

## 4. Why 5M ticks can never pass Gate A on this metric (arithmetic, not opinion)

Rule 18 / `Docs/Architecture/Ascent.md` requires capability `C(t)` to rise **≥ 25% in monotone trend over ≥ 5M ticks from its post-bootstrap baseline**:

- From the current late baseline (~89.9%): +25% relative requires **112.4%** bit accuracy — impossible, the metric is bounded at 100%. (A)
- From the early baseline (~83–86%): +25% relative requires **104–108%** — also impossible. (A)
- From the NOLEARN floor (~49.9%): +25% relative = 62.4% — **already exceeded at tick 200 of the 2k run**. (O)

So under every reading of "baseline", the diagnostic's bit-accuracy metric either already satisfies the 25% rise in its first few hundred ticks, or can never express it. **The capability rise this substrate can produce is ~+8% relative, delivered by tick ~4k. No duration of run changes that.**

Two further binding-definition gaps (O, `Ascent.md` §2): Rule 18's finish line is defined on **a single live `sim_loop` run** with `C(t)` = the **prediction-depth income fraction**, plus Gate B (learning-ablation control) and Gate C (`C/footprint` non-decreasing). The sub4 standalone numpy diagnostic is a substrate *screen*, not the finish-line instrument — a 5M-tick sub4 run would not count toward Rule 18 even if its curve rose. (Context: `Ascent.md` records the kill criterion for the SNN-on-RAM substrate as **triggered 2026-08-01** — this branch is the substrate pivot.)

---

## 5. Practical constraints & opportunity cost

- **Realistic for home hardware?** Yes — 18 h unattended on 8 cores, <2 GB RAM, <3 GB disk, ~1.6 kWh. Operationally boring. (M/A)
- **Opportunity cost:** a full 20k protocol (8 runs) costs ~30 min serial. The ~18 h a 5M run takes ≈ **36 full 20k substrate-variant protocols** — e.g. depth/width, patch diversity, LR, or nonstationarity sweeps. The expected information gain from the 5M run is ≈ 0 (saturation already demonstrated); the expected gain from variant sweeps is not. (A/O)
- **Risk:** pure wall-clock risk only (power cut / reboot). The code has no checkpoint/resume — a 5M run restarted at tick 4.9M loses everything. Any long run must add periodic state snapshots. (O)

## 6. Recommendation

1. **Do not run sub4 to 5M ticks as-is.** Record the 2k/20k/5M-infeasible-by-saturation analysis as the falsification artifact for this substrate variant — per Rule 18's own guidance ("change the substrate hypothesis rather than adding economy levers").
2. **If independent confirmation is politically necessary**, run a LEARN-only, single-seed staged pilot with hard early-stop:
   - 100k ticks (~22 min) → 500k (~1.8 h) → 1M (~3.6 h). Stop the moment the late-window mean lands inside the 20k plateau band (~90 ± 3pp) — which the existing data says it will. Total exposure ≤ ~6 h instead of 18.
3. **Redirect the saved compute to substrate iteration.** The nonstationary variant is the most informative direction: it cut the delta to +3.13pp and late acc to 70.7% — i.e. the substrate's gain is largely *memorising a fixed 500-byte patch*, not robust learning. Variants that attack that gap (larger/more diverse patches, d_model scaling, true 2-layer depth, LR schedules) have real headroom.
4. **Re-open the 5M budget question only when a substrate clears Gates A+B at diagnostic scale.** At that point the relevant cost model is the live `sim_loop` numba `world_tick` path (a different, larger per-tick budget) — benchmark *that* path for the 5M finish-line run, not this screen.

## 7. If you run it anyway — optimal checkpoint schedule

| Item | Setting | Rationale |
|---|---|---|
| Window logging | every 5,000 ticks | 1,000 records/run ≈ 0.1 MB; plateau/noise structure fully resolved |
| Weight snapshots | every 100k ticks (all 60 orgs) | 50 snapshots ≈ 285 MiB/run; enables resume + norm-drift audit |
| Early-stop gates | 100k / 500k / 1M / 2M | compare late-window acc vs the 90 ± 3pp plateau band; stop on first match |
| Parallelism | 8 runs concurrently, 1 core each | wall-clock = slowest run (~18 h), not the 5.2-day serial sum |
| Resume | restart-from-snapshot logic | current code has none; a crash at 4.9M ticks loses ~18 h (O) |

---

### Appendix — reproducibility

- Benchmark cell: `run_arm` from `sub4_small_transformer.py`, `TICKS=200`, min of 2 reps per arm, sandbox 8×Xeon 2.6 GHz/8 GB, numpy 2.x, single-threaded BLAS workload (matrices ≤ 256×32).
- Result files read: `experiments/sub4_results/{sub4_summary, sub4_20k_summary, sub4_nonstationary_summary, sub4_novel_summary}.json`.
- Rules read: `.agents/rules/Rules-17-21.md`, `Docs/Architecture/Ascent.md` (finish line + kill-criterion status).
- Known code/docstring discrepancies (O): 1 attention block implemented vs "2" documented; 25,088 params vs "~10,000" documented.
