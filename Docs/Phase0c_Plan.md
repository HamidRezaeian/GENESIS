# Phase 0c Plan — Synaptic Machinery

Date: 2026-08-13
Branch: biophysical/whole-neuron-cell-v0
Status: PLANNING COMPLETE — implementation not started
Scope: `src/biophysical/` (whole-neuron cell track)

## Context

- Phase 0a (passive cable) and Phase 0b (voltage-gated NaV1.6 / SKv3.1 channels,
  Hines 1984 staggered solver) are COMPLETE: 225 passed + 2 xfail.
- Phase 0c adds synaptic machinery: AMPA / NMDA / GABA_A receptors, spike-timing-
  dependent plasticity (STDP), biologically-placed synapses, and a validation suite.
- Goal: input integration and synaptic plasticity on the L5 pyramidal cell.
- Target: ~280-320 total tests (add ~85 new).

## 1. Terrain summary (what 0a/0b established)

| Convention | Where | Implication for 0c |
|---|---|---|
| Mechanisms = current-density sources (A m^-2), inward-positive, `I = -g·p·(V - E_rev)` | `core/interfaces.py`, `channels/base_channel.py` | Synapses subclass `AbstractMembraneMechanism`, same sign convention |
| Hines (1984) staggered split: gates at V^n, current at V^{n+1}; conductance folded into matrix diagonal + g·E into RHS | `simulation/active_solver.py` | Synaptic conductance joins the same g/I accumulation; Mg2+ block frozen at V^n per step |
| Region-based placement via a Distribution class + `DensityProvider` Protocol (Phase 0e hook), idempotent attach | `channels/channel_distributions.py` | Mirror exactly with a `SynapseDistribution` |
| Parameters live in `core/constants.py` namespaces (`MEM`, `CHAN`), literature-cited | `core/constants.py` | Add a `SYN` namespace |
| Honest-fail validation: `ValidationReport.add_check`, known findings -> xfail, never masked | `validation/report.py`, `neuron_cell.validate_active()` | Same pattern for `validate_synapses()` |
| Facade pattern: `build(active=True)` opt-in, passive default untouched | `neuron_cell.py` | `build(synaptic=True)`; default builds remain bit-identical |

Note: `core/interfaces.py`'s docstring lists Phase 0c receptor ABCs
(`AMPAReceptor`, `NMDAReceptor`, `GABAaReceptor`, `GABAbReceptor`) as
"already defined" — they are not. Step 1 writes `AbstractSynapse` and fixes
this docstring drift (Rule 16).

## 2. Key design decisions

1. **Synapses are membrane mechanisms, not voltage-gated channels.**
   New ABC `AbstractSynapse(AbstractMembraneMechanism)` + concrete base
   `SynapseReceptor`. Event-driven point processes (`deliver_spike(t)`) with a
   conductance waveform `g(t)`, not HH gates. `is_linear = False`.

2. **Solver integration extends `ActiveSolver`, gated by a build flag.**
   Add `_index_synapses()` alongside `_index_channels()`; synaptic g contributes
   to the same refactor-tolerant matrix path. `NeuronCell.build(synaptic=True,
   active=False)` must work (passive cable + synapses = clean, fast EPSP/IPSP
   validation); `active=True` + `synaptic=True` enables AP-coupled and
   NMDA-nonlinear tests.

3. **NMDA Mg2+ block evaluated at V^n (frozen per step).**
   `B(V) = 1 / (1 + ([Mg2+]_o / 3.57 mM) * exp(-0.062 * V_mV))`
   (Jahr & Stevens 1990). Evaluating at V^n is the only choice consistent with
   the Hines stagger; document it in the module docstring.

4. **STDP is a separate object composed onto a synapse, not baked into receptors.**
   An `STDPRule` consumes explicit pre/post spike-time lists (unit-testable
   without any APs — critical given FINDING-1) and scales the synapse's `g_peak`.
   Distinct from the legacy engine's reward-modulated R-STDP
   (`Docs/RSTDP_Implementation_Guide.md`): different substrate, different rule;
   one-line cross-reference only, no code sharing.

5. **GABA_A reversal equals leak reversal (E = -70 mV = `MEM.E_leak_V`).**
   At rest, GABA_A is a near-pure *shunt*: zero driving force, zero
   hyperpolarizing IPSP. This is biophysically correct but has a validation
   consequence (§5): IPSP amplitude must be measured from a depolarized
   baseline, and a separate shunting check (EPSP attenuation) validates
   inhibition at rest. Flag prominently — it will otherwise look like a bug.

## 3. File-by-file build plan (6 steps, mirroring 0b's Step cadence)

### Step 1 — Core constants & interfaces
- `core/constants.py`: add `SYN` namespace (parameters in §4), each constant
  with a citation comment.
- `core/interfaces.py`: add `AbstractSynapse` (extends
  `AbstractMembraneMechanism` with `deliver_spike(t_s)`, `pending_events`,
  `g_peak_S`, `waveform(t)`, `plasticity` slot); fix the "already defined"
  docstring drift.

### Step 2 — New subpackage `src/biophysical/synapses/` (mirrors `channels/`)
- `base_synapse.py` — `SynapseReceptor`: double-exponential waveform
  `g(t) = g_peak * w * K * (exp(-t/tau_decay) - exp(-t/tau_rise))`,
  normalization factor K so peak = 1; event queue; `current(V, t)`;
  `state_dict` / `reset`.
- `ampa.py` — fast excitatory, E = 0 mV.
- `nmda.py` — slow excitatory, E = 0 mV, × B(V^n) Mg2+ block.
- `gabaa.py` — fast inhibitory, E = -70 mV.
- `events.py` — `SpikeTrain` / Poisson generator (seeded) + per-synapse event
  queue; the synaptic analogue of `current_clamp.py`.
- `synapse_locations.py` — `SynapseDistribution` mirroring
  `ChannelDistribution`: excitatory (AMPA+NMDA co-localized) on `BASAL`,
  `APICAL_OBLIQUE`, `APICAL_TUFT`; inhibitory (GABA_A) on `SOMA` + proximal
  `APICAL_TRUNK` (+ optional AIS); never on `MYELIN` / `NODE` /
  `AXON_TERMINAL`; seeded RNG placement; idempotent apply; `SynapseProvider`
  Protocol as the Phase 0e hook.
- `plasticity.py` — `STDPRule`: pre/post eligibility traces,
  `dw = A+ * exp(-dt/tau+)` (pre->post, LTP),
  `dw = -A- * exp(-dt/tau-)` (post->pre, LTD),
  soft-bounded in `[0, w_max]`, nearest-spike pairing.

### Step 3 — Solver support
- `simulation/active_solver.py`: `_index_synapses()`, event delivery before
  gate update, synaptic conductance into `_collect_conductances()` (same
  refactor logic), `has_synapses` / `n_synapses` introspection. No behavioral
  change when zero synapses exist.
- Optional `simulation/synaptic_protocol.py`: declarative stimulation protocol
  (synapse × spike-train) paralleling `CurrentClampProtocol` / `MultiProtocol`.

### Step 4 — NeuronCell facade
- `build(synaptic=True, distribution=None, seed=...)`; `run_synaptic(protocol,
  ...)`; `synapses` property; passive default preserved exactly; docstring
  quick-start extended (matching existing style).

### Step 5 — Validation
- `validation/synaptic_validation.py` + `NeuronCell.validate_synapses()`
  (spec in §5).

### Step 6 — Tests + docs
- 9 new test files (§6), then update `Docs/ARD.md`, `Docs/Roadmap.md`,
  `Docs/Result.md`, `Docs/RESUME_NEXT_SESSION.md` per the repo's standing
  rules, and `src/biophysical/__init__.py` phase status.

## 4. Parameters (proposed `SYN` constants — literature defaults)

| Param | AMPA | NMDA | GABA_A |
|---|---|---|---|
| E_rev | 0 mV | 0 mV | -70 mV |
| tau_rise | 0.2 ms | 5 ms | 0.3 ms |
| tau_decay | 3 ms | 60 ms | 8 ms |
| Unitary g_peak | ~0.5 nS | ~0.7 nS | ~1.0 nS |

STDP (Bi & Poo 1998): `A+ ~ 1.0`, `tau+ ~ 16.8 ms`, `A- ~ 0.5`,
`tau- ~ 33.7 ms` (relative units, soft bounds).
Mg2+: `[Mg2+]_o = 1.2 mM`.
All Q10 / temperature handling consistent with the `MAMMALIAN_MS96` precedent.

## 5. `validate_synapses()` — proposed check suite

| Check | Target | Notes |
|---|---|---|
| `epsp_amplitude_soma` | 0.1-0.5 mV unitary | Passive build, single basal/apical synapse |
| `epsp_time_course` | t_peak 5-15 ms at soma | Dendritic filtering widens vs. local EPSP |
| `ipsp_amplitude` | 0.5-3 mV hyperpolarizing | From depolarized baseline (-60 mV) — because E_GABA_A = E_leak |
| `ipsp_shunting_at_rest` | co-located EPSP attenuated >= 30% | The correct at-rest inhibitory signature |
| `nmda_mg_block` | B(-70 mV) ~ 1-3 %, B(-20 mV) ~ 30-50 % | Analytic check, no solver needed |
| `nmda_voltage_dependence` | supralinear I-V in -40..0 mV | Frozen-per-step B(V^n) documented |
| `temporal_summation` | paired-pulse (d=10 ms) ratio > 1.2 | NMDA-dominated summation at d=40-60 ms |
| `spatial_summation` | ~linear at passive soma; supralinear with NMDA | Supralinearity check is active-mode -> honest-fail aware |
| `stdp_ltp` / `stdp_ltd` | sign correctness by dt sign | Explicit spike lists, no APs required |
| `stdp_curve_fit` | tau+, tau- within ±25 % of Bi & Poo | Fit over ~11 dt values |
| `weight_bounds` | w stays in [0, w_max] over 10^3 pairings | |

## 6. Test plan (~86 new tests -> ~311 + xfail total, inside the 280-320 band)

| File | ~Tests |
|---|---|
| `test_synapse_base.py` (waveform shape, normalization, event queue, reset/state_dict) | 8 |
| `test_ampa_receptor.py` | 10 |
| `test_nmda_receptor.py` (incl. Mg2+ block curve) | 12 |
| `test_gabaa_receptor.py` (incl. shunting behavior) | 8 |
| `test_synapse_locations.py` (region rules, counts, seeded determinism, idempotence) | 10 |
| `test_synaptic_solver.py` (event timing, conductance folding, finite traces, passive-regression) | 10 |
| `test_stdp.py` (LTP/LTD sign, windows, bounds, curve fit, nearest-spike) | 14 |
| `test_synaptic_integration.py` (facade API, EPSP/IPSP end-to-end, summation) | 8 |
| `test_synaptic_validation.py` (report structure, all checks present) | 6 |

Passive-region and `build()` default regressions extend `test_integration.py`'s
existing pattern (exact-type check on the solver). Any active-mode synaptic
test that depends on repolarization gets the established honest-fail / xfail
treatment and cites FINDING-1 / FINDING-2.

## 7. Risks & watch-items

- **FINDING-1 (h-gate swap)**: does not touch passive-regime EPSP/IPSP/STDP
  unit tests; only AP-coupled integration tests are exposed -> xfail
  candidates, exactly per 0b precedent.
- **E_GABA_A = E_leak**: the "IPSP amplitude" requirement needs the
  depolarized-baseline protocol in §5; call this out in the validation report
  messages so it reads as design, not failure.
- **Refactor tolerance interplay**: synaptic conductance transients are fast;
  verify `refactor_rel_tol = 0.10` does not miss AMPA rising edges (likely
  needs per-step conductance refresh during event windows — Step 3 includes a
  test for this).

## 8. Execution order

Steps 1-2 -> 3 -> 4 -> 6 (tests written with each step, 0b-style) -> 5 ->
docs sweep.

Out of scope for 0c (later phases): Ca2+ dynamics & Ca-dependent plasticity
(0d), gene-expression-driven receptor densities (0e, via `SynapseProvider`),
GABA_B, neuromodulated / reward-gated plasticity (legacy R-STDP lineage).
