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
