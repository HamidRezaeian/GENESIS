# Nonstationary Variants Protocol — Attacking the Memorization Gap in Substrate 4

**Status: PRE-REGISTERED (binding) — 2026-08-06. Every variant's success criterion and both
hypothesis-predictions are fixed HERE before any run (Rule 2). Shortcut accountability per
Rule 20 applies to every positive claim: each variant ships with its own NULL control.**

**Protocol ID:** `SUBSTRATE_4_NONSTATIONARY_VARIANTS_v1`
**Base:** `SUBSTRATE_4_EXTENDED_20K_v1`. **The substrate, update rule, LR, seeds [0,1,2,3],
cohort size, and metric definitions are IDENTICAL across all variants. Only the data stream
changes.** All variants run at 20k ticks, LEARN + NOLEARN arms, REPORT_EVERY = 1000.

---

## 1. The gap being attacked

Evidence that Substrate 4's gain is **memorizing a fixed 500-byte patch**, not general
sequence learning:

| Run (20k, 4 seeds) | In-lifetime delta | Late acc | Gap vs NOLEARN |
|---|---|---|---|
| Static patch (`sub4_20k_summary.json`) | +3.70pp | **89.9%** | +39.97pp |
| Nonstationary task | +3.13pp | **70.7%** | +21.48pp |
| Novel sequence (A→B) | +2.31pp | **74.7%** | +25.73pp |

Moving from a static to a nonstationary/novel stream costs ~19–15pp of late accuracy while the
in-lifetime delta barely moves — the signature of a learner whose advantage is *content-specific
storage* (W_head / tok_embed rows converging to the patch's local statistics), which evaporates
when the content stops holding still. The substrate question Rule 18 cares about is whether
in-lifetime learning is **load-bearing and general**; these variants discriminate the two
mechanisms directly.

**Standing predictions (fixed before any run):**
- **If memorization dominates:** variants that perturb content (V1, V2, V4–V8) degrade accuracy
  toward the NOLEARN floor (~50% bit-acc) in proportion to how much they break exact-content
  storage; only V3 (bigger static corpus) preserves most of the gain.
- **If generalization dominates:** late accuracy stays ≥ 80–85% across variants, because the
  head learns *portable* byte-level structure (local n-gram / syntactic statistics) that
  transfers across content.

## 2. Common protocol and cost

Per variant: 20k ticks × 4 seeds × 2 arms = 8 runs ≈ **35 min serial** / **~5 min on 8 cores**
(measured 77.5 / 102.6 ticks/s). Full suite ≈ **4.7 h serial, ~40 min parallel**. Every variant
reports the frozen metrics: early (mean of windows 1–3), late (mean of last 3 windows),
in-lifetime delta, gap vs its NOLEARN arm. "Floor" below = the NOLEARN late mean (~50%).

Suite-level decision rule (pre-committed): **≥ 5/8 variants pass** their criteria →
generalization signature; substrate justifies scale-up and the staged pilot proceeds.
**≤ 2/8 pass** → memorization confirmed as the dominant mechanism; per Rule 18's kill-criterion
logic the substrate hypothesis pivots (bigger capacity / recurrent state / different update
rule), not longer runs.

---

## 3. The variants

### V1 — Rotating patches
- **Change:** the 500-byte patch is replaced with a fresh patch (different book/category draw)
  every **5,000 ticks** (4 patches per run). Cursor positions persist across rotation.
- **Hypothesis:** does adaptation *accelerate* with experience (meta-learning / portable
  structure) or restart from scratch each time (pure re-memorization)?
- **Success criterion:** recovery to ≥ 85% window accuracy takes **≤ 2,000 ticks after
  rotations 2 and 3**, i.e. faster than the initial ~4k-tick climb.
- **If memorization:** each rotation reproduces the same ~3–4k-tick re-climb; sawtooth with
  constant period and amplitude ≈ the full early→late delta.
- **If generalization:** recovery time shrinks across rotations (4k → ≤2k); post-rotation
  floors rise.

### V2 — Multi-patch mixture
- **Change:** 8 distinct patches coexist; each organism's cursor teleports to a random patch
  with p = 0.1 per tick (uniform mixture).
- **Hypothesis:** can ~25k params hold 4,000 bytes of content, and does learning aggregate
  cross-patch structure?
- **Success criterion:** late acc ≥ **85%** (static reference: 89.9%).
- **If memorization:** capacity binds — late acc ≤ ~75%, with `norm_w` saturating early and
  per-patch accuracy anti-correlated with patch visitation frequency.
- **If generalization:** ≥ 85%, because the shared byte statistics dominate and are
  content-independent.

### V3 — Patch-size scaling (control variant)
- **Change:** PATCH_SIZE ∈ {500, 5,000, 50,000} (three sub-runs), single patch per run.
- **Hypothesis:** separates "memorize this string" from "learn this distribution": a
  memorizer degrades as content exceeds storage; a distribution-learner is size-invariant
  (bigger sample of the same statistics).
- **Success criterion:** late acc ≥ **85% at all three sizes**.
- **If memorization:** ~90% → < 80% → < 70% across sizes.
- **If generalization:** flat within noise (±3pp). This is the variant expected to pass even
  under memorization-adjacent behavior — it is the suite's internal sanity check. If V3 fails
  AND V2 passes, the model is distribution-learning but interference-limited; interpret the
  suite accordingly.

### V4 — Hierarchical / compositional patches
- **Change:** patches are generated from a small compositional grammar — 8 sentence templates
  × 32 slot-fillers (256 unique sentences). Train stream draws from a **held-in 224-sentence
  subset**; every 5th evaluation window is scored on a stream of the **32 held-out
  recombinations** (same templates and fillers, novel combinations).
- **Hypothesis:** does the learner acquire the *compositional* structure (template + slot
  statistics) or the *sentences*?
- **Success criterion:** held-out recombination accuracy within **5pp** of seen-sentence
  accuracy in the late windows.
- **If memorization:** held-out ≈ floor (the recombinations were never stored).
- **If generalization:** held-out ≈ seen − ≤5pp (template/slot statistics transfer).
- **Rule 20 NULL:** a marginal-matched control stream (same byte histogram, shuffled
  bigram structure) must NOT show the seen/held-out gap closing — otherwise the gap is a
  marginal artifact, not compositionality.

### V5 — Transfer test (A → B, frozen)
- **Change:** train LEARN 20k on patch A as usual; then freeze all weights and evaluate
  **without learning** for 2k ticks on an unseen patch B from a different category.
- **Hypothesis:** the cleanest possible memorization test — frozen weights on novel content.
- **Success criterion:** frozen transfer acc ≥ **65%** (midway between floor ~50% and static
  90%).
- **If memorization:** ≈ 50–55% (only unigram byte frequencies transfer).
- **If generalization:** ≥ 65% (n-gram/syntactic structure transfers).
- **Rule 20 NULL:** also evaluate frozen on a **byte-shuffled** B (same marginals, destroyed
  structure). Transfer(B) − Transfer(shuffled B) isolates the structural component; a claim of
  generalization requires this delta > 10pp.

### V6 — Adversarial mutation
- **Change:** every 1,000 ticks, **5% of patch bytes are replaced** in place (uniform random
  bytes). Content drifts incrementally rather than rotating wholesale; length and rough
  marginals are preserved.
- **Hypothesis:** does the learner *track* drifting content (online adaptation) or accumulate
  stale memory?
- **Success criterion:** after each mutation, recovery to ≥ 85% within **500 ticks**, and
  cumulative late-acc degradation < 5pp by 20k.
- **If memorization:** monotonic accumulation of stale content — sawtooth that never fully
  recovers, cumulative loss > 10pp.
- **If generalization:** mutation barely dents accuracy (the mutated bytes are a small
  perturbation of the learned statistics).

### V7 — Continuous drift sweep
- **Change:** every tick, each patch byte mutates independently with probability p ∈
  {1/2000 (slow), 1/200 (fast)}. Two sub-runs.
- **Hypothesis:** measures the substrate's **tracking bandwidth** — the drift rate at which
  in-lifetime learning stays load-bearing.
- **Success criterion:** slow drift: late acc ≥ **80%**; fast drift: late acc ≥ **65%** AND
  still > 3pp above its NOLEARN arm (Gate B survives drift).
- **If memorization:** fast drift collapses acc to within ~5pp of floor (re-memorization
  cannot keep up); slow drift partially preserves it.
- **If generalization:** both hold above their lines; degradation slow→fast is graceful.

### V8 — Retention after rotation (catastrophic forgetting)
- **Change:** train 10k on patch A → rotate to patch B for 10k → freeze → re-test on A for
  1k ticks without learning.
- **Hypothesis:** does new learning **overwrite** old content (the current update rule writes
  W_head and tok_embed rows per observed byte — an overwriting substrate forgets)?
- **Success criterion:** retention ≥ **70%** of the pre-rotation A accuracy (i.e. A-retest ≥
  ~0.7 × 90% ≈ 63% bit-acc).
- **If memorization-with-overwrite:** A-retest ≈ floor (~50%) — A's rows were overwritten by B.
- **If generalization with stable representations:** retention ≥ 70%.
- **Rule 20 NULL:** re-test on a *third*, never-seen patch C must score ≤ the A-retest (if C ≈
  A-retest, "retention" is just generic byte statistics, not retained content).

## 4. Execution order and accounting

Cheapest-to-run first, highest-information first: **V5, V8** (frozen-eval probes; directly
quantify storage-vs-structure) → **V1, V6, V7** (tracking family) → **V2, V3** (capacity
family) → **V4** (compositionality; most engineering). V5+V8 alone (~70 min serial) already
yield the decisive memorization-vs-generalization bit; the rest refine *which* generalization
fails.

Every variant driver records: this protocol ID, git SHA, seed set, and its pre-registered
thresholds copied verbatim into the output JSON (Rule 2 hygiene — the criteria travel with
the data). No variant may be re-thresholded after its first run; a failed criterion is a
result, not a draft.
