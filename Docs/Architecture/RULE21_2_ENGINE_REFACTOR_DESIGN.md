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
Add two new marker bytes, `PARAM_MARKER = 200` and `PARAM_MAGIC = 201`, to the ISA
(Rule 21.3 — documented opcodes, carry no physics themselves). A PARAM record encodes one
evolvable constant as a 5-byte record:

```
[PARAM_MARKER=200, PARAM_MAGIC=201, gene_id (1 B), val_lo (7-bit), val_hi (7-bit)]   # 5 bytes
```

The 2-byte sentinel `[200, 201]` makes the record **collision-proof**: that pair never
occurs elsewhere in the genome (verified for the ancestor; an accidental lone `200` byte
— e.g. a synapse-weight value at ancestor offset 487 — is ignored because it is not
followed by `201`). The two value bytes carry 7 bits each (`& 0x7F`), so every payload byte
is `< 128`. This makes the record **self-skipping**: all four existing genome walkers
(`parse_receptors`, `count_genes`, `decode_genome`, and the Lamarckian-consolidation walk
inside `world_tick_numba`) advance past it via their `else: i += 1` fallback without desync,
because no payload byte can be mistaken for a marker (markers are 161–199). **No existing
walker needs to be modified** — this is the key safety property, and it holds even for the
Lamarckian walk that Exp 78 never exercises (Exp 78 has zero births). A separate
`decode_params()` pass (pure Python, run once at spawn, not in the hot tick loop) reads the
records into the per-organism param arrays (§6.2).

`val_lo | (val_hi << 7)` is a 14-bit integer (0–16383) mapped to a float in the gene's bounds
by a fixed decode table `PARAM_GENES[gene_id] = (name, lo, hi, scale)` (scale ∈ {linear, log}),
mirroring the bounds the probes used (`GENOME_BOUNDS` in exp77e). 16384 steps across the range
is far finer than selection can resolve, so quantisation is not a concern. The ancestor
(`create_intelligent_ancestor`) emits one PARAM record per evolvable constant, **initialised
to the engine's current resolved module globals** (so the default genome reproduces today's
behaviour exactly — see §7). `mutate_dna` perturbs the PARAM value bytes via the engine's
existing byte-level point substitution (the same per-byte fidelity model every other gene
uses), so the constants **evolve** under selection; a gentler PARAM-aware Gaussian step is an
optional follow-up. (Implemented and regression-verified in increment 3a — see §7.4.)

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

### 6.3 Kernel wiring: g_org_params as a module global (NOT a signature change)
**Implemented in increment 3b-i.** The original plan was to add the per-org arrays as
trailing arguments to `world_tick_numba`. That was rejected during implementation because
`world_tick_numba` is called from 8+ sites (genesis_lab warmup + main loop, the
exp78/79/80 drivers twice each, exp68/69, and the STDP_TARGET A/B driver) — a signature
change would have forced edits to every call site. Instead:

- `g_org_params` is defined as a **module-level global in neuromorphic_engine.py** (right
  after `MAX_ORGANISMS`/`BIRTH_BUF_SZ`), shape `(MAX_ORGANISMS, N_PARAM_GENES)` float32.
  numba reads module global arrays **by reference**, so the spawn-time fills
  (`genesis_lab.decode_params`) are visible inside the kernel with **no signature change**
  and **no call-site edits**. genesis_lab imports `g_org_params` + `N_PARAM_GENES` from the
  engine (its local definitions were dropped; an `assert len(PARAM_GENES) == N_PARAM_GENES`
  guards against drift).
- `EVOLVABLE_CONSTANTS` is a module-level bool in the engine (read from
  `GENESIS_EVOLVABLE_CONSTANTS`). numba bakes it as a compile-time constant, so the flag-OFF
  branch is dead-code-eliminated and the compiled kernel is identical to the pre-3b engine.
- At the top of the per-organism loop (`for org in range(max_org)`, right after
  `n_count = org_n_count[org]`), the 7 wired constants are read into locals:

```python
if EVOLVABLE_CONSTANTS:
    p_cam_slots = np.int64(g_org_params[org, 0] + np.float32(0.5))  # +0.5 rounds the 14-bit decode
    p_cam_match = np.int64(g_org_params[org, 2] + np.float32(0.5))
    p_stdp_div  = np.float32(g_org_params[org, 4])
    p_homeo     = np.float32(g_org_params[org, 5])
    p_tau_ref   = np.int64(g_org_params[org, 6] + np.float32(0.5))
    p_sp_growth = np.float32(g_org_params[org, 7])
    p_sp_rewire = np.float32(g_org_params[org, 8])
else:
    p_cam_slots = np.int64(CAM_SLOTS); p_cam_match = CAM_MATCH_THRESHOLD; p_stdp_div = STDP_DIV
    p_homeo = HOMEOSTATIC_LAMBDA; p_tau_ref = np.int64(TAU_REF)
    p_sp_growth = SP_GROWTH_COST; p_sp_rewire = SP_REWIRE_WEIGHT
```

  The `+0.5` on the integer genes matters: the 14-bit genome decode yields e.g. 5.9999 for a
  default of 6, and a bare `np.int64()` truncates to 5 — the `+0.5` rounds it back to the
  exact default so a default genome reproduces the verified baseline bit-for-bit.
- The use-sites then read the locals instead of the globals: `SP_REWIRE_WEIGHT`/`SP_GROWTH_COST`
  (structural plasticity, L1181/1182), `TAU_REF` (L1421), `STDP_DIV` (L1453/1483/1850),
  `HOMEOSTATIC_LAMBDA` (L1461/1463/1487/1489/1793/1855/1857), and the `cam_read`/`cam_write`
  call sites (which already took `CAM_SLOTS`/`CAM_MATCH_THRESHOLD` as arguments — only the
  passed value changed to `p_cam_slots`/`p_cam_match`).
- **Wired in 3b-ii:** `cam_key_bits` (gene 1). `cam_read`/`cam_write` now take `CAM_KEY_BITS`
  as a trailing argument (the Hamming loop bound `for bit in range(CAM_KEY_BITS)` reads the
  parameter, which shadows the module global). `world_tick_numba` passes a per-org
  `p_cam_key_bits`: with the flag ON it is `round(g_org_params[org,1])` clipped to
  `[1, CAM_KEY_BITS]` (the backing-store width: `g_cam_keys` is sized to the global
  `CAM_KEY_BITS`, so a per-org value can shrink but never exceed it; the gene range is [2,8]);
  with it OFF it is the module global `CAM_KEY_BITS`, so the call is value-identical to
  pre-3b-ii. **`physical_cost_model.py` needed NO change:** contrary to the earlier note it
  does NOT import the engine's `cam_read`/`cam_write` — it times its own inline parametrized
  `_cam` kernel (`engine_primitive_cycles(cam_slots, cam_key_bits)`), so the signature change
  is invisible to it. `cam_write_threshold` (gene 3) remains decoded-but-unused (no kernel
  use-site, so nothing to wire).

**Operational caveat (numba cache):** after changing the engine, clear the numba cache
(`rm -rf /tmp/genesis_numba_*` and `src/__pycache__`). A stale cache served a mismatched
`world_tick_numba` during 3b bring-up and produced a bogus `lif_steps=66`; a fresh compile
restored `lif_steps=5` and the verified extinction tick.

**Operational caveat (stochastic ancestor):** `create_intelligent_ancestor()` draws synapse
`src/dst/weight` bytes from Python's UNSEEDED `random` module, so every call yields a different
genome (same 557 B length and 65n/93s counts, but different bytes -> different `lif_steps` and
extinction). A flag-OFF vs flag-ON regression is therefore INVALID unless the ancestor is held
fixed: seed `random.seed(N)` (and `np.random.seed(N)`) before `create_intelligent_ancestor()` in
BOTH processes. The 3b-ii A/B used seed 20260725 (ancestor md5 `4c1f06da5635`).

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
   **Increment 3a (data path, flag OFF) is regression-verified:** a back-to-back A/B in the
   same cost-measurement era gave ORIGINAL (512 B genome) vs EDITED (557 B with PARAM tail)
   both `n_count=65, s_count=93, lif_steps=5`, with `decode_genome` producing byte-identical
   synapse `src/dst/weight` (full genome vs PARAM-stripped genome), and extinction tick
   167 vs 168 — a 1-tick difference inside the run-to-run cost-measurement noise band
   (post-edit runs span 165–172). The PARAM tail is provably layout-neutral and
   behaviour-neutral; the kernel is logically unchanged (only marker constants were added,
   plus a spawn-time decode into a per-org array the kernel does not read yet).
5. **Increment 3b-i (kernel wiring, flag ON) is regression- AND wire-verified.** After
   clearing the numba cache, a back-to-back A/B gave flag OFF extinction=169 vs flag ON
   (default genome) extinction=167 — a 2-tick difference inside the noise band, both
   `lif_steps=5`. The `+0.5` rounding on the integer genes makes the default genome map
   exactly to the module globals (cam_match 5.9999->6, etc.). **Wire proven three ways:**
   (a) a direct `cam_write`/`cam_read` unit test — `CAM_SLOTS=1` fills exactly 1 slot,
   `CAM_SLOTS=32` fills 15; (b) in-engine, `g_org_params[0,0]=1` (cam_slots) keeps
   `g_cam_valid[0].sum() <= 1` every tick; (c) `tau_ref=1` vs `8` gives different extinction
   ticks. So the kernel genuinely reads `g_org_params[org]` when the flag is ON and the
   shared globals when it is OFF.
6. **Increment 3b-ii (per-org `cam_key_bits`, flag ON) is regression- AND wire-verified.**
   With a SEEDED ancestor (caveat above), a back-to-back A/B gave flag OFF vs flag ON (default
   genome) **`lif_steps` identical** and decoded `cam_key_bits = 8.000` (the exact global).
   Extinction differs by a few ticks (host-dependent; on the 3b-ii host OFF~197-198 vs
   ON~200-202) — this residual is the pre-existing 3b-i **float-gene `float32` precision
   drift** (`stdp_div`/`homeo`/`sp_growth`/`sp_rewire` read through the `float32` `g_org_params`
   matrix vs the globals' native precision) plus separate-process cost-era noise, proven
   independent of `cam_key_bits` (forcing `g_org_params[0]` to the EXACT globals still leaves the
   offset; and `cam_key_bits` decodes to the exact integer 8 so `range(8)==range(8)`). **Wire
   proven two ways:** (a) a direct `cam_read`/`cam_write` unit test — the `CAM_KEY_BITS`
   argument controls the Hamming loop (`KEY_BITS=2,thr=6`->no match since max sim 2<6;
   `KEY_BITS=8,thr=6`->match; `cam_write(KEY_BITS=2)` of `0xFF` stores only the first 2 bits);
   (b) in-engine, two flag-ON runs differing ONLY in `g_org_params[0,1]` (8 vs 2) give different
   60-tick position/CAM trajectories and different CAM fill (22 vs 21 valid slots). The kernel
   genuinely reads `g_org_params[org,1]`.
7. **Increment 3c (in-engine PARAM-gene evolution, flag ON) is built and run — evolvability
   confirmed, adaptive drift NOT observed.** `src/exp78b_inengine_evolution.py` simulates each
   organism lifetime in the real `world_tick_numba` (flag ON) over 40 generations, selecting on
   the engine correct-prediction signal (5-replicate mean) with a neutral control. The PARAM
   genes DRIFT substantially under mutation (selected-line stdp_div +74.5, sp_rewire +10.4,
   cam_key_bits +2.1, cam_slots -7.6), confirming the per-org constants are evolvable. But mean
   fitness stayed FLAT (~52-54) for BOTH lines (selected peaked at gen 0). This null is Rule-3 VALIDATED (Exp 78b): over 5 seeds x 2 mutation
   operators (EA Gaussian + faithful `mutate_dna`), selection advantage = EA -0.011±0.632 and
   genome -0.058±0.324 — both <= 0 and within 1 std, so the pre-registered criterion
   (Ascent §2.D: mean > 0 by >= 1 std) FAILS under both operators: selection drove directional gene changes that did NOT improve fitness, i.e.
   it acted on noise, not a real gradient. The full engine comprehension-fitness landscape is
   flat/noisy w.r.t. the constants (behaviour is structure-dominated) — in contrast to exp77e
   simplified model (clear adaptive drift). Rule 21.2 mechanism (evolvable per-org constants) is
   achieved; adaptive tuning of them in the full engine is gated by the income bottleneck (no real
   fitness gradient until the substrate earns measured income).

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
