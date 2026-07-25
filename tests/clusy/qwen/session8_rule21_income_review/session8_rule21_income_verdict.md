# Session 8 — Rule-21 Review: Income ∝ Shannon Information vs Measured Work

**Question (session 8):** To break the metabolic ceiling measured in Exp 87 (pure-idle cost
≈ 436 cycles/tick > income quantum = 256 cycles/tick; fraction of net-positive ticks = 0.000
in every condition), two scenarios were proposed:

- **(1)** Income ∝ measured Shannon information gain (bits of surprise reduced) — the Free
  Energy Principle made literal. The engine already has DELAY/DIGESTION machinery that scales
  `gain` with `curriculum_delay`; can this be generalised to a law "income ∝ measured information"?
- **(2)** Re-derive the income quantum as a measured WORK quantity (design doc §10 open question).

**Status of this document:** a Rule-21 review **prior to any engine change**, exactly as the
Exp 87 verdict recommended ("A dedicated Rule-21 review of (1)/(2) is the recommended next step
before any engine change"). Companion analysis notebook: *Session 8 — Rule-21 Review* (Clusy),
figures `exp87_ceiling_reproduced.png`, `rule21_4_tuning_test.png`, `shannon_info_gain_collapse.png`.

---

## The governing rules (verbatim anchors)

- **Rule 21.1** — Costs are REAL hardware work. *"Invented 'cost points' (e.g. `SPIKE_COST = 1`,
  a fixed 'income = 256') are FORBIDDEN — they are game mechanics."* The current quantum survives
  only because `CELL_STATES = 256 = 2^BITS_PER_BYTE` is **H-derived** (microstates of one byte),
  not because 256 was chosen.
- **Rule 21.4 (Tuning Test)** — *"If changing a number makes the system 'work better' because it
  was tuned, that number is an illegal game mechanic. A legitimate value is either derived
  (changing it would be physically wrong) or evolved (selection, not the designer, set it)."*
- **Rule 7** — Efficiency must emerge from substrate physics; if pressure is too weak, fix the
  *resource economy / substrate accounting*, never add a top-down score.
- **Rule 9** — The final environment must not be human-authored puzzles (diagnostic tests allowed).
- **Rule 5 corollary** — the thermodynamic Catch-22: compositional cognition is unaffordable while
  `n_neurons × depth × spike_cost > 256`.

## What the engine ALREADY decided (the decisive precedent)

The income path is already information-theoretic: echo (naming the sensed cell) pays **0**
(0 surprise → 0 energy); only predicting the **next** symbol — which is on no sensory input —
earns `(net_correct_bits/8) × CELL_STATES`, fuel-bounded by DEPLETE. Crucially, the engine's own
history adjudicated this exact question:

- **DELAY** scaled income by a multiplier: `gain *= curriculum_delay × 8.0`.
- **DIGESTION** (Exp 48) **replaced that multiplier** with grounded fuel extraction, with the
  explicit comment: *"The energy cannot be scaled by a magic multiplier. Instead, the organism
  extracts the fuel it SWALLOWED DELAY_N ticks ago: `gain = (net/BITS_PER_BYTE) × swallowed_fuel`."*

So the project already rejected "scale income by an information multiplier" and chose "income =
a measured, conserved work/fuel quantity." DIGESTION is the working template for scenario (2).

## The Rule-21.4 tuning test applied (4 regimes)

Reference physics (Exp 87 ancestor): pure-idle cost `C = 436`, income quantum `IQ = 256`.

| Regime | Income rule | Free knob? | Rule 21.4 | Ceiling? |
|--------|-------------|:----------:|:---------:|:--------:|
| **A** current | `(bits/8)·256`, fuel-bounded | none (256 = 2⁸ is H) | **PASS** | binds (256 < 436) |
| **B** scenario (1) *naive* | `(bits/8)·256·k` | **k** (designer's multiplier) | **FAIL** | "solved" only by tuning k>k\*=C/IQ≈1.70 |
| **C** scenario (2) | measured fuel/work `F` | none (F is measured) | **PASS** | binds when F < C |
| **D** scenario (1) *honest* | `info_gain(t)·ρ`, ρ derived (Landauer) | none (ρ is a physical constant) | **PASS** | binds; on repetitive content info_gain→0 ⇒ income→0 |

**Regime B fails 21.4:** the net-positive fraction is a step that turns on at a designer-selectable
`k* = C/IQ ≈ 1.70`. Choosing `k ≥ k*` to make the organism survive is precisely the tuned game
mechanic 21.4 forbids — and is exactly DELAY's `gain *= curriculum_delay×8` that the engine already
removed. **Generalising that multiplier into "income ∝ information" would re-introduce the violation
DIGESTION was built to fix.**

**Regime D passes 21.4 but collapses into C:** with ρ derived from Landauer (kT·ln2 per bit, mapped
to the host's measured cycles/bit), changing ρ would be physically wrong, so it is not a knob. But
then `income = measured_bits × measured_cycles/bit = a measured WORK quantity` — i.e. regime C.

## The convergence (the core answer)

> **Scenarios (1) and (2) are distinct ONLY when scenario (1) keeps a free multiplier — which is
> exactly the Rule-21.4 violation. Once the multiplier is removed, honest (1) ≡ (2).**

## A physical finding about scenario (1) on barren content

Even the honest version (D) does **not** lift the ceiling on Exp 87's repetitive scroll: once the
period is learned, surprise → 0, so the measured information gain → 0 and income → 0 **on any ρ**.
Scenario (1) therefore does not "fix" the ceiling there — it **reframes** it as *"the environment
supplies no learnable information"* (a Rule-9 statement). The only honest lever is the environment's
information richness, never the exchange rate.

## Rule 7 / Rule 9 compliance

- **Rule 7:** the honest versions change the *resource economy* (how income is generated), not a
  top-down efficiency score → compatible. The multiplier version is not (it adds an authored score).
- **Rule 9:** honest (1) **requires** an informationally rich, autotelic environment. On the fixed
  Exp 87 scroll (a permitted diagnostic) income is zero — correctly.

## Verdicts

| Question | Answer |
|----------|--------|
| Is scenario (1) as an information *multiplier* honest? | **NO** — fails Rule 21.4; the engine already rejected it (DELAY→DIGESTION). |
| Is scenario (1) with a *derived* exchange rate honest? | **YES**, but it **collapses into scenario (2)** (measured work). |
| Is scenario (2) honest? | **YES** — a pure measurement audit, zero 21.4 risk; DIGESTION is its template. |
| Which is the more honest path? | **Scenario (2)**, plus a derived bit→work rate (Landauer) and an informationally rich environment (Rule 9). |
| Does either "fix" the ceiling on Exp 87's repetitive scroll? | **NO** — and that is the honest answer; the ceiling is a real thermodynamic bound (Rule 5 corollary). |

## How far from AGI (honest framing)

The metabolic ceiling is a **real thermodynamic statement**, not a bug to tune away. The honest
frontier is not "pick a bigger income quantum" but:

1. **Do scenario (2) as a measurement audit** — re-ground the income unit as a measured WORK
   quantity exactly as Rule 21.1 grounded cost (the §10 open question). Do **not** redefine the
   quantum upward to escape the ceiling (that is tuning).
2. **Derive the bit→work exchange rate** from Landauer / measured host cycles-per-bit — never tune it.
3. **Make the environment informationally rich (Rule 9)** so measured information gain is non-zero;
   on repetitive content no information income is possible, by construction.
4. **Accept the ceiling as a bound:** compositional cognition is unaffordable while
   `measured_information × cycles/bit < measured_idle_cost`. "Distance to AGI" = distance to an
   environment that supplies enough measured learnable information to flip that inequality in
   cognition's favour — with no rigged multiplier.

## Recommended next step (before any engine change)

1. Measurement audit of scenario (2): income unit = measured work (close the §10 open question).
2. Design an informationally rich (non-repetitive, open-ended) curriculum so a real test of
   "income ∝ measured information gain" becomes possible.
3. Only then implement the income change and re-run the Rule-21.4 tuning test on the full engine
   (sweep any candidate exchange-rate constant; a flat/derived response = pass, a peaked/turn-on
   response = illegal mechanic).
