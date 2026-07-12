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
- Lifetime STDP changes are held in the runtime weight array (Baldwin-style in-lifetime
  learning). At **reproduction** they are **partially written back**: each synapse's weight
  byte is blended 50/50 with the weight the parent learned via STDP this lifetime
  (**Lamarckian consolidation**, `neuromorphic_engine.py` birth block ~L498–521), so
  acquired plasticity is partially heritable rather than reset to the initial DNA value each
  generation. See §2.6 (Reproduction) and `Result.md` Exp 2. *(An earlier revision of this doc
  claimed learned weights were never written back — that is stale; the 50/50 blend adds a
  Lamarckian channel on top of Baldwin lifetime learning.)*

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
(`ATP_MAX = 1,000,000` ceiling). Costs are **honest raw-cycle counts** — one executed
operation debits one cycle (Rule 15/17), with no arbitrary discounts:
- synapse transmission `1` (when the pre-synaptic neuron fired), **neuron membrane update
  `1 × n_neurons` per step** (`CYCLES_PER_NEURON_UPDATE`), **STDP weight update `1`**
  (`CYCLES_PER_STDP_UPDATE`, charged only when a synapse actually potentiates or depresses —
  activity-gated), movement `3`, and a viscosity stall costs `n_neurons` cycles.
- **Consume** a `0x55` food byte → `+CYCLES_PER_EAT_GAIN` (default **15,000**, env-tunable via
  `GENESIS_EAT_GAIN`; the `books` economy sets it to **16** so mindless grazing is bare
  subsistence). *This meal value is an un-derived Rule 17 constant still under review (Roadmap P4).*
- **Reproduce**: pay `genome_length × CYCLES_PER_BYTE_COPY` to copy the genome, then split
  the remaining energy in half with the child. An organism dies when energy `≤ 0`.

Because neuron and synapse work is now billed at its true rate — the neuron update was
formerly discounted to `0.1×`, making brain size ~10× too cheap to matter — a leaner brain
retains more energy and out-reproduces a costlier one. **Rule 7 efficiency is therefore
selected _emergently by thermodynamics_, never by a fitness metric** (the dashboard
`elite_iq = age / footprint` is observation-only and must never feed back into selection;
Rule 5/9). Synapse/plasticity costs are deliberately **activity-gated** rather than a flat
size tax, so the substrate rewards *many synapses firing sparsely* (the 20 W paradigm,
Rule 11), not merely *few* synapses. Sensory input is computed once per world-tick (it is
invariant across a tick's LIF sub-steps), keeping the simulator itself lean.

### 2.2 Computational Viscosity (Rule 13)
Each tick, local code density in a ±16-byte window sets a stall probability (up to 0.5).
Stalled steps still burn maintenance energy but do no computation, penalising dense
genomes and (in principle) favouring sparse topologies.

### 2.3 Architecture-Derived Compute Latency
Each organism runs, per world-tick, exactly as many LIF substeps as its own synapse graph is
**deep** — the longest input→node path plus one final membrane fire, computed at spawn from the
decoded topology (`g_org_lif_steps`). Metabolic burn (1 cycle/neuron/substep) therefore scales with
an organism's real computational latency: a 1-hop echo reflex costs 2 substeps, a deeper evolved
brain costs proportionally more. This replaces an earlier population-coupled step *pool*
(`steps = GLOBAL_CYCLE_POOL / population`), which was un-physical — an organism's burn depended on
how many *others* were alive — and a death-spiral: as a population fell, each survivor ran more
steps and burned faster, forcing synchronous collapse regardless of income. Consequence: **Rule 7
efficiency is selected emergently** — deeper, costlier brains are out-reproduced by leaner ones with
no imposed constant or fitness term (measured: a books cohort's mean depth selects 8→2). The world
clock advances each tick by the deepest live brain's latency so sub-tick STDP timestamps never
collide across ticks.

### 2.4 Cosmic Radiation (Entropy)
Each tick, two random bit-flips are applied **inside the genomes of living organisms**
(germline mutation), not into the mostly-empty 5 MB arena where ~99% of flips previously
landed in vacuum. This is heritable thermal entropy that error-correction must out-run.
*(Known limitation: a phenotype is decoded once at spawn, so a flip alters the organism's
OFFSPRING, not its already-running brain; true in-lifetime somatic entropy remains future
work — see the roadmap.)*

### 2.5 The Elite Ark (Rule 14)
`sim_loop` continuously tracks the highest-age living genome. On **total extinction** the
universe is reseeded (300 organisms) from mutated copies of that Elite genome, guaranteeing
strictly ascending evolution; the Elite genome is also checkpointed to `Brain/Brain.npz`.

### 2.6 Reproduction & Mutation
`mutate_dna` applies insertion (5%), deletion (5%) or gene duplication (5%), otherwise
point mutations at an expected rate of `1/genome_length` (thermal copy noise). Bytes 0–1
(the base receptor marker) are protected so a lineage can never lose all STDP in one flip.

**Lamarckian consolidation (generational memory).** Before mutation, the birth path
(`neuromorphic_engine.py` ~L498–521) re-walks the child's copied genome exactly as
`decode_genome` does and, for every hidden/output synapse, overwrites the weight byte with a
50/50 blend of (a) the parent's initial DNA-encoded weight and (b) the weight the parent
**learned via STDP** this lifetime (`global_conn_weight`, re-encoded `+128`). Acquired
plasticity is therefore partially heritable — a Lamarckian channel layered on top of the
Baldwin-style lifetime learning of §1.5. The 50/50 constants are currently hardcoded inline
(a Rule 17 target for DNA-encoding).

### 2.7 The Oracle Uplink & Curriculum
The user can broadcast an 8-bit character (sensed on inputs 7–14) and read back the Elite's
vocal-cord output, and can inject ASCII "books" as byte patterns into the substrate — the
current, still-human-in-the-loop scaffold toward the Autotelic Imperative (Rule 9).
