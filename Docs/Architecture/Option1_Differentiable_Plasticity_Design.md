# Option 1 — Differentiable Plasticity: Design (PATH A)

**Status:** DESIGN — PATH A **approved** by `Docs/Decision/Final_Pivot_Decision.md` (2026-08-05).
Design-doc only. **NO implementation, NO experiment, NO PR, NO merge until explicitly approved.**
**Date:** 2026-08-05
**Branch:** `arena/019fd2b8-genesis` (session branch; parent decision merged via PR on `feature/reservoir-readout`)
**Parent decision:** `Docs/Decision/Final_Pivot_Decision.md` §3 PATH A (approved) — this document is its §5 step 1.
**Predecessor results:** Exp 101 (R-STDP, NULL — self-silencing), Exp 102 (STDP_TARGET, NULL),
Exp 103 (shared reservoir readout, STATIC ONLY), Exp 103b (per-organism reservoir readout,
NULL_OR_DEGRADED), Exp 3 (neuroevolution, NULL — extinction cycles). **SNN-on-RAM falsified for
in-lifetime learning** across five mechanism classes; the remaining untested hypothesis class is
gradient-based credit assignment.
**Kill criterion (registered in advance, binding):** the feasibility probe (§3) fails →
**PATH B3 executes immediately** (`Substrate_Limits_Acceptance.md`, README/ARD claim corrections,
Rule-18-A/B finish-line downgrade). **No further experiments of any kind.**

---

## 0. Motivation — why gradient-based credit assignment (from the five nulls)

Five pre-registered mechanisms were executed against in-lifetime learning on the SNN-on-RAM
substrate. The mechanism changed every time; the outcome did not:

| Exp | Mechanism | Binding result | Root cause |
|---|---|---|---|
| 101 | R-STDP (reward = surprise × efficiency) | reward ≡ 0, eligibility ≡ 0, drift ≡ 0 at every checkpoint through 2000t — **NULL (self-silencing)** | Reward gate collapses when baseline is static |
| 102 | STDP_TARGET (direct per-bit error) | learner Δ −11.1pp vs NOLEARN −11.3pp — **NULL** | Local spike-gated update: credit never reaches silent weights |
| 103 | Shared reservoir + LMS readout | in-run Δ +0.06pp (bar +2pp); static gap +10.35pp — **STATIC ONLY** | Readout saturates at best linear predictor; no nonlinear feature learning |
| 103b | Per-organism reservoir + readout | in-run Δ −0.02pp; static gap +21.31pp — **NULL_OR_DEGRADED** | Same ceiling at per-organism granularity |
| 3 | Cross-generation evolution of fixed weights | fitness Δ −30.8/−29.3/−29.4%; extinction cycles all seeds — **NULL** | Abandons in-lifetime acquisition entirely |

The binding conclusion of the decision: **SNN-on-RAM is falsified as a substrate for in-lifetime
learning**, and the single missing ingredient across all five nulls is **credit assignment**, in two
confirmed structural forms:

1. **Silent-synapse recruitment barrier** — spike-gated local rules update only recently-active
   weights; credit never reaches needed-but-silent synapses.
2. **Reward/eligibility collapse (self-silencing)** — directionless or baseline-gated signals
   vanish exactly when the world is static, which is the probe condition.

Gradient-based learning is the one credit-assignment mechanism that is structurally immune to both:
it produces a **dense** gradient over all weights (no silent-synapse barrier) driven by a
**directional** error signal independent of any baseline (no self-silencing). It is the only
remaining path that preserves the founding in-lifetime-learning vision, and it directly optimizes
the exact metric the falsifying probes measured. Exp 103/103b additionally prove the *task* is
learnable to ~78–79% by an error-driven method and the substrate can *retain* structure — what
fails is *in-run acquisition*, which is precisely the question gradient descent is the strongest
existing instrument for.

---

## 1. Architecture

### 1.1 What is replaced

- **Hebbian/reservoir learning is removed from the learning path.** The R-STDP / STDP_TARGET /
  reservoir + LMS machinery is not extended; the gradient learner becomes the in-lifetime learning
  mechanism. The certified engine paths (world loop, economy, movement, CAM, prediction-income
  physics) remain, per the migration boundary in §1.5.
- **The learning substrate moves off the event-driven numba kernel.** The current `@njit`
  `world_tick_numba` cannot host gradient flow (no autograd). A new autograd-compatible backend is
  mandatory, not optional (decision §3 PATH A).
- **What survives unchanged:** the world loop, the tick structure, the frozen-cohort harness, the
  task (next-byte prediction), the income physics (correct-read quantum), and the experimental
  protocol skeleton (LEARN vs NOLEARN arms, 4 seeds, early/late windows).

### 1.2 Backend selection — JAX vs PyTorch

**Decision: PyTorch (CPU), eager execution, deterministic mode. JAX is the documented fallback.**

| Criterion | PyTorch (chosen) | JAX (fallback) |
|---|---|---|
| Dependency delta | Already declared in `pyproject.toml` (`cuda` extra: `torch>=2.0.0`) — smallest change | Adds `jax` + `jaxlib` + `optax`, stricter version pinning |
| Determinism (parity harness) | `torch.use_deterministic_algorithms(True)` + fixed thread count → bitwise reproducibility on CPU | Reproducibility requires discipline around XLA seeds; workable but more fragile |
| Cost calibration (Rule 21) | Eager-mode timing is direct and trustworthy; no XLA rewrite uncertainty | `jit` compiles change the op graph between calibration and run; harder to attribute |
| Surrogate-gradient upgrade path (candidate 1) | Mature ecosystem (snntorch / spikingjelly) | Weaker ecosystem |
| Per-organism parallelism | Straightforward (per-org weight tensors, one optimizer loop) | `vmap` over 60 orgs is elegant but adds abstraction |

The decision is a **recorded engineering choice, not a tuning axis** (Rule 17): both candidates were
named in the pivot decision; this document fixes the selection so no later session can swap backends
to chase results. GPU is **out of scope** for the probe and full run: CPU-only, deterministic,
cost-measurable. A GPU port is a separate, post-verdict decision.

### 1.3 Gradient mechanism — rate-coded reference backend first

The pivot decision listed three candidate mechanisms (decreasing physical fidelity, increasing
implementation speed):

1. **Surrogate-gradient SNN** (BPTT with surrogate derivatives) — keeps spiking physics; most
   faithful; highest cost.
2. **Rate-coded reference backend** — fastest decisive YES/NO on whether gradient-based in-lifetime
   learning beats ablation on this task family; risks becoming the product.
3. **Local gradient approximations** (e-prop / feedback alignment / predictive-coding-style) — the
   Rule-21-plausible middle ground for a later physically-grounded port back toward event-driven
   hardware.

**Staged choice (binding):** the **rate-coded reference backend (candidate 2)** is the mechanism
for the probe (§3) and the full run (§4). The kill criterion is the priority: the five nulls must
be answered on the cheapest decisive instrument, and the probe's question is *can gradient-based
learning acquire capability in-lifetime on this substrate*, not *can it do so with spiking
physics*. The rate-coded MLP (linear + tanh + linear + sigmoid) is the minimal gradient-trainable
network with strictly more capacity than the linear readouts that failed (Exp 103/103b).

**Explicitly NOT required for the probe or full run:**
- **Surrogate-gradient SNN (candidate 1)** is the post-pass fidelity upgrade. If and only if the
  full run succeeds, a surrogate-gradient SNN port is a **new, separately pre-registered
  experiment** — never a silent substitution. This is the re-scope gate that contains the
  "rate-coded becomes the product" risk (decision §3 risk 2).
- **e-prop / feedback alignment (candidate 3)** is the eventual physical port-back target
  (20W / event-driven thesis, Rule 21), deferred until the verdict.

### 1.4 Network geometry (per organism, rate-coded MLP)

Per-organism network `in(8) → hidden(n_hidden) → out(8)`:

```
h     = tanh(W_in_po[org] · x + b_in_po[org])        # x = 8-bit current byte at patch position
pred  = σ(W_out_po[org] · h + b_out_po[org])         # 8-bit predicted next byte (per-bit Bernoulli)
loss  = Σ_bits BCE(pred_b, target_b)                 # target = actual next byte (ground truth)
```

- **Input 8 bits / output 8 bits:** forced by the substrate (uint8 cells, `CELL_STATES = 2^8`;
  class FORCED-BY-DESIGN — same byte width the prediction-income physics uses).
- **Hidden width `n_hidden`:** class **(E) evolvable gene** (Rule 21.2), default 64 with an
  H-derived lower bound: must exceed the rank-8 linear readout (which saturates at ~78% in
  Exp 103/103b) to be a genuine feature layer. Default is a documented bound, not a tuned value.
- **Activations:** tanh hidden, sigmoid output — fixed by the loss/accuracy metric, not tuned.
- **Weight init:** class **(H) hardware-derived** — Glorot/Xavier scale from fan-in
  (`σ_init = 1/√fan_in`), the standard bound on preserving activation variance; documented, not
  tuned. Same init for LEARN and NOLEARN arms (only the update differs).
- **Optimizer:** **plain SGD only**. Momentum, Adam, schedules, and the entire optimizer zoo are
  **out of scope** (decision §3: "The optimizer zoo is a tuning magnet and is out of scope").
- **Learning rate:** class **(E) evolvable gene** (per-organism, genome-inherited, mutated through
  inheritance), H-derived default `1/√fan_in ≈ 0.35 × 0.1` scale class bound — the full provenance
  row is fixed in §1.8. In the frozen cohort all organisms carry the ancestor's default gene, so
  lr is a fixed documented constant per run — but its class is (E), so Rule 21.2 is satisfied and
  ecology can later shape it.
- **Learning window `K`:** class **(E) evolvable gene**, H-derived default = one lap over the probe
  fragment (64 ticks) for the probe, one half-lap over the patch (256 ticks) for the full run.
  Backward passes run every K ticks (see §1.5).

### 1.5 Integration with the existing world loop (migration boundary)

**The certified `world_tick_numba` kernel is NOT modified for gradient math.** The gradient learner
is an isolated host-side module; the kernel's only additions are inert-by-default arrays and a
compile-time-gated event emission, following the exact precedent of the reservoir/readout and
neuroevolution flags (flag-OFF behaviour byte-identical by construction; DCE'd when off).

**New module:** `src/gradient_learner.py` (pure host-side; owns the PyTorch backend, the optimizer,
the calibration harness, and the Rule-21 ledger for gradient ops). It is the **only** file that may
import torch.

**Kernel additions** (all trailing args, same pattern as `g_reservoir_state`, `g_readout_w_po`):

```
g_grad_w_in_po     (MAX_ORGANISMS, 8, n_hidden)  float32   # W_in  per organism
g_grad_b_in_po     (MAX_ORGANISMS, n_hidden)     float32   # b_in  per organism
g_grad_w_out_po    (MAX_ORGANISMS, n_hidden, 8)  float32   # W_out per organism
g_grad_b_out_po    (MAX_ORGANISMS, 8)            float32   # b_out per organism
g_grad_events      (MAX_EVENTS, 4)               int32     # ring: [org, in_byte, tgt_byte, tick]
g_grad_n_events    (1,)                          int32     # ring head
```

- **Kernel-side forward (inference):** at the organism's read/predict event (where the kernel
  computes `nxt = pos + 1`, `next_byte = ram_substrate[nxt]` and gates the prediction block on a
  printable patch byte), the kernel executes the rate-coded forward with the organism's row views
  (numba-compatible array math), writes `pred_byte` to the existing prediction path (income physics
  unchanged), and appends `[org, in_byte, tgt_byte, tick]` to the ring. The forward pass stays in
  the kernel because prediction → income must remain a single certified path; the forward is cheap
  array math whose per-primitive cost is already MEASURED (§7).
- **Host-side backward/update (learning):** every `K` ticks, the lab's run loop calls
  `gradient_learner.update_all()`: drain the ring, build per-organism batches of `(in, target)`,
  compute per-bit BCE loss, `backward()`, apply plain SGD with the organism's lr gene, write the
  updated weights back into `g_grad_*_po`. Autograd — the only genuinely new capability — is thus
  confined to the host module behind the migration boundary.
- **Charging:** the kernel charges forward cost per read event (both arms); `gradient_learner`
  charges backward + update cost at each update (LEARN arm only) through the same Rule-21 ledger
  (§7). In the frozen cohort energy is pinned, so these charges are honest accounting recorded in
  telemetry; they become load-bearing in any future ecological integration (same posture as the
  reservoir's §10).

**Flags (Exp 103/103b construction):** both experiment arms run with the gradient path active —
same forward, same event recording — and differ **only** in whether weights update:

- **LEARN:** `GENESIS_GRAD_LEARN=1`, learning rate = the organism's lr gene (> 0).
- **NOLEARN:** `GENESIS_GRAD_LEARN=1`, `GENESIS_GRAD_LR=0` — identical mechanism, weights frozen
  at birth init (the host update call is skipped when lr = 0; the matched ablation, exactly the
  reservoir's `READOUT_LR=0` arm).
- `GENESIS_GRAD_LEARN=0` is the **mechanism-off** state used only for the parity harness's
  flag-OFF byte-identity gate (§1.6 gate 2) — never an experiment arm.

`GENESIS_GRAD_LR` is a fingerprint/env knob for constructing the lr=0 arm, not a tuning axis
(Rule 17).

### 1.6 Parity / determinism harness (rebuilt before any measured row)

Session-18 instrument-inheritance rule: **no measured row until the harness passes.** Four gates,
all before the probe:

1. **Fingerprint:** `compile_fingerprint` registers `GENESIS_GRAD_LEARN` (+ the new kernel-state
   arrays) — 5/5 PASS with 0 uncovered.
2. **Flag-OFF byte-identity:** kernel with `GENESIS_GRAD_LEARN=0` is float-identical to the
   committed artifacts (flag-off vs flag-off smoke test).
3. **Smoke-divergence proof:** flag-ON diverges from flag-OFF on the weight/prediction hashes —
   the mechanism is genuinely wired, not DCE'd.
4. **Backend determinism:** PyTorch CPU with `torch.use_deterministic_algorithms(True)` and fixed
   thread count — same seed → bitwise-identical weights after N updates; verified over ≥ 3 seeds.
   (`NUMBA_CACHE_DIR` keyed by fingerprint, Rule 21.8 cache hygiene.)

### 1.7 Rule 21 accounting plan (summary)

Designed in from day one, not retrofitted (decision §3: "Rule 21 accounting designed in from day
one"). Every gradient op cost is **MEASURED on the actual host** by a calibration harness that
mirrors `physical_cost_model.calibrate_native()` but for the new backend; no invented points. The
three headline constants — **cycles per forward pass, cycles per backward pass, cycles per
update** — and the full charging policy are specified in §7.

### 1.8 Rule 17 provenance table (every new constant)

No tuned constants. Every new quantity is **(H) hardware-derived**, **(E) evolvable gene**,
**FORCED-BY-DESIGN**, or **deleted** (Rule 21.2 / 21.6c):

| Constant | Default | Class | Derivation / justification |
|---|---|---|---|
| Network: in/out width | 8 / 8 bits | FORCED-BY-DESIGN | uint8 cell width; matches prediction-income byte width |
| `n_hidden` | 64 | (E) gene, H-derived bound | Lower bound: > rank-8 linear readout (which saturates at ~78%, Exp 103/103b) |
| Weight init scale | Glorot `1/√fan_in` | (H) hardware-derived | Variance-preservation bound from fan-in; documented, not tuned |
| Learning rate | `0.1/√fan_in` | (E) gene, H-derived default | Scale bound from fan-in; gene-inherited + mutated through inheritance |
| Optimizer | SGD, no momentum | DELETED (out of scope) | Optimizer zoo is a tuning magnet (decision §3); momentum/schedules forbidden |
| Learning window `K` | 64 (probe) / 256 (full run) | (E) gene, H-derived default | One lap over the probe fragment / half-lap over the 500-byte patch |
| Surrogate slope | n/a | DELETED for probe | Rate-coded backend has no surrogate; straight-through path is the post-pass SNN port's problem |
| Loss | per-bit BCE | FORCED-BY-DESIGN | Matches the per-bit accuracy metric exactly (no invented objective) |
| `CYCLES_PER_GRAD_FORWARD/BACKWARD/UPDATE` | measured | (H) MEASURED | Calibration harness on the reference host (§7); never hand-set |

---

## 2. Credit assignment mechanism

### 2.1 How it solves the silent-synapse barrier

The silent-synapse barrier is structural in spike-gated local rules: an update rule of the form
`Δw ∝ pre · post · g` touches a weight only when its pre-synaptic neuron was recently active and
its post-synaptic neuron spiked. A weight that is *needed* but silent (never co-active, so never
eligible) is structurally unreachable — credit never arrives. Exp 34/35 documented the recruitment
gap; every mechanism tested since (101–103b, 3) inherited it or avoided it only by abandoning
in-lifetime updates.

Backpropagation removes the barrier structurally: the chain rule gives `∂L/∂W` for **every**
weight in the network, including weights attached to never-firing or near-zero units, because the
gradient is a function of the *error path* (`δ_out = ∇_pred L`, `δ_hidden = W_outᵀ δ_out ⊙ σ'(h)`)
— not of recent spiking activity. A silent-but-needed hidden unit still has a well-defined
`δ_hidden` (its activation's derivative may be near zero only where the unit is saturated, and the
rate-coded tanh keeps `σ'(h) > 0` everywhere), so its afferent weights receive non-zero credit and
are recruited exactly when the error gradient demands it. **Dense gradient = no silent synapse
exists by construction.**

### 2.2 How it avoids self-silencing

Self-silencing (Exp 101) was the learning signal collapsing to *identically zero* in the static
world: reward = surprise × efficiency → 0 when the deviation-from-baseline gate closed, so
eligibility never accumulated and drift ≡ 0 despite large remaining error. The failure is that the
update signal was **gated by a baseline comparison**, not by the error itself.

The gradient learner's signal is the error itself:

```
g_w  = ∂/∂W  Σ_bits BCE(pred_b, target_b)
```

- **Directional:** the per-bit cross-entropy gradient points *toward* the target byte; it carries
  sign and magnitude for every bit that is wrong, independent of any baseline, reward, or
  surprise term. There is no gate that can collapse it.
- **Non-vanishing exactly when there is something to learn:** if the organism is wrong,
  `BCE > 0` and the gradient is non-zero. If the organism is right, the gradient is (near) zero —
  that is **convergence**, not silencing: learning has completed for that input, and the weight
  stays at its solution.
- **No eligibility window:** updates are computed directly from the stored `(x, target)` window
  via autograd; there is no eligibility trace that can decay to zero and no requirement that a
  neuron spiked recently for its weights to update.

The contrast with all five nulls, stated plainly: 101's reward collapsed to zero while error
remained (silencing); 102's local rule never reached silent weights; 103/103b's linear readout
saturated at the best linear predictor (a *capacity* ceiling, not a learning failure — gradient
descent through a nonlinear hidden layer escapes the linear ceiling); 3 abandoned in-lifetime
learning entirely. None of those failure modes applies to a dense, error-driven, nonlinear
gradient path.

### 2.3 Reward signal integration

Three distinct signals, kept deliberately orthogonal:

1. **Learning signal (gradient):** supervised per-bit prediction error — `target` = the actual
   next byte from the patch (the same ground-truth teacher Exp 102's STDP_TARGET used). This is
   the only signal that drives weight updates. It is **pure supervised error with no reward gate**,
   because every reward-gated mechanism tested (Exp 101, and the reward-modulated lineage before
   it) collapsed; the decision explicitly calls for directional error independent of any baseline.
2. **Ecological reward (income):** unchanged engine physics — a correct read pays the
   information-capacity quantum (`CELL_STATES = 256`, FORCED-BY-DESIGN) under the Books economy.
   The gradient learner does not touch income; income remains the ecology-side consequence of
   prediction, so a learned predictor is rewarded by the existing physics (and any future
   ecological integration inherits the load-bearing link between learning and survival).
3. **Deferred three-factor variant:** gating the update magnitude by energy income (e.g.,
   update ∝ income) is explicitly **out of scope** for the probe and full run. It was the shape of
   every failed mechanism and is a tuning magnet; it may be revisited only as a *new*
   pre-registered experiment after a PASS verdict, never before.

---

## 3. Probe protocol (kill criterion)

**Protocol:** `EXP200_DIFF_PLASTICITY_PROBE_v1` — authored as a standalone pre-registration doc
(`Docs/Exp200_Protocol.md`) **before any implementation begins** (decision §5 step 2). The binding
spec below is fixed here so the pre-registration cannot drift.

**Question (minimal test):** *can the substrate — the integrated gradient learner inside the world
loop — learn a simple task in 1000 ticks?*

**Design:**

| Element | Spec |
|---|---|
| Task | Simple deterministic mapping: first-order next-byte prediction over a **64-byte fragment** of the Books patch (a fixed, learnable byte→byte function — the simplest non-trivial prediction the substrate faces) |
| Cohort | Frozen 60 organisms, no reproduction, no death (`GENESIS_AUTO_REPRO=0`, pinned energy) — same harness as Exp 101–103b |
| Duration | **1,000 ticks** (per seed) |
| Seeds | 4 — freshly drawn and **pinned in the pre-registration before any run**; no seed is added, removed, or re-drawn after results are visible (Rule 16) |
| Arms | **LEARN** (`GENESIS_GRAD_LEARN=1`, SGD on) vs **NOLEARN** (`GENESIS_GRAD_LEARN=1`, lr=0 — identical mechanism, weights frozen at birth init; the matched ablation) |
| Network | §1.4 rate-coded MLP, default `n_hidden=64`, lr gene default, K = 64 ticks |
| Windows | early = ticks 1–250, late = ticks 751–1000 (last quarter); cohort-mean per-bit accuracy over each window |
| Metric | **Δ = late − early** (cohort-mean accuracy, LEARN arm) |

**Success (kill-criterion PASS, binding, all required):**
1. **Δ(LEARN) > +5.0 pp** — the substrate visibly acquires the mapping in 1000 ticks;
2. **Δ(LEARN) > Δ(NOLEARN) + 3.0 pp** — the matched-ablation guard (per the decision's "one
   pre-registered probe, one matched ablation"); the gain is learning, not environmental drift.

**Failure → B3 executes immediately.** If either bar fails — including "crash, instability, or
undetermined" — **PATH B3 executes immediately: no second probe, no re-tuning, no mechanism swap,
no alternative task, no longer horizon.** This sentence is the registered kill clause (decision §4
item 3: "If it fails, PATH B3 executes immediately with no further experiments"). A non-binding
diagnostic (e.g., per-seed learning curves, weight-norm trajectory, which bit errors decay first)
may be recorded for the Result.md writeup, but **no diagnostic may ever gate or re-open the
verdict.**

**Why this bar is fair:** 1000 ticks × 60 organisms ≈ 60,000 read events ≈ 60,000 gradient-bearing
samples on a 1,096-parameter network — two orders of magnitude more samples than parameters, on a
deterministic 64-byte mapping. A mechanism that cannot show > +5pp of acquisition here is not
viable at any horizon, and no further experiment can rescue it.

---

## 4. Task spec for full run

On probe PASS, the full run executes **unchanged task geometry from Exp 100–103b** (the same
frozen cohort, same duration, same seeds, same ablation control):

| Element | Spec |
|---|---|
| Protocol | `EXP201_DIFF_PLASTICITY_FULL_RUN_v1` (pre-registered before the probe executes, so the escalation path is fixed in advance) |
| Task | Next-byte prediction over the **500-byte text patch** (Books economy, contiguous library; organisms walk the scroll via the existing saccade — time-varying input per organism, as Exp 103b) |
| Cohort | **Frozen 60 organisms**, no reproduction, no death (pinned energy; `GENESIS_AUTO_REPRO=0`) |
| Duration | **20,000 ticks** per seed |
| Seeds | **4** (0–3 or freshly drawn per the pre-registration; fixed before any run) |
| Arms | **LEARN** (`GENESIS_GRAD_LEARN=1`, SGD on) vs **NOLEARN** (same network, lr=0, weights frozen at init) |
| Network | §1.4 rate-coded MLP, defaults as the probe; K = 256 ticks |
| Windows | early = first third of report windows, late = last third (as Exp 103/103b) |
| Reporting | every 1000 ticks: cohort-mean 8-bit accuracy, per-bit \|err\|, mean weight norms, mean \|grad\| (learning-activity proxy) |
| Artifacts | `experiments/exp201_results/exp201_{learn,nolearn}_s{0..3}_20000t.json` + `exp201_full_summary.json` |

---

## 5. Success criteria (binding)

**Both gates must pass — no partial credit:**

1. **Probe passes (kill criterion):** §3 bars — Δ(LEARN) > +5.0 pp AND Δ(LEARN) > Δ(NOLEARN) + 3.0 pp
   in 1000 ticks.
2. **Full run passes (all three, mirroring Exp 103/103b):**
   - Δ(LEARN) = late − early > **+2.0 pp** (in-run acquisition, the criterion every prior mechanism
     failed);
   - late(LEARN) > late(NOLEARN) + **+3.0 pp** (separates learning from environmental drift);
   - **no monotonic decline** — no late-phase window drops > 5 pp below the running peak (no
     catastrophic forgetting).

Verdict on full pass: `DIFFERENTIABLE_PLASTICITY_CONFIRMED` — the founding in-lifetime-learning
claim is restored on the gradient substrate, and the path continues (surrogate-gradient fidelity
port as a new pre-registered experiment, Rule-18 finish line re-opened).

---

## 6. Failure criteria

| Condition | Action (binding) |
|---|---|
| **Probe fails** (§3 bars not met, crash, or undetermined) | **B3 executes immediately** — `Docs/Decision/Substrate_Limits_Acceptance.md`, README/ARD claim corrections, Rule-18-A/B finish-line downgrade, five-null + gradient-null evidence trail published as the negative result. No further experiments of any kind. |
| **Full run null** (§5 gate 2 not met) | **B3 executes immediately** — same acceptance path. The probe passing but the full run nulling is a *scaled* negative result: gradient learning acquires simple structure but not the full task; the substrate question is answered (task-learnability is not the blocker — §0) and the finish line is downgraded. |

No post-hoc metric changes, no re-running with different windows/seeds/horizons, no "one more
tuning pass" (Rules 16/17: one probe, pass or kill).

---

## 7. Rule 21 — measured-cost model for gradient ops

**Principle (Rule 21.1):** every cost the organism pays is the real measured hardware work of the
op on the reference host. The gradient learner adds three charging constants — forward, backward,
update — all **MEASURED**, none invented. The existing constants (`CYCLES_PER_SYNAPSE_READ`,
`CYCLES_PER_NEURON_UPDATE`, etc.) are reused wherever the forward pass decomposes into existing
primitives.

### 7.1 Calibration harness (mirrors `physical_cost_model.calibrate_native`)

`gradient_learner.calibrate_gradient_ops(backend="torch-cpu", n_rep=...)` times each op in a tight
loop with warmup on the actual host, divided by iterations (and by batch size where applicable) →
seconds/op → **cycles = seconds × NOMINAL 3.0 GHz** (same NOMINAL-HOST clock convention as the
existing model). Basis class for all three: **MEASURED** (timed on the actual host; native
torch-CPU cost). Each of the three ops is a fixed computational graph, so it is calibrated as one
op — no per-primitive decomposition of the backward pass is possible or honest (autograd is a
host-library op with no engine primitive equivalent).

### 7.2 Cycles per forward pass

Charged **per read event, both arms** (inference is real work; the forward pass runs every read).

```
CYCLES_PER_GRAD_FORWARD = (8·n_hidden + n_hidden·8) × CYCLES_PER_SYNAPSE_READ   # the two matvecs
                        + n_hidden            × CYCLES_PER_NEURON_UPDATE       # hidden tanh units
                        + 8                   × CYCLES_PER_GRAD_ACT             # sigmoid readout (NEW, MEASURED)
```

- The two matvecs reuse the **existing MEASURED** `CYCLES_PER_SYNAPSE_READ` (a MAC — the
  calibrated primitive is `gv[dst] += w`, exactly one synapse-read per weight).
- The hidden-unit updates reuse the **existing MEASURED** `CYCLES_PER_NEURON_UPDATE`.
- The only new constant is `CYCLES_PER_GRAD_ACT` (one sigmoid/activation), calibrated once on the
  reference host; the tanh and sigmoid are the same class of op, measured together.
- **Pre-calibration estimate at `n_hidden=64`:** 1,024 × synapse_read + 64 × neuron_update +
  8 × grad_act ≈ **1.5–3 kcycles per forward pass** — an order-of-magnitude planning figure only;
  the harness output replaces it before any measured row (Rule 21.1: no invented points, estimates
  never enter the ledger).

### 7.3 Cycles per backward pass

Charged **in the LEARN arm only, at each update (every K ticks)**, amortized per sample:

```
CYCLES_PER_GRAD_BACKWARD = measured wall-time of autograd backward over the K-window batch ÷ K   [per-sample]
```

- Measured on the reference host with the real batch geometry (batch = K samples per organism);
  amortizing per sample keeps the charge comparable to the per-read forward charge.
- Pre-calibration estimate: backward ≈ **2–3× the forward pass** (the chain-rule pass touches every
  parameter plus stores activations) — planning figure only, replaced by measurement.
- The NOLEARN arm pays **zero** backward cost (the update never runs; at compile time lr = 0 the
  host call is skipped) — the ablation is also a cost ablation, exactly as Exp 103b's frozen-readout
  arm.

### 7.4 Cycles per update

Charged **in the LEARN arm only, at each update**, amortized per sample:

```
CYCLES_PER_GRAD_UPDATE = measured wall-time of the SGD apply over the K-window batch ÷ K   [per-sample]
```

- Pre-calibration estimate: update ≈ **0.2–0.5× the forward pass** (elementwise ops only) —
  planning figure only.
- SGD has no optimizer state, so the update op is a pure `w ← w − lr·g` sweep over the 1,096
  parameters — the smallest possible update op, by design (optimizer zoo out of scope, §1.8).

### 7.5 Charging policy and ledger

| Op | When charged | Which arm | Constant |
|---|---|---|---|
| Forward | every read/predict event | both | `CYCLES_PER_GRAD_FORWARD` (reuses existing constants + one new MEASURED op) |
| Backward | every K ticks | LEARN only | `CYCLES_PER_GRAD_BACKWARD` (new, MEASURED) |
| Update | every K ticks | LEARN only | `CYCLES_PER_GRAD_UPDATE` (new, MEASURED) |

- Charges are applied per contributing organism (backward/update prorated over the organisms whose
  events formed the batch) into the same `total_atp` ledger the kernel uses; recorded in telemetry
  under `energy_basis` with basis class MEASURED.
- **No invented points:** the three constants are the ONLY new cost quantities, all from the
  calibration harness; the Rule-17 table (§1.8) records them; the calibration script, its host
  fingerprint, and its raw timing logs are committed artifacts.
- In the frozen cohort energy is pinned (no death), so charges are honest accounting that becomes
  load-bearing in any future ecological integration (same posture as the reservoir's §10).

---

## 8. Risk mitigation

### 8.1 Staged implementation (backend → integration → full run), gated at each stage

| Stage | Gate to proceed | Session |
|---|---|---|
| **S0 — Design (this doc)** + pre-register `EXP200`/`EXP201` protocols | explicit approval of this design | 1 |
| **S1 — Backend prototype** (`gradient_learner.py`: rate-coded MLP, SGD, calibration harness; cost constants measured; Rule-17 table committed) | calibration produces MEASURED constants; MLP learns the 64-byte fragment standalone | 2–3 |
| **S2 — Integration** (kernel arrays + flag + event ring; fingerprint; byte-identity; divergence proof; backend determinism) | §1.6 harness 4/4 PASS | 3–4 |
| **S3 — Probe** (`EXP200`, §3) | verdict recorded either way; kill gate | 5 |
| **S4 — Full run** (`EXP201`, §4) | probe PASS only | 6–7 |
| **B3 — Acceptance** (on any fail) | immediate; no further experiments | +1–2 |

### 8.2 Rule 21 accounting plan (top review item per decision)

- Measured-cost charging designed in from day one (§7): three MEASURED constants, reusing certified
  per-primitive costs for the forward pass; calibration harness mirrors the existing
  `physical_cost_model` pattern; no invented points; estimates are explicitly labeled and never
  enter the ledger.
- Rule 17 provenance table (§1.8) covers every new constant before implementation; lr, `n_hidden`,
  and `K` are (E) genes with H-derived defaults — no tuned literals; optimizer zoo deleted.

### 8.3 Migration-boundary risk (certified engine untouched)

- Gradient math is confined to `gradient_learner.py`; the kernel's changes are trailing
  inert-by-default arrays + a compile-time-gated event emission (the established reservoir/CAM
  pattern). Flag-OFF is byte-identical by construction; the parity harness (§1.6) proves it before
  any measured row (Session-18 instrument-inheritance rule).

### 8.4 Determinism risk

- `torch.use_deterministic_algorithms(True)`, fixed thread count, float32, seed-pinned init;
  backend-determinism gate (§1.6 gate 4) before any measured row.

### 8.5 "Rate-coded becomes the product" risk (decision §3 risk 2)

- Rate-coded is declared the probe/full-run instrument, and the surrogate-gradient SNN port is
  explicitly **not** required for either; any fidelity port is a new pre-registered experiment
  after a PASS (§1.3 re-scope gate). The physical-fidelity concession (backprop's non-local weight
  transport vs the 20W event-driven thesis) is documented, not hidden; e-prop is named as the
  eventual port-back target.

### 8.6 Timeline risk (bounded by the kill criterion)

- The binding kill gate (§3) bounds total PATH-A cost at ~5–7 sessions: a probe fail triggers B3
  (1–2 sessions) with zero further experiments. The schedule cannot slip into an open-ended tuning
  loop because no tuning axis exists (Rule 17).

### 8.7 Timeline estimate (~5–7 sessions)

Per the decision: 1 design doc → 2–3 prototype backend + both-passes cost accounting + parity
harness → 1 pre-registered feasibility probe → binding verdict in **~5–7 sessions** (table in
§8.1). No tuning axis: one probe, pass or kill.

---

## 9. Implementation checklist (ONLY after explicit approval)

1. Author `Docs/Exp200_Protocol.md` + `Docs/Exp201_Protocol.md` (pre-registrations, binding §3/§4
   specs) — no code until both are committed.
2. `src/gradient_learner.py`: rate-coded MLP (torch CPU, deterministic), plain SGD, lr/`n_hidden`/K
   gene plumbing, `calibrate_gradient_ops()` harness → MEASURED constants → Rule-17 table.
3. `src/neuromorphic_engine.py`: `g_grad_*_po` arrays + `g_grad_events` ring in the
   `world_tick_numba` signature; compile-time forward + event emission at the read/predict event;
   forward charge (§7.2).
4. `src/genesis_lab.py`: drain/update orchestration every K ticks; backward + update charges
   (§7.3/§7.4).
5. `src/compile_fingerprint.py`: register `GENESIS_GRAD_LEARN` (+ arrays). Parity harness §1.6 —
   4/4 PASS before any measured row.
6. Probe `experiments/exp200_probe.py` (60 orgs, 1000 ticks, 4 seeds, LEARN/NOLEARN) →
   verdict → kill gate.
7. Full run `experiments/exp201_full_run.py` (60 orgs, 20000 ticks, 4 seeds) on probe PASS →
   verdict.
8. Report both to `Docs/Result.md` (pre-registration cross-refs) per Rule 20; on any fail, execute
   B3 immediately per §6.

---

*Recorded 2026-08-05 on branch `arena/019fd2b8-genesis`. This document states the approved PATH A
design and its registered kill criterion; it authorizes no code. Awaiting explicit approval to
proceed to the Exp 200/201 pre-registrations.*
