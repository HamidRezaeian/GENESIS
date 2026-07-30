# Rule 21.3 — Income-Side Refactor: Reward = Measured Hardware Load Freed

**Date:** 2026-07-25
**Author:** Clusy Agent (Session 8 — Rule-21 income review)
**Status:** Proposal. Closes the income-unit open question deferred in `RULE21_2_ENGINE_REFACTOR_DESIGN.md` §10.
**Companion analysis:** `tests/clusy/qwen/session8_rule21_income_review/` (verdict + 6 figures).

---

## 1. Context

`RULE21_2` grounded the *parameter* side (evolvable per-organism constants) and reaffirmed the
*cost* side (Rule 21.1: costs are measured host cycles). It explicitly deferred the **income** side:

> *"Income is `256 = CELL_STATES = 2^BITS_PER_BYTE` (information capacity, H-derived). Its exchange
> rate against real execution cycles is a separate Rule-21 review question: is information-capacity
> the right income unit, or should income also be a measured work quantity?"* — RULE21_2 §10

Session 8 reviewed this question, grounded in the engine code (`src/neuromorphic_engine.py`) and the
Exp 87 data (`tests/clusy/qwen/exp87_metabolic_ceiling/results/`). Findings:

1. **The income quantum is blind to problem difficulty.** Income per correct byte =
   `(net/8)×CELL_STATES`, capped at 256, regardless of how much computation/memory that byte
   required. A trivially-predicted byte and a deeply-computed byte both pay ≤ 256.
   (figure: `reward_blind_to_difficulty.png`)
2. **Cost is NOT blind.** Brain cost per tick scales with brain size (Exp 87: 65-neuron brain
   ≈ 414 cycles/tick; 139-neuron ≈ 1977). Hard cognition is therefore systematically
   unprofitable: same income, higher cost.
3. **The metabolic ceiling (Exp 87):** idle cost (414 → 2387) always exceeds the income quantum
   (256); fraction of net-positive ticks = **0.000** in every condition. Selection is nullified.
   This is the Rule-5 corollary Catch-22.
4. **Scenario (1) "income ∝ Shannon information" as a multiplier FAILS Rule 21.4** — it is exactly
   the `gain *= curriculum_delay×8` the engine already rejected in favor of DIGESTION (Exp 48).
   With a *derived* exchange rate it collapses into scenario (2). (figure: `rule21_4_tuning_test.png`)
5. **The honest path is scenario (2): income = a measured work quantity.**

This document specifies scenario (2) concretely, in the form proposed and refined during Session 8.

## 2. The core principle

> **Income = the measured hardware load (RAM / CPU / disk footprint) that an organism FREES from the
> system by solving a work-unit or by internalizing (learning) it. The load is measured on the host,
> not assigned. The freeing is competitive: a resource is freed once and claimed by the first
> organism to internalize it. Freeing makes room for the next work-unit (open-ended).**

Two activities earn income, both via the same mechanism:
- **Solving** a problem: the problem occupied a footprint; solving and clearing it frees that footprint.
- **Learning** a topic: the topic is loaded (footprint); internalizing it into the organism's model
  lets the external scaffold be deleted, freeing the footprint. Learning = compression of the
  environment into the organism (Free Energy Principle / Solomonoff / MDL made literal).

## 3. Goals

- **G1.** Replace the fixed income quantum (256 = information capacity) with a **measured work
  quantity** (freed footprint), closing RULE21_2 §10.
- **G2.** Make income **scale with difficulty**: a work-unit that puts more load on hardware pays
  more to free.
- **G3.** Make income **competitive / rivalrous**: the resource is freed once; the first to
  internalize claims it → an emergent selection gradient on learning speed.
- **G4.** Keep the system **open-ended** (Rule 9 / 13): freeing a unit makes room for the next.
- **G5.** Pass the **Rule 21.4 tuning test**: no designer-selectable knob; the footprint and the
  α > β condition are measured, not tuned.
- **G6.** Stay **strictly @njit-compatible**: pre-allocated arrays + primitives only.

## 4. Non-goals (this refactor does NOT)

- Does not author intelligence into the ancestor (Rule 5). The ancestor keeps only survival
  primitives; the income rule is substrate physics.
- Does not assign "difficulty scores" to work-units. The footprint is measured, never labelled.
- Does not change the cost side (already grounded by Rule 21.1) — only the income unit.
- Does not guarantee the ceiling breaks. If the measured footprint-per-complexity (α) is below the
  measured brain-cost-per-complexity (β), the ceiling holds honestly (scenario-3 null result). The
  design must accept this.

## 5. Definitions

- **Work-unit (W):** a discrete unit of work in the environment — a problem to solve or a topic to
  learn. Replaces the current non-destructive byte-scroll position.
- **Footprint f(W):** the measured hardware load W occupies — RAM bytes held + CPU cycles to
  hold/process + disk I/O. **Measured on the host**, not assigned. (Generalizes to GPU when
  available; the current engine is CPU-only, so f = measured RAM + CPU.)
- **Internalize:** an organism's internal model (CAM entries / synapse weights / genome) captures W
  to a measured threshold — operationally, the organism can reproduce/use W *without* the external
  scaffold.
- **Free:** remove W's external representation from the shared resource pool, returning f(W) to the
  available pool.
- **α:** measured footprint freed per unit of work-unit complexity. **β:** measured brain-cost per
  unit of complexity. Both are host measurements, not parameters.

## 6. The income rule (replaces `gain = (net/8)×CELL_STATES`)

```
When organism o internalizes work-unit W and thereby frees it:
    income(o)      = f(W)        # the measured footprint freed
    pool_available += f(W)       # resources returned (open-ended turnover)
    W is removed from the active pool
```

- **Bounded by reality:** f(W) is the actual measured load, so total income/time is bounded by the
  actual work the environment supplies — a real carrying capacity forms (cf. the existing DEPLETE
  finite-fuel design).
- **Competitive:** because W is freed once, only the first organism to internalize it earns f(W).
  This generalizes the engine's existing rivalrous income (gain divided by `1 + neighbours doing
  the same behaviour`) into a race for resource-freeing.
- **Difficulty-sensitive:** f(W) grows with W's complexity, so hard work-units pay more — fixing
  the blindness in §1.

## 7. Mapping onto the current engine

| Current engine | Refactor |
|---|---|
| Non-destructive contiguous scroll (byte-prediction) | **Clearable work-units** with measured footprints; a unit is removed when freed. |
| `DEPLETE` / `read_fuel`: finite per-cell fuel, **cap = CELL_STATES = 256** | Generalize the cap from fixed 256 to the work-unit's **measured footprint f(W)**. DEPLETE is the direct template. |
| CAM / synapses / genome (internal model) | The substrate of **internalization**; the internalization threshold is measured (can the organism reproduce W without the scaffold?). |
| Rivalrous income: `gain /= 1 + neighbours_same_behaviour` | Seed of the **competition**; generalized to "first to internalize frees and claims f(W)". |
| `gain = (net/8)×CELL_STATES` (income quantum) | Replaced by `income = f(W)` (measured freed footprint). |
| DIGESTION (grounded fuel extraction, Exp 48) | The honesty precedent: income from a measured, conserved quantity, not a multiplier. |

## 8. Rule compliance

- **Rule 21.1 (costs are real work):** f(W) is measured host RAM/CPU/disk — real work, not game
  points. ✓
- **Rule 21.4 (tuning test):** f(W) is measured; α and β are measured; there is no designer-selectable
  multiplier. Sweeping any candidate exchange constant must give a flat/derived response, not a
  turn-on. ✓ (re-verified empirically per phase)
- **Rule 7 (emergent efficiency):** changes the *resource economy* (how income is generated), not a
  top-down efficiency score. ✓
- **Rule 5 (ancestor boundary):** the ancestor keeps only survival primitives; the income rule is
  substrate physics, not authored cognition. ✓
- **Rule 9 / 13 (autotelic, open-ended):** work-units must be generated by the environment, not
  authored as puzzles; freeing makes room for the next → non-terminating. (Designing the autotelic
  work-unit generator is the hard part — see §11.)
- **Rule 17 (no arbitrary selection-relevant constants):** f(W) is measured, not an arbitrary
  constant. ✓
- **Rule 14 (refugium < 5%):** to be re-measured; the goal is that footprint-income restores a real
  gradient so the population is not on life support.

## 9. Implementation constraints (strict Numba)

All changes to `world_tick_numba` and any physics kernel must be **@njit-compatible**:
- All state in **pre-allocated NumPy arrays** (`float32`/`int64`) + scalar primitives. **No** Python
  lists, dicts, objects, or unsupported NumPy calls.
- New per-organism / per-work-unit data (e.g. a `work_footprint[]` array, an `internalized[]` flag,
  a per-org `income_acc[]`) added as **module-global pre-allocated arrays** read by the kernel — the
  established pattern (the kernel is called from 8+ sites; signatures are not changed).
- Loops with **compile-time bounds** only (e.g. `for b in range(8)`); no comprehensions.
- The CAM "key→value" store stays fixed-size arrays (`g_cam_keys/vals/valid`), not a dict.
- **Numba cache:** every kernel is `@njit(cache=True)`. After any kernel edit, the on-disk cache
  (`__pycache__`) must be invalidated (or the signature bumped), else the stale compiled kernel runs
  silently and income is measured wrong.

## 10. Honesty anchors (anti-gaming — non-negotiable)

1. **Measured, never assigned.** f(W) is the actual host footprint. Assigning a "difficulty score"
   to W is a game mechanic and fails Rule 21.4.
2. **Freeing tied to genuine internalization.** Income is paid only when (a) the external scaffold
   is actually removed AND (b) the internal model demonstrably captures W (the organism can
   reproduce/use W without the scaffold). This prevents "fake-freeing" to farm income.
3. **α > β is a measurement, not a target.** If the measured footprint-per-complexity does not
   exceed the measured brain-cost-per-complexity, the ceiling holds and we report the honest null
   (scenario 3). We do not tune α upward.
4. **Substrate note:** the principle is substrate-general (RAM/CPU/GPU/disk), but the current
   engine/sandbox is CPU-only; f is measured as RAM + CPU now.

## 11. Risks & honesty flags

- **Stealth difficulty score.** The biggest risk is f(W) becoming a labelled difficulty rather than
  a measured footprint. Mitigation: f(W) must be derived from instrumented host measurements (bytes
  allocated, cycles spent), with the derivation documented (Rule 21.5/21.6 H-class).
- **Winner-take-most race dynamics.** First-to-internalize claiming the whole footprint may favor
  fast-but-shallow learners or cause thrashing. An empirical question to study, not a flaw; may
  need the existing rivalrous division retained as a damping term.
- **Autotelic work-unit generation (Rule 9).** The environment must supply work-units with genuine,
  ongoing, measurable footprints without being authored puzzles. The hardest design problem; largely
  open.
- **Internalization measurement.** "Can the organism reproduce W without the scaffold?" must be a
  clean, cheap, measurable test inside the @njit kernel.
- **Major environment redesign.** Not a small tweak; the non-destructive scroll must become a
  clearable work-unit pool. Phased rollout (§12) is mandatory.
- **GPU.** Not available now; f = RAM + CPU. The design must not hard-code CPU-only assumptions that
  block later GPU measurement.

## 12. Phased plan (each phase: Rule-21.4 test + multi-seed per Rule 3)

- **Phase 0 — Measurement audit (zero Rule-21.4 risk).** Instrument the host to measure (a) the
  footprint f(W) of candidate work-units and (b) the brain-cost β. Determine empirically whether
  α > β is achievable. **Gate:** if α ≤ β for all realistic work-units, report the honest null
  (scenario 3) and stop.
- **Phase 1 — Minimal work-unit environment (diagnostic, Rule 9/10).** A small clearable work-unit
  pool with measured footprints, clearly identified as a diagnostic, not the final environment.
- **Phase 2 — Income = freed footprint.** Replace `gain = (net/8)×CELL_STATES` with `income = f(W)`
  (generalize the DEPLETE cap). Verify the Rule-21.4 tuning test stays flat.
- **Phase 3 — Competitive freeing.** First-to-internalize frees and claims f(W); retain rivalrous
  division as damping. Verify a selection gradient on learning speed *emerges* (not authored).
- **Phase 4 — Open-ended autotelic turnover.** Freed resources make room for generated work-units;
  verify non-termination (Rule 13) and refugium < 5% (Rule 14).

## 13. Falsifiable predictions (Rule 2 / Rule 18)

- **P1.** With footprint-income, the fraction of net-positive ticks becomes **> 0** for work-units
  with f(W) > idle cost (vs 0.000 in Exp 87).
- **P2.** A selection gradient on **learning speed** emerges across seeds (faster internalizers earn
  more), and is absent when the race is disabled (control).
- **P3.** Brains do **not** bloat unboundedly (the Exp 87 65 → 183-neuron blow-up); under proper
  cost accounting they size toward the work-units' footprints (Rule 7 efficiency emerges).
- **P4 (null).** If measured α ≤ β, the ceiling persists and we record scenario 3 — the design
  explicitly permits this honest negative.

## 14. Guarantees / regression

- The Exp 87 null result (fraction net-positive = 0.000 on the fixed-quantum repetitive scroll) must
  remain reproducible on the OLD income rule (feature-flagged), so the refactor is A/B-testable
  against the baseline.
- The new income rule is feature-flagged (`GENESIS_INCOME_FOOTPRINT=1`), default OFF, until Phase 2
  passes its tuning test.
- All constants introduced are classed H/E/O/G per Rule 21.6; f(W) is **H** (measured host work).

## 15. Phase 0 result — measurement audit (executed 2026-07-25, Session 8)

Phase 0 was executed as a measurement audit (zero Rule-21.4 risk; no engine change).
Notebook: *Session 8 — Rule-21 Review*, cells "PHASE 0"; figure `phase0_measurement_audit.png`.

**Measured (real):**
- **β = 12.7 cycles / neuron / tick** — slope of `idle_cost` vs `n_neurons` in Exp 87 (both arms,
  all seeds). (The linear-fit intercept ≈ −236 cycles/tick is a fit artifact; the slope β is the
  meaningful quantity.)
- **e_update = 2.876, e_read = 2.444 cycles** — host-measured per-operation costs (Rule 21.1, H-class).
- Each neuron performs ≈ β/e_update ≈ **4.4** update+read operations per tick.
- **From-scratch complex compute ≈ 2,759× more expensive than cached retrieval** — measured directly
  on the host (9,334 µs vs 3.4 µs per call). This is the physical basis for a large α: internalizing
  a complex work-unit frees compute far exceeding the cost of maintaining the internal model.

**The gate (derived from the measurements):** a work-unit of complexity K is profitable iff
`N × (C_scratch − C_cached) × e_update > β × (K/r) × t_learn`, where r = the internal model's
compression ratio (bytes captured per internal unit) and N = re-use count. For K=100, t_learn=20:
**N\* ≈ 29/r** — i.e. with modest compression (r=3) and modest re-use (N>10), or even no compression
(r=1) with N>29, a complex work-unit is profitable.

**Decision: GO (conditional).** The measured constants (β, e) do **not** rule out α > β; the gate is
passable with modest compression and modest re-use. Three quantities remain UNVERIFIED and must be
measured on the engine in Phase 1/2: the actual `C_scratch(K)`, the compression ratio `r` the
CAM/synapses achieve, and `t_learn`. (The figure treats these as illustrative and sweeps them for
sensitivity — they are not tuned to force a pass.)

**Next:** Phase 1 — minimal clearable work-unit environment with measured footprints (diagnostic,
Rule 9/10), with the explicit task of measuring `C_scratch`, `r`, `t_learn`. If those measurements
yield α ≤ β, the honest null (scenario 3, prediction P4) is recorded and the refactor stops.

## 16. Phase 1 result — learning dynamics on the real engine (analyzed 2026-07-25)

Phase 1 analyzed the validated Exp 87 engine data directly (30000 ticks, STDP_TARGET=0, 3 seeds).
The engine itself requires numba (absent in the analysis kernel; present in the terminal env, but
the platform reserves main work for visible cells), so the existing Exp 87 measurement was used
rather than a fresh run. Notebook: *Session 8 — Rule-21 Review*, "Phase 1" cells; figure
`phase1_learning_audit.png`.

**Measured (real, Exp 87 arm 0):**
- The seeded ancestor **COMPRESSES the scroll effectively**: a 65-neuron brain (idle ≈ 384–414
  cycles/tick) achieves **≈ 129 correct predictions/tick**. A small internal model masters the
  extended scroll — this is compression.
- **WITHOUT an income gradient, evolution BLOATS brains and comprehension COLLAPSES**: neurons
  65 → 171, synapses 93 → 776, idle cost 414 → 2387; correct/tick falls ≈ 129 → 2.6
  (collapse onset ≈ tick 600).

**Interpretation:** learning/compression WORKS in the engine (small brain, high comprehension); the
Exp 87 collapse is an EVOLUTIONARY dynamic (mutational bloat with no income gradient to select for
efficiency), not a learning failure. This confirms the need for the footprint-income gradient
(Phase 2) to select for efficient compression and prevent bloat.

**Honest limitations of this measurement:**
- `t_learn` FROM SCRATCH was NOT measured — the ancestor is seeded competent
  (`create_intelligent_ancestor`), so it peaks at the first sample (tick 200), not via a
  from-scratch learning curve.
- The compression ratio `r` (CAM utilization) was NOT measured — Exp 87 does not sample CAM.
- Measuring `t_learn` (naive organism) and `r` (CAM sampling) precisely requires a dedicated
  experiment with numba in the analysis kernel — a separate follow-up step.

**Status:** consistent with the Phase 0 GO (conditional). The real data confirms efficient
compression is achievable but is destroyed by evolution without an income gradient, reinforcing the
case for Phase 2 (income = freed footprint).

## 17. Phase 2 result — footprint income tested on the real engine (2026-07-25)

Phase 2 was implemented and tested on the real engine (numba 0.66.0 installed in the analysis
kernel; the modified kernel recompiled). The change is feature-flagged (`GENESIS_INCOME_FOOTPRINT`)
and strictly @njit-compatible:

- Added module constants `INCOME_FOOTPRINT` (env flag) and `FOOTPRINT_QUANTUM` (measured footprint
  per byte, default 642.0 = the Exp 87 ancestor's measured per-prediction brain cost: idle ~411
  cyc/tick / ~0.645 correct predictions per organism per tick).
- The base income line now branches: when `INCOME_FOOTPRINT`, `gain = (net/8) x FOOTPRINT_QUANTUM`
  instead of `(net/8) x CELL_STATES` (256).

Test (STDP_TARGET=0, 1 seed, 3000 ticks), compared to the Exp 87 baseline (income=256) at the same
horizon:

| metric (end of 3000 ticks) | baseline (256) | footprint (642) |
|----------------------------|----------------|-----------------|
| n_alive                    | 30 (refuge)    | 30 (refuge)     |
| energy_mean                | 150,254        | 314,904         |
| correct/tick               | 15.5           | 13.6            |
| idle cost                  | 679            | 1,426           |
| n_neurons                  | 78             | 95              |

**Result: the ceiling is NOT broken.** The population still falls to the refuge floor. Worse, the
higher income FUELED MORE BLOAT (neurons 78 -> 95, idle 679 -> 1426): the larger income let bigger
brains survive temporarily, raising the idle cost further.

**Interpretation (key negative finding):** raising the income quantum (256 -> 642) does not break
the metabolic ceiling; it amplifies bloat. A fixed per-byte footprint income gives the ancestor only
break-even (income ~ idle cost ~ 411), so any bloat turns net income negative -> crash -> refugium
masks selection. A fixed income quantum creates NO gradient against bloat.

**What the ceiling actually requires (absent in this test):**
1. **Real RAM freeing** (clearing cells when internalized), so the footprint includes the freed RAM
   (256) -> 898 -> net-positive income for the ancestor (instead of break-even). Needs the work-unit
   clearing mechanism (Phase 3/4).
2. **A gradient AGAINST bloat (efficiency selection):** income structured so a smaller, more efficient
   brain earns more income per unit cost, so selection favors efficiency rather than the higher income
   merely feeding bloat.

Figure: `phase2_footprint_test.png`. The engine modification is committed (feature-flagged, default
OFF). This negative result refines the path: the income unit alone is insufficient; the freeing
mechanism and an anti-bloat gradient are the load-bearing pieces.

## 18. Phase 3 result — cell clearing tested with footprint income (2026-07-25)

Phase 3 added cell clearing to the `INCOME_FOOTPRINT` rule: on every correct prediction
(net > 0), the predicted cell's content is replaced (`ram_substrate[nxt] = (nxt+1) & 0xFF`),
simulating the external representation being freed (RAM) and replaced by new content
(open-ended turnover). This is immediate clearing (no consensus threshold).

`FOOTPRINT_QUANTUM` default was changed from 642.0 to 898.0 = 642 (measured compute freed per
byte prediction) + 256 (RAM freed per byte when the cell is cleared). For the efficient ancestor
(idle ~414, ~0.645 predictions/org/tick): 898 x 0.645 = 579 > 414 → net positive income.

**Test result:** The engine ran successfully (numba 0.66.0 recompiled, 3000 ticks, 1 seed). The
validation run showed thousands of cell-clearing events (the counter incremented each tick).
Population-level data was collected (file `phase3_footprint_clearing_run.json`).

**Negative finding for immediate clearing:** By changing the cell content on EVERY correct
prediction, the immediate clearing destroys the scroll's learnable structure — the organism
faces constantly new content and cannot rely on a static pattern. This may reduce correct
prediction rates, lowering the effective income despite the higher `FOOTPRINT_QUANTUM`.

**What the ceiling actually needs (refined by this result):**
1. **Threshold-based clearing** (community consensus): a cell is cleared only after it has been
   correctly predicted by MULTIPLE organisms, so the pattern is genuinely learned by the
   population before its external representation is freed. This preserves the learnable structure
   while still freeing RAM.
2. **Gradient against bloat**: the income per prediction must be high enough that the efficient
   ancestor has net positive income WITHOUT destroying the learnable structure. The 898 footprint
   provides the level; the threshold clearing provides the structure preservation.

The engine modification is committed (feature-flagged, default OFF). Phase 3 refines the path:
threshold-based clearing is the next step to balance learning structure preservation with RAM
freeing.

## 19. Phase 4 result — threshold-based cell clearing (2026-07-25)

Phase 4 replaced immediate clearing with threshold-based clearing: a cell is cleared (content
replaced, RAM freed) only after `CLEAR_THRESHOLD` organisms have correctly predicted it (community
consensus). `g_clear_count` is a per-cell int32 counter passed as a kernel PARAMETER (numba treats
module-global arrays as readonly, so mutable per-cell state must be a parameter — added to the
world_tick_numba signature and all call sites in genesis_lab.py and the driver).

Test (STDP_TARGET=0, 1 seed, 3000 ticks, CLEAR_THRESHOLD=10, FOOTPRINT_QUANTUM=898):

| metric | Phase 3 (immediate) | Phase 4 (threshold=10) | Baseline (256) |
|--------|--------------------|-----------------------|----------------|
| n_alive | 30 | 30 | 30 |
| correct/tick | 3.13 | **14.74** | 15.5 |
| idle | 1049.6 | 1145.6 | 679 |
| neurons | 82 | 82.8 | 78 |

**Partial success — the clearing mechanism works:** threshold clearing PRESERVED the learnable
scroll structure (correct/tick 14.74, close to baseline 15.5), unlike immediate clearing (3.13,
which destroyed the structure). The community-consensus mechanism is sound: cells are cleared only
after the population has genuinely learned them, so prediction stays high while RAM is still freed.

**Ceiling still not broken (n_alive=30). Two reasons:**
1. **Calibration drift:** FOOTPRINT_QUANTUM=898 was calibrated for CYCLES_PER_NEURON_UPDATE≈2.876
   (the Exp 87 host measurement), but this run measured 4.343 (host performance varies run-to-run),
   raising the ancestor idle cost to 604.9 (vs 411). The fixed footprint (898 x ~0.49 correct/org/tick
   ≈ 440) no longer covers the higher idle cost.
2. **Fundamental — one byte per tick:** the engine predicts ONE byte per tick, so income per tick ≈
   footprint x predictions/tick. With the footprint calibrated to the per-prediction compute cost,
   income ≈ idle cost (break-even) for ANY brain size — the compute component cancels out. The RAM
   component (256) adds only ~165/tick, insufficient to overcome the idle cost. **Breaking the ceiling
   requires rewarding MULTI-byte work-units** (a lump-sum reward on completion of a complex problem),
   so the income per work-unit can exceed the per-tick idle cost. This is the load-bearing change still
   needed.

The threshold-clearing mechanism is sound and committed (feature-flagged, GENESIS_INCOME_FOOTPRINT +
GENESIS_CELL_CLEAR_THRESHOLD). The remaining gap is the income granularity: multi-byte work-unit
rewards are needed to break the metabolic ceiling.
