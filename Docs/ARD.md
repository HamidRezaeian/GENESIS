# Architecture Requirements Document (ARD)

> **Status:** Reflects the live codebase as of 2026-07-10 (the genome-encoded Spiking
> Neural Network engine). Earlier opcode/graph engines described in prior revisions
> (`turing_engine.py`, `genesis_engine.py`, `DynamicBrain`) have been deleted and are
> preserved only as historical narrative in `Result.md` / `Article_Draft.md`.

## 1. System Architecture
GENESIS is split into a **Python Backend (Neuromorphic Physics Engine)** and a
**Vanilla-JavaScript Frontend (Observation Deck)**, connected over a single WebSocket
(`ws://<host>:8085`).

### 1.1 Backend
Two modules plus a curriculum helper:
- **`neuromorphic_engine.py`** — the hot path, a Spiking Neural Network simulator compiled
  to machine code with **Numba `@njit(cache=True)`**. Contains the memory allocator,
  genome decoder, sensory encoder and the per-tick world update `world_tick_numba`.
- **`genesis_lab.py`** — owns all global state (NumPy arrays), the deep-time `sim_loop`,
  reproduction/mutation, the Elite Ark, and the `asyncio`/`websockets` server.
- **`books_of_genesis.py`** — injects ASCII curriculum text into the RAM substrate.

### 1.2 The Universe (RAM Substrate)
- **Space is literal RAM.** A 1D toroidal `uint8` array of **`RAM_SIZE = 65536`** bytes
  (`g_ram`). An organism's position is a byte address; movement is pointer arithmetic
  modulo `RAM_SIZE`.
- **Food** is the byte value `0x55`, seeded (≈1000 bytes at start, then replenished at a
  user-controlled rate) only into empty (`0x00`) cells.
- **Curriculum / Oracle text** occupies the printable ASCII range (`32–126`).

### 1.3 The Global Heap (No per-organism matrices)
Neurons, synapses and genomes for the whole universe live in flat global arrays, and each
organism `malloc`s contiguous blocks from them via `malloc_block`/`free_block`:
- `UNIVERSE_MAX_NEURONS = 500000`, `UNIVERSE_MAX_SYNAPSES = 2000000`,
  `UNIVERSE_MAX_DNA = 5000000`, `MAX_ORGANISMS = 600`, `MAX_DNA_PER_ORG = 8192`.
This models the universe's total computational matter as one shared heap; memory
fragmentation is itself a spatial hazard.

### 1.4 Organisms — Genome-Encoded SNNs
A genome is a byte string parsed into three record types:
- **`RECEPTOR_MARKER = 195`** (10 bytes): a "receptor protein" — one of up to
  `MAX_RECEPTORS_PER_ORG = 16` DNA-encoded plasticity profiles
  `(A_PLUS, A_MINUS, TAU_P, TAU_M, V_REST, V_RESET, TAU_DEFAULT, SPIKE_RATE_MAX)`.
- **`NEURON_MARKER = 162`** (5 bytes): a hidden neuron, expressing a receptor id, a
  threshold and a leak time-constant.
- **`GENE_MARKER = 161`** (4 bytes): a synapse `(src, dst, weight)`; `weight` maps a raw
  byte to `float(w) − 128` (i.e. −128..+127).

Every organism has a fixed I/O layer of **`N_INPUT = 15`** sensory + **`N_OUTPUT = 14`**
motor neurons (`N_IO = 29`) plus a variable number of hidden neurons.

### 1.5 Neuron & Synapse Model
- **Leaky Integrate-and-Fire** with `float32` voltage: leak `v += (v_rest − v)/tau`,
  fire when `v ≥ threshold`, reset to `v_reset`, refractory `TAU_REF = 1` step.
- **Input neurons** fire stochastically with probability proportional to the sensed value
  × the receptor's `SPIKE_RATE_MAX`.
- **STDP (Hebbian)**: on a post-synaptic spike, pre-before-post potentiates
  (`w += A_PLUS·e^(−Δt/TAU_P)`); pre-after-post depresses
  (`w −= A_MINUS·e^(−Δt/TAU_M)`). Weights clamp to `[W_MIN, W_MAX] = [−128, 127]`.
- Learned weights are **not** written back to the genome (Baldwin-effect lifetime
  learning); offspring inherit the *initial* DNA-encoded weights only.

### 1.6 Sensors (15) and Motors (14)
- **Inputs:** `0` energy reserve, `1` constant bias, `2` local crowding (density),
  `3` RAM byte under the pointer, `4–6` neighbours' vocal-cord bits (low/mid/high),
  `7–14` the 8 bits of the Oracle broadcast.
- **Outputs:** `0` jump +1, `1` jump −1, `2` jump +10, `3` jump −10, `4` consume,
  `5` reproduce, `6–13` the 8 vocal-cord bits (emitted ASCII character).

### 1.7 Frontend: The Observation Deck (`public/`)
- Renders the 65536-byte RAM as a folded 256×256 HTML5 canvas: food `0x55` green, living
  organisms blue, vocalising ("screaming") organisms yellow, curriculum text purple.
- KPI tiles (era lifespan, population, extinctions, elite age), an extinction chart, a D3
  **Brain Analyzer** that decompiles the Elite genome's synapses, an **Oracle Terminal**
  to broadcast ASCII into the universe, and a **Library of Genesis** curriculum injector.

## 2. Core Mechanisms
### 2.1 Thermodynamics = CPU Cycles
Energy is execution cycles, drained per action from each organism's reserve
(`ATP_MAX = 1,000,000` ceiling):
- synapse read `1`, movement `3`, per-step idle metabolism `0.1 × n_neurons`, a viscosity
  stall costs `n_neurons` cycles.
- **Consume** a `0x55` food byte → `+CYCLES_PER_EAT_GAIN = 1024`.
- **Reproduce**: pay `genome_length × CYCLES_PER_BYTE_COPY` to copy the genome, then split
  the remaining energy in half with the child. An organism dies when energy `≤ 0`.

### 2.2 Computational Viscosity (Rule 13)
Each tick, local code density in a ±16-byte window sets a stall probability (up to 0.5).
Stalled steps still burn maintenance energy but do no computation, penalising dense
genomes and (in principle) favouring sparse topologies.

### 2.3 Conservation of Compute
The per-tick LIF step budget is a global pool: `steps = GLOBAL_CYCLE_POOL(3000) / population`.
Mass replication dilutes everyone's compute, coupling population to a fixed energy budget.

### 2.4 Cosmic Radiation (Entropy)
Two random bit-flips per tick are applied to the global genome arena, providing thermal
mutation pressure. *(Known limitation: because phenotypes are decoded once at spawn and
most of the 5 MB arena is unallocated, this currently behaves as inheritance noise rather
than real-time entropy — see the roadmap.)*

### 2.5 The Elite Ark (Rule 14)
`sim_loop` continuously tracks the highest-age living genome. On **total extinction** the
universe is reseeded (300 organisms) from mutated copies of that Elite genome, guaranteeing
strictly ascending evolution; the Elite genome is also checkpointed to `Brain/Brain.npz`.

### 2.6 Reproduction & Mutation
`mutate_dna` applies insertion (5%), deletion (5%) or gene duplication (5%), otherwise
point mutations at an expected rate of `1/genome_length` (thermal copy noise). Bytes 0–1
(the base receptor marker) are protected so a lineage can never lose all STDP in one flip.

### 2.7 The Oracle Uplink & Curriculum
The user can broadcast an 8-bit character (sensed on inputs 7–14) and read back the Elite's
vocal-cord output, and can inject ASCII "books" as byte patterns into the substrate — the
current, still-human-in-the-loop scaffold toward the Autotelic Imperative (Rule 9).
