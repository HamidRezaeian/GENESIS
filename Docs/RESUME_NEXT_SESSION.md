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
