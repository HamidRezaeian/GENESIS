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
| `src/genesis_lab.py` | 1,934 | Lab orchestration, ancestor, curriculum |
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
