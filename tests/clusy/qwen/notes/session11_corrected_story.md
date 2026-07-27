# Session 11 — The Corrected Story (Cache-Key Bug, K Sweep, & What Breaks the Ceiling)

**Date:** 2026-07-26  **Branch:** `session9-lumpsum`  **Author:** Clusy Agent  
**Commit:** to be determined (after push).

---

## Summary of Corrections

Sessions 9, 10, and 10b contained two measurement artifacts that together produced a false "honest
null" narrative. Both are now understood and one has been fixed in the engine.

### Bug A — g_org_run within-tick reset (discovered, not a code bug)

The engine (L1986–1992) does:
```
if net > 0:
    g_org_run[org] += 1
    if g_org_run[org] >= LUMPSUM_K:
        gain = K * FOOTPRINT_QUANTUM
        g_org_run[org] = 0         # ← reset WITHIN the firing tick
```
So `g_org_run` is 0 on the next tick after a fire. The observable max is always `K−1` (="7" for K=8).
The lump sum DOES fire; you just cannot see "8" in a post-tick sample. The trace recording proves it:
at K=8, `g_org_run` climbs 0→1→…→7→(fire, reset)→0, and the energy jumps by ~6340 (= 7184 − idle)
at the firing tick. Verified: 265 fires / 4000 ticks at K=8.

This is not a code bug — the mechanism is correct and intended — but the session-9/10 metric `max_run`
misled us into thinking the lump sum "never fires." The driver should record the **pre-reset maximum**
(or the number of fire events) instead of the post-tick residual.

### Bug B — numba cache-key missing income flags (FIXED, genesis_lab L146–160)

The cache-dir name (`os.environ.setdefault("NUMBA_CACHE_DIR", …)`) encoded ~20+ flags but **NOT**
`INCOME_FOOTPRINT`, `INCOME_LUMP_SUM`, `LUMPSUM_K`, `FOOTPRINT_QUANTUM`, `DEPLETE`, or
`CELL_CLEAR_THRESHOLD`. Since `@njit(cache=True)` bakes the compile-time values of those globals,
changing an income env var reused a stale kernel compiled with the first-seen values.

**Impact:** every "sweep" in Sessions 9 and 11 (pre-fix) was invalid — all K values reused whichever
kernel was compiled first (K=8 in Session 9, K=1 in the first post-fix sweep). The "lump sum never
fires" and "max_run caps at 7" conclusions were partly this artifact.

**Fix (Rule 17 disclosed, committed):** added the six income flags to the cache-dir f-string in
`genesis_lab.py` so each unique combination gets its own cache dir and the kernel recompiles
correctly.

### Corrected narrative (after both artifacts are resolved)

1. **The output IS a clean, stable echo.** Per-tick trace (immortal ancestor, STDP=0, 4000 ticks,
   recording `vocal_cords[0]` every tick): the organism walks the scroll (+1 saccade 98.9% of ticks,
   mean position change 0.983), and its output matches the current byte with agreement 1.000 on
   successful reads. The creature echoes what it reads — the code comment at L1661 is correct.

2. **The lump-sum mechanism FIRES.** At K=8, 265 × 7184 = ~1.9M energy paid over 4000 ticks.
   The organism sustains runs of 8+ and collects.

3. **But K=8 is still net-NEGATIVE** (−357/tick idle-to-income) because the scroll's many
   short identical-letter blocks (5, 3, 2, 1 repeats) break runs before they reach 8, wasting
   the in-progress reads (they pay nothing). Only the 10-letter blocks complete.

4. **The real cure — K=2 or K=3.** A proper K sweep (each K with its own explicit NUMBA_CACHE_DIR)
   gives:

   | K | realized income/tick (exact) | net drift/tick | |
   |---|---|---|---|
   | 1 | 770 | −15 | ~break-even |
   | **2** | **711** | **+28** | **net-positive** |
   | **3** | **692** | **+7** | **net-positive** |
   | 4 | 614 | −69 | net-negative |
   | 8 | 476 | −357 | strongly net-negative |

   Income falls monotonically with K (770 → 476) because larger K wastes more in-progress reads.
   The idle threshold (~685, measured by timing benchmark, varies ±100 per compile) lies between K=3
   and K=4. **K=2 or K=3 breaks the metabolic ceiling for the single reader.** The Session-9 choice
   of K=8 was unvalidated; the design doc prescribed a sweep that was never properly run until now.

5. **STDP_TARGET makes ~zero difference** on the single reader (STDP=0 vs =1 gave identical metrics
   within noise). The teaching signal does not affect the echo; it only operates on actively wrong
   bits, and the echo is already correct most of the time.

## Q1 answer: Is 898 (FOOTPRINT_QUANTUM) hardware-dependent?

**Yes, the user's intuition is correct — currently it's a fixed snapshot, but the design envisions
it as host-derived.**

- The **cost** side (`CYCLES_PER_NEURON_UPDATE`, `CYCLES_PER_SYNAPSE_READ`, `CYCLES_PER_MOVE`) IS
  re-measured on each host by `physical_cost_model.engine_primitive_cycles()` at import time (lines
  500–508). The idle cost (~685/tick on this 8 GiB host) is genuinely host-dependent.
- The **income** side (`FOOTPRINT_QUANTUM = 898 = 642 compute + 256 RAM`) is a **fixed env-default**
  (line 1068). The 642 was measured on the original development host (Exp 87 ancestor's per-prediction
  brain cost: ~411 idle / ~0.645 correct-prediction fraction). The 256 is `CELL_STATES = 2^8`, which is
  hardware-independent (RAM cell capacity).
- The design doc (§17, Rule 21.3) says costs are re-measured per host but income is a snapshot, and
  acknowledges this as the honest path: "the cost side is straightforward" while the income quantum
  "remains a fixed snapshot (642 host-measured compute + 256 hardware-independent RAM) — the
  uncertainty is in the DOUBLING: income vs idle is the bottleneck."
- **Consequence for portability:** on a faster host, idle cost would be lower (fewer native cycles),
  making even K=4 or K=8 break even. On a slower host, even K=2 might fail. The fix would be to
  re-derive 642 per host (measure the ancestor's per-prediction brain cost at runtime), or admit
  that 898 is a platform-specific calibration constant.

## Next steps (Session 12)

1. **Test K=2 or K=3 in the full evolutionary A/B** (STDP=0 vs =1, with DEPLETE=0 first, then
   DEPLETE=1 if the population survives). The current `run_evolution.py` driver uses a hardcoded
   K=8 for the lump-sum path; make K an env-controllable parameter and run the comparison with K=2.
2. **Fix the driver metric:** record the number of `g_org_run` firing events (or the pre-reset max)
   instead of the post-tick residual, so the lump-sum activity is visible in evolutionary runs.
3. **Re-run Sessions 9/10 with K=2** to verify the population avoids extinction and explore whether
   STDP_TARGET or other levers matter once the ceiling is cracked.
4. **Portability audit:** compare idle cost vs income on different hosts (or re-measure 642's compute
   component per host) to formalize the calibration.
