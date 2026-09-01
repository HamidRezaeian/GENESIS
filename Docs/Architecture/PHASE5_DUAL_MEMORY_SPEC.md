# GENESIS Phase-5 — Dual-Timescale Addressable-Memory Substrate Specification

**Document ID:** `PHASE5_DUAL_MEMORY_SPEC_v1`
**Status:** BINDING SPECIFICATION (pre-registered under Rule 18 / Rule 23)
**Date:** 2026-08-31
**Supersedes (AGI-path only):** Phase-E flat single-timescale SNN substrate
**Audience:** implementer (Antigravity) + scientific auditor (GLM 5.3)

---

## 0. Scope & Binding Declaration

This document is the formal **new substrate hypothesis** required by the Rule-23 pivot
protocol, issued after the Rule-18 kill criterion executed on the SNN-on-RAM line
(Ascent.md, 2026-08-01) and after the 2026-08-31 instrument campaign that decomposed
the Phase-E v1 "learning signal" (z up to +3.63, 30/30 positive streak) into two
artifacts: (a) within-probe sequential STDP exposure (order artifact) and (b) stimulus
sensitivity masquerading as memory (NULL artifact). The honest delta series
(+0.012, −0.008, −0.017, +0.030, +0.005) is noise around zero. Phase-5 therefore
RETAINS: the multi-world ALife population shell, thermodynamic energy accounting,
and the contrastive LLM sensory bridge. It DISCARDS: the flat single-timescale
cortex as the load-bearing learner. It REPLACES: memory-as-voltage-persistence
with memory-as-gated-addressable-state.

Every design requirement below cites the falsifying evidence that forces it.
Nothing in this spec exists because it "seemed like a good idea."

## 1. Requirements Provenance Table

| ID | Requirement (one line) | Forcing evidence (failure without it) |
|----|------------------------|--------------------------------------|
| R1 | Dual-timescale synapses (fast re-tracking + slow consolidation) | Exp-99: two-timescale signal REAL but UNSTABLE (+5.34, p=0.0015; static fidelity 92.34 < 95 gate) — a design requirement, not a solution |
| R2 | Gated addressable external memory (write/read enables, identity-keyed slots) | Exp-43/44/45: depth-1 holds, depth>=2 collapses; latch without gates = overwritten every tick; "memory is an ADDRESS, not a voltage" (Exp-46) |
| R3 | Credit-assigning third factor that can CONSTRUCT new pathways (signal reaches silent-but-wanted neurons) | Exp-34: STDP prunes but cannot recruit; Exp-35: teaching signal recruits (40%->99% in-lifetime) — the ONLY rule ever shown to build new circuits |
| R4 | Instrumentation-first: counterbalanced clones, NULL controls, metric versioning pre-registered BEFORE first run | 2026-08-31 campaign: v1 signal was ~70-90% artifact; honest instruments changed the verdict; legacy_fabricated quarantine |
| R5 | No search-set constants: every number carries [H]/[E]/[mathematical-invariant]/[empirical, documented]/[opcode] class from day one | Rule 17/21: Phase-E carried unclassified constants (query_to_move_ratio=500, repro_cost=5.0) — the debt that rotted the audit trail |
| R6 | Population in stable demographic regime (no extinction-reseed cycles) | Live ledger 2026-08-31: 665->356->313 alive, cumulative deaths ~4.97M vs births ~0.7M — marginal survival produces NO selectable learning gradient |
| R7 | Contrastive LLM latent bridge retained as sensory channel (not teacher) | phase_e_plus InfoNCE machinery: existing, functional, decoupled; Rule 9 autotelic boundary preserved |

---

## 2. Core Architecture

### 2.1 Dual-Timescale Synapses (R1)

Each organism carries TWO coupled weight tensors over the same topology
(pre/post indices shared, `syn_active` shared):

```
W_fast[t+1]  = W_fast[t] + eta_f(t) * M(t) * E(t)          (fast re-tracking)
W_slow[t+1]  = W_slow[t] + eps(t) * (W_fast[t] - W_slow[t]) (slow consolidation)

eta_f(t)      = eta_f0 * g_gate(t)          [E] genome-encoded, gate-modulated
eps(t)        = eps0 * beta(info(t))        [E] consolidation gated by information
W_eff[t]      = W_fast[t] + W_slow[t]        (effective drive onto postsyn)
```

- `g_gate(t)`: surprise gate (Eq. 6) — plasticity fires ONLY on
  deviation-from-expectation (Exp-98: the gate works mechanically; S2 p=0.0001).
- `beta(info(t))`: consolidation runs only when the trace carries information
  (eligibility magnitude above its own running median — a rank statistic,
  Rule-17-safe: no threshold constant, only an order statistic of the signal itself).
- Bound discipline: `W_fast` in [-4, 4] (same rail as Phase-E, [S] structural);
  `W_slow` is UNBOUNDED but every consolidation step is charged Landauer FLOPs
  (Rule 21) — slow memory grows only by paying measured host work, never free.
- Falsifiable distinction from Exp-99: there, tau_slow was a single global decay.
  Here consolidation is *event-gated by information content*, and the static-fidelity
gate (Gate S, section 4) is enforced per-slot, not per-population.

**Hypothesis H1 (pre-registered):** with R2 present, fast-tracking transfers into
slow consolidation at fidelity >= 95 per slot (Gate S); without R2, it must decay
(Exp-99 replication control).

### 2.2 Gated Addressable External Memory (R2)

Each organism owns a slot bank outside the leaking membrane:

```
MEM[j] ∈ R^{b}          j = 0..K-1        (K slots, b bits/slot; K, b from RAM budget [H])
key[j]  ∈ R^{d}                           (identity key, written on store, immutable)
valid[j] ∈ {0,1}                          (occupancy)

WRITE (fired when write-enable gate w(t)=1):
  j* = argmin_j  (1 - valid[j]) + sim(key[j], k_write(t))      (empty slot first)
  MEM[j*] <- encode(x(t));  key[j*] <- k_write(t);  valid[j*] <- 1

READ (fired when read-enable gate r(t)=1):
  out(t) = softmax_j( sim(key[j], k_read(t)) / T_ret )^T · MEM[j]
  T_ret: retrieval temperature = mathematical invariant 1/sqrt(d)   [M]

GATES (the load-bearing part — Exp-45: ungated memory degenerates to a 1-frame buffer):
  w(t) = 1  iff  a_write neuron fires          (a_write: dedicated motor neuron, action space +1)
  r(t) = 1  iff  a_read  neuron fires          (a_read:  dedicated motor neuron, action space +1)
  k_write(t), k_read(t) = the organism's OWN output symbol vector states[-4:]   (autotelic: Rule 9 — the address is self-generated, never author-supplied)
```

- **Identity-keyed** (R4 lesson from the v4 instrument fix): writes and reads align
  by CONTENT KEY, not by slot-count — population churn (death/birth) cannot corrupt
  the address space; only a matching key retrieves.
- `sim(a,b) = dot(a_hat, b_hat)` (cosine; normalized — scale-free, Rule 17).
- Energy: every WRITE costs `b * K` FLOPs (associative search) + `b` bits traffic;
  every READ costs `K` FLOPs. All charged at measured `E_flop` (Rule 21). Memory
  that is never read still pays storage traffic per audit epoch — no free memory.
- Capacity discipline (Rule 19): `live_size = sum(valid[j]) * b` bytes; compaction
  (eviction of lowest-retrieval-count slots) runs ONLY between kernel ticks, is
  logged in telemetry, and is reversible within the epoch (audit trail).
- Wiring: MEM output injects on RESERVED sensory channels (the final `b` channels),
  gated by `r(t)` — the cortex cannot see memory it did not ask for.

**Hypothesis H2 (pre-registered):** depth-2 working memory (delay-2 sandbox) is
solvable ONLY through R2 (write at t1, read at t2). Without gates (dense read),
score must collapse to the depth-1 level (Exp-44 replication).

### 2.3 Constructive Credit Assignment (R3)

The ONLY plasticity rule ever shown to BUILD a new pathway (Exp-35: 40%->99%
within-lifetime re-tracking, repeated every phase flip) is the error/teaching
signal that reaches silent-but-wanted neurons. It is mandatory, in its Exp-99-
reconciled form — modulated by the surprise gate, applied to BOTH weight scales:

```
err_i(t)  = target_i(t) - out_i(t)          (signed, per readout unit i)
dW_fast  += eta_f(t) * err_i(t) * pre_j(t) * g_gate(t)         (recruit: silent neuron -> eligible)
dW_slow  += eps(t)  * err_i(t) * pre_j(t) * beta(info(t))       (consolidate the recruit)
```

- `target_i(t)`: DERIVED FROM THE ORGANISM'S OWN ECONOMY (its next-sensory state,
  or its own read-back of MEM) — never a human label (Rule 9). The 2026-08-31
campaign proved why: reward-gated STDP consolidated whatever fired, correct or not.
- Contrastive bridge (R7): the InfoNCE pair (action_embed, llm_hidden) remains the
  ONLY supervised coupling — but as SENSORY data (Rule 9: sensory, never reward).
  Its loss value is telemetry, not fitness.
- Gated multimodal wiring (Exp-44 lesson — "dense plastic fabric + STDP = drift"):
  ALL new sensory channels (MEM readback, LLM latent, future modalities) connect
  through modality GATES initialized SILENT (gate=0) and modulated by the same
  `g_gate` surprise signal; a channel is discovered only when prediction error
  demands it. No dense-open connections anywhere.

### 2.4 Population Shell (retained from Phase-E, minimal diff)

- Multi-world batched tensors [W, N, ...], zero-allocation kernels, CUDA graphs:
  UNCHANGED (validated 4M ticks).
- Action space grows by the two gate actions (a_write, a_read) — motor budget,
  metabolic cost per action identical to existing moves (Rule 21: same measured
  host work class).
- R6 stable-demography requirement is enforced by ECONOMY ONLY (no artificial
  rescue): if extinction-reseed cycles dominate the first 10^5 ticks, that is a
  FALSIFICATION of the substrate's bootstrap, not a tuning target. Pre-registered
  kill: reseed-rate > 50% of deaths for 10^5 consecutive ticks -> halt and audit.

## 3. Constant Registry (Rule 17 / Rule 21 — BLOCKING)

No constant enters the codebase without a row here. A row without evidence is a
Rule-17 violation; the v1 Phase-E debt (query_to_move_ratio=500 labeled "grounded"
while its own model_params went unused; repro_cost=5.0; beta_cx/beta_cy/beta_xy
undocumented in probes) is the cautionary precedent. The registry:

| Constant | Class | Derivation / provenance | Default |
|----------|-------|--------------------------|---------|
| E_flop | [H] | measured FLOPs-to-joules on host (延续 Phase-E 1e-4 energy/FLOP measurement) | host-measured at startup |
| E_base, E_traffic | [H] | Phase-E measured metabolic coefficients, unchanged | 0.05, 2e-5 |
| K (memory slots) | [H] | RAM budget / b — hardware capacity, not performance-tuned | budget-derived |
| b (bits/slot) | [H] | same RAM budget split | budget-derived |
| W_fast rail +-4 | [S] | structural (identical to Phase-E; synapse amplitude ceiling) | 4.0 |
| T_ret = 1/sqrt(d) | [M] | mathematical invariant (softmax temperature for unit-norm keys) | derived |
| eta_f0, eps0, tau_trace, A_plus, A_minus, tau_homeo, E_threshold, metabolic_rate | [E] | genome-encoded, evolved — same class as Phase-E CPPN tail | evolved |
| beta(info) threshold | [M] | running median of eligibility magnitude (order statistic of the signal itself) | self-derived |
| surprisal prior | [E] | genome-encoded variance floor for novelty normalization | evolved |
| retrieval temperature T_ret | [M] | fixed invariant | 1/sqrt(d) |
| LLM query cost | [H] | 2 * N_params * T * E_flop (measured work; REPLACES the 500x flat ratio) | derived at runtime |
| reseed kill threshold 50% | [S] | structural kill-criterion parameter, pre-registered | 0.5 |
| Gate thresholds z=2.58, fidelity=95 | [S] | pre-registered statistical bounds (p<0.01; Exp-99 gate) | fixed |

**Prohibited patterns** (auto-reject in review): any `500.0`-style exchange ratio;
any hand-searched learning-rate ladder; any unclassified numeric literal in a
kernel; any threshold whose justification is "it worked".

---

## 4. The Four Pre-Registered Gates (binding; pass ALL before any scaling)

### Gate B-honest — Learning Is Load-Bearing, Under Clean Instruments

**Protocol (inherits the 2026-08-31 campaign, mandatory verbatim):**

- INDEPENDENT clones per arm (counterbalanced: no sequential STDP exposure of the
  ablation arm; the v1 order artifact must be structurally impossible).
- Full NULL controls per task family: DMTS shuffled non-match pair (memory score =
  diff_match - diff_null, FULL subtraction — no 0.5 coefficient, Rule 17); parity
  label-shuffle; every positive claim paired with its format- and marginal-matched
  control (Rule 20).
- >= 5 independent seeds, each in a FRESH PROCESS (Phase-E's in-process "10 seeds"
  was stimulus variance, not replication; this gate requires process isolation).

**Pass criterion:** paired delta (normal - ablation) with z >= 2.58 (p < 0.01) AND
100% positive seed deltas, on the NULL-subtracted metric, sustained across the
pre-registered window. Failure -> substrate falsified at Criterion B; no economy
levers may be added (Rule 23).

**Honest-expectation note:** the Phase-E honest series was noise around zero. This
gate is DESIGNED to kill the substrate quickly if Phase-5 does not actually fix
the mechanism — that is its function, not a formality.

### Gate D — In-Lifetime Pathway CONSTRUCTION (the remap test)

The delay-remap sandbox (Exp-34/35 instrument, retained verbatim): a frozen,
energy-pinned cohort; the correct mapping flips mid-lifetime on a clock visible to
NO sensory channel; per-bit accuracy split into swapped vs unchanged bits.

**Pass criterion:** swapped-bit accuracy must RISE from post-flip floor by >= 25
percentage points within 2,000 in-phase ticks, in EVERY phase cycle, while
unchanged bits hold >= 95. A genome cannot pre-encode the mapping (clock is
sensory-invisible) — only in-lifetime construction passes. NOLEARN control must
sit flat at the floor (else the task leaks).

**This is the gate STDP never passed and the Exp-35 teaching signal DID pass** —
it separates tuning (Exp-33) from building (Exp-35), which is precisely the
distinction the v1->v2 decomposition exposed as missing.

### Gate S — Consolidation Fidelity (the Exp-99 gate, per-slot)

**Protocol:** after a write->consolidate->write-again cycle on trained content,
measure static fidelity per slot: the fraction of consolidated (W_slow / MEM)
readbacks bit-identical to the originally written value across a no-input hold
period of 8,000 ticks (Exp-99's window, unchanged for comparability).

**Pass criterion:** mean per-slot fidelity >= 95.0 AND no single slot below 80.0
(Exp-99 failed at 92.34 mean; the per-slot floor is new — a single rotten slot can
poison a causal graph, so population-mean is not sufficient).

**Failure mode to watch (pre-registered):** the 2026-08-31 campaign showed the
v1 fast signal was mostly within-probe exposure. Gate S must therefore run on a
SECOND, untouched probe cohort after the training cohort rests 1,000 ticks —
consolidation measured across organisms, never re-measured on the trained
cohort itself (the order artifact, one level up).

### Gate R — Independent Replication (Series-1200 discipline, hardened)

**Protocol:** the confirmation pipeline that generated REP_CERT certificates,
upgraded with every 2026-08-31 lesson:

- Each seed: FRESH PROCESS, loading the frozen base checkpoint by SHA256;
  pre/post weight-hash drift must be 0.0%.
- Exact formula assertion per seed: |delta - (normal - ablation)| < 1e-6.
- Environmental invariants pinned (GENESIS_REFUGIUM=0, GENESIS_ARK=0,
  GENESIS_AUTO_REPRO as pre-registered per gate).
- Series-1200 seeds (1201+), >= 10 seeds, p < 0.01 (z >= 2.58), 100% positive
  deltas — the strict certificate gate, ALREADY IMPLEMENTED in phase_e_cert.py
  (z >= 2.58 and all_positive). Reuse that gate verbatim.
- **Hardening 1 (artifact quarantine):** no certificate file may exist before its
evidence; test outputs live in separate TEST_ARTIFACT files (the quarantined
  REP_CERT_LEVEL_1_5M.TEST_ARTIFACT.json is the standing precedent).
- **Hardening 2 (report completeness):** every gate report includes ALL fields,
favorable and unfavorable — mann_kendall_z, is_emergence_certified, rule18_passed
  included. Omitting an unfavorable field voids the report (three occurrences in
  the 2026-08-31 record; this clause exists because of them).
- **Hardening 3 (metric versioning):** every ledger record carries metric_version;
scale-changing edits bump the version and document the change point (the v1->v4
  history is the canonical example).

**Pass criterion:** certificate with level1_certified=true emitted from the LIVE
run at the pre-registered tick, or an honest REPLICATION_PENDING with full provenance.
BOTH outcomes are valid scientific artifacts. Neither may be massaged.

### 4.5 Instrumentation-First (R4 — the meta-gate over all four)

ORDER OF OPERATIONS IS BINDING. Before the FIRST organism is ever stepped:

1. The ledger (cortex_longitudinal.jsonl successor, `phase5_ledger.jsonl`) must
   already log: metric_version, tick, ts_utc, weight_sha256 (16-hex over the
   full [W,N,S] weight bytes), per-gate fields — with the v4 identity-aligned
   predictor (prev_alive & alive mask) from day one. The 0.5-frozen dead
   instrument bug and the world-0-only scope bug are both PRE-REGISTERED as
   forbidden regressions: a record where prediction_error == 0.5 exactly, or
   population_total_alive == population of a single world, fails CI.

2. Counterbalance + NULL controls committed BEFORE the first probe run (not
   retrofitted — retrofitted controls are what made v1 look alive for 30 records).

3. CI checks (continuous, in .github/workflows): ledger schema conformance;
   metric_version monotone non-decreasing; constant registry completeness
   (every numeric literal in kernels matched against section 3); report
   completeness (every field present, favorable or not).

**Stable-demography telemetry (R6):** every audit record carries alive counts
per world, reseed events, births/deaths — an extinction-reseed regime is a
DATA point, reported, never patched silently. The pre-registered kill
(section 2.4) triggers a halt, not a parameter tweak.

**Population sampling in probes:** stratified sampling across ALL worlds
(already true in clone_sample_organisms); every probe report additionally
records cohort composition — survivor-era vs fresh-reseed founders (age since
seed >/< median) — so the mixture confound observed on 2026-08-31 (survivors
eroded by STDP, fresh founders clean) is always analyzable.

---

## 5. Implementation Phasing (each phase gated by the previous)

**Phase 5a — Substrate skeleton + instruments (NO learning claims allowed).**
BatchedPopulation with dual-timescale tensors + MEM banks + gate actions; the
ledger, CI schema checks, and all NULL/counterbalance instruments running.
Exit: 10^5 ticks of stable demography (R6) under energy accounting with zero
instrument alarms. NO plasticity verdicts are read at this stage (instruments
must mature first — the v3 warm-up lesson).

**Phase 5b — Mechanism validation (sandbox-first, the Exp-34/35/43/46 ladder).**
Delay-remap sandbox (Gate D); depth-2/depth-3 memory sandbox via MEM (Gate H2);
consolidation cycles (Gate S). Sandbox = frozen cohort, energy-pinned, survival
decoupled (the proven instrument pattern from tests/remap_sandbox_probe.py).
Exit: Gates D and S pass on >= 5 sandbox seeds. Fail -> mechanism revision
BEFORE any live economy exists (cheap falsification, Rule 18's own discipline).

**Phase 5c — Live economy + Gate B-honest.** The full ALife economy with
grounded foraging; pre-registered window (10^6 ticks minimum for the first
read, then continuous). Exit: Gate B-honest (5 seeds, fresh processes).
Fail -> SUBSTRATE FALSIFIED, kill criterion executes, no economy levers.

**Phase 5d — Long-horizon + Gate R.** Only after B-honest: the deep-time run
(tick budget set by feasibility report, NOT a round number — 5M is a Phase-E
heritage; Phase-5's horizon is set by measured saturation curves) culminating
in the Series-1200 certificate attempt.

## 6. Module Layout (minimal diff from Phase-E server tree)

```
src/genesis/server/
  phase5_substrate.py      # BatchedPopulation5: dual W tensors, MEM banks,
                           #   gate actions, zero-alloc kernels, CUDA graphs
  phase5_memory.py         # MEM ops: keyed write/read, eviction, energy cost
  phase5_plasticity.py     # constructive third-factor rule (2.3), surprise gate
  phase5_probes.py         # counterbalanced harness + NULL controls (R4 verbatim)
  phase5_cert.py           # inherits phase_e_cert gate (z>=2.58, all_positive);
                           #   adds fresh-process seed runner, CI schema
  phase5_ledger.py         # v4-equivalent logger from day one (4.5)
```

Reuse policy: phase_e_plus.py (LLM bridge) and phase_e_ecology.py import
UNCHANGED. brain_server.py gains a substrate selector (`GENESIS_SUBSTRATE=phase5`)
with byte-identical Phase-E default (the proven compile-fingerprint discipline).

## 7. Known Risks & Honest Expectations (pre-registered)

| Risk | Evidence | Mitigation |
|------|----------|------------|
| Dual-timescale remains unstable even with R2 | Exp-99: signal real, fidelity 92.34 < 95 | Gate S per-slot floor kills fast; failure is DATA |
| Constructive rule drifts under live selection | Exp-42 step-size cliffs (DIV=4 collapse) | step = 1 microstate of 256 (the Rule-17-derived cap, kept verbatim) |
| MEM becomes a lookup reflex (no generalization) | Task-familiarity confound (Rule 20) | Gate R fresh-process replication on NOVEL content |
| Contrastive bridge degenerates to teacher | Rule 9 boundary | bridge output is sensory-only; loss is telemetry, never fitness |
| Economy reshaping temptation on failure | 29-experiment loop diagnosis (Ascent.md §1) | Rule 23 clause: falsification -> pivot, never levers |

**Explicit non-claims:** Phase-5 does NOT promise AGI. It promises a falsifiable
substrate hypothesis in which memory is an address, construction is possible,
and every verdict — positive or negative — carries cryptographic provenance.
If all four gates pass, the result is a validated learner worth scaling; if
any fails, the project owns a clean negative. Both advance the science.

---

## 8. Signatures

**Spec author (GLM 5.3, scientific auditor):** derived from the 2026-08-31
instrument campaign (v1->v4), the Exp-30..99 falsification record, and the live
ledger evidence at tick 3,940,000. Every requirement cites its forcing evidence.

**Implementer (Antigravity):** acceptance = all four gates wired and passing
CI BEFORE the first live economy run; report completeness clause (4.5, Hardening
2) acknowledged — an omitted unfavorable field voids the report.

**Change control:** amendments require a new document version and a ledger
citation; silent edits are the exact failure mode this campaign existed to end.

**Provenance anchor:** the honest Phase-E v2-v4 delta series
(+0.0117, -0.0078, -0.0166, +0.0303, +0.0049) and the quarantined TEST_ARTIFACT
certificate are permanent exhibits — what this substrate produced under clean
instruments, and why Phase-5 exists.
