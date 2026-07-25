# Resume Next Session — Start Here

Read this file FIRST. It tells you exactly where the project stands.

---

## Latest Session Update (2026-07-25 — session 3: Tier-1 increment 3a IMPLEMENTED)

**Increment 3a (evolvable-constant DATA PATH, flag OFF) is built, unit-tested, and
regression-verified. Commit on `main`. Read `Docs/RULE21_2_ENGINE_REFACTOR_DESIGN.md` §6.1/§7.4.**

### What was built (the genome -> per-organism constant data path)
- **Two new ISA marker bytes:** `PARAM_MARKER = 200`, `PARAM_MAGIC = 201` (neuromorphic_engine.py).
  A PARAM record is 5 bytes: `[200, 201, gene_id, val_lo(7-bit), val_hi(7-bit)]`.
- **9 Tier-1 evolvable constants** now live as PARAM genes decoded into a per-organism matrix
  `g_org_params[MAX_ORGANISMS, 9]` (genesis_lab.py): cam_slots, cam_key_bits, cam_match_threshold,
  cam_write_threshold, stdp_div, homeostatic_lambda, tau_ref, sp_growth_cost, sp_rewire_weight.
  Defaults = the engine's CURRENT resolved module globals (so flag-ON == today's behaviour).
- **create_intelligent_ancestor** appends one PARAM record per gene (encoding the defaults);
  **spawn_organism** calls `decode_params(dna, org_id)` to fill `g_org_params[org]`.
- **`GENESIS_EVOLVABLE_CONSTANTS` flag** added (default OFF). The kernel does NOT read
  `g_org_params` yet — that is increment 3b. So this increment is behaviour-neutral by construction.

### Key design property: self-skipping + collision-proof (NO walker edits needed)
- Payload bytes are kept `< 128` (7 bits each), so all four existing genome walkers
  (parse_receptors, count_genes, decode_genome, and the Lamarckian walk inside world_tick_numba)
  advance past a PARAM record via their `else: i += 1` fallback WITHOUT desync — no payload byte
  can be mistaken for a marker (markers are 161-199). **Zero existing walker modified.**
- The `[200, 201]` sentinel is collision-proof: the ancestor has an accidental lone `200` byte at
  offset 487 (a weight value, followed by 161=GENE_MARKER) which decode_params correctly IGNORES
  (not followed by 201). The pair `[200,201]` never occurs elsewhere; byte 201 never appears.
- This matters because the Lamarckian walk is NOT exercised by Exp 78 (zero births) — the
  self-skipping property makes the data path safe there anyway.

### Verification
- **Unit tests PASSED:** ancestor = 557 bytes with exactly 9 valid `[200,201]` records; the lone-200
  @487 ignored; `count_genes` identical with/without the PARAM tail (s=93, h=26 -> layout-neutral);
  spawn decodes `g_org_params[0]` to `[32, 8, 6, 2, 1.0, 0.01, 1, 10, 5]` (the engine constants,
  14-bit round-trip); 300 mutated genomes all decode finite & in-bounds.
- **Regression PASSED (definitive back-to-back A/B, same cost era):** ORIGINAL (512 B) vs EDITED
  (557 B) both give `n_count=65, s_count=93, lif_steps=5`; `decode_genome` produces byte-identical
  synapse `src/dst/weight` (full vs PARAM-stripped); extinction tick **167 vs 168** (1-tick diff,
  inside the run-to-run cost-measurement noise band — post-edit runs span 165-172). The earlier
  "lif_steps 6 / extinction 147" was separate-process cost noise, NOT a code effect (proven: the
  A/B in the same era is identical).

### Files changed this session
- `src/neuromorphic_engine.py` — `PARAM_MARKER = 200`, `PARAM_MAGIC = 201` (+ comments). Kernel logic UNCHANGED.
- `src/genesis_lab.py` — import of the 7 engine constants + markers; `PARAM_GENES`/`PARAM_DEFAULTS`/
  `g_org_params`; `encode_param_records()`/`decode_params()`; ancestor PARAM records; spawn decode call;
  `EVOLVABLE_CONSTANTS` flag.
- `Docs/RULE21_2_ENGINE_REFACTOR_DESIGN.md` — §6.1 updated to the implemented 5-byte sentinel design;
  §7.4 records the regression proof.

### Priority for NEXT session (increment 3b: wire the kernel)
1. **Thread `g_org_params[org]` into `world_tick_numba`** behind `GENESIS_EVOLVABLE_CONSTANTS`:
   add the per-org param arrays as kernel args; at each Tier-1 use-site replace the module global
   with `g_org_params[org, gid]` (int-rounded+clipped for cam_slots/cam_key_bits/cam_match/cam_write/
   tau_ref). Use-sites: STDP_DIV (L1445/1475/1842), HOMEOSTATIC_LAMBDA (L1453/1479/1785/1847/1849),
   TAU_REF (L1380), SP_GROWTH_COST/SP_REWIRE_WEIGHT (L1173/1174), CAM_SLOTS/CAM_MATCH_THRESHOLD
   (cam_read/cam_write at L575-642, L1198, L1972, L2055). Pass `EVOLVABLE_CONSTANTS` as a kernel arg
   so flag-OFF dead-code-eliminates the per-org reads (compiled kernel identical to today).
2. **Re-run Exp 78 with `GENESIS_EVOLVABLE_CONSTANTS=1` + default genome** -> must reproduce the
   verified baseline (extinction ~167 on this host, ~1532 cycles/tick) since defaults == globals.
3. **Then 3c:** an in-engine evolution run showing the PARAM genes drift across generations under
   selection (the definitive Rule-21.2 evidence for the full engine, vs the probe).
4. (Open) PARAM-aware Gaussian mutation (gentler than byte substitution); Tier-2 constants
   (food_scan_radius, long_jump_stride, delay_n, remap_period/states, sp_max_growth/prune);
   STDP_TARGET separate-process A/B; RAPL on bare metal; income-unit (256=CELL_STATES) review.

---

## Latest Session Update (2026-07-25 — session 2: Rule 21.2 G-constant migration)

**Read `Docs/RULE21_2_ENGINE_REFACTOR_DESIGN.md` for the full engineering design.**

### Re-verified on THIS host (Rule 21.1 still holds)
- Repo confirmed at `d1bbc72` (Rule 21.1 DONE). numba 0.61.2 installed.
- `physical_cost_model.engine_primitive_cycles(32,8)` measured real native costs on this
  host: synapse_read=4.14, neuron_update=3.70, stdp_update=7.90, move=0.97, byte_copy=1.07,
  **cam_read=764.95 cycles/op** (cam_read still dominates; absolute numbers differ from the
  original host's 857 — methodology portable, values host-dependent as documented).
- Engine imports cleanly; all `CYCLES_PER_*` populated from measurement at import.
- **Exp 78 smoke test (300 ticks): PASSED.** Ancestor spawns (512 B, 65 neurons, 93 synapses),
  JIT warmup 10.2 s, **EXTINCTION @ tick 147** (this host; original was 163 — net burn slightly
  faster here because synapse/neuron costs are a bit higher even though cam_read is cheaper),
  CAM full (32) at death, ZERO income. Confirms the compositional-reading bottleneck and the
  Rule 21.1 wiring end-to-end.

### NEW: Exp 77e — 5 MORE engine constants proven evolvable (Rule 21.2)
- `src/exp77e_engine_genes_probe.py` extends exp77d's 15 genes to **20**, adding 5 new
  engine-constant genes that faithfully mirror the engine semantics:
  - `cam_slots` -> CAM_SLOTS (L152); `cam_key_bits` -> CAM_KEY_BITS (L153)
  - `stdp_div` -> STDP_DIV (L141, divides the STDP step)
  - `tau_ref` -> TAU_REF (L456, refractory counter)
  - `homeostatic_lambda` -> HOMEOSTATIC_LAMBDA (L146, `w -= lam*(w - w_dna)`)
- **Result (`exp77e_engine_genes_results.json`, pop 24x15, best fitness 6/32):**
  **13/20 genes drifted** off designer default. **All 5 new genes moved under selection:**
  - cam_slots 32 -> **2.95** (norm drift -0.937, strong — selection shrinks an unused CAM)
  - cam_key_bits 16 -> **7.77** (-0.588, strong — narrows toward the engine's 8-bit default)
  - tau_ref 1 -> **3.23** (+0.371, longer refractory selected)
  - stdp_div 1.0 -> **12.27** (+0.088; 12x smaller STDP steps — under the 0.10 *normalized*
    threshold only because the range is 0.1-128 log; clearly moved)
  - homeostatic_lambda 0.01 -> **0.0** (-0.050; selection turns anchoring OFF in this task)
- Combined with exp77c (11) + exp77d (4), **20 substrate parameters are now shown to be
  evolvable genes** rather than designer fiat. Fitness staying at 6/32 is expected (the
  bottleneck is compositional reading, not a tunable constant).

### NEW: Full engine refactor design documented
- `Docs/RULE21_2_ENGINE_REFACTOR_DESIGN.md` — the engineering plan to thread per-organism
  evolvable constants through `world_tick_numba`:
  - **18 tunable G-constants classified:** 14 -> E (evolvable), RAM_SIZE -> H, DT -> O,
    four CAM thresholds -> E-or-H. (CYCLES_PER_* and CELL_STATES already H.)
  - **Why not per-org today:** the constants are numba module globals, baked into the
    compiled kernel as compile-time constants -> shared by all organisms.
  - **Design:** new `PARAM_MARKER` genome record `[PARAM_MARKER, gene_id, value(2B)]` +
    per-organism param arrays (`g_org_cam_slots[org]`, `g_org_stdp_div[org]`, ...) +
    decode-at-spawn + kernel global->`array[org]` replacement at ~30 use-sites.
  - **Key fact:** CAM is ALREADY per-organism (`g_cam_keys[MAX_ORGANISMS, CAM_SLOTS,
    CAM_KEY_BITS]`), so cam_slots/cam_key_bits migration is just per-org loop bounds —
    exactly the max-size-backing-store design exp77e validated.
  - **Backward compat:** default genome reproduces the verified Exp 78 path bit-for-bit;
    gated behind `GENESIS_EVOLVABLE_CONSTANTS` (default OFF) until re-validated.

### Priority for NEXT session
1. **Tier 1 kernel threading** (the main effort): implement the PARAM_MARKER record +
   decode + the 8 Tier-1 per-org arrays (cam_slots, cam_key_bits, stdp_div, tau_ref,
   homeostatic_lambda, cam_match_thr, sp_growth_cost, sp_rewire_w) + replace the global
   reads in `world_tick_numba` + re-run Exp 78 with the flag ON to confirm the verified
   baseline (extinction @~163, ~1532 cycles/tick). See design doc sections 6-7.
2. **Tier 2 probe coverage:** extend exp77e -> exp77f for the remaining constants
   (sp_max_growth, sp_max_prune, cam_write_threshold, food_scan_radius, long_jump_stride,
   delay_n, remap_period/states), then thread them through the kernel.
3. **In-engine evolution validation:** run a multi-organism evolution in the FULL engine
   with the flag ON and show PARAM genes drift across generations (the in-engine counterpart
   of the exp77e probe result — the definitive Rule-21.2 evidence for the engine).
4. **Tier 3 re-labelling:** document RAM_SIZE as H (power-of-2 / 16-bit addressing) and
   DT as O (config timestep). Trivial.
5. (Still open) STDP_TARGET separate-process A/B (after G-constants grounded); RAPL on
   bare-metal Intel for real joules; income-unit (256=CELL_STATES) exchange-rate review.

### Key files added this session
- `src/exp77e_engine_genes_probe.py` — 20-gene evolvable probe (5 new engine constants).
- `exp77e_engine_genes_results.json` — drift evidence (13/20 drifted, all 5 new moved).
- `Docs/RULE21_2_ENGINE_REFACTOR_DESIGN.md` — full per-organism-constant refactor design.

---

## Current State (2026-07-25)

### Code Status
- **Progenitor restored** — ALL experiments Exp 70–86 reverted. No gate circuit, no constant 'a', no JMP_FWD change. Genesis_lab.py and neuromorphic_engine.py are back to commit `c2715a5` (before Exp 73).
- **Git commits pushed** — Magic-numbers fix (commit `824c5c6`) pushed to `main`. Contains only hardware-derived documentation changes.
- **Magic numbers audit** — 21 red/orange constants identified in neuromorphic_engine.py + genesis_lab.py.

### What Was Fixed (Hardware-Derived Only)

| Constant | Value | Derivation |
|---|---|---|
| `BITS_PER_BYTE` | 8 | 8-bit architecture |
| `CELL_STATES` | 256 | 2^8 |
| `STDP_SCALE` | BITS_PER_BYTE | Derived |
| `W_MIN` | -128 | Signed byte range |
| `W_MAX` | +127 | Signed byte range |

All other constants left at original project-author values (design choices, not hardware).

### What Was NOT Fixed (15 Synapse Weights)

The progenitor ancestor has 93 GENE_MARKER with 15 unique weights. Each weight (e.g., JMP_FWD bias = +20, FOOD_AHEAD → JMP_FWD = +96) is a design choice. Fixing these requires either:
- Deriving each from a physical constraint (firing threshold, LIF dynamics)
- Making them evolvable (encoded in the genome rather than hardcoded)

### Final Scientific Finding

16 experiments (Exp 70–86) established:
1. Memory is not the bottleneck ✓
2. Attractor discrimination is solvable ✓
3. Write selectivity is architecturally solvable ✓
4. Gate circuit design is correct ✓
5. **Metabolic cost (n_neurons × depth × spike_cost) exceeds maximum reading income (256 cycles/tick)** — the substrate cannot support compositional cognition within its energy budget

### Repository

```
REPO:  https://github.com/HamidRezaeian/GENESIS
MAIN:  commit 824c5c6 (magic numbers fix, pushed)
FIRST: commit eba9dfb (original progenitor, genesis_engine.py)
PROG:  commit c2715a5 (before Exp 73, has both genesis_lab.py + neuromorphic_engine.py)
```

### Key Files

| File | Lines | Role |
|---|---|---|
| `src/neuromorphic_engine.py` | 2,165 | Core simulation engine (LIF, STDP, world_tick) |
| `src/genesis_lab.py` | **0 (EMPTY in this checkout)** | Lab orchestration — **MISSING**; every `exp*_driver.py` that imports it fails. See correction below. |
| `src/books_of_genesis.py` | 217 | Book/curriculum system |
| `Docs/Result.md` | ~3,284 | Full experiment log (Exp 1–86) |
| `Docs/Roadmap.md` | ~974 | Roadmap and bottleneck status |

### Next-Session Quick-Start

```bash
cd /home/user/repos/GENESIS
python3 src/genesis_lab.py  # Starts the simulation lab
# Or run a headless experiment:
GENESIS_HEADLESS=1 python3 src/genesis_lab.py
```

### Unfinished Business

1. **15 synapse weights in progenitor** — each needs physical derivation or evolution encoding
2. **13 design-choice constants** (FOOD_SCAN_RADIUS=16, CYCLES_PER_MOVE=3, LONG_JUMP_STRIDE=10, etc.) — not hardware-derived but part of the original project. Could be documented or evolved.
3. **Metabolic ceiling** — the fundamental constraint (cost > income) remains unsolved. Options: reduce n_neurons, reduce depth, or increase reading reward. All require either engine modification or organism evolution.

---

<!-- CLUSY_EXP77_AUDIT_2026-07-25 -->
## Session Correction — Exp 77 Autopsy (2026-07-25, Clusy audit)

**Purpose:** correct the record before the next session runs anything.

### Verified facts (this checkout)
1. **`src/genesis_lab.py` is 0 bytes (EMPTY).** It is NOT 1,934 lines here. The root
   drivers `exp78_driver.py`, `exp79_driver.py`, `exp80_driver.py` all do
   `import genesis_lab as gl` and import ~40 symbols → `AttributeError` on the empty
   module. **Exp 78 cannot be run as written.** `fix_genesis_lab.py` is a string-patch
   script pointing at `C:\Users\Hamid\source\repos\GENESIS\src\genesis_lab.py`;
   it presupposes a populated file and cannot create one. The real orchestrator appears
   to live on the author's Windows machine, not in this repo.
2. **The "gate drive circuit" is NOT in the substrate.** `exp77_gate_drive_probe.py`
   imports only `os, json, numpy` and computes `or_123 = bits[1] or bits[2] or bits[3]`
   in plain Python. Its "100% theoretical accuracy" is a combinatorial count
   (64 `(c1,c2)` pairs → 64 unique 16-bit keys), not a simulated/evolved result.
   `neuromorphic_engine.py` has **no** `GATED_NEURON_MARKER(201)` and **no**
   `sense_type==253` gated-write logic (0 hits each). The exp76 docstring claims those
   engine changes; they are absent.
3. **Rule 5 verdict:** the exp77 *probe* is a forbidden cognitive module in spirit (the
   experimenter hand-wires cue/answer detection), but it never touched the engine, so
   there is nothing in the substrate to "rip out." The misleading claim/docstring is what
   must be struck, not engine code.
4. **"SOLVED ALL BOTTLENECKS" is false.** The binding constraint is the **metabolic
   ceiling**: `n_neurons × depth × spike_cost > 256 cycles/tick` reading income.

### The Rule-5-compliant organic route (already scaffolded in the engine)
Let reading-reward-gated **STDP3/STDP3C** eligibility (L191) + **structural plasticity**
(L164, rewire/prune) grow the cue→bank routing into the **CAM** working-memory store
(L150, non-leaky, write-on-reward), with the **WMEM** shift register (L257). The engine
itself names the two honest blockers: self-clocking/address ("a gated latch cannot
SELF-CLOCK", L271) and the metabolic ceiling.

### Next-session quick-start (CORRECTED)
```bash
# DO NOT run `python3 src/genesis_lab.py` — the file is empty in this checkout.
# First restore the real genesis_lab.py (from the author's machine / a prior commit),
# THEN run a headless experiment:
GENESIS_HEADLESS=1 python3 src/genesis_lab.py
```

### Unfinished business (updated)
0. **BLOCKER: restore `src/genesis_lab.py`** (0 bytes) before ANY simulation can run.
1. Metabolic ceiling — reduce n_neurons/depth or raise reading reward.
2. Self-clocking/address — evolve a store-clock; do NOT hardcode a TOGGLE.
3. Re-label exp74–77 probes as oracle diagnostics, not organism capabilities.

---

<!-- CLUSY_EXP77B_2026-07-25 -->
## Exp 77b — Organic-Route Probe Ran (2026-07-25)

The Phase-2 pivot was executed: instead of the Exp 77 hand-wired gate, a small LIF
substrate using ONLY the engine's Rule-5-compliant primitives — CAM write-on-reward
(L150), reward-gated STDP3C per-bit signed eligibility (L200/L1259), and structural
plasticity rewire/prune (L164) — was run on the Latin-square compositionality task
`answer=(c1+c2) mod 8`, stream `[c1,noise,noise,c2,noise,noise,GO]`, with the autotelic
reading reward as the ONLY teaching signal. Probe: `src/exp77b_organic_route_probe.py`.

| Arm | Associative recall (TRAIN) | Compositional gen. (HELD) |
|---|---|---|
| ORG + motor exploration | **96.9%** | 21.9% |
| ORG, no exploration | 31.2% | 25.0% |
| REF (NOLEARN control) | 6.2% | 18.8% |
| chance | 12.5% | 12.5% |

**Findings:**
1. The organic substrate **DOES learn cue→answer associations** (97% on trained
   pairs via CAM write-on-reward) — a genuine positive result with NO hardcoded gate.
2. It **does NOT generalise compositionally** (22% on held-out pairs ≈ chance): the
   mod-8 addition for NOVEL (c1,c2) pairs can neither be looked up (no CAM entry) nor
   computed by the STDP-shaped linear readout on the decaying hidden echo.
3. **Without motor exploration even associative recall collapses** (31%) — confirming
   the engine's documented L290 recruitment gap (reward-gated STDP cannot break the
   output bias / recruit a silent-but-correct neuron).
4. **Metabolic:** the small net costs 1.7 cycles/tick << 256 ceiling — affordable
   yet compositionally powerless; a net deep enough to compose (break-even 6.1 hops
   at 42 neurons) crosses the 256 ceiling.

**Updated unfinished business:** compositionality is NOT solved. The two concrete targets
are now (a) **evolve a store-clock / address** so c1 can be written to CAM at the right
moment without a hardcoded TOGGLE (the L271 self-clocking blocker), and (b) **close the
STDP3C recruitment gap** (L290) so silent-but-correct pathways can be reinforced. The
metabolic ceiling remains the binding constraint on scaling either up.

---

<!-- CLUSY_RULE21_AUDIT_2026-07-25 -->
## Rule 21 — Physical-Grounding Audit (2026-07-25)

**New binding rule added:** `FixedRules.md` Rule 21 (Physical Grounding — No Game
Mechanics). GENESIS is a PHYSICAL system: costs = real measured hardware work
(CPU/GPU/RAM cycles, memory traffic, joules, wall-time); parameters = hardware-derived
(H) or evolvable genes (E) only; opcodes/markers = documented ISA (O). The Tuning
Test: if tuning a number makes it "work better," it is an illegal game mechanic.

**Audit of every numeric variable (43 classified):**
| Class | Meaning | Count |
|---|---|---|
| H | hardware-derived (LEGIT) | 6 |
| E | evolvable gene (LEGIT) | **0** |
| O | opcode/marker ISA (LEGIT) | 10 |
| G | game-mechanic VIOLATION | **27** |

**Core finding:** 27 of 43 numeric variables are game-mechanic violations, and **zero**
parameters are currently evolvable genes — everything that should be evolvable is
hard-coded designer-fiat. The 15 ancestor synapse weights live in the EMPTY
`src/genesis_lab.py` and cannot be audited until it is restored (they are class E by
rule — must become evolvable genes).

**Cost model is invented, not measured (Rule 21.1):** `SPIKE_COST=1` and `income=256`
are dimensionless points, NOT hardware work. Measured on this host: one LIF spike
≈ 654 CPU cycles (218 ns); one full
substrate tick ≈ 39,937 cycles ≈ 9.4 nJ.
The invented "income=256" is LESS than the real cost of a single spike — so the
"metabolic ceiling = cost > 256" finding is about ARBITRARY numbers and is not
falsifiable. The grounded replacement: the organism's budget = the host's real
measured cycle/time/energy budget.

**Remediation (Rule 21.6):** every G must be (a) derived from hardware with the
derivation documented, (b) made an evolvable gene, or (c) deleted. Priority: replace
the invented cost model with real measured hardware cost FIRST.

---

<!-- CLUSY_REAL_COST_MODEL_2026-07-25 -->
## Cost Model Rebuilt on REAL Measurement (2026-07-25, Rule 21.1)

The invented cost model (`SPIKE_COST=1`, `income=256`) is replaced by a model that
MEASURES the real work the host performs: `src/physical_cost_model.py` (new reusable
module). Each substrate primitive is timed on the host and expressed in wall-time /
CPU cycles / FLOPs / joules.

**Real measured cost per primitive (this host):**
| primitive | wall-time | share |
|---|---|---|
| `cam_read` (associative lookup, Python loop) | 108.5 us | **91%** |
| `stdp_update` | 4.2 us | 3.5% |
| `sp_rewire` | 2.0 us | 1.7% |
| synapse currents | ~1.2 us each | ~1% each |
| `lif_update` | 374 ns | 0.3% |

**Key finding:** the associative-memory lookup (a Python loop), NOT the neural
dynamics, is 91% of the cost — in this implementation the memory, not the neurons,
is the metabolic load.

**Invented vs REAL accounting (same organism):**
- OLD: cost = 12.1 spikes x 1 = 12.1 dimensionless "points"; income = 256 (NOT hardware work).
- NEW: cost/trial = 388 us = 1,163,640 CPU cycles; cost/tick = 55 us = 166,234 cycles.
- The invented "256" is ~649x smaller than the REAL cost of one tick — it describes no hardware work.

**Grounded metabolic ceiling:** with a REAL budget of 1 ms host compute/tick, the host
can afford ~2,374 hidden neurons — a falsifiable, physical limit (the old "ceiling =
cost>256" moved whenever 1 or 256 changed). The 24-neuron substrate spends 55
us/tick, well within budget.

**Honesty flags:** wall-time/cycles are direct measurements; joules use
`joules_per_flop ~ 10 pJ` (order-of-magnitude) — a true energy budget needs RAPL power
monitoring (flagged gap). For Python-loop ops the FLOP count understates true work, so
wall-time/cycles are the reliable measure.

**Status of Rule 21 remediation:** cost model (21.1) is now grounded. The 27
game-mechanic parameters (TAU, THRESH, STDP_LR, weights, ...) still need to be made
evolvable genes (21.2) — that is the next step.

---

<!-- CLUSY_EVOLVABLE_GENOME_2026-07-25 -->
## Rule 21.2 — Evolvable Genome POC (2026-07-25)

A proof of concept (`src/exp77c_evolvable_genome_probe.py`) demonstrates that substrate
parameters can be ENCODED in the organism's genome rather than hard-coded as module
constants. Eleven tunable parameters (`tau`, `thresh`, `stdp_lr`, `sp_*_threshold`,
`eps_explore`, weight-init scales) are read from a genome dict and shaped by
mutation + selection over 25 generations (30 organisms × 32 trials each).

**Result:** selection discovered VALUES DIFFERENT from the hand-set defaults — e.g.
`sp_prune_threshold` drifted from 0.5 → 7.4, `sp_rewire_weight` from 5.0 → 35.2,
`tau` from 200 → 139 — while maintaining comparable reading reward. This proves the
MECHANISM: parameters NEED NOT be designer constants; they can be evolvable genes
(Rule 21.2 is satisfiable). Fitness did not improve (the compositionality blockers
L271/L290 are architectural, not parametric — an honest finding).

**Remaining Rule 21 gaps:**
- 21.2: apply the same pattern to the remaining 21 G-variables in the engine (weights,
  `FOOD_SCAN_RADIUS`, `MAX_ORGANISMS`, etc.) — the POC pattern generalises.
- 21.1: measure real energy via RAPL (closes the `joules_per_flop` order-of-magnitude gap).
- Restore `src/genesis_lab.py` for the full 15 ancestor weights.


---

<!-- CLUSY_SESSION_2026-07-25_verify_rule21 -->
## Session 2026-07-25 (Clusy) — engine verified, Rule 21 advanced (priorities 1-5)

The sandbox was cold (recycled), so the repo was re-cloned fresh from GitHub before any work.
All findings below are from verified runs on commit `5f1ffc0` (genesis_lab.py restored).

### Priority 1 — Exp 78 runs on the restored engine (BLOCKER RESOLVED, verified)
- `src/genesis_lab.py` (1959 lines) imports headless and exposes **all 78 symbols** the drivers need
  (0 missing); `world_tick_numba` JIT-compiles (~11 s, then cached) and ticks end-to-end.
- **Exp 78 result** (`exp78_restored_engine_results.json`): the seeded ancestor (512 B -> 65 neurons /
  93 synapses, E=250000) earns **EXACTLY ZERO income** on the book economy — **0/1561 alive ticks** had a
  positive energy delta. It pays a real metabolic burn (median **161 energy/tick**, range 28-310) and starves
  at **tick ~1563-2161** (stochastic). It fills **all 32 CAM slots**, so the reward-gated write/STDP learning
  signal fires — but that signal is **decoupled from metabolic income**: it can memorise, not earn.
- This is a direct, measured confirmation of the Rule 21.1 metabolic ceiling (real cost >> real income=0).
- Figure: `exp78_energy_trajectory.png`.

### Priority 2 — Rule 21 audit of create_intelligent_ancestor (the ancestor weights)
- Parsed L615-852: 38 synapse genes, **11 unique weight bytes**, 2 neuron genes, 6 sensor genes.
- Weight encoding `eff = (byte-128)/BITS_PER_BYTE` is hardware-derived (H). Class tally: **H=4, E=0, O=2, G=12**.
- The **10 non-zero weights** {8,88,120,148,168,176,200,220,224,255} are hand-tuned **G** (comments document
  intent; "retuned 2026-07-11"); only neutral zero (byte 128) is legit. Neuron tau/thresh (0,40,8) and sensor
  offsets (LONG_JUMP_STRIDE) are also G. **E=0** — no evolvable genes. (`rule21_ancestor_audit.csv`,
  `rule21_ancestor_weight_audit.png`.)

### Priority 3 — engine G-constant audit + evolvable-gene generalisation (exp77d)
- `neuromorphic_engine.py` audit (86 constants): O/config=25, **G=18**, O=18, H=10, ?=9, **G-21.1=6**.
- **NEW 21.1 finding:** the six `CYCLES_PER_*` constants are invented dimensionless cost points (forbidden by
  21.1) **still inside the engine's accounting** — `physical_cost_model.py` is a separate module NOT wired into
  `world_tick`. Closing 21.1 means replacing these with measured per-primitive costs.
- 18 tunable G migration targets: FOOD_SCAN_RADIUS, STDP_DIV, HOMEOSTATIC_LAMBDA, CAM_SLOTS/KEY_BITS,
  CAM_MATCH/WRITE_THRESHOLD, SP_GROWTH_COST/MAX_GROWTH/MAX_PRUNE/REWIRE_WEIGHT, LONG_JUMP_STRIDE, REMAP_*,
  DELAY_N, TAU_REF, DT, RAM_SIZE. (`rule21_engine_constant_audit.csv`.)
- **exp77d** (`src/exp77d_engine_genes_probe.py`): extends the genome 11 -> **15 genes**, adding 4 engine
  constants (input_gain, output_gain, cam_match_frac, v_reset). Evolving 24x15: **12/15 genes drifted** off
  default; **3/4 new engine constants moved** (output_gain 0.5->1.57, cam_match_frac 0.9375->0.643 = fuzzier
  matching, v_reset 0->-0.145). Fitness 6/32 (blockers are architectural, not parametric). Standalone probe;
  engine untouched. (`exp77d_engine_genes_results.json`, `exp77d_engine_gene_drift.png`.)

### Priority 4 — RAPL energy gap: assessed, monitor built, blocked by hypervisor
- This host is a **KVM VM** (Intel Xeon): no `/sys/class/powercap`, no `perf`, and `/dev/cpu/0/msr` exists but
  `MSR_RAPL_POWER_UNIT(0x606)` & `MSR_PKG_ENERGY_STATUS(0x611)` **read 0** (hypervisor stub). **Real joules
  cannot be measured here**, and 21.1 forbids substituting the estimate.
- Built `src/rapl_energy_monitor.py`: tries powercap -> perf -> MSR (validates the power-unit MSR so a zero-stub
  is REJECTED), returns real joules via `measure_joules()`, else raises `RaplUnavailable` with the bare-metal
  command. **Never estimates** (integrity check passes). Ready to close the gap on bare-metal Intel.

### Priority 5 — architectural compositionality: reframed + testability finding
- **Reframe:** both "unsolved blockers" already have engine mechanisms — **SCRATCH** (store-clock, default-ON;
  needs the organism to evolve STORE-neuron firing) and **STDP_TARGET** (recruitment delta-rule, default-OFF;
  unvalidated). The honest question is empirical: does enabling STDP_TARGET close recruitment?
- **Testability finding:** compile-time-gated flags **cannot be A/B tested in a long-lived process** — numba
  caches the kernel in-memory at process level; `importlib.reload` reuses the first-compiled kernel regardless
  of the flag (verified: reload 0.02 s, no cache regeneration, identical output for flag 0/1). Each config needs
  its own fresh OS process.
- Delivered `src/exp_stdp_target_ab_driver.py` for a VALID separate-process A/B (run with GENESIS_STDP_TARGET=0
  and =1 in two processes, compare JSON). Context: Exp 78 earns 0 income regardless, so recruitment alone likely
  won't close the gap (multi-factor: store-clock + recruitment + reading->income mapping).

### Next-session quick-start (updated)
```bash
cd /home/user/GENESIS_GIT   # clone fresh if sandbox recycled
pip install "numba==0.61.2"  # for numpy 2.1.2
# Valid STDP_TARGET A/B (two SEPARATE processes — see Priority 5 testability finding):
GENESIS_STDP_TARGET=0 python3 src/exp_stdp_target_ab_driver.py
GENESIS_STDP_TARGET=1 python3 src/exp_stdp_target_ab_driver.py
# RAPL real-joule measurement requires bare-metal Intel (src/rapl_energy_monitor.py).
```

### Updated unfinished business
1. **Wire physical_cost_model.py into world_tick** and delete the 6 `CYCLES_PER_*` invented cost points (21.1).
2. **Run the STDP_TARGET separate-process A/B** (driver ready) to validate/close the L290 recruitment gap.
3. **Migrate the 18 tunable G-constants** to evolvable genes (pattern proven for 15); the engine refactor that
   threads per-organism genes through the numba kernel is the large remaining effort.
4. **RAPL on bare metal** to replace joules_per_flop with measured energy.
5. Test whether an organism can **evolve to drive the SCRATCH STORE neuron** (the L271 store-clock half).


---

<!-- CLUSY_SESSION_2026-07-25_rule21_1_wiring -->
## Session 2026-07-25 (Clusy) — Rule 21.1 DONE: metabolic cost is now real measured hardware work

The user re-emphasised the core principle: **real AGI, not a game/simulation with magic numbers.**
The single most on-principle next step was closing the Rule 21.1 gap in the engine's energy accounting.

### What was wrong
The engine charged metabolism via six INVENTED `CYCLES_PER_*` "cost points" (`1 cycle per operation`,
`3 cycles per move`) — exactly the game mechanics Rule 21.1 forbids ("Invented cost points ... are
FORBIDDEN"). `physical_cost_model.py` existed (Rule 21.1 cost model) but was NOT wired into `world_tick`.

### What was done
1. **Extended `src/physical_cost_model.py`** with `calibrate_native()` — times each engine primitive in
   **numba (native code)** on this host (the substrate runs JIT-compiled, so native timing is the honest
   cost; Python-interpreter timing over-estimates ~100-1000x). Added `engine_primitive_cycles()` (cached
   per config) returning real cycles/op: synapse_read=2.75, neuron_update=2.84 (array-based, matches the
   Phase-2 ILP), stdp_update=7.76, move=1.05, byte_copy=1.04, cam_read=857.5 (32x8 Hamming).
2. **Wired `src/neuromorphic_engine.py`**: the six `CYCLES_PER_*` now read from `engine_primitive_cycles()`
   (each documented inline as hardware-derived H via measurement). **Deleted `CYCLES_PER_SPIKE_CHECK`**
   (unused dead code, Rule 21.6c). Grounded the two bare-count charges: `+= CAM_SLOTS` -> `+= CYCLES_PER_CAM_READ`,
   viscous `+= n_count` -> `+= n_count * CYCLES_PER_NEURON_UPDATE`. Updated stale "1 cycle/op" comments.
   (Backup: `src/neuromorphic_engine.py.bak_rule21`, deleted after commit.)
3. The **income side was already H-grounded** (`CELL_STATES = 2^BITS_PER_BYTE = 256` cycles/resolved cell =
   the cell's information capacity), so it was left unchanged.

### The honest result (Exp 78, real costs) — `exp78_rule21_real_cost_results.json`
- Real metabolism = **1532 cycles/tick** median (range 1341-1883), **~10x** the invented 161 — dominated by
  the **857-cycle CAM Hamming read** (consistent with the earlier "cam_read = 91% of cost" finding).
- Seeded ancestor still earns **ZERO income** (0/162 ticks; fills 32 CAM slots but cannot read correctly),
  so it now starves at **tick 163** (vs ~1563 with invented costs). Break-even needs **~6 cells/tick**.
- **Conclusion:** the metabolic-ceiling finding now rests on REAL measurement, not invented points. The
  bottleneck is the substrate's compositional reading ABILITY (L271/L290 architectural blockers), NOT a
  tunable cost constant. No magic numbers remain in the cost accounting.

### Updated unfinished business (priority order)
1. **Run the STDP_TARGET separate-process A/B** (`src/exp_stdp_target_ab_driver.py`, ready) to validate the
   L290 recruitment delta-rule — the most informative open experiment on the reading-ability bottleneck.
2. **Migrate the 18 tunable G-constants** to evolvable genes (pattern proven for 15 in exp77d); the engine
   refactor threading per-organism genes through the numba kernel is the large remaining effort.
3. **RAPL on bare metal** (`src/rapl_energy_monitor.py`, ready) to replace `joules_per_flop` with measured joules.
4. Test whether an organism can **evolve to drive the SCRATCH STORE neuron** (L271 store-clock half).
5. (Open question surfaced by real costs) The income magnitude `256 = CELL_STATES` is H-derived but its
   *exchange rate* against real execution cycles deserves scrutiny — is information-capacity the right
   income unit, or should income also be a measured work quantity? Worth a Rule-21 review.

### Quick-start (this work)
```bash
cd /home/user/GENESIS_GIT   # clone fresh if sandbox recycled
pip install "numba==0.61.2"  # for numpy 2.1.2
python3 -c "import sys; sys.path.insert(0,'src'); import physical_cost_model as p; print(p.engine_primitive_cycles(32,8))"
# -> real native cycles/op on THIS host (measured at engine import, cached)
```
