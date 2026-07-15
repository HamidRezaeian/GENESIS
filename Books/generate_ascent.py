"""
generate_ascent.py — emit Books/English/00_Ascent.txt, the COGNITIVE-COMPLEXITY gradient
curriculum for Experiment 20.

WHY (Result Exp 12-19): every prior curriculum (incl. 00_Graded) ramps difficulty by RUN-LENGTH
only (AAAA...->ABAB...). Even its hardest section (run=1, "ABCDEFGHIJ" cycling) is a fixed loop an
organism solves by MEMORISING a lookup — no symbol's value must be COMPUTED from context. That is
why reading plateaus: the task is reflex-solvable, so minds stay simple (Exp 19's root cause of the
peer plateau too). 00_Ascent ramps COGNITIVE COMPLEXITY: predicting the next symbol progressively
requires more COMPUTATION OVER PRIOR CONTEXT held in the SNN's own recurrent state (working memory).
Reading pays for predicting pos+1 (the UNSENSED next cell; Exp 12) and an organism senses only the
CURRENT cell, so a computed next-symbol can ONLY come from a mind that carries context — the
brain-like computation the whole project chases.

DESIGN — ONE MONOTONIC 6000-BYTE SCROLL (fixes the Exp 20 first-iteration cliff). The engine lays the
book as a contiguous scroll of BOOK_TARGET_BYTES glyphs, TILING a short file to fill it. A short
ramp tiled 5x resets easy->hard->easy 5x and (first attempt) left ~77% of the standing scroll as the
hard tail -> a COLD colony could not bootstrap (pop->refuge floor, reads=0, the known Exp 12/17 cold
cliff). Instead this emits a book sized to the whole scroll so difficulty rises ONCE, end to end:
  - a BOOTSTRAP-DOMINANT head of long low-change runs, so a cold random colony ignites reading
    (echo-a-run is already a correct next-symbol predictor there — the Exp 12/17 foothold), then
  - a smooth ramp into computation as a CLIMBABLE FRONTIER (Rule 10): the saccade-walker cannot camp
    (Exp 13) and advances +1 only on a correct prediction, so it grazes forward INTO harder text and
    piles up at the easy->hard boundary; only a mind that cracks the next stage advances and eats
    fresh scroll. Frontier position over deep time = a direct ascent read.

STAGES (easy -> hard), each a COMPRESSIBLE rule (the Exp 19 redirect: learning the rule out-earns
memorising the loop, so computing is the cheaper long-run strategy = what selects for it):
  BOOTSTRAP   long shrinking runs over A..J       reflex / echo-a-run          (survival foothold)
  SUCCESSOR   cyclic increment A..Z / 0..9        learn "+1" (one rule)        (first computation)
  CARRY       two-digit counting 00..99           "+1 with carry" over 2 cells (working memory)
  ARITHMETIC  a+b=c facts (compute over context)  add mod 10 from held operands(deepest demand)
Budgets are bootstrap-heavy so ignition is guaranteed; the computational tail is the minority
frontier. Only printable ASCII 32..126 is emitted (matches the engine's injection filter, so on-disk
length == in-RAM glyph count and the ramp's spatial proportions are exact).
"""

# Total scroll size — match genesis_lab BOOK_TARGET_BYTES (default 6000) so the book fills the scroll
# in ONE pass (no tiling, no easy->hard reset).
TARGET = 6000
# Fraction budgets across the ramp (sum ~1.0). Bootstrap-DOMINANT so a cold colony ignites; the
# computational stages are the climbable minority frontier.
FRAC = {"bootstrap": 0.55, "successor": 0.20, "carry": 0.12, "arithmetic": 0.13}


def _fill(pattern, budget):
    """Tile `pattern` (a same-difficulty motif) up to `budget` glyphs. Tiling WITHIN a stage repeats
    one difficulty level (no ramp reset); the ramp lives BETWEEN stages."""
    if not pattern or budget <= 0:
        return ""
    reps = (budget // len(pattern)) + 1
    return (pattern * reps)[:budget]


def stage_bootstrap(budget):
    # Long shrinking runs over A..J. Weighted toward LONG runs (16/12/10/8) so most of the head is
    # low-change — the big foothold a cold colony needs (the first-iteration cliff came from too small
    # a foothold). The shrinking tail (6/4/3/2) starts demanding real sequence-tracking, easing into
    # the successor stage.
    letters = "ABCDEFGHIJ"
    ramp = []
    for run in (16, 12, 10, 8, 6, 4, 3, 2):
        for c in letters:
            ramp.append(c * run)
    return _fill("".join(ramp), budget)


def stage_successor(budget):
    # Long cyclic increment over the full alphabet and digits. Predicting the next glyph = apply the
    # successor rule; the cycles are long enough that learning "+1" beats a per-position lookup
    # (compressible complexity). Adjacent glyphs are bit-similar, so this is the GENTLE first rung of
    # real computation above the runs.
    return _fill("ABCDEFGHIJKLMNOPQRSTUVWXYZ" + "0123456789", budget)


def stage_carry(budget):
    # Two-digit counting 00 01 02 ... 99 (no separators). The TENS glyph advances only when UNITS
    # wraps 9->0, so predicting the next glyph requires REMEMBERING the previous one across a cell =
    # genuine working memory / carry, unsolvable by any memoryless successor reflex.
    return _fill("".join(f"{n:02d}" for n in range(100)), budget)


def stage_arithmetic(budget):
    # Single-digit addition facts "a+b=c " with wrap so c stays one glyph (mod 10). Standing on '=',
    # predicting c requires having COMPUTED a+b from operands sensed cells earlier and held in state —
    # the deepest working-memory-plus-computation demand. Rule-regular so "add mod 10" GENERALISES
    # across every fact (a rule to learn, not a table to memorise). '=' (0x3D) -> a digit is
    # bit-distant, so an echo reflex scores badly here: only actually computing earns.
    facts = "".join(f"{a}+{b}={(a + b) % 10} " for a in range(10) for b in range(10))
    return _fill(facts, budget)


def build(target=TARGET):
    parts = [
        stage_bootstrap(int(target * FRAC["bootstrap"])),
        stage_successor(int(target * FRAC["successor"])),
        stage_carry(int(target * FRAC["carry"])),
        stage_arithmetic(int(target * FRAC["arithmetic"])),
    ]
    text = "".join(parts)
    text = "".join(ch for ch in text if 32 <= ord(ch) <= 126)
    return text, [len(p) for p in parts]


if __name__ == "__main__":
    import os
    text, sizes = build()
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "English", "00_Ascent.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    b, s, c, a = sizes
    print(f"wrote {out_path}")
    print(f"total glyphs={len(text)} (target {TARGET})  "
          f"bootstrap={b} ({b/len(text):.0%}) successor={s} carry={c} arithmetic={a}")
