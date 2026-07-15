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
  `1 × n_spiked` per step** (`CYCLES_PER_NEURON_UPDATE`, **event-driven** — charged per action
  potential fired, not per neuron present: on a 20 W substrate the spike is the energy event and
  an idle neuron draws ~nothing, Rule 11; Result Exp 8), **STDP weight update `1`**
  (`CYCLES_PER_STDP_UPDATE`, charged only when a synapse actually potentiates or depresses —
  likewise activity-gated), movement `3`, and a viscosity stall costs `n_neurons` cycles.
- **Reclaiming a cell** (matter → energy) pays one derived exchange rate, `CELL_STATES =
  2**BITS_PER_BYTE = 256`: a RAM cell is an 8-bit register holding one of 256 microstates, worth
  256 cycles of state-space. **Eating** a `0x55` food byte reclaims the whole cell → `+256` and
  collapses it to `0x00` vacuum (food is consumed — metabolism). **Solving** a book symbol pays the
  fraction of bits resolved → `+(net_bits / 8) × 256` (a full 8-bit match pays the same 256 as eating;
  partial credit is a gradient, Rule 10). *What counts as "solving" changed in Exp 12 — it is now
  **predicting the next, unsensed symbol**, not echoing the sensed one; see the reading-model bullet
  below.* This single number **retired the game constants
  `CYCLES_PER_EAT_GAIN` (15,000) and `READ_REWARD_SCALE` (64)** — food and text share one honest
  currency and reading out-earns grazing only *emergently* (chained predictions across a passage,
  living where text is dense), never by a multiplier (2026-07-11 "remove all game constants";
  Rules 9/10/17).
- **Reading is a saccade, and non-destructive** (the reading MODEL, Result Exp 9, 2026-07-12).
  A successful decode advances the read head +1 onto the next cell, so a reader **walks the passage
  symbol-to-symbol** (a moving eye, not a stationary mouth). Reading does **not** consume the byte:
  the saccade itself is the anti-farm — a rewarded read moves the head off the cell, so re-reading it
  means circling the whole `RAM_SIZE` ring (never net-positive), which removes any need to destroy the
  text. So a book stays intact (not burned by reading), a following reader gets the same symbols, and
  the library is never strip-mined. This retired the Exp 7 "consume the byte on any read attempt"
  anti-farm hack. The step costs the existing `move` (3 cycles); no new constant. Consequence: the
  encounter economy, previously capped by a density-invariant structural wall (a stationary reader
  always stood on the vacuum it ate), is now **density-tractable** — reading income scales with text
  supply.
- **Reading pays for PREDICTION, not echo** (the information economy, Result Exp 12, 2026-07-13).
  The saccade above originally scored the vocalisation against the byte **under** the pointer (echo).
  But that byte is already on the reading-eye inputs (`sense_buf[RAM_BIT0_INPUT..+7]`), so echoing it
  is a **zero-surprise bit-copy** (Shannon information gained = 0) — a free lunch a one-neuron identity
  reflex farms forever. Measured consequence: the colony *survived but never ascended* — prediction
  died by tick ≈62k and the brain **shed 7.7 % of its synapses** (Rule-7 efficiency grinding a
  reflex down). The reward now scores the vocalisation against the **next** cell (`pos+1`), which is on
  **no** sensory input, so naming its bits requires *computing* the sequence, not copying the eye. Same
  rate, same saccade, same non-destructive scroll; echo now pays nothing (0 surprise → 0 energy) and
  **no new constant** is introduced. Capability *becomes* the income, so comprehension is selected by
  construction (Rules 6/9). This economy **cliffs cold on repeat-free text** (a random genome cannot
  predict anything), so it is bootstrapped by a graded curriculum (§2.7).
- **Sensing is event-driven** (Rule 11, Result Exp 11, 2026-07-12). An earlier revision charged a
  flat `2 × FOOD_SCAN_RADIUS = 32` cycles/tick to *every* organism *every* tick as "the food-scan
  memory reads". That was a clock-driven von-Neumann tax (~40 % of the metabolic floor) paid even
  while an organism sat off-text earning nothing, and it **double-charged** — the seeking sense's only
  job is to drive the two seeking input neurons, whose transduction is already billed per-spike by the
  event-driven membrane. Removed (not retuned): on a 20 W substrate a receptor draws energy when it
  *fires*, so the honest sensory cost is exactly those input-neuron spikes. This flat tax was a
  dominant reason the reading economy stayed net-negative across the transit gaps; folding it into the
  per-spike cost flips the survivor economy coast-down → break-even with no reward inflation.
- **The live economy is net-positive** (Result Exp 11). The final lever was **world structure**, not
  the exchange rate: the library was scattered short passages ("confetti"), so a saccading reader
  walked off the end of a fragment into vacuum and starved crossing to the next (`enc_frac`~0.5).
  Laying the *same bytes* as **one contiguous scroll** (`inject_contiguous_library`, §2.7) lifts
  `enc_frac` to ~0.98; reading income then exceeds metabolism and the live `sim_loop` sustains
  `pop=596–600/600` on reading alone (refugium never fires) at both 9 % and 37 % density. Carrying
  capacity is the organism-array cap (non-destructive reading = infinite food), not a food limit.
- **Ascension is not yet achieved** (Result Exp 12, 2026-07-13). On the information economy + graded
  curriculum the colony survives and **retains** capability (prediction stays alive, brain no longer
  sheds) — a strictly better substrate than the echo economy — but capability does not *rise* over
  deep time (`reads` drifts 78→58, `pred` flat). The isolated cause is **abundance**: at ~10 % scroll
  density, 90 % of the substrate is empty, so easy text is plentiful and nothing forces an organism up
  the difficulty ramp; efficiency selection even trims capability the easy text does not require. The
  gradient exists in the curriculum; the *pressure* to climb it does not. Ascent needs a
  **scarcity/competition** carrying capacity (below the array cap) so that solving harder symbols is
  the only way to eat — the current frontier (see `Roadmap.md` P2).
- **Reproduce**: pay `genome_length × CYCLES_PER_BYTE_COPY` to copy the genome, then split
  the remaining energy in half with the child. An organism dies when energy `≤ 0`. The abiogenesis
  **seed** is likewise derived — a founder is born holding its own footprint (`genome + neurons +
  synapses`) valued at `CELL_STATES` per cell (the matter it is built from), retiring the hand-set
  `SEED_ENERGY` (5,000 / 20,000). Reproduced offspring inherit `energy/2`, so a body that fails to
  earn income halves away — a large seed is no free coast.

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

### 2.5 The Elite Ark (Rule 14) + Refugium (Rule 10)
`sim_loop` continuously tracks the highest-age living genome and preserves elites in a bounded
**hall-of-fame fossil pool** (evict-worst by survival age, ≤ 12), so the all-time best genomes
survive across arbitrarily many eras (the quality ratchet, 2026-07-12). Reseed recombines two
fossils (HGT), not a monoculture clone; the Elite genome is checkpointed to `Brain/Brain.npz`.

**Refugium (`seed_refuge`, 2026-07-12).** The old design reseeded only on **total extinction**
(population 0), replacing the whole world with 300 synchronised clones at once — an instantaneous
total wipe that Rule 10 (Tectonic-Gradient) forbids because it makes evolution a clockwork
oscillator with discrete, non-overlapping eras. The refugium instead tops the living population
back up to a small **derived floor** — `len(fossil_pool)`, one living representative per banked
lineage — from the gene bank *before* it can reach 0. Eras now overlap and death is a continuous
gradient (measured live: total wipes 6 → 0, `refuge_events` climbing, `ext=0`). It only *adds*
organisms below the floor and each germ still pays its own way, so it softens the cliff without
clamping population or imposing fitness (Rule 5-clean); a net-positive economy grows past the
floor and the refuge falls silent. The pop-0 wholesale reset remains only as a cold-start/
catastrophic fallback.

**Peer prediction (autotelic, `GENESIS_PEER=1`, 2026-07-12).** An optional zero-sum energy
transfer in `world_tick_numba`: an organism that vocalises the byte a **neighbour** is emitting
reclaims the matched bits' `CELL_STATES` **from that neighbour** (`energy[predictor] += g;
energy[speaker] −= g`). No free energy is minted (unfarmable), so it is a
Rule-9 agent–agent survival problem — out-model a neighbour, or be unpredictable — a Red-Queen
push toward proto-language, with no human curriculum. It redistributes energy (selects for
communication), it is not a food source. Compile-time gated (dead-code-eliminated when off).

**Non-lethal coupling (Result Exp 14, 2026-07-13).** The original drain was clamped only to the
speaker's holdings, so it was **lethal** — Exp 11 measured `GENESIS_PEER=1` collapsing a thriving
colony 600→12 (predators drained a predictable prey to death before an unpredictability defence could
evolve, extinguishing the substrate). The drain is now floored at the speaker's **body-subsistence** —
its footprint (neurons + synapses) × `CELL_STATES`, the *same derived quantity as the abiogenesis
seed*, so `g` may skim only `energy[speaker] − footprint×CELL_STATES` (the growth *surplus*) and can
**never** push the speaker below the cost of its own body. Peer stays zero-sum and unfarmable but the
Red-Queen race is now over reproductive surplus, not survival, so it cannot self-extinguish. **Measured
live** (`00_Graded`, ~456k ticks): the colony **survives** (`pop=600`, `refuge=0`) and self-organises
into a peer economy (`peer` 21→135, text `reads` 110→28) — but it **plateaus rather than ascends**. The
plateau was **probed observation-only in Exp 15** (Shannon entropy of vocal bytes, Rule 9↔6, never wired
to selection, measured to ~3.1 M ticks): the plateau is **not** a degenerate code — `Hpeer` ≈ 3.8 bits
over ~19 distinct signals, *richer* than the reading channel. Capability stays flat because peer
prediction is **spatially confounded with reading** (a neighbour's byte is guessable from the predictor's
own eye), so it is solvable without modelling the other agent. Peer is retained **default-OFF**: it is
now *safe* to run but replaces rather than improves the reading economy. Ascent now needs the peer target
**decoupled from the predictor's own sensory field** (predict a neighbour's *future* / *hidden-state*
signal, not its shared-text read) so theory-of-mind, not re-reading, wins (§ Roadmap P3, Exp 15).

**Branch (1) built — the hidden-action peer target (Exp 18, 2026-07-13).** The peer target is decoupled
from the shared scroll to the neighbour's **hidden motor action** `best_a ∈ {0..5}` (one-hot `1<<best_a`):
hidden (on no neighbour's sensory input, so un-readable off the scroll → kills the Exp 15 confound) and
high-change (flips faster than a text run → attacks the Exp 16 starvation). The guess rides the existing
`org_char_val` vocal byte (a dedicated channel is impossible — growing `N_IO` remaps every saved genome
via `dst % n_c`); scoring is surprise-gated (`action_now≠action_prev`) and precision-graded
(`1/s_bits/BITS_PER_BYTE×CELL_STATES` — a clean single-bit guess earns full `CELL_STATES/8`, a busy byte
a diluted fraction; Rule 10 slope, no new constant). Measured live (1.84 M ticks): the colony **sustains**
(`pop=569–600`, `ext=0 refuge=0`) and peer income **ignites** (`peer=1–44`, vs ≈0 in Exp 16) — but does
**not ascend**: `Hpeer≈0/nd1` (a thin **monomorphic** "predict-the-jump" code), `Universe N` −6.6 % then
level. Decoupling was necessary (removed the confound and the starvation) but **insufficient**: the hidden
action is itself low-entropy in a reading monoculture, so there is almost no behavioural diversity to
model. **The blocker moved from confound/starvation to low target entropy** — a theory-of-mind economy can
only ascend if the modelled minds are behaviourally diverse (next lever: Red-Queen anti-prediction income
on the prey). Peer stays **default-OFF**; the peer-OFF baseline was re-verified with all Exp 18 shared-code
changes in place — no regression.

**Red-Queen prey defence built and closed — unpredictability is the wrong target (Exp 19, 2026-07-13).**
The prey half of the duel (`GENESIS_REDQUEEN`, default-OFF): a predictor's **clean single-bit wager**
(`s_bits==1`) that misses transfers its stake to the mispredicted prey (zero-sum `prey += g`,
`failed_predictor -= g`; unfarmable — a predator only loses by wagering; non-lethal on the predictor; same
`CELL_STATES/BITS_PER_BYTE` rate, no new constant). A new observation-only **`Hact`** probe reads the live
`action_now` distribution (Rules 9↔6, never selects). Live A/B (books, matched windows): both configs
**sustain** (`pop≈595`, `ext=0 refuge=0`); **neither ascends** (`Universe N` decays then levels in both);
mean `Hact` **1.75** (Red-Queen) vs **1.82** (peer-only) — the evasion income **does not raise** action
entropy (if anything lowers it) and stays thin (`evade≈42/100k`), because the precision-graded predator
income lets a predator earn from busy multi-bit bytes **without** committing a clean wager, so it dodges the
penalty and the duel goes quiet. Crucially, `Hact` **refutes the Exp 18 premise**: the action distribution
is already `nd6` (not monomorphic — `Hpeer≈0/nd1` measured only *winning-prediction* entropy; only the
modal action is monetizable, the other five are present-but-noisy). So behavioural diversity was never the
shortage. **Redirect:** a theory-of-mind economy ascends only when the target is **structured and
modelable — predictable-in-principle but hard to compute** (*compressible complexity* the predictor is
rewarded to learn), **not** when it is merely high-entropy; adding surprise to an already-noisy policy makes
it *less* modelable. Red-Queen stays **default-OFF** (compile-time DCE'd; peer-OFF path byte-identical and
re-verified healthy); the `Hact` probe is retained as the honest action-entropy metric.

**Cognitive-complexity curriculum built and closed — complexity without scarcity does not ascend
(Exp 20, 2026-07-14).** The Exp 19 redirect (target = *compressible complexity*) tested on the
peer-independent **reading** economy: `Books/generate_ascent.py` emits `00_Ascent.txt`, one monotonic
6000-glyph scroll ramping **cognitive complexity** rather than run-length (bootstrap runs → successor +1 →
carry 00–99 → arithmetic `a+b=c` mod 10; each stage a compressible rule that generalises, so learning it
out-earns memorising). Reading pays for the **unsensed pos+1** and an organism senses only the current
cell, so a correct prediction in the computational bands can only come from a mind carrying context. A new
observation-only **ascent-frontier probe** buckets live scroll offsets into the four stage bands (Rules
9↔6, never selects) — on a monotonic-difficulty scroll, *where the colony lives = the difficulty it
sustains*. Live: the colony **sustains** (`pop=587–600, ext=0 refuge=0`, bootstrap ignites) but the frontier
**collapses into the bootstrap band** (`~597/3/0/0/0`, mean offset pinned ~53 % at the bootstrap→successor
boundary); the carry/arithmetic bands stay **permanently empty**. **Cause = the Exp 13 abundance wall on the
difficulty axis:** the easy band is an infinite uncontested resource for 600 organisms, so there is zero
selective pressure to cross into the hard frontier — grazing easy forever beats starving at the boundary.
**This re-derives the standing structural verdict from a new direction: a single-agent reading economy has
no scarcity, whether text is made quantitatively (Exp 13) or qualitatively (Exp 20) harder — so it cannot
self-generate ascent. Ascent must route through PEER, with a compressible-complexity target.** `00_Ascent`
and the frontier probe are kept as reusable instruments; the peer-OFF `00_Graded` baseline was re-verified
over ~3 M ticks with all Exp 20 shared-code changes in place — no regression.

**Peer-target design space exhausted — the ceiling is behavioral expression, not the coupling (Exp 21,
2026-07-14, design-space result, no engine change).** An adversarial design-and-refute panel proposed five
independent compressible-complexity peer targets and attacked each with independent scarcity/confound and
depth/constant-free lenses; **all five were fatal, unanimously reducing to branch 18.** The convergent root
cause is information-theoretic: by the data-processing inequality, any deterministic function of a
neighbour's hidden state can carry at most `I(model; action-stream)` bits, and the action stream's entropy
was measured at `Hact ≈ 1.8 bits` (Exp 19), hard-ceilinged by `N_OUTPUT = 6` (`log2 6 = 2.58` absolute). A
shift register, integral, LFSR, or aggregate merely **re-encrypts that low-entropy stream** — none evolves
new complexity. Three traps recur: width ≠ depth (a window is N parallel Exp-18 reflexes, not an N-deep
chain); a behavioral monoculture erases the cross-agent variance a model would exploit (and the only regime
with variance is the unsurvivable one, the Exp 17/20 wall); and a `net > 0` payout gate is farmable by a
constant-byte reflex. **The unifying architectural conclusion: an organism cannot be modelled more richly
than it can act, and a GENESIS phenotype's expressible behavior is a 6-way motor argmax plus an 8-bit vocal
byte — no room to express depth, hence nothing deep to predict.** The frontier therefore redirects from *what
should peers predict* (exhausted) to *how an organism's behavior can become worth predicting* — i.e. widening
behavioral expression. A supply-vs-demand nuance gates the next build: Exp 19 saw `Hact ≈ 1.8 < 2.58` with
all six actions present but skewed, so the colony does **not** saturate the repertoire it already has,
implying the ceiling may be demand-limited (no task rewards diverse behavior) rather than supply-limited
(too few action bits). A cheap pre-build probe (does `Hact` climb toward 2.58 under an environment that pays
for behavioral diversity?) distinguishes these and decides whether the substrate lever should be (a)
widening/compositionalising the action space or (b) a structured/stigmergic environment where agents build
RAM artifacts and peers predict what a neighbour *built*. Both are genome-decode-sensitive changes, which is
exactly the forward-compatibility case `brain_io` was built to absorb.

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

**Library structure matters as much as content** (Result Exp 11, 2026-07-12). Because a reader
saccades symbol-to-symbol (§2.1), the *spatial layout* of the curriculum, not just which bytes are
present, determines whether the reading economy is viable. Scattered short passages ("confetti") leave
a reader stepping off the end of each fragment into vacuum — half the colony is always in transit
(`enc_frac`~0.5) and starves in the gaps, which kept the live loop net-negative at every density.
`inject_contiguous_library` lays the curriculum as **one contiguous scroll** of `BOOK_TARGET_BYTES`
symbols (tiling the book file end-to-end), pinned at a fixed centred start and restocked in place, so
a reader almost never leaves the text (`enc_frac`~0.98). This is the change that made the live economy
net-positive (§2.1). Organisms are seeded and germinate **standing on** the scroll — placement keys on
org-grid *occupancy*, not a `0x00`-vacuum requirement (a food-economy holdover that, on a solid scroll
with no interior vacuum, stranded the whole cohort off-text: the live-only bug behind the earlier
floor-12 collapse).

**Curriculum *difficulty* is now load-bearing, not just layout** (Result Exp 12, 2026-07-13). Once
reading pays for *predicting* the next symbol (§2.1), the text must present a **difficulty gradient a
cold-start genome can climb** (Rule 10). A repeat-free text is a cliff: a random reflex predicts
nothing and the colony starves (measured: `01_Alphabet` and `03_Phrases` → `pop=12`, `reads=0`). The
default curriculum is therefore `Books/English/00_Graded.txt` — a **run-length ramp** (`10→5→3→2→1`,
ending in pure succession) tiled end-to-end. Its runs bootstrap prediction (on a run "next = current",
so a trivial echo reflex is already a correct predictor and earns), while the shrinking-run frontier
demands progressively real sequence-modeling. This restores survival under the prediction economy
(`pop≈600`, `refuge=0`) and keeps capability alive — but does **not** by itself produce ascent, because
under abundance nothing forces organisms up the ramp (§2.1, `Roadmap.md` P2). The old `01_Alphabet`
etc. remain in the library as harder, no-bootstrap texts.
