# GENESIS Runbook — Quick Start & Parameter Reference

> **Last updated:** 2026-07-23  
> **Engine:** `genesis_lab.py` + `neuromorphic_engine.py`  
> **Economy:** Books (default), Food (legacy)  
> **Default curriculum:** Hard_WM (16 cues, delays 4-64)

---

## Quick Start

```bash
# Default run (Hard_WM + DEPLETE + CAM + Homeostatic STDP + Structural Plasticity):
cd /path/to/GENESIS
python src/genesis_lab.py

# Headless mode (no WebSocket dashboard, faster):
GENESIS_HEADLESS=1 python src/genesis_lab.py

# Run for N ticks then exit:
GENESIS_MAX_TICKS=50000 GENESIS_HEADLESS=1 python src/genesis_lab.py

# Use a specific curriculum:
GENESIS_BOOK_NAME=Hard_WM GENESIS_HEADLESS=1 python src/genesis_lab.py
```

### Verify It's Running

The simulation prints a dashboard every ~3 seconds to stdout:
```
⏱ 1360  👥 38  💰 168  ✓ 72.7%  ～ 2178  ⏪ 0  ⛑ 48  📚 b|g|r
```

| Icon | Field | Meaning |
|:----:|-------|---------|
| ⏱ | 1360 | Tick number |
| 👥 | 38 | Living population |
| 💰 | 168 | Mean energy / organism |
| ✓ | 72.7% | Prediction accuracy (last window) |
| ～ | 2178 | Throughput (ticks/sec) |
| ⏪ | 0 | Extinctions (era resets) |
| ⛑ | 48 | Refugium germinations |
| 📚 | b/g/r | Book categories present |

---

## Parameter Categories

1. [Economy & Environment](#1-economy--environment)
2. [Curriculum & Books](#2-curriculum--books)
3. [Reading Economy](#3-reading-economy)
4. [Stigmergy & Authoring](#4-stigmergy--authoring)
5. [Plasticity & Learning](#5-plasticity--learning)
6. [Neural Substrate](#6-neural-substrate)
7. [CAM (Content-Addressable Memory)](#7-cam-content-addressable-memory)
8. [Structural Plasticity](#8-structural-plasticity)
9. [Checkpointing](#9-checkpointing)
10. [Runtime & Debug](#10-runtime--debug)

---

## 1. Economy & Environment

### `GENESIS_ECONOMY`
- **Values:** `food` | `books`
- **Default:** `books`
- **What it does:** Selects the energy economy.
  - `food`: Original 0x55-based foraging economy. Organisms eat food bytes to survive.
  - `books`: (Default) Curriculum-based reading economy. Organisms earn energy by predicting text symbols.

### `GENESIS_GROUNDED`
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** Enables grounded 2D spatial environment with food patches and shelter. When ON, organisms navigate a grid world with patch-based resources. When OFF, pure RAM-substrate reading economy.

### `GENESIS_GROUNDED_FOOD`
- **Values:** integer (bytes)
- **Default:** `3000`
- **What it does:** Number of food bytes seeded in the grounded environment.

### `GENESIS_GROUNDED_SHELTER`
- **Values:** integer (bytes)
- **Default:** `1500`
- **What it does:** Number of shelter bytes seeded in the grounded environment.

### `GENESIS_GROUNDED_PATCH`
- **Values:** integer (bytes)
- **Default:** `24`
- **What it does:** Patch size for grounded food/shelter clusters.

### `GENESIS_FOOD_RATE`
- **Values:** float (0.0–1.0)
- **Default:** `0.1`
- **What it does:** Rate at which food spontaneously spawns in empty cells (tick-independent, per-cell probability).

### `GENESIS_DEPLETE`
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** When ON, each cell has finite reading fuel. Correct predictions drain fuel; when depleted, the cell pays nothing. Creates real resource scarcity. **Recommended: ON** (proven in Exp 30 Arm G+).

### `GENESIS_DEPLETE_REGROW`
- **Values:** float
- **Default:** `256.0` (= `CELL_STATES`)
- **What it does:** How much fuel is restored per cell each restock cycle. Lower values = tighter scarcity.

### `GENESIS_PEER` (PEER_PREDICT)
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** Enables zero-sum peer prediction. Organisms can drain energy from neighbours by predicting their vocal output. Creates a Red Queen arms race toward informative signalling.

### `GENESIS_REDQUEEN`
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** Red Queen action-entropy pump. When ON, evading peer prediction pays both sides, preventing action monoculture.

### `GENESIS_NICHE_ECON`
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** Negative frequency-dependent niche sharing. Organisms exploiting the same behavioural niche share reading income, penalizing crowded strategies.

### `GENESIS_NICHE`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Niche jump mode. Organisms can jump between behaviour clusters to avoid crowding.

### `GENESIS_TRUE_CONTENTION`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** (Experimental) True bandwidth contention on the RAM bus. When ON, organisms compete for actual substrate access latencies instead of cycle-count penalties.

---

## 2. Curriculum & Books

### `GENESIS_BOOK_CATEGORY`
- **Values:** directory name under `Books/`
- **Default:** `English`
- **What it does:** Which book category to inject into the RAM substrate. Examples: `English`, `Diagnostic`, `Persian`.

### `GENESIS_BOOK_NAME`
- **Values:** filename (without `.txt`) under `Books/<category>/`
- **Default:** `00_Graded`
- **What it does:** Which book/curriculum file to use. Common values:
  - `00_Graded` — Graded English text (easy)
  - `GradedMemory` — Cue+noise+answer working memory task
  - `Hard_WM` — 16-cue random-permutation working memory (hard)
  - `DelayedMatch` — Delayed match-to-sample task

### `GENESIS_BOOK_TARGET_BYTES`
- **Values:** integer (bytes)
- **Default:** `6000`
- **What it does:** How many bytes of curriculum to inject at startup.

### `GENESIS_BOOK_RESTOCK_EVERY`
- **Values:** integer (ticks × 10⁻³)
- **Default:** `8`
- **What it does:** How often the curriculum is re-injected (in thousands of ticks). Default 8 = every 8000 ticks.

### `GENESIS_CURRICULUM`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** When ON, injects the curriculum file contiguously (as a single passage). When OFF, scatters text randomly.

### `GENESIS_DELAY`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Working memory delay task. The organism must predict a byte `DELAY_N` positions ahead of its current pointer, not the byte under it. Tests memory retention.

### `GENESIS_DELAY_N`
- **Values:** integer (1–64)
- **Default:** `1`
- **What it does:** How many ticks/bytes back the prediction target is. `3` = predict the byte 3 positions ago.

### `GENESIS_SEEKING`
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** Enables text-seeking behaviour. Organisms sense local text density (input channels 23-24) and can evolve climbing reflexes.

---

## 3. Reading Economy

*When `DEPLETE=1`:*

Each read pays `(net_bits / 8) × 256` energy, bounded by the cell's remaining fuel. Cells recover `DEPLETE_REGROW` fuel on each restock (every `BOOK_RESTOCK_EVERY` ticks).

*When `DEPLETE=0`:*

Each correct bit pays `CELL_STATES / BITS_PER_BYTE = 32` energy, minted from nothing. Unlimited energy — no scarcity.

---

## 4. Stigmergy & Authoring

### `GENESIS_STIGMERGY`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Enables stigmergic authoring. Organisms can write their vocal output into RAM cells (authoring). Authored cells earn royalties when read by others. Requires DEPLETE=1.

### `GENESIS_STIG_PERSIST`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Ownership persistence. A living author's cells cannot be overwritten by others. Author death releases cells.

### `GENESIS_STIG_LEASE`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Leasing mode. Owners must periodically refresh cells or lose ownership. Prevents ghost-town cells.

### `GENESIS_STIG_SEED`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Seed initial stigmergy content at universe startup.

### `GENESIS_CANVAS`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Dedicated authoring canvas band (separate from reading scroll). Solves the Exp-25b "nobody visits vacuum" problem by placing canvas adjacent to scroll.

### `GENESIS_CANVAS_SEED`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Seed initial canvas content at startup.

---

## 5. Plasticity & Learning

### `GENESIS_NOLEARN`
- **Values:** `0` (learn) | `1` (frozen)
- **Default:** `0`
- **What it does:** When `1`, STDP is compile-time deleted. Synapses keep their DNA-decoded weights for life. Used for ablation experiments (Exp 30 Arm B).

### `GENESIS_STDP_COSTONLY`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** When `1`, STDP energy cost is charged but weight updates are zeroed. Used to isolate energy-cost vs weight-drift effects (Exp 30 Arm C).

### `GENESIS_STDP_DIV`
- **Values:** float
- **Default:** `1`
- **What it does:** Divisor on the STDP increment. Higher values = smaller weight changes. Tuning parameter for STDP step size.

### `GENESIS_STDP3` — Three-Factor STDP
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Neuromodulated three-factor STDP. The plasticity gain for each tick is scaled by the organism's own reading reward — so learning is gated by success.

### `GENESIS_STDP3C` — Credit-Assigning STDP
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Per-synapse credit assignment. Each synapse onto a vocal-bit neuron is gated by that bit's correctness (+1 correct, -1 wrong, 0 silent). Superset of STDP3.

### `GENESIS_STDP_TARGET`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Teaching-signal plasticity. A local delta rule that supplies the RECRUITMENT gradient that STDP3C cannot provide structurally. Uses err_b = target_b - output_b to nudge synapses directly.

### `GENESIS_HOMEOSTATIC_LAMBDA`
- **Values:** float (0.0–1.0)
- **Default:** `0.01`
- **What it does:** Homeostatic anchoring rate for STDP. The update rule becomes:
  ```
  w += Δw_STDP − λ(w − w_DNA)
  ```
  `λ=0`: identical to destructive STDP.  
  `λ=0.01`: weights anchored ±10% around DNA baseline **(recommended)**.  
  `λ=1.0`: weights snap back to DNA every tick (no learning).

### `GENESIS_REMAP`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Sensorimotor remapping experiment. Periodically swaps two bits of the reading eye and vocal cords, forcing the organism to re-learn the mapping.

### `GENESIS_REMAP_PERIOD`
- **Values:** integer (ticks)
- **Default:** `4000`
- **What it does:** How often the remapping swaps.

### `GENESIS_REMAP_STATES`
- **Values:** integer
- **Default:** `2`
- **What it does:** Number of remapping states (2 = identity vs swapped).

### `GENESIS_REMAP_SB0`, `GENESIS_REMAP_SB1`
- **Values:** integer (0–7)
- **Default:** `0`, `1`
- **What it does:** Which two vocal/eye bits swap during remapping.

---

## 6. Neural Substrate

### `GENESIS_EVOSENSE`
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** Evolvable sensors. Organisms can evolve custom sensory neurons that read specific RAM bytes, neighbour energy, or neighbour vocal bits — not just the fixed 25 input channels.

### `GENESIS_EVOSENSE_SEED`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Seed initial sensor diversity at startup (add sensor genes to the Intelligent Ancestor).

### `GENESIS_EVOACT`
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** Evolvable actuators. Organisms can evolve custom motor neurons that map to specific actions, not just the 6 fixed motor outputs.

### `GENESIS_EVOACT_SEED`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Seed initial actuator diversity at startup.

### `GENESIS_WMEM`
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** Working Memory Latch neurons (Exp 44). Non-leaky, non-resetting integrator neurons that hold values across ticks — a RAM register in neural form.

### `GENESIS_SCRATCH`
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** External scratchpad registers (Exp 46). Store/recall sensors that let organisms write to and read from RAM-based external storage.

### `GENESIS_DIGESTION`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Digestion mode. Organisms can absorb and retain fuel from cells they consume, not just read in-place.

### `GENESIS_TRUE_CONTENTION`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** True RAM bus bandwidth contention. When ON, organisms compete for actual memory access bandwidth instead of cycle-count penalties.

### `GENESIS_ACTPROBE`
- **Values:** `0` (off) | `1` (on)
- **Default:** `0`
- **What it does:** Action probe mode. Logs all action selections for behavioural analysis.

---

## 7. CAM (Content-Addressable Memory)

*Added in Exp 30 (2026-07-23). Proven: enables genuine working memory.*

### `GENESIS_CAM`
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** Enables the Content-Addressable Memory substrate. Organisms get a per-organism key-value store that persists across ticks (non-leaky). CAM stores `(cue_byte → answer_byte)` associations learned from correct predictions.

### `GENESIS_CAM_SLOTS`
- **Values:** integer (1–256)
- **Default:** `32`
- **What it does:** Number of (key, value) slots per organism. Each slot holds an 8-bit key and 8-bit value.
  - `8`: Bare minimum — can only store 8 cue→answer mappings.
  - `32`: **(recommended)** — stores all 16 Hard_WM cues plus extra.
  - `64`: Stores all 64 composite pairs for compositionality tasks.

**CAM Read:** Every tick, computes Hamming similarity between the current sensory byte and all stored keys. The best match (≥6/8 bits) is fed back as input channel 1.

**CAM Write:** On every tick, stores `(delay_buffer[curriculum_delay-1], current_sensory_byte)` in the LRU (least-recently-used) slot. This creates associative memory: "last time I saw cue X, the answer was Y."

---

## 8. Structural Plasticity

*Added in Exp 30 (2026-07-23). Proven: +30pp on compositionality tasks.*

### `GENESIS_STRUCTURAL_PLASTICITY`
- **Values:** `0` (off) | `1` (on)
- **Default:** `1`
- **What it does:** Enables synapse rewiring and pruning during an organism's lifetime. Breaks the fixed-topology limitation.

**Synapse Growth (Rewiring):** When a hidden neuron fires but has no strong outgoing synapses (max |weight| < 5.0), the weakest outgoing synapse is rewired to a new pseudo-random hidden-neuron target.

**Synapse Pruning:** Synapses with |weight| < `SP_PRUNE_THRESHOLD` are set to weight 0, effectively removing them.

### `GENESIS_SP_GROWTH_COST`
- **Values:** float
- **Default:** `10.0`
- **What it does:** Energy cost for one synapse rewire operation. Set to ~5-10× a simple STDP update.

### `GENESIS_SP_PRUNE_THRESHOLD`
- **Values:** float
- **Default:** `0.5`
- **What it does:** |weight| threshold below which a synapse is pruned. Higher = more aggressive pruning.

### `GENESIS_SP_MAX_GROWTH`
- **Values:** integer
- **Default:** `3`
- **What it does:** Maximum synapse rewires per tick per organism. Limits topology churn.

### `GENESIS_SP_MAX_PRUNE`
- **Values:** integer
- **Default:** `5`
- **What it does:** Maximum pruned synapses per tick per organism.

### `GENESIS_SP_REWIRE_WEIGHT`
- **Values:** float
- **Default:** `5.0`
- **What it does:** Initial weight for newly created synapses. Must be above `SP_PRUNE_THRESHOLD` to survive the first pruning check.

---

## 9. Checkpointing

### `GENESIS_BRAIN_PATH`
- **Values:** filesystem path
- **Default:** `Brain/Brain.npz`
- **What it does:** Where the Brain checkpoint is saved/loaded.

### `GENESIS_RESUME`
- **Values:** `0` (fresh start) | `1` (resume)
- **Default:** `1`
- **What it does:** When `1`, loads the Brain checkpoint from `GENESIS_BRAIN_PATH` and resumes the simulation. When `0`, starts a fresh universe.

### `GENESIS_MAX_ERAS`
- **Values:** integer (0 = forever)
- **Default:** `0`
- **What it does:** Maximum extinctions before the simulation halts. Used for ascension probes. `0` = run forever.

### `GENESIS_MAX_TICKS`
- **Values:** integer (0 = forever)
- **Default:** `0`
- **What it does:** Maximum world-ticks before the simulation halts. `0` = run forever. Set to e.g. `50000` for controlled experiments.

---

## 10. Runtime & Debug

### `GENESIS_HEADLESS`
- **Values:** `0` (dashboard) | `1` (headless)
- **Default:** `0`
- **What it does:** When `1`, runs without the WebSocket dashboard server. Faster — use for batch experiments.

### `GENESIS_EVOSENSE_SEED`
- **Values:** `0` | `1`
- **Default:** `0`
- **What it does:** Seed evolvable sensors in the Intelligent Ancestor at startup.

### `GENESIS_EVOACT_SEED`
- **Values:** `0` | `1`
- **Default:** `0`
- **What it does:** Seed evolvable actuators in the Intelligent Ancestor at startup.

### `NUMBA_CACHE_DIR`
- **Values:** filesystem path
- **Default:** None (Numba default)
- **What it does:** Numba compilation cache directory. Set to e.g. `/tmp/numba_cache` to persist compiled kernels across runs with identical feature flags.

---

## Quick Reference Cards

### 🧪 For AGI Research (Default)
```bash
GENESIS_ECONOMY=books \
GENESIS_BOOK_NAME=Hard_WM \
GENESIS_DELAY=1 \
GENESIS_DELAY_N=3 \
GENESIS_DEPLETE=1 \
GENESIS_CAM=1 \
GENESIS_CAM_SLOTS=32 \
GENESIS_HOMEOSTATIC_LAMBDA=0.01 \
GENESIS_STRUCTURAL_PLASTICITY=1 \
GENESIS_HEADLESS=1 \
GENESIS_MAX_TICKS=200000 \
python src/genesis_lab.py
```

### 🔬 For Ablation Experiments
```bash
# Disable CAM:
GENESIS_CAM=0 ... python src/genesis_lab.py

# Disable Structural Plasticity:
GENESIS_STRUCTURAL_PLASTICITY=0 ... python src/genesis_lab.py

# Disable Homeostatic STDP (original destructive STDP):
GENESIS_HOMEOSTATIC_LAMBDA=0 ... python src/genesis_lab.py

# Freeze all learning (NOLEARN):
GENESIS_NOLEARN=1 ... python src/genesis_lab.py

# Disable DEPLETE (unlimited reading fuel):
GENESIS_DEPLETE=0 ... python src/genesis_lab.py
```

### 📚 For Curriculum Testing
```bash
# Hard_WM (16 cues, random permutation, delays 4-64):
GENESIS_BOOK_NAME=Hard_WM ...

# GradedMemory (2 cues, graded delays 1-40):
GENESIS_BOOK_NAME=GradedMemory ...

# DelayedMatch (match-to-sample):
GENESIS_BOOK_NAME=DelayedMatch ...

# Custom curriculum (put your file in Books/<Category>/):
GENESIS_BOOK_CATEGORY=MyCategory \
GENESIS_BOOK_NAME=my_curriculum ...
```

---

## Rule 19 Compliance Note

All tunable parameters above are classified as either:

| Symbol | Meaning |
|:------:|---------|
| **✅ DERIVED** | Hardware-derived (e.g., `CELL_STATES = 2^8` from 8-bit byte) |
| **📐 MODEL** | Model parameter with documented rationale (needs calibration) |
| **❌ UNJUSTIFIED** | Status: needs experimental calibration (scheduled for Exp 31) |

Unjustified parameters are env-gated for easy tuning. See `Docs/MagicNumbers.md` for the full audit.

---

*Generated by Clusy AI Agent — 2026-07-23*
