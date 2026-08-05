# Per-Organism Reservoir + Readout — Exp 103b Design (Pre-Registered)

**Status:** DESIGN — approved; implementation NOT started. This document recreates
the Exp 103b design doc that was approved in the previous session (commit `bca29fe`,
never pushed, lost when the session closed). Recreated verbatim-in-substance from the
approved 10-point spec on 2026-08-05. Implementation begins only after explicit
approval.

**Date:** 2026-08-05
**Protocol:** EXP103B_PER_ORG_RESERVOIR_v1
**Branch:** `feature/reservoir-readout` (this doc lives on the session branch
`arena/019fd11f-genesis`, at the branch tip `8b7d257` = merge of PR #12 / `5f0a035`)
**Parent design:** `Docs/Architecture/Next_Substrate_Design.md` (Exp 103, global reservoir)
**Predecessor result:** Exp 103 executed — `RESERVOIR_HELPS_STATICALLY_BUT_INRUN_LEARNING_WEAK`

---

## 0. Motivation (why per-organism, from Exp 103's executed verdict)

Exp 103 (`EXP103_RESERVOIR_READOUT_v1`, executed on this branch) ran ONE shared
reservoir + ONE shared readout against a single driver-side cursor over the 500-byte
patch. Measured (4 seeds × 20k ticks, `experiments/exp103_results/`):

| Metric | Exp 103 (global) |
|---|---|
| LEARNER late − early (Δ) | **+0.06 pp** (criterion 1 FAIL) |
| LEARNER late − NOLEARN late | **+10.35 pp** (criterion 2 PASS) |
| Monotonic decline | none (criterion 3 PASS) |
| Verdict | `RESERVOIR_HELPS_STATICALLY_BUT_INRUN_LEARNING_WEAK` |

The global reservoir confers a large **static** advantage but its in-run learning
**saturates**: every organism shares one input stream (a single cursor around a
fixed 500-byte sequence), so the readout converges to the best linear predictor of
that one stream (~78%) and stops improving.

**Exp 103b hypothesis:** make the reservoir and readout **per-organism**. Each
organism reads at **its own** patch position, which is **time-varying** as it
saccades along the scroll. A per-organism readout therefore faces a non-stationary
input stream, error stays > 0, and NLMS keeps adapting through tick 20,000 —
**continuous learning, no saturation** (binding prediction, §9).

---

## 1. Architecture

### 1.1 New per-organism state in `src/genesis_lab.py`

Two per-organism persistent arrays (allocated once, module globals, same pattern as
`g_cam_*` / `g_conn_w_slow`):

```
g_reservoir_state_po = np.zeros((MAX_ORGANISMS, RESERVOIR_N),     dtype=np.float32)  # [org, 256]
g_readout_w_po       = np.zeros((MAX_ORGANISMS, 8, RESERVOIR_N),  dtype=np.float32)  # [org, 8, 256]
```

- `reservoir_state_po[org]` — organism `org`'s private echo-state vector (256 floats).
- `readout_w_po[org]` — organism `org`'s private linear readout (8 output bits × 256
  reservoir units). Unlike the global `g_readout_w[N_OUTPUT, 256]`, the per-organism
  readout is exactly `[8, 256]` — only the 8 prediction bits, no motor rows.
- **Shared, not per-organism:** the fixed recurrent topology `g_reservoir_src / dst /
  weight` (one sparse Dale 80/20 connectivity draw, seed 42, spectral-scaled ~0.9).
  Recurrent weights are fixed forever; **all adaptation lives in the per-organism
  readout** (§4).

Memory: `(600, 256)` = 0.6 MB and `(600, 8, 256)` = 4.9 MB at the default
`MAX_ORGANISMS=600` (0.5 MB + 4.0 MB at the exp103-pinned 512). The 60-organism
frozen cohort uses rows 0..59. Negligible against the existing multi-MB arena.

### 1.2 Threading into `world_tick_numba`

Both arrays are added to the `world_tick_numba` signature as new trailing kernel
arguments (same precedent as `g_cam_*`, `g_conn_w_slow`, and the Exp-103 global
reservoir arrays: always passed, **only touched under the compile-time flag**, so
flag-OFF behaviour is byte-identical by construction).

Inside the per-organism loop, at the organism's **read/predict event** — where the
kernel computes `nxt = pos + 1`, `next_byte = ram_substrate[nxt]` and gates the
prediction block on a printable patch byte (`32 <= next_byte <= 126`) — call the
**existing, already-verified** `reservoir_step()` njit function with the organism's
row views:

```
pred_byte, err_sum = reservoir_step(
    g_reservoir_state_po[org], g_reservoir_src, g_reservoir_dst, g_reservoir_weight,
    g_readout_w_po[org], n_syn,
    in_byte, tgt_byte, RESERVOIR_N, RESERVOIR_TAU, READOUT_LR, 8, 0)
```

where `in_byte = ram_substrate[pos]` (the byte at the organism's current patch
position), `tgt_byte = next_byte`, `vocal0 = 0` (the per-organism readout's 8 rows
are exactly bits 0..7), and `READOUT_LR` is the module-global learning rate
(`GENESIS_READOUT_LR`, default `0.01`). The returned `pred_byte` is stored to a
small per-organism buffer `g_po_pred_byte` (`(MAX_ORGANISMS,)` uint8) so the driver
measures **exactly** the prediction the kernel made (pre-update), not a
driver-side recomputation.

No coupling into the brain: the reservoir is an observer/predictor running in
parallel. Its prediction does not alter the SNN reward, movement, or income
(substrate untouched); the only interaction is the honest Rule-21 energy charge (§10).

---

## 2. I/O

- **Input:** `in_byte` = the 8-bit byte read at the organism's patch position
  (`ram_substrate[pos]`, the cell underfoot — the same byte the reading eye senses).
  **Time-varying:** the organism saccades along the scroll as it predicts, so its
  position — and therefore its input byte — changes over time.
- **Output:** 8-bit prediction `pred_byte` via the linear readout
  `pred_k = readout_w_po[org][k] · reservoir_state_po[org]`, bit set when `pred_k > 0.5`.
- **Error:** per-bit `err_k = tgt_bit_k − pred_k` (continuous, in [−1, +1]), where
  `tgt_byte = ram_substrate[nxt]` is the NEXT patch byte (the economy's existing
  prediction target). The readout learns from the signed error (directional
  gradient), never from a reward signal — this is what fixes self-silencing (parent
  design §3.3).

---

## 3. Learning — Normalized LMS (NLMS)

```
Δw = lr · err · x / (||x||² + ε)          lr = 0.01, ε = 1e-8
```

- Applied to the organism's own readout rows, **only when that organism reads**
  (its read/predict event fires; dead or non-reading organisms are untouched).
- NLMS (not raw LMS) is carried over from Exp 103 unchanged: raw LMS diverged to NaN
  on correlated echo-state features; NLMS is a magnitude-invariance correction, NOT
  a tuning change — `lr` stays the pre-registered 0.01 (Rule 16 / Rule 17; disclosed
  in `Docs/Result.md` Exp 103 section).

---

## 4. Reservoir

- Leaky echo-state network, **per organism**, pre-registered defaults — identical to
  Exp 103, NO tuning (Rule 16): size **256**, sparsity **0.1**, E/I **0.8** (Dale's
  80/20 split), τ = **20.0**, spectral scaling ≈ 0.9.
- **Fixed recurrent weights, all adaptation in the readout:** the shared topology is
  drawn once (seed 42) and never mutated. Per-organism state dynamics (exactly the
  verified `reservoir_step()` body):

```
net[i]   = in_bits[i] + Σ_j W[i, j]·state[j]          (input injected on units 0..7)
state[i] = (1 − 1/τ)·state[i] + (1/τ)·tanh(net[i])    (leaky integrate)
```

---

## 5. Integration flag — `GENESIS_RESERVOIR_PER_ORG`

- New environment flag, **default `0`**:
  - Flag OFF → byte-identical to the current verified kernel. The new arrays are
    passed but never read; the per-organism block is a compile-time branch,
    dead-code-eliminated (same pattern as every other flag in the kernel; the Exp-103
    global reservoir args are already inert-by-default precedent).
  - Flag ON → `reservoir_step()` is called **per reading organism** inside
    `world_tick_numba`.
- **Verification BEFORE any measured row** (instrumentation lesson, `Docs/Result.md`):
  1. `compile_fingerprint` registers the new flag + arrays (`ENV_NAME_MAP`,
     `KERNEL_STATE_VARS`), 5/5 PASS with 0 uncovered;
  2. flag-OFF vs flag-OFF byte-identity smoke test — float equality against
     committed artifacts;
  3. smoke-divergence proof — flag-ON diverges from flag-OFF on the
     reservoir-state/readout hashes (mechanism genuinely wired, not DCE'd).
- Rule 21.8 cache hygiene: `NUMBA_CACHE_DIR` keyed by the fingerprint; fresh kernel
  for the new signature.

---

## 6. Task — identical geometry to Exp 103, per-organism mechanism

- **Frozen cohort:** 60 organisms, no reproduction, no death (pinned energy;
  `GENESIS_AUTO_REPRO=0`), seeded onto the patch as in Exp 101's driver.
- **Patch:** 500-byte text patch (Books economy, contiguous library). Organisms walk
  the scroll via the existing saccade, so each reads a **time-varying** byte stream.
- **Duration:** 20,000 ticks.
- **Seeds:** 4 — `0, 1, 2, 3`.
- **Arms** (same construction as Exp 103):
  - **PERORG**: `GENESIS_RESERVOIR_PER_ORG=1`, `GENESIS_READOUT_LR=0.01`
  - **NOLEARN**: `GENESIS_RESERVOIR_PER_ORG=1`, `GENESIS_READOUT_LR=0` (identical
    mechanism, readout frozen — the ablation control)
- **Driver:** `experiments/exp103b_full_run.py` (pattern: `exp101_rstdp_probe.py`
  world-loop + `exp103_full_run.py` reporting). Per-organism init per seed: state
  zeroed; readout rows `(rand − 0.5) × 0.2` (matching Exp 103 init).
- **Reporting** every 1000 ticks:
  - cohort-mean 8-bit prediction accuracy (bits correct / 8, over alive orgs, from
    `g_po_pred_byte` vs the target byte),
  - cohort-mean per-bit |err|,
  - cohort-mean `||readout_w_po||` (readout-norm, learning-activity proxy).
- **Metric:** early = first third of windows, late = last third (as Exp 103).
- Artifacts: `experiments/exp103b_results/exp103b_{perorg,nolearn}_s{0..3}_20000t.json`
  + `exp103b_full_summary.json`.

---

## 7. Success criteria (binding, pre-registered)

1. **Δ = late − early > +2.0 pp** (cohort-mean accuracy, PERORG arm);
2. **late(PERORG) > late(NOLEARN) + 3.0 pp**;
3. **No monotonic decline**: no late-phase window drops **> 5 pp below the running
   peak** (i.e., no >5 pp drop from peak).

All three must hold for SUCCESS (mirrors Exp 103's binding clause).

---

## 8. Failure

Null result (Δ ≤ +2.0 pp, or gap ≤ +3.0 pp, or monotonic decline) → report honestly
and **pivot to Option 1 (differentiable plasticity) or Option 3 (neuroevolution)**,
per the parent design's failure clause. No post-hoc metric changes (Rule 16).

---

## 9. Binding prediction

**Continuous learning (no saturation)** — unlike Exp 103's global readout (one
shared stream → converged at ~78%, Δ = +0.06 pp), each per-organism readout faces a
**time-varying input** (the organism walks its own position along the scroll), so
per-bit error stays > 0 and NLMS keeps adapting through tick 20,000. The cohort mean
keeps climbing rather than flattening.

Secondary prediction: per-organism readouts **diverge** (different streams →
different learned weights) — the cohort becomes a population of specialized
predictors rather than one shared predictor.

---

## 10. Rule 21 — honest energy accounting

Per reading organism, per read event, charged to that organism's own `total_atp`:

- `CYCLES_PER_NEURON_UPDATE` **× 256** — one charge **per reservoir unit** updated
  (the existing measured neuron-update cost; Rule 21.1, commit `d1bbc72`);
- `CYCLES_PER_STDP_UPDATE` **× 8 × 256** — one charge **per readout weight update**
  (2048 weights; the existing measured STDP-update cost) — charged **only when a
  weight update actually occurs** (`lr > 0`; the NOLEARN arm pays the state-update
  cost but no update cost, and at compile-time `lr = 0` the update loop is DCE'd).

No new magic numbers: both constants are the existing measured costs in
`src/neuromorphic_engine.py`. In the frozen-cohort geometry energy is pinned (no
death), so the charge is honest accounting that becomes load-bearing in any future
ecological integration.

---

## Implementation checklist (Phase 3 — ONLY after explicit approval)

1. `src/genesis_lab.py`: allocate `g_reservoir_state_po`, `g_readout_w_po`,
   `g_po_pred_byte`; add `READOUT_LR` module global; thread all three into the
   `world_tick_numba` call site.
2. `src/neuromorphic_engine.py`: add the arrays to the `world_tick_numba` signature;
   add the compile-time per-organism block at the read/predict event calling
   `reservoir_step()` with row views; add the Rule-21 charges (§10).
3. `src/compile_fingerprint.py`: register `GENESIS_RESERVOIR_PER_ORG` +
   `GENESIS_READOUT_LR` and the new kernel-state arrays.
4. Verification (§5): fingerprint, byte-identity, divergence proof — before any
   measured row.
5. `experiments/exp103b_full_run.py` + `experiments/exp103b_results/` artifacts.
6. Report to `Docs/Result.md` (pre-registration cross-ref) after execution.
