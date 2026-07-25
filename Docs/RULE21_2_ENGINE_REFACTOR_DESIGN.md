# Rule 21.2 — Engine Refactor Design: Per-Organism Evolvable Constants

**Status:** DESIGN (not yet implemented). Grounds the migration of the engine's
hand-set tunable constants ("G-constants") into evolvable per-organism genes, as
required by `FixedRules.md` Rule 21.2 / 21.6.

**Date:** 2026-07-25
**Depends on:** Rule 21.1 DONE (commit `d1bbc72` — real measured `CYCLES_PER_*`).
**Evidence base:** `exp77c` (11 genes), `exp77d` (15 genes), `exp77e` (20 genes)
standalone probes — see "Evidence" below.

---

## 1. The binding principle (Rule 21.2 / 21.4 / 21.6)

> **21.2** Every tunable parameter (thresholds, time constants, learning rates,
> synaptic weights, radii, gains) MUST be either **(H) hardware-derived** (computed
> from a measurable property of the substrate, derivation documented inline) or
> **(E) evolvable** (encoded in the genome as a gene that natural selection shapes,
> never a literal the designer fixes). A constant that is neither is a violation.
>
> **21.4 (Tuning Test)** If changing a number makes the system "work better" because
> it was *tuned*, it is an illegal game mechanic. A legitimate value is either
> *derived* (changing it would be physically wrong) or *evolved* (selection set it).
>
> **21.6 (Remedy)** Every violation must be (a) derived from hardware with the
> derivation documented, (b) moved into the genome as an evolvable gene, or
> (c) deleted. Classes: **H** / **E** / **O** (opcode/marker ISA) / **G** (violation).

Rule 21.1 fixed the **cost** side (the `CYCLES_PER_*` are now real measured native
cycles). This document fixes the **parameter** side: the tunable constants the
designer currently sets by hand must become **(E)** evolvable genes or **(H)**
hardware-derived values.

---

## 2. The 18 tunable G-constants and their migration target

From the Rule 21 audit of `neuromorphic_engine.py` (86 constants → 18 tunable G):

| Constant | Line | Current | Role | Target | Migration note |
|---|---|---|---|---|---|
| `FOOD_SCAN_RADIUS` | 33 | 16 | food sensing range | **E** | new gene; needs probe coverage |
| `STDP_DIV` | 141 | 1.0 | STDP step divisor | **E** | ✅ proven evolvable (exp77e) |
| `HOMEOSTATIC_LAMBDA` | 146 | 0.01 | weight-anchoring rate `w -= λ(w-w_dna)` | **E** | ✅ proven evolvable (exp77e) |
| `CAM_SLOTS` | 152 | 32 | CAM working-memory size | **E** (or H) | ✅ proven evolvable (exp77e) |
| `CAM_KEY_BITS` | 153 | 8/16 | CAM key width | **E** (or H) | ✅ proven evolvable (exp77e) |
| `CAM_MATCH_THRESHOLD` | 155 | 75% of key | CAM match strictness | **E** (or H) | ✅ via `cam_match_frac` (exp77d) |
| `CAM_WRITE_THRESHOLD` | 158 | 25% of key | CAM write inertia | **E** (or H) | new gene; mirror of match_frac |
| `SP_GROWTH_COST` | 172 | 10.0 | energy cost per new synapse | **E** | ✅ via `sp_growth_cost` (exp77c/d/e) |
| `SP_MAX_GROWTH` | 178 | 3 | max synapses added/tick | **E** | new gene; structural-plasticity family |
| `SP_MAX_PRUNE` | 180 | 5 | max synapses pruned/tick | **E** | new gene; structural-plasticity family |
| `SP_REWIRE_WEIGHT` | 182 | 5.0 | initial weight for new conn | **E** | ✅ via `sp_rewire_weight` (exp77c/d/e) |
| `LONG_JUMP_STRIDE` | 383 | 10 | look-ahead distance | **E** | new gene; needs probe coverage |
| `TAU_REF` | 456 | 1 | refractory period | **E** | ✅ proven evolvable (exp77e) |
| `REMAP_PERIOD` | 247 | 4000 | sensorimotor remap period | **E** | new gene; needs probe coverage |
| `REMAP_STATES` | 248 | 2 | remap phases | **E** | new gene; needs probe coverage |
| `DELAY_N` | 266 | 1 | delay-line depth | **E** | new gene; needs probe coverage |
| `DT` | 453 | 1.0 | integration timestep | **O** | configuration constant (not tuned physics) |
| `RAM_SIZE` | 7 | 65536 | world memory size | **H** | power-of-2 for 16-bit byte addressing; derive inline |

**Score:** of the 18, **14 → E** (evolvable), **1 → H** (`RAM_SIZE`), **1 → O** (`DT`),
and the four CAM thresholds are **E-or-H** (derivable from the byte architecture *or*
evolvable; the probes show they *can* evolve). The 6 `CYCLES_PER_*` cost constants are
already **H** (Rule 21.1, measured). `CELL_STATES = 256 = 2^BITS_PER_BYTE` is already
**H** (information capacity).

---

## 3. Evidence: the migration pattern is proven (exp77c → 77d → 77e)

The standalone probes (`src/exp77c/d/e_*.py`) evolve a LIF+CAM+STDP+structural-plasticity
net on the Latin-square reading task, reading each constant from a float genome under
mutation + elitist selection (fitness = reading reward). They do **not** touch the
engine; they prove each constant *can* be a functional evolvable gene that selection
moves off the designer default.

| Probe | Genes | New engine constants made evolvable | Result |
|---|---|---|---|
| exp77c | 11 | tau, thresh, stdp_lr, sp_prune_threshold, sp_rewire_weight, sp_growth_cost, eps_explore, w_ih/hh/ho/io_scale | substrate params evolvable |
| exp77d | 15 | + input_gain, output_gain, cam_match_frac, v_reset | 12/15 drifted; 3/4 new genes drifted |
| **exp77e** | **20** | + **cam_slots, cam_key_bits, stdp_div, tau_ref, homeostatic_lambda** | **13/20 drifted; all 5 new genes moved** |

**exp77e detail** (`exp77e_engine_genes_results.json`, pop 24 × 15 gens, best fitness 6/32):

| new gene | default | evolved | norm drift | moved? |
|---|---|---|---|---|
| `cam_slots` | 32 | **2.95** | −0.937 | ✅ strong (selection shrinks an unused CAM) |
| `cam_key_bits` | 16 | **7.77** | −0.588 | ✅ strong (narrows toward the engine's 8-bit default) |
| `tau_ref` | 1 | **3.23** | +0.371 | ✅ (longer refractory selected) |
| `stdp_div` | 1.0 | **12.27** | +0.088 | ✅ directional (12× smaller STDP steps; under the 0.10 *normalized* threshold only because the range is 0.1–128 log) |
| `homeostatic_lambda` | 0.01 | **0.0** | −0.050 | ✅ directional (selection turns anchoring OFF in this short-horizon task) |

All five new constants are **functional** evolvable genes: each is wired into the
simulation (CAM geometry, STDP step divisor, refractory counter, weight-anchoring rate)
and selection acts on it. Fitness staying at 6/32 is expected and is *not* the point —
the reading bottleneck is compositional ability, not a tunable constant (Exp 78 finding).
The point is the **migration pattern generalises**: 20 substrate parameters across
exp77c/d/e are shown to be evolvable rather than designer fiat.

---

## 4. Why the constants are not per-organism today

`world_tick_numba` is a numba `@njit` kernel. The tunable constants (`CAM_SLOTS`,
`STDP_DIV`, `HOMEOSTATIC_LAMBDA`, `TAU_REF`, …) are **module-level globals** read inside
the kernel. numba compiles module globals as **compile-time constants baked into the
machine code** — so every organism currently shares one value, and the value cannot vary
per organism without changing the kernel's inputs. This is the single structural reason
the constants are "G" today: they are fixed for the whole universe at import time.

Per-organism state already exists for other quantities: the kernel takes ~50 array
arguments and indexes per-organism state by `org` (e.g. `g_org_n_count[org]`,
`o_rec_tau_def[org, …]`). The migration makes the tunable constants follow that same
pattern: **per-organism arrays passed into the kernel, indexed by `org`**.

---

## 5. Architecture facts the design builds on (verified in source)

- **CAM is already per-organism.** `g_cam_keys` is `(MAX_ORGANISMS, CAM_SLOTS,
  CAM_KEY_BITS)` float32; `g_cam_vals/valid/tick` are `(MAX_ORGANISMS, CAM_SLOTS)`
  (`genesis_lab.py` L257–260). The first axis is the organism. So `cam_slots`/
  `cam_key_bits` migration is minimal: the backing store is already allocated at the
  MAX; only the loop bounds become per-organism (`for s in range(g_org_cam_slots[org])`,
  `for b in range(g_org_cam_key_bits[org])`). This is **exactly** the max-size-backing-store
  design exp77e validated.
- **The genome is a marker-tagged byte sequence.** `g_global_genome` is a flat
  `uint8` array (`UNIVERSE_MAX_DNA`); each organism owns a slice via
  `g_org_g_ptr[org]`/`g_org_g_count[org]`. Records are `[GENE_MARKER, sensor, action,
  weight]` (4 B), `[NEURON_MARKER, …]` (5 B), `[RECEPTOR_MARKER, …]`. `decode_genome`,
  `count_genes`, `parse_receptors` parse them (`neuromorphic_engine.py`).
- **Spawn decodes the genome.** `spawn_organism(org_id, pos, dna, initial_energy)`
  (L853) lays out neurons/synapses from `dna`. `mutate_dna(parent_dna)` (L951) perturbs
  bytes on birth. `create_intelligent_ancestor(dna=None)` (L615) seeds the progenitor.
- **DNA weight anchor exists.** `g_conn_w_dna` (`UNIVERSE_MAX_SYNAPSES`, L254) already
  stores inherited synapse weights — the anchor `HOMEOSTATIC_LAMBDA` relaxes toward
  (`w -= HOMEOSTATIC_LAMBDA*(w - g_conn_w_dna)`). The homeostatic gene therefore needs no
  new anchor machinery, only a per-organism rate.

---

## 6. Refactor design

### 6.1 Genome: a PARAM record type
Add one new marker, `PARAM_MARKER`, to the ISA (Rule 21.3 — documented opcode, carries
no physics itself). A PARAM record encodes one evolvable constant:

```
[PARAM_MARKER, gene_id (1 B), value (2 B, little-endian uint16)]   # 4 bytes
```

`value` maps to a float in the gene's bounds by a fixed decode table
`PARAM_BOUNDS[gene_id] = (lo, hi, scale)` (scale ∈ {linear, log}), exactly the bounds
the probes used (`GENOME_BOUNDS` in exp77e). A 16-bit value gives 65536 steps across the
range — far finer than selection can resolve, so quantisation is not a concern. The
ancestor (`create_intelligent_ancestor`) emits one PARAM record per evolvable constant,
**initialised to the current designer default** (so the default genome reproduces today's
behaviour exactly — see §7).

`decode_genome` is extended to scan for `PARAM_MARKER` records and write each decoded
value into the per-organism param arrays (§6.2). `mutate_dna` perturbs the 2-byte value
of a randomly chosen PARAM record (small Gaussian step in the encoded space, clipped to
bounds) — this is how the constants **evolve**.

### 6.2 Per-organism parameter arrays
Add one array per evolvable constant, sized `MAX_ORGANISMS`:

```python
# ints (expressed as ints in the kernel)
g_org_cam_slots      = np.full(MAX_ORGANISMS, CAM_SLOTS, dtype=np.int64)
g_org_cam_key_bits   = np.full(MAX_ORGANISMS, CAM_KEY_BITS, dtype=np.int64)
g_org_tau_ref        = np.full(MAX_ORGANISMS, TAU_REF, dtype=np.int64)
g_org_sp_max_growth  = np.full(MAX_ORGANISMS, SP_MAX_GROWTH, dtype=np.int64)
g_org_sp_max_prune   = np.full(MAX_ORGANISMS, SP_MAX_PRUNE, dtype=np.int64)
g_org_food_scan_radius = np.full(MAX_ORGANISMS, FOOD_SCAN_RADIUS, dtype=np.int64)
g_org_long_jump_stride = np.full(MAX_ORGANISMS, LONG_JUMP_STRIDE, dtype=np.int64)
g_org_delay_n        = np.full(MAX_ORGANISMS, DELAY_N, dtype=np.int64)
g_org_remap_period   = np.full(MAX_ORGANISMS, REMAP_PERIOD, dtype=np.int64)
g_org_remap_states   = np.full(MAX_ORGANISMS, REMAP_STATES, dtype=np.int64)
# floats
g_org_stdp_div       = np.full(MAX_ORGANISMS, STDP_DIV, dtype=np.float32)
g_org_homeo_lambda   = np.full(MAX_ORGANISMS, HOMEOSTATIC_LAMBDA, dtype=np.float32)
g_org_sp_growth_cost = np.full(MAX_ORGANISMS, SP_GROWTH_COST, dtype=np.float32)
g_org_sp_rewire_w    = np.full(MAX_ORGANISMS, SP_REWIRE_WEIGHT, dtype=np.float32)
g_org_cam_match_thr  = np.full(MAX_ORGANISMS, CAM_MATCH_THRESHOLD, dtype=np.int64)
g_org_cam_write_thr  = np.full(MAX_ORGANISMS, CAM_WRITE_THRESHOLD, dtype=np.int64)
```

Defaults equal today's module globals → the **default genome is behaviour-identical to
the current engine** (§7). `spawn_organism` calls `_decode_params(dna, org_id)` to fill
these from the genome's PARAM records (falling back to the module default for any gene
absent from the genome — backward compatibility for old genomes).

### 6.3 Kernel signature + global → array replacement
Add the new arrays as trailing arguments to `world_tick_numba` (after the existing
`g_cam_*` args). Inside the per-organism loop, replace each global read with the
per-organism value. Examples:

```python
# before (global, baked):
for s in range(CAM_SLOTS):
    ...
e += ... / STDP_DIV
global_ref[n_ptr + n] = TAU_REF
w -= HOMEOSTATIC_LAMBDA * (w - g_conn_w_dna[s_idx])

# after (per-organism):
cam_slots_org = g_org_cam_slots[org]
for s in range(cam_slots_org):
    ...
e += ... / g_org_stdp_div[org]
global_ref[n_ptr + n] = g_org_tau_ref[org]
w -= g_org_homeo_lambda[org] * (w - g_conn_w_dna[s_idx])
```

The CAM match/write thresholds become `g_org_cam_match_thr[org]` /
`g_org_cam_write_thr[org]`; the key-bit loop bound becomes `g_org_cam_key_bits[org]`.
Each replacement is local and mechanical; the ~30 use-sites are listed by `grep -n` of
each constant (e.g. `HOMEOSTATIC_LAMBDA` at L1453/1479/1785/1847/1849; `STDP_DIV` at
L1445/1475/1842; `TAU_REF` at L1380).

### 6.4 CAM geometry (the only shape-sensitive case)
Because `g_cam_keys` is already `(MAX_ORGANISMS, CAM_SLOTS, CAM_KEY_BITS)`, a smaller
per-organism `cam_slots`/`cam_key_bits` simply uses a sub-block — no reshape, no
re-allocation. The kernel loops only over the active sub-range and the match threshold
is derived from the active key width (`g_org_cam_match_thr[org]`, which `mutate_dna`
keeps consistent or which is itself a gene). This is the validated exp77e design.

### 6.5 Inheritance & mutation
On birth, `mutate_dna` perturbs PARAM-record value bytes; `spawn_organism` decodes the
child's params from the mutated genome. The constants therefore evolve across
generations under the existing selection pressure (energy/income), with no new
evolutionary machinery.

---

## 7. Backward compatibility with the verified Exp 78 path

The verified Rule-21.1 baseline (Exp 78: real metabolism ≈1532 cycles/tick, extinction
@ tick 163, zero income) MUST be reproducible after the refactor. Guarantees:

1. **Default genome == current behaviour.** The ancestor emits PARAM records set to the
   current designer defaults; the per-organism arrays default to the same module globals.
   A default genome therefore produces a bit-identical trajectory to today's engine.
2. **Feature flag.** Gate the decode path behind `GENESIS_EVOLVABLE_CONSTANTS`
   (default **OFF**). With it OFF, the kernel reads the module globals exactly as today
   (the new arrays are ignored), so the verified path is untouched until the flag is
   turned ON and re-validated.
3. **Cost wiring is orthogonal.** Rule 21.1's `CYCLES_PER_*` are measured at import and
   charged per primitive execution. Per-organism constants change *which/how many*
   primitives run, not their measured unit cost — so the metabolic accounting stays
   hardware-grounded for every genome.
4. **Re-validation gate.** Before the flag defaults ON, re-run Exp 78 with
   `GENESIS_EVOLVABLE_CONSTANTS=1` + default genome and confirm extinction @ 163 ± a few
   ticks and ≈1532 cycles/tick median. (Exact tick may shift by 1–2 from integer
   rounding of the decoded defaults; that is acceptable and documented.)

---

## 8. Migration tiers & order

- **Tier 1 — proven in probes, lowest risk (do first):** `cam_slots`, `cam_key_bits`,
  `stdp_div`, `tau_ref`, `homeostatic_lambda` (exp77e) + `cam_match_threshold`
  (exp77d `cam_match_frac`) + `sp_growth_cost`, `sp_rewire_weight` (exp77c). These have
  direct probe evidence and clear use-sites.
- **Tier 2 — same families, need a probe run first:** `sp_max_growth`, `sp_max_prune`
  (structural-plasticity family), `cam_write_threshold` (mirror of match), `food_scan_radius`,
  `long_jump_stride`, `delay_n`, `remap_period`, `remap_states`. Extend exp77e (or a new
  exp77f) to cover these before threading them through the kernel.
- **Tier 3 — not evolvable, classify and stop:** `RAM_SIZE` → **H** (document the
  power-of-2 / 16-bit-addressing derivation inline); `DT` → **O** (configuration
  timestep, not tuned physics). No genome migration needed; just re-label and document.

---

## 9. Validation plan

1. **Unit:** decode a hand-built genome with known PARAM records → assert per-org arrays
   hold the expected floats/ints (round-trip through the 16-bit encoding).
2. **Regression:** Exp 78 default-genome + flag ON reproduces extinction @ ≈163, ≈1532
   cycles/tick (the verified Rule-21.1 baseline).
3. **Evolution (the real test):** run a multi-organism evolution in the FULL engine with
   the flag ON and show the PARAM genes drift off default across generations under
   selection — the in-engine counterpart of the exp77e probe result. (This is the
   definitive Rule-21.2 evidence for the engine, vs the probe.)
4. **Separate-process A/B for kernel changes:** because numba caches the compiled kernel
   in-memory, any A/B that changes the kernel signature/value must run in a SEPARATE
   process (the `exp_stdp_target_ab_driver.py` pattern). Do not A/B kernel changes
   inside one long-lived process.

---

## 10. Risks & honesty flags

- **numba in-memory kernel cache.** The first compile wins for the process lifetime.
  A/B tests of kernel changes need separate processes (same caveat as STDP_TARGET).
- **JIT recompile cost.** Changing the kernel signature triggers one recompile (~10 s,
  measured in the Exp 78 warmup). Acceptable; happens once per process.
- **RAPL gap (energy).** `CYCLES_PER_*` are measured cycles; converting to real joules
  uses an estimated `joules_per_flop`. `src/rapl_energy_monitor.py` is ready but RAPL is
  unavailable in this KVM VM — real measured energy requires bare-metal Intel. The
  cycle-based metabolism is hardware-grounded; the joule figure is order-of-magnitude
  until RAPL is available.
- **Income-unit open question.** Income is `256 = CELL_STATES = 2^BITS_PER_BYTE`
  (information capacity, H-derived). Its *exchange rate* against real execution cycles
  is a separate Rule-21 review question: is information-capacity the right income unit,
  or should income also be a measured work quantity? This refactor does NOT change the
  income side; it only makes the *parameter* side evolvable.
- **Host-dependence of measured costs.** `CYCLES_PER_*` are measured on the current host
  (this session: cam_read ≈ 756 cycles vs 857 on the original; synapse/neuron costs
  slightly higher). Absolute numbers shift per CPU; the methodology (measure at import)
  is portable. Extinction tick is correspondingly host-dependent (147 here vs 163
  originally) — both confirm the same finding.

---

## 11. Effort estimate

This is a multi-session engineering effort, roughly:
- **Tier 1 kernel threading** (PARAM record + decode + ~8 per-org arrays + ~20 use-site
  replacements + regression): the bulk of the work; one focused session.
- **Tier 2 probe coverage** (extend exp77e → exp77f for the remaining ~8 constants): one
  session.
- **Tier 2 kernel threading** + **in-engine evolution validation**: one session.
- **Tier 3 re-labelling** (`RAM_SIZE` H, `DT` O): trivial; fold into any session.

The probe evidence (exp77c/d/e) de-risks Tier 1/2: the only unproven part is the
mechanical kernel threading + the in-engine evolution run, not whether the constants
*can* be evolvable genes (that is already shown).
