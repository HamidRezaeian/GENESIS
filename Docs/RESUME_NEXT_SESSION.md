# Resume Next Session — Start Here

Read this file FIRST at the start of the next Clusy session. It tells you exactly where the project
stands and what the next step is.

---

## Last Session: 2026-07-24 (Clusy Agent, ~8 hours)

### Accomplished

| Area | What was done | Evidence |
|------|---------------|----------|
| Rules audit | Analysed `Q.md`, `Rules1.md`, `Rules2.md` — identified missing Rules 2, 3, 16, 19 | `Docs/FixedRules.md` (21 rules + footnotes) |
| Article audit | Read `Article_Draft.md` — identified 3 fatal flaws (F-1: compositionality claim unsupported, F-2: no limitations section, F-3: Exp 60-67 ≠ ascent) | `Docs/Article_Draft_Review.md` |
| Article fix | Revised article with Exp 68 null result (§3.4), Known Limitations (§3.5), full Exp 30 table, parameter appendix | `Article_Draft.md` (commit `fc430ea`) |
| Docs update | `Roadmap.md` + `Result.md` — added Exp 68 entry, current status, Ascent.md evaluation | commits `a216c26` |
| **cam_write dead function** | `cam_write()` was defined (line 553) but NEVER called. Wired it on correct stationary reads (type 1) and correct jump-predicts (type 3). Gated with `if CAM:` | commit `5d19411` |
| **CAM_KEY_BITS** | Extended CAM key from 1 byte (8 bits) to configurable width (8/24-bit). `cam_read`, `cam_write` now accept `byte0, byte1, byte2` for 3-byte context. CAM_MATCH_THRESHOLD scales with key width. Backward compatible (default 8). | commits `e871760`, `b826b9b`, `ce6fb4d` |
| CAM diagnostic | With CAM_KEY_BITS=24, CAM stores 832 three-byte entries like `'Dea'->'a'` (trigram context). CAM is working. | diagnostic cell |

### Key Scientific Findings

1. **Exp 68: Compositionality is NOT real** under controlled, shortcut-proof conditions. 8 seeds × 80k ticks: RULE vs NULL, Δ = −7.2pp ± 16.6, z = −1.22 (n.s.). The prior ~70% was a measurement artifact (structural position + bigram shortcut + single seed).

2. **Shortcut-free curricula are NON-VIABLE.** The refugium fires ~50% of ticks; population stabilises at 20–24 (down from 300). The colony survives only by exploiting statistical regularity — removing the shortcuts removes the survival gradient.

3. **cam_write was a dead function** — it was defined but never called. Now wired on correct predictions. Result: 3018 CAM slots filled after 50k ticks (all noise→noise bigrams with 8-bit keys).

4. **1-byte CAM key is a fundamental limitation.** The noise byte 'a' appears at positions 2 and 5 in the period-7 stream, producing identical keys but requiring different predictions (c2 vs answer). CAM_KEY_BITS=24 fixes this by encoding 3 bytes of context.

5. **CAM_KEY_BITS=24 compiles and runs** (proven: `KEYS=(600,32,24)`), but CAM=1 with 24-bit keys causes 0% accuracy (bug in CAM read comparison with zero-filled bits). The fix needs deeper debugging: the CAM match threshold should be proportional to the actual non-zero bit count, or the key encoding should use a sentinel bit structure. **Deferred to next session.**

### Current Ascent.md Evaluation (from Roadmap.md)

| Criterion | Status | Evidence |
|-----------|:------:|----------|
| **A** — `C(t)` rise ≥25% over 5M ticks | ❌ NOT met | No compositionality → unlikely on current substrate |
| **B** — Learning load-bearing | ✅ MET | Exp 30 A/B/C: 43% vs 2.9% (14×) |
| **C** — Efficiency non-decreasing | ⏳ Not measured | — |

### Files Changed This Session

- `src/neuromorphic_engine.py` — cam_write wiring, CAM_KEY_BITS, CAM_MATCH_THRESHOLD scaling
- `src/genesis_lab.py` — CAM_KEY_BITS import, g_cam_keys allocation
- `Docs/FixedRules.md` — new (21 rules + footnotes)
- `Docs/Article_Draft_Review.md` — new (full audit)
- `Docs/Article_Draft.md` — revised with Exp 68 null result, limitations, Figure 1, parameter appendix
- `Docs/Result.md` — Exp 68 entry added
- `Docs/Roadmap.md` — current status section added

### Exp 69 (2026-07-24): Phased Curriculum — Null Result

**Finding:** Adding survival padding ('a' runs) between probes destroys answer-byte prediction ability
(0% answer accuracy across all seeds). The substrate's predictor converges to always predicting the
most frequent byte ('a'), and never learns to predict uppercase answer bytes. This confirms the
catch-22 as a structural limitation of the substrate, not just a curriculum design issue.

**Ascent.md update:** Criterion A (capability rise ≥25%) is now FAILED. No compositionality under any
viable curriculum. The substrate fails to demonstrate the primary ascent criterion.

### Open Problems

1. **Compositionality catch-22 is CONFIRMED as a structural limitation.** Probe-only: colony starves
   (pop~23). Survival-padded: answer prediction = 0%. These are not separate problems — they are the
   same problem viewed from two angles. The substrate's prediction mechanism (first-order Markov) is
   fundamentally incompatible with compositionality testing.

2. **Ascent Criterion A is FAILED.** The project's primary metric shows no capability rise. Exp 68
   and 69 together demonstrate that compositionality is absent under any controlled condition.


1. **CAM_KEY_BITS=24: 0% accuracy bug** — when CAM=1 and KEY_BITS=24, all correct_reads are 0 despite colony surviving. Likely cause: false CAM match from zero-filled high-order bits in the 24-bit key. Fix option: use CAM_MATCH_THRESHOLD proportionally scaled OR add a sentinel bit in the key encoding that prevents empty slots from matching.

2. **Population viability on hard curricula** — the fundamental catch-22. Shortcut-free curricula collapse the colony because reading income drops below survival threshold. The refugium masks this by firing ~50% of ticks.

3. **ARD.md and PRD.md are stale** — last updated 2026-07-10, before Homeostatic STDP, CAM v2, DEPLETE, STRUCTURAL_PLASTICITY, and CAM_KEY_BITS.

---

## Next Experiment: Phased Curriculum Design

**Hypothesis:** A curriculum where EXPLOITABLE material provides baseline reading income (keeping the colony viable) while SHORTCUT-PROOF compositionality probes are interleaved and measured separately will decouple survival from the compositionality test.

**Design sketch:**
- **Survival stream** (80% of bytes): predictable structure (e.g., repeated runs of constant 'a' + simple letter sequences) — gives ~100% accuracy → enough reading income → colony stays at pop ≈ 300.
- **Compositionality probes** (20% of bytes): interleaved at regular intervals. Format: `[c1 a a c2 a a A]` where answers are uppercase (for tagged measurement) and Latin-square rule (shortcut-proof).
- **Measurement:** answer-byte-specific accuracy using uppercase/read_log classification (same as Exp 68 tagged mode). Survival-stream accuracy is measured separately.
- **Multi-seed:** 5+ seeds.

**Files to read before starting:**
- `Docs/Roadmap.md` (last section → Current Status)
- `Docs/Result.md` (last entry → Exp 68)
- `src/exp68_shortcut_proof_compositionality_probe.py` (template for the phase curriculum probe)
- **This file** (`Docs/RESUME_NEXT_SESSION.md`)

**Rules to follow:**
- `Docs/FixedRules.md` (especially Rules 2, 3, 10, 14, 18, 19, 20)
- Always use **Qwen3.8 Max** model — never switch to Auto
- Commit + push all changes to main
- Keep `Docs/` files updated (especially `Result.md`, `Roadmap.md`, `Article_Draft.md`)

---



## ⚠️ CRITICAL: GitHub Token

**Before the next session, DO THIS FIRST:**
1. Go to github.com → Settings → Developer settings → Personal access tokens
2. DELETE the old token (it was exposed in chat)
3. Create a NEW token with scope 
4. Send the NEW token in your FIRST message of the next session

The token is needed for . Without it, commits stay local.

## Quick-Start Prompt

Copy this into the next session's first message (after the agent introduces itself):

```
GENESIS project position as of previous session:

EXP 68 (closed): RULE vs NULL compositionality test — Null result (Δ=−7.2pp, z=−1.22).
The prior 70% compositionality was a structure + bigram artifact.

ARCHITECTURE FIXES applied and on main:
1. cam_write() wired (was a dead function) — commit 5d19411
2. CAM_KEY_BITS configurable (8/24-bit, backward compat) — commit e871760
3. CAM_MATCH_THRESHOLD scales with key width — commit b826b9b

CAM_KEY_BITS=24: compiles but 0% accuracy bug needs debugging (false CAM match).

OPEN BOTTLENECK (next step): phased curriculum design.
Design a curriculum where 80% of bytes are exploitable structure (survival income)
and 20% are shortcut-proof compositionality probes interleaved at regular intervals.
Measure answer-byte-specific accuracy SEPARATELY on probe bytes (uppercase tagging).
Multi-seed (5+ seeds). This decouples survival viability from the compositionality test.

PENDING DOCS: ARD.md and PRD.md are stale (2026-07-10).
ALL RULES: Docs/FixedRules.md.

GITHUB TOKEN: [SEND NEW TOKEN IN FIRST MESSAGE]
REPO: https://github.com/HamidRezaeian/GENESIS
GITHUB TOKEN: [SEND NEW TOKEN IN FIRST MESSAGE]
MODEL: Qwen3.8 Max ONLY. Never Auto.
```
