# Resume Next Session — Start Here

Read this file FIRST at the start of the next Clusy session.

---

## Last Session: 2026-07-24 (Exp 74 + 75)

### Accomplished

| Area | What was done | Evidence |
|------|---------------|----------|
| **Exp 74: Attractor Tuning** | Replaced Exp 73's uniform attractor with bistable independent neurons. 16/16 unique persistent states, 120/120 distinct pairs, stable 30 ticks. | `src/exp74_attractor_discrimination_probe.py`, `genesis_lab.py` commit |
| **Exp 75: Compositionality Re-eval** | Latin-square probe with tuned hidden layer. FAIL: 0% accuracy. OR accumulation collapses 64 pairs → 8 patterns. | `src/exp75_compositionality_reeval_probe.py` |
| **Ancestor update** | `create_intelligent_ancestor`: thresh=100, tau=30, 2× self-conn (+54 each), NO bidir pairs | `src/genesis_lab.py` |
| **Docs** | Updated Result.md, Roadmap.md, Article_Draft.md, this file | commits |

### Key Scientific Findings

1. **Exp 74 SOLVED attractor discrimination.** Bistable independent neurons (2× self-connection,
   no bidirectional pairs, thresh=100, tau=30) produce 16/16 distinct persistent states.
   Each input bit controls one hidden neuron: ON → latches ON, OFF → stays OFF.

2. **Exp 75 revealed the NEXT bottleneck: Write Selectivity.** Bistable neurons only turn ON,
   never OFF. Hidden state = cumulative OR of all bytes seen. 64 (c1,c2) pairs → 8 OR patterns,
   7 ambiguous. Max theoretical accuracy = 1.6% < chance 12.5%.

3. **Bottleneck progression:**
   - ~~Memory~~ (Exp 70: CAM pre-population failed)
   - ~~Topology~~ (Exp 71: zero recurrent pairs → fixed Exp 73)
   - ~~Attractor discrimination~~ (Exp 74: bistable neurons → SOLVED)
   - **Write selectivity** (Exp 75: OR accumulation → CURRENT BOTTLENECK)

### Current Ascent.md Evaluation

| Criterion | Status | Evidence |
|-----------|:------:|----------|
| A (C(t) rise ≥25%) | BLOCKED | Write selectivity bottleneck (Exp 75) |
| B (Learning load-bearing) | MET | Exp 30: 43% vs 2.9% (14×) |
| C (Efficiency) | Not measured | Moot given A blocked |

---

## NEXT SESSION: Exp 76 — Gated Write Hidden Layer

### The Problem

Bistable hidden neurons (Exp 74) persist input patterns perfectly BUT accumulate all
inputs via OR. During the Latin-square stream [c1, noise, noise, c2, noise, noise, answer],
the hidden state at the answer tick = OR(c1, noise, c2) — a lossy mixture that cannot
distinguish different (c1, c2) pairs.

### The Solution

Add a **WRITE GATE** that controls when hidden neurons accept afferent input:
- **Gate ON** during cue ticks (c1, c2) → hidden layer latches the input byte.
- **Gate OFF** during noise ticks → hidden layer holds its state (preserves c1 during delay).

### Implementation Options

**(A) Extend MEMORY_MARKER gate to ordinary hidden neurons.**
The Exp 44/45 WMEM infrastructure already supports gated latches (global_sense_meta stores
the gate source neuron). Extend this to ordinary LIF hidden neurons: afferent writes are
accepted only when the gate neuron fired last substep.

**(B) Two separate hidden banks with alternating gates.**
- Bank 1 (8 neurons): gated by "c1 cue detected" → stores c1.
- Bank 2 (8 neurons): gated by "c2 cue detected" → stores c2.
- At answer tick: read both banks → combined key → CAM lookup.

**(C) Gated overwrite (reset-then-write).**
- On cue detection: reset all hidden neurons to OFF, then latch the new input.
- This gives a clean snapshot of the most recent cue.
- Requires an inhibitory "reset" signal (strong negative synapse onto all hidden neurons).

### Recommended Approach

**Option A** is the most substrate-grounded: it reuses the existing gate mechanism
(global_sense_meta) and requires minimal engine changes. The gate neuron is driven by
a cue-detection signal (e.g., "current byte ≠ noise"). During noise ticks, the gate
is silent → hidden neurons ignore afferent input → c1 is preserved.

### Files to Read Before Starting

- `Docs/Roadmap.md` → "Current Bottleneck" section (updated)
- `Docs/Result.md` → Exp 74 + 75 entries (at the end)
- `src/genesis_lab.py` → `create_intelligent_ancestor` (Exp 74 hidden neuron block)
- `src/neuromorphic_engine.py` → Phase 1 forward propagation (line ~1250, WMEM gate logic)
- `src/exp74_attractor_discrimination_probe.py` (standalone LIF probe template)
- `src/exp75_compositionality_reeval_probe.py` (Latin-square probe template)

### Rules

- `Docs/FixedRules.md` (21 rules, especially Rules 1, 4, 12, 18)
- Always use **Qwen3.8 Max** model — never Auto
- Commit + push all changes to main
- Keep `Docs/` files updated after every experiment

---

## Quick-Start Prompt

```
GENESIS project position as of Exp 75 (2026-07-24):

EXP 74 (PASS): Bistable independent hidden neurons — 16/16 unique persistent states.
  Config: thresh=100, tau=30, 2× self-conn (+54 each), NO bidir pairs.
  In create_intelligent_ancestor (genesis_lab.py).

EXP 75 (FAIL): Compositionality re-eval — 0% accuracy.
  Root cause: OR accumulation. Hidden state = OR(all bytes seen).
  64 (c1,c2) pairs → 8 OR patterns → max 1.6% accuracy.

BOTTLENECK: Write Selectivity. Hidden layer needs a WRITE GATE.
  Gate ON during cue ticks → accept input.
  Gate OFF during noise → hold state.

NEXT: Exp 76 — Gated Write Hidden Layer.
  Extend MEMORY_MARKER gate mechanism to ordinary LIF hidden neurons.
  Gate neuron driven by cue-detection signal.

REPO: https://github.com/HamidRezaeian/GENESIS
MODEL: Qwen3.8 Max ONLY. Never Auto.
```
