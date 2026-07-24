# Article_Draft.md — Rigorous Audit & Fix Proposal

> **Auditor:** Clusy Agent  
> **Date:** 2026-07-24  
> **Evidence base:** Exp 30 (14 arms), Exp 68 (8-seed controlled compositionality test),  
> `Docs/Ascent.md` (binding finish line), live engine code (`neuromorphic_engine.py` v2132).  
> **Stance:** Fatal-flaw-first. Each issue is graded 🔴 (fatal — sinks the paper if unaddressed),  
> 🟡 (serious — must fix before submission), or 🟢 (cosmetic — nice to have).  
> Every claim below is grounded in a tool result from this session — nothing is recalled from
> model memory.

---

## 🔴 F-1: The 70 % Compositionality Claim Is Scientifically Unsupported

**Where:** Lines describing Exp 30 Arm K — the article presents ~70 % "compositionality" as a
positive substrate result.

**Evidence (Exp 68, run 2026-07-24, 8 seeds × 80 k ticks/seed):**

| Metric | RULE (Latin square) | NULL (random answer) | Δ (RULE − NULL) |
|--------|:------------------:|:--------------------:|:----------------:|
| Mean accuracy | 63.0 % ± 9.4 | 70.2 % ± 9.6 | **−7.2 pp ± 16.6** |
| z-score | — | — | **−1.22 (n.s., p > 0.2)** |
| Refugium triggers | 37 k–50 k / 80 k ticks | 37 k–60 k / 80 k ticks | life-support regime |
| Seeds favouring RULE | 4/8 | 4/8 | coin-flip |

**The controlled test shows Δ ≈ 0 — no compositionality.** The prior 70 % was a measurement
artifact from three uncontrolled confounds, all now closed:

1. **Bigram shortcut (C3):** English text has peaked `P(next | current)` (e.g. q→u 99.8 %).
   Removing this (uniform 8-symbol alphabet, Latin-square `P(answer|cue)=uniform`) collapsed
   the apparent advantage.
2. **Positional-structure prediction (C2):** The original metric counted ALL next-byte
   predictions — most of the 70 % came from predicting the FIXED LINE FORMAT (cue → noise →
   cue → noise → answer) and the non-uniform noise marginal, not the compositional answer.
3. **Single seed + random table (C1):** Exp 30 Arm K used `random.choice(answers)` — a table
   with NO compositional rule. The only possible result is partial memorisation (CAM stores
   at most 32 of the 16 pairs). An 8-seed replication was never performed.

**Impact on paper:** If the paper goes to peer review claiming "70 % compositionality" without
the controlled condition, a reviewer familiar with shortcut-confounds will (correctly) reject
it. **Fix:** Either (a) remove the compositionality claim entirely and present only the STDP
ablation result, or (b) add the Exp 68 null result with an honest discussion of why the prior
70 % is now understood as an artifact. Option (a) is safer for the current version. [🔗 Exp 68
results: `exp68_shortcut_proof_results_overall.json`]

---

## 🔴 F-2: No "Adversarial Evaluation" Section — Only Positive Results

**Where:** Chapter 3 (Results) presents ONLY findings that confirm the substrate works.
There is no counterpart titled "Limitations" or "Negative Findings" or "Failure Modes."

**Evidence (multiple experiments from this session):**
- **Population collapse on maximum-entropy curricula (Exp 68 v1):** On a uniform-iid stream
  (every byte uniform over 8 symbols, 12.5 % chance per byte), the colony collapses to
  pop ≈ 7–14 with refugium firing ~50 % of ticks. The colony CANNOT survive without
  exploitable statistical regularity in its environment.
- **Reading-foraging behaviour (Exp 68 diagnostic):** Even on the constant-noise scaffold,
  the colony's read events are concentrated on structurally predictable positions (noise
  bytes) and sparse on the actual compositional answer positions (only 5 % of reads, vs
  14 % expected from uniform coverage).
- **Survivorship confound (all Exp 68 runs):** Zero extinctions is presented as a positive,
  but it is achieved only through the refugium, which fires ~50 % of ticks — meaning the
  colony never reaches a stable equilibrium.

**Impact on paper:** A results section with only positive findings is a sales pitch, not a
scientific paper. Every evolutionary-computation journal expects a "Failure Modes" or
"Limitations" subsection. **Fix:** Add §3.5 "Known Limitations" covering: (a) shortcut
dependency, (b) refugium confound, (c) single-task specialisation risk, (d) the CAM-32 slot
capacity cap.

---

## 🔴 F-3: Exp 60–67 Do NOT Meet the Published Ascent Criterion

**Where:** §4 "Discussion & Recent Empirical Ascents (Exp 60–67)" — the word "ascents" in the
title claims these experiments demonstrate ascent.

**Evidence (`Docs/Ascent.md` §2, binding since 2026-07-16):**
> Criterion A: `C(t)` monotone up ≥25 % over 5 M world-ticks.
> Criterion B: STDP-ablation shows learning is load-bearing.
> Criterion C: Efficiency non-decreasing.

**What Exp 60–67 actually show:** Zero extinctions, high throughput, sensor retention,
seasonal migration — all infrastructure validations. **None measures `C(t)` or shows a 25 %
rise.** Criterion B (learning load-bearing) IS supported by Exp 30 A/B/C, but that is already
in §3.2–3.3 — not a new achievement of Exp 60–67.

**Impact on paper:** Claiming "ascent" when the paper's own Ascent.md defines it differently
is an internal contradiction that a reviewer will spot immediately. The word "ascents" in the
section title is misleading. **Fix:** Rename to "Recent Infrastructure Milestones (Exp 60–67)"
and explicitly state that ascent (criterion A) is NOT yet met — these experiments validate
that the substrate runs stably, which is necessary but not sufficient.

---

## 🟡 S-1: Exp 30 Parameter Discoveries Not Documented

**Where:** §2 Design Principles lists only the original engine parameters. The findings of
Exp 30 (Homeostatic STDP, CAM v2 write-on-reward) are described qualitatively in §3 but
their **exact parameter values** never appear in a table.

**Required additions (per Rule 17 Category E):**

| Parameter | Default | Discovered | Justification |
|-----------|---------|------------|---------------|
| `HOMEOSTATIC_LAMBDA` | 0.01 | Exp 30 Arm C/D | Prevents STDP weight drift; restoring force toward DNA-birth weight. λ=0.01 gives drift-ceiling ≈10 % per lifetime at typical STDP rates. |
| `CAM_SLOTS` | 32 | Exp 30 Arm J | 32 slots sufficient for 4×4 (16 pair) compositionality; hard bound for 8×8 (64 pairs). |
| `CAM_MATCH_THRESHOLD` | 6 | Original engine | Number of bits that must match a CAM key. |
| `CAM_WRITE_THRESHOLD` | 3 | Exp 30 Arm F→J | CAM writes occur only on CORRECT prediction (reward-gated). |
| `STRUCTURAL_PLASTICITY` | 1 (on) | Exp 30 Arm N | Synaptic rewiring + pruning. `SP_MAX_GROWTH=2`. |

**Fix:** Add as Table IV in §3.3 or as an appendix.

---

## 🟡 S-2: Only 3 of 14 Exp 30 Arms Are Reported

**Where:** Table III shows only Arm A (STDP ON), Arm B (STDP OFF), Arm C (STDP_COSTONLY).

**Missing arms with informative results:**

| Arm | What | Finding |
|-----|------|---------|
| D | Homeostatic STDP, Easy WM | 67.6 % accuracy — drift fix confirmed |
| E | Hard_WM curriculum | 42.9 % vs 6.25 % chance — first proof of genuine working memory |
| G | DEPLETE + CAM v2 on Hard_WM | 16.8 % = 2.7× chance, bursts of 78 % — selective pressure works (learn or die) |
| J | CAM_SLOTS=32, scaled pop | 77 % — scaling validated |
| L, N | 8×8 compositionality w/wo Structural Plasticity | 72 % (L) / 72.7 % (N) — same result, SP doesn't help on 8×8 |

**Fix:** Either add the full arm table (Table IV) or add a note: "Full 14-arm results in
Supplementary Material." The current selective reporting creates an appearance of cherry-picking.

---

## 🟡 S-3: DEPLETE Is the Default but Never Documented

**Where:** Nowhere in §2 (Economy) or §3 (Results).

When `GENESIS_DEPLETE=1` (the default), reading draws from finite per-cell fuel
(`CELL_STATES = 256.0`) instead of unlimited income. This is the mechanism that creates
selective pressure (Exp 30 Arm G). Without documenting it, a reader cannot understand why
the colony doesn't simply read continuously — nor why the refugium exists (it refuels cells
when population drops below threshold).

**Fix:** Add a 2–3 sentence description in §2 with a reference to Exp 30 Arm G.

---

## 🟡 S-4: Write-on-Reward CAM (CAM v2) Semantics Are Missing

**Where:** §3.3 mentions CAM but not that CAM writes are gated on correct prediction.
This is a critical detail — it means CAM cannot learn from errors; it only consolidates
successes. This limits how quickly the substrate can adapt to novel patterns and creates a
"success-only bootstrap" problem.

**Fix:** Add: "CAM entries are written only on correct prediction (reward-gated write).
Incorrect predictions do not create new CAM associations — the organism must first land
a correct prediction by evolution+STDP alone, then CAM consolidates it for reuse."

---

## 🟡 S-5: Engine Version Stale (Claims to Reflect 2026-07-10; Current Is 2026-07-24)

**Where:** The header says "Status (2026-07-10)" but the engine has:
- `STRUCTURAL_PLASTICITY` default ON (line 153 of `neuromorphic_engine.py`)
- `CAM_SLOTS` = 32 (not 8)
- `HOMEOSTATIC_LAMBDA` = 0.01 (line 133)
- `DEPLETE` = 1 (not mentioned)
- Exp 34 REMAP mechanics (line 1644–1665)

**Fix:** Bump to 2026-07-24 and add a changelog footnote.

---

## 🟢 C-1: The "Future Work" Section Should Mention the Shortcut-Proof Bottleneck

**Where:** §4 ends with "the search has pivoted from shaping the market to designing the
learning rule." This is correct. A natural follow-up sentence: "A key open question is
whether the substrate can learn systematic (compositional) rules rather than exploit
statistical shortcuts — early controlled experiments suggest this is not yet the case
(Exp 68)."

---

## 🟢 C-2: Citation for Rule 16 (Archived Original)

**Where:** If the paper cites `RULES.md`, it should note which version. The original Rule 16
was archived per `Docs/FixedRules.md` footnote [9].

---

## Action Priority

1. 🔴 **F-1**: Decide on the compositionality claim — remove or add Exp 68 null result.
2. 🔴 **F-3**: Rename "ascents" to "milestones" and add explicit "ascent not yet met" statement.
3. 🔴 **F-2**: Add §3.5 "Known Limitations" with shortcut-dependency, refugium confound, CAM cap.
4. 🟡 **S-1, S-3, S-4, S-5**: Parameter documentation + DEPLETE + CAM v2 + version bump.
5. 🟡 **S-2**: Full Exp 30 arm table or supplementary reference.
6. 🟢 **C-1, C-2**: Cosmetic polish.

---

*This audit was produced by reading `Article_Draft.md` (22 kB, 226 lines) in full and cross-referencing
every claim against `exp68_shortcut_proof_results_overall.json`, `Docs/Ascent.md`, and the live
`neuromorphic_engine.py` source. No claim in this review is based on model memory — all numbers
are from tool results in the 2026-07-24 session.*
