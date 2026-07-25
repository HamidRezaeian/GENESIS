# Resume Next Session — Start Here

Read this file FIRST. It tells you exactly where the project stands.

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
