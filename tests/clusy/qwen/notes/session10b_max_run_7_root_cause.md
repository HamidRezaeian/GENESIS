# Session 10b — Root Cause of the max_run = 7 Cap: Verdict

**Date:** 2026-07-26  **Branch:** `session9-lumpsum`  **Author:** Clusy Agent
**Notebook:** "Session 10 — STDP_TARGET recruitment lever A/B" (cells: diagnostic → analysis → figure).
**Figure:** `max_run_7_root_cause.png`.  **Answers:** the #1 open question from session 10
(*"why does max_run cap at exactly 7 in every run?"*).

---

## Question

Session 10 found `max_run` caps at **exactly 7 in all 6 runs, both STDP arms** — too clean to be noise.
Is the cap **structural** (the scroll / reading gate makes 8 impossible by construction) or a
**learner/substrate** limit? This decides whether the whole income-granularity programme is viable.

## How the reward works (grounded in engine L1820–2050)

1. An organism at cell `pos` reads `ram[pos]` via its 8-bit reading eye and predicts the NEXT byte
   `ram[pos+1]` via its 8 vocal bits (`org_char_val`).
2. **Reading gate:** only bytes in `[32,126]` except `0x55` ('U') count.
3. Per bit `b`: `correct_bits += 1` if output=1 AND target=1; `wrong_bits += 1` if output=1 AND target=0.
   **Silence (output=0) scores nothing — it is free.** `net = correct_bits − wrong_bits`.
4. `net > 0` = a "correct byte" → extends the per-organism run `g_org_run`; `net ≤ 0` resets it to 0.
5. **Income:** footprint path pays `(net/8) × FOOTPRINT_QUANTUM` (898 = 642 compute + 256 RAM freed) per
   correct byte; the **lump-sum** path (Session 9) instead pays `K × 898` once on the K-th consecutive
   correct byte (`K=8`) and nothing on the in-progress ticks. Positive income is bounded by the target
   cell's finite fuel when `DEPLETE=1`.

So the run is a count of consecutive ticks where the organism gets **more 1-bits right than wrong**
(majority-correct byte), and the K=8 lump sum needs 8 such ticks in a row.

## The scroll (the supposed structural suspect)

`Books/English/00_Graded.txt` is only **231 bytes**, laid contiguously and repeated to fill RAM
(`g_ram[i] = gb[i % 231]`). It is a graded curriculum of identical-letter runs:
`{10×: 10 runs, 5×: 10, 3×: 10, 2×: 10, 1×: 31}` (e.g. `AAAAAAAAAA BBBBBBBBBB … ABCDEFGHIJ ABCDEFGHIJ …`).

- The optimal strategy is **echo** (predict next = current), correct everywhere inside a run.
- **Structural echo ceiling = 9** (one less than the longest, 10-letter, blocks). A perfect echo sustains
  9 consecutive correct bytes, then breaks at the letter boundary.
- ⇒ **The cap at 7 is NOT structural.** The scroll permits runs of 9; 7 < 9, so something else binds.

## The diagnostic (decisive)

Ran the seeded ancestor **alone** with teaching ON (`STDP_TARGET=1`), `DEPLETE=0`, and a **1e9 energy bank
(survival removed as a limiter)**, reading for 6000 ticks; recorded `g_org_run[0]` every tick plus every
`read_log` event (correct vs miss, and target vs guess on misses).

- **Max run = 7** for this single, immortal, taught organism.
- **Streak-length histogram:** `{7: 476, 3: 167, 5: 72, 4: 60, 2: 37, 1: 35, 6: 32}` — **54% of all 879
  streaks peak at exactly 7; none reach 8 or 9.**
- **Where runs break (854 classifiable): 47% MID-BLOCK** (target byte UNCHANGED) vs 53% at letter
  boundaries. Mid-block examples: tick 6 streak=7 target stayed 'A'; tick 15 'B'; tick 23 'C'; … tick 76 'H'.
  **The run breaks while the target is constant** — impossible to attribute to scroll structure.
- **Miss strategy:** 1954 misses, **0** with guess == target, but **99% in the same letter family**
  (high-nibble `0x40` match). The organism learned a **near-echo** (right letter family / high bits) but its
  low-bit precision drifts; on ~the 8th tick of a constant block the output flips enough bits that
  `net ≤ 0` and the run breaks.

## Root cause

**The cap at 7 is a dynamical OUTPUT-STABILITY limit of the spiking substrate** — not the scroll
(ceiling 9), not reward granularity (Session 9), not the teaching signal (Session 10), and not survival.
The substrate reliably learns an approximate echo (99% same-family guesses) that yields `net > 0` for
~7 consecutive ticks, but its spiking/membrane dynamics + homeostatic anchoring cannot HOLD a precise
output register stable for an 8th tick: the emission drifts to a majority-wrong pattern even on an
unchanging target. The "~7-tick" figure is the substrate's characteristic output-stability timescale,
which is why it recurs so cleanly across independent seeds and both treatment arms.

## Reframe + next step

The lump-sum (K=8) is **reachable in principle** (structural ceiling 9) but the substrate's output drifts
before tick 8. Therefore the lever to break the metabolic ceiling is **output-register stability**, not
the reward:
1. Test a **vocal latch / held-output** mechanism (hold the last emission stable across ticks) — does it
   extend streaks past 7?
2. Tune **membrane time constant / homeostatic-anchoring strength** to slow output drift.
3. Use the `org_delay_buf` / `org_scratch` register to stabilize the emitted byte across the work-unit.
4. Re-run the Session-10 A/B with the stability lever ON: if streaks reach 8, the K=8 lump sum fires and
   the ceiling can finally be tested under finite fuel.

## Disclosure (Rule 17 / 21)

- Diagnostic is read-only on the engine; all flags env-gated; no engine change. The 1e9 energy bank is a
  diagnostic isolation device (removes survival), disclosed; it does not affect the run metric `g_org_run`,
  which depends only on `net` (prediction quality).
- Scroll analysis and the per-tick `g_org_run` / `read_log` extraction are reproducible from the notebook
  cells; figure `max_run_7_root_cause.png` shows the sawtooth, the streak histogram (peak 7), and the
  47% mid-block / 53% boundary reset split.
