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
A genome is a byte string parsed into record types:
- **`RECEPTOR_MARKER = 195`** (10 bytes): a "receptor protein" — one of up to
  `MAX_RECEPTORS_PER_ORG = 16` DNA-encoded plasticity profiles
  `(A_PLUS, A_MINUS, TAU_P, TAU_M, V_REST, V_RESET, TAU_DEFAULT, SPIKE_RATE_MAX)`.
- **`NEURON_MARKER = 162`** (5 bytes): a hidden neuron, expressing a receptor id, a
  threshold and a leak time-constant.
- **`GENE_MARKER = 161`** (4 bytes): a synapse `(src, dst, weight)`; `weight` maps a raw
  byte to `float(w) − 128` (i.e. −128..+127).
- **`SENSOR_MARKER = 196`** (5 bytes, `GENESIS_EVOSENSE`, default-OFF — Exp 37): an **evolvable
  sensor** — a hidden-band neuron whose firing is driven by a real hardware **affordance**
  `(aff_type, signed offset, param)` sampled at `pos+offset` (RAM byte / a single RAM bit /
  cell occupancy / neighbour energy / neighbour vocal bit / own energy), not by LIF integration.
  So the organism can **grow its own senses** coupled only to quantities the substrate physically
  exposes (Rule 15), rather than a designer-fixed input layer. It is an ordinary synapse *source*,
  so the reward/plasticity machinery is untouched; each affordance sample costs one honest cycle
  (Rule 17). When off, dead-code-eliminated → byte-identical.
- **`ACTUATOR_MARKER = 197`** (5 bytes, `GENESIS_EVOACT`, default-OFF — Exp 38): an **evolvable
  effector** — an ordinary LIF hidden-band neuron that, when it fires, *also* drives a physical
  action `(act_idx)` by adding its spike into `out_accum[act_idx]`, the same accumulator the innate
  output neuron for that action uses. So the organism can **grow its own effectors** (a new evolved
  *route* to an action, not a replacement of the fixed outputs), widening the behavioural-expression
  channel Exp 21 named as the cognition ceiling. The fixed output neurons the reward/STDP/REMAP
  machinery reads are untouched (verified: `STDP_TARGET` recruitment intact under EVOACT). When off,
  dead-code-eliminated → byte-identical. *(Exp 38 finding: the mechanism is sound, but a new effector
  is retained only under an economy that rewards behavioural diversity — the single-reward books
  economy prunes it; see `Ascent.md` §5.)*

Every organism has an innate fixed I/O layer of **`N_INPUT = 25`** sensory + **`N_OUTPUT = 14`**
motor neurons (`N_IO = 39`) plus a variable number of hidden/sensor neurons. *(This fixed I/O is the
Rule-5 baseline and the last major un-dissolved abstraction; Exp 37 Phase A0 adds evolvable sensors
alongside it, with Phases B/C — evolvable actuators, then dissolving the fixed input block so
`N_INPUT/N_OUTPUT` stop being constants — pre-registered in Roadmap P4.)*

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
  **Brain Analyzer** that decompiles the Elite genome's synapses (neuron roles derived live from
  `N_INPUT`/`N_IO`, and evolvable sensor/actuator neurons labelled `S<aff>`/`A<act>` when those modes
  are on — Exp 37/38), an **Oracle Terminal** to broadcast ASCII into the universe, and a **Library of
  Genesis** curriculum injector.
- **Live Cognition panel + feature-flag bar (2026-07-18).** The dashboard surfaces the engine's live
  cognitive metrics — reading solve-rate (`reads`/`miss`), next-symbol `pred`, autotelic `peer`, and
  the evolvable-I/O counts (`sensors`/`actuators`) — not just population, so the mind signals are
  watchable, not reconstructed from logs. A flag bar shows which engine modes are running
  (PEER / EVO-SENSE / EVO-ACT / REMAP), and the Library is labelled a **survival scaffold** (Ascent.md
  §5). An **Auto-inject toggle** lets the user enable/disable the automatic library restock live
  (`set_auto_inject` over the WebSocket → the `g_auto_inject` gate on the sim_loop restock); the manual
  inject button is unaffected. The WebSocket `state` payload carries a `metrics` and `flags` block so
  the UI stays honest with whatever engine configuration is live.

## 2. Core Mechanisms
### 2.1 Thermodynamics = CPU Cycles
Energy is execution cycles, drained per action from each organism's reserve
(`ATP_MAX = RAM_SIZE × CELL_STATES` ceiling — the total matter-energy the universe holds, i.e. the honest
physical bound on the cycles one organism can bank; a Rule-17 derivation of the former arbitrary `1e6`, Exp 36
2026-07-18). Costs are **honest raw-cycle counts** — one executed
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

**Supply-vs-demand settled — the ceiling is behavioral collapse to the single monetized action (Exp 22,
2026-07-14).** `GENESIS_ACTPROBE` (compile-time, observation-only, default-OFF, kernel byte-identical when
off) records `best_a` on the peer-OFF path and prints the full 6-way action histogram. Live measurement to
equilibrium refutes the "skewed-but-diverse" reading of Exp 19: each economy pays for exactly one behavior
and the colony **collapses onto it** — the reading economy converges to an `eat`-monoculture (73–86 %,
`Hact ≈ 0.8–1.2`), and the peer run before ignition converges to a `fwd`-monoculture (88–95 %,
`Hact ≈ 0.35–0.6`). The early `Hact ≈ 2.2` is founder-cohort diversity *decaying*, so the equilibrium the
peer economy must model is even lower than the Exp 19/21 time-average of ~1.8. Two of six actions (`f10`,
`b10` = jump ±10) are structurally dead throughout, so the effective repertoire is ~4 and at steady state
~1. **This is decisive for the substrate fork: the ceiling is *demand*-limited, not supply-limited** — the
distribution is dictated by what pays, not by how many action bits exist, so widening `N_OUTPUT` would add
capacity a single-reward economy has no reason to use. The lever is an economy in which *different behaviors
pay off for different organisms* (niche structure / division of labour), which re-ranks the Exp 21 fork
toward **(b) a structured/stigmergic environment** over **(a) action-space widening**. `GENESIS_ACTPROBE` is
retained as the honest per-action instrument; the default economy (probe off) is byte-identical and was
re-verified with no regression.

**A second energy niche lifts action entropy, but a passive lattice does not recruit the targeted gait
(Exp 23, 2026-07-14, partial).** `GENESIS_NICHE` (default-OFF, pure driver change, no new constant) stocks
ambient food only on a stride-`LONG_JUMP_STRIDE` lattice, where the stride derives from the jump-10 actuator
distance (the literal `10` was named into `LONG_JUMP_STRIDE` so the niche and the actuator share one number).
The demand prediction holds *in direction*: at matched food rate the lattice sustains a two-mode locomotion
equilibrium (`fwd`+`bck`, `Hact ≈ 1.7`) where uniform food of the same magnitude collapses to a single-action
`bck`-monoculture (`Hact ≈ 1.1`) — the first intervention in the arc that *raises* equilibrium action
entropy. But it did **not** recruit the intended jump gait (`f10`/`b10` stayed ~0–9 %): a passive stride-10
lattice is walk-reachable, so `+1`/`−1` drift still lands on lattice cells and no long jump is *required* —
"option ≠ pressure", the Exp-20 failure recast on the foraging axis. The architectural lesson: spatial-demand
structure genuinely moves `Hact`, but (i) forcing a *specific* action needs the alternative gaits to *fail*
(a true energy barrier only a long jump crosses, not a spacing preference), and (ii) even a perfect two-niche
split yields only a 1-bit reader-vs-forager label to a peer predictor — generic action diversity is still not
*modelable behavioral depth*. This keeps **(b) a stigmergic environment** (diversity in open-ended built
artifacts, not a fixed gait menu) as the favoured substrate lever, with Exp 23 as evidence that spatial
structure is a real handle on the distribution. `GENESIS_NICHE` and `GENESIS_FOOD_RATE` are kept as
instruments; the default economy is byte-identical and was re-verified with no regression.

**Stigmergy design space names two walls; bounding reading income breaks Wall 1 (Exp 24, 2026-07-14).** An
adversarial workflow vetted five stigmergy economies against all prior lessons; all five were fatal, but they
converged on two structural walls. **Wall 1:** reading income is *minted* on a non-destructive infinite
scroll, so any authored, royalty-charging cell is strictly dominated by the free book — builders earn nothing
and building is selected out (lessons 13/22). **Wall 2:** the single vocal byte is confounded with the shared
text (peer-adjacency = reading-adjacency, so a neighbour's "authored" byte is readable from the predictor's
own eye) and cannot simultaneously serve reading-prediction and an independent register (lessons 15/17/21);
moreover a flat royalty is maximised by predictability, not depth, so the economy selects against complexity
(18/20). Wall 1 was then attacked directly as a physics change: `GENESIS_DEPLETE` (default-OFF, no new
constant, byte-identical when off) makes reading draw from a finite per-cell fuel reservoir (`read_fuel`,
cap = `CELL_STATES`) instead of minting, with the driver regrowing `GENESIS_DEPLETE_REGROW` per iteration.
Live, at a mid regrow rate (~`CELL_STATES/2`) a **carrying capacity forms for the first time in the project**
— population oscillates 400–598 rather than pinning at the 600 cap, action entropy rises to the highest
sustained level measured (`Hact ≈ 1.2–2.5` vs ~0.8 for the minted eat-monoculture), and the colony sustains
100k+ ticks without extinction; tighter bounds cold-cliff (the founder bootstrap needs near-full income, the
Exp-20 bootstrap-vs-scarcity tension on the energy axis). So the infinite-uncontested-resource wall is not a
property of the substrate but a consequence of *minting*, and it is breakable. This is the missing
precondition for the stigmergy class — with reading no longer an infinite free substitute, an authored
economy is no longer dominated — so the next build is a stigmergy economy layered on bounded reading, using
the vetting's escape recipe (destructive/rivalrous built cells, an authored value decoupled from the reading
eye, and depth that pays more per cell rather than a flat royalty). `GENESIS_DEPLETE` and
`GENESIS_DEPLETE_REGROW` are kept as instruments; the default economy is byte-identical and was re-verified
with no regression.

**Stigmergy built — first persistent agent-authored substrate structure (Exp 25, 2026-07-14).**
`GENESIS_STIGMERGY` (default-OFF, requires `DEPLETE`, byte-identical when off) overloads `OUT_CONSUME`
(keeping `N_OUTPUT=6`, no genome-decode risk): choosing CONSUME on a writable cell with a printable emission
authors the vocal byte there and claims ownership (`cell_owner`), and reading an owned cell pays the author a
per-bit royalty (zero-sum, non-lethal). The build revealed a *location* constraint: authoring only into
vacuum failed outright (`authored=0`) because survival keeps every organism on the readable scroll, so no one
ever stands on vacuum — build and read sites were spatially disjoint. Co-locating them (authoring a
*depleted* scroll cell — printable but out of fuel, exactly where readers are and where income has stopped)
made authoring emerge and persist: ~270–278 owned cells held by ~150 authors at full population, the first
persistent agent-written structure in the substrate. It remains shallow (broad thin dabbling, not a
specialist builder niche), does not raise brain size or action entropy, and needs a seeded write reflex to
bootstrap. The diagnosis is that the royalty is too *flat*: a thin per-bit slice makes authoring a marginal
side-income rather than a livable niche, so the Exp-24 recipe's third leg — rent that scales *super-linearly*
with authored difficulty, plus a text-*independent* authored value (the deeper half of Wall 2) — is the next
lever. `GENESIS_STIGMERGY` and `GENESIS_STIG_SEED` are kept as instruments; the default economy is
byte-identical and was re-verified with no regression.

**Super-linear rent lifts diversity but a specialist needs territory persistence (Exp 26, 2026-07-14).** The
authorship royalty was made to scale super-linearly with a cell's cumulative read-traffic (a per-cell
`read_hits` counter, reset on authoring; fraction = `min(hits, BITS_PER_BYTE-1)/BITS_PER_BYTE` of the
reader's gain — constant-free, zero-sum, non-lethal). This corrected the Exp-25 flatness in the intended
direction: action entropy stayed elevated (`Hact ≈ 2.0–2.45`, the pure-depletion level, versus ~1.3 under
flat rent) and heavily-read hotspots emerged (`toptraf` 894 → 9 879). But no specialist formed — the maximum
holding any author accumulated (`tophold`) never exceeded ~6 cells while the author count kept rising, i.e.
broad dabbling persisted. The cause is structural: super-linear rent rewards *holding* high-traffic
territory, but nothing lets an author *hold* it — any organism can re-author a depleted cell and seize
ownership, so cells churn and income cannot concentrate; late in the run the churn actively destabilises the
colony (entropy and population decay). Rent depth is therefore necessary but insufficient without a **property
right**: the next lever is ownership persistence (re-authoring an owned, still-fuelled cell must cost more
than claiming vacuum, or an owner's cheap refresh must keep held cells live) so a builder can defend a patch,
income concentrates, and a stable division of labour can lift capability (Rule-22 logic). `read_hits` and the
`tophold`/`toptraf` probes are observation-only instruments; the default economy is byte-identical and was
re-verified with no regression.

**Absolute ownership persistence freezes the map — ownership needs a decay gradient (Exp 27, 2026-07-14).**
Adding a binary property right (`GENESIS_STIG_PERSIST`: a living owner's cell is unseizable; the owner alone
may refresh it; owner death releases it) did not produce a specialist — it produced an economic *freeze*.
Over ~418 k ticks the authored map locked at exactly 112 cells held by 91 authors and never changed again,
peak per-cell traffic climbed without bound (>100 k reads on a handful of founder cells that became permanent
toll-booths), and action entropy collapsed monotonically from ~2.0 to ~0.1 as the colony funnelled onto
reading-through-owned-cells. The maximum holding per author stayed at ~4: the freeze locked in before
selection could sort winners, so ownership concentrated on *cells* (traffic) but never on *authors*
(holdings). This is the opposite failure from the Exp-26 churn and worse for capability. The architectural
lesson is that a property right must obey the Tectonic Gradient Principle (Rule 10) like every other hazard:
ownership must **decay** — an owner must keep paying to hold territory and an unrefreshed claim must weaken
until it is contestable — so that claims are persistent enough for a better builder to hold and out-earn, yet
impermanent enough never to ossify into a founder cartel. Neither the churn extreme (no persistence) nor the
freeze extreme (absolute persistence) works; the next lever is a decaying/leaky ownership claim.
`GENESIS_STIG_PERSIST` is kept as the frozen A/B extreme (default-OFF); the default economy is byte-identical
and was re-verified with no regression.

**Leaky ownership destabilises the colony — the decay gradient collides with the reading substrate (Exp 28,
2026-07-14).** Building the decay gradient (`GENESIS_STIG_LEASE`: owned cells lose the full free fuel-regrow,
so an owner must pay `CELL_STATES` to refresh and hold, and a neglected claim lapses) cold-cliffed the colony
(`pop → 12`) in both a binary form (owned cells get zero regrow) and a partial form (owned cells regrow at
`1/BITS_PER_BYTE` of the free rate), with and without the seeded write reflex. The cause is a structural
coupling the stigmergy line has carried since Exp 25b: authoring reuses *depleted scroll cells*, so an
authored cell **is** a reading cell — putting a holding-cost on owned cells therefore puts a holding-cost on
the shared reading substrate, and orgs that author scroll cells convert live reading territory into
slow-refuelling owned cells that drain, lapse, and churn the scroll into a low-fuel state, collapsing the
reading (survival) economy. The seeded write reflex compounds it by bankrupting the founder cohort. The
architectural conclusion is that the ownership-persistence axis cannot be tuned in isolation while authoring
and reading share the same cells: the open half of Wall 2 — a *text-independent authored territory* (a region
or value channel distinct from the reading scroll) — must be closed first, so that ownership upkeep, lapse,
and rent act on an authored resource without draining reading fuel. `GENESIS_STIG_LEASE` is kept as the
destabilising A/B extreme (default-OFF); the default economy is byte-identical and was re-verified with no
regression.

**Substrate decoupling built — the fuel coupling breaks and migration works, but a new energy-currency
coupling bankrupts the colony (Exp 29, 2026-07-14).** After adversarial vetting of five decoupling designs, the
surviving synthesis `GENESIS_CANVAS` (default-OFF, requires DEPLETE+STIGMERGY, no new constant, `N_OUTPUT`=6
kept) places a **canvas band** of one scroll-width immediately after the reading scroll (bounds derived from
`LIB_START + BOOK_TARGET_BYTES`), with authoring **index-confined** to it so a scroll cell can never be owned —
ownership upkeep and lapse therefore cannot touch survival fuel, making the Exp-28 cannibalisation structurally
impossible. The band abuts the scroll (a forward-saccading reader walks onto it) and rent is surprise-gated so
echo/constant-run content earns the builder nothing. Two first-time positive results: the **fuel decoupling
holds** (reading fuel is never drained), and **reader migration succeeds** (`oncanvas` climbs 40→168→596 —
readers colonise the authored territory en masse, defeating the Exp-25b barrenness that blocked every prior
stigmergy build). But the colony still collapses (`pop→12`) through exactly the failure the vetting panel
predicted: **the fuel pools are decoupled but energy is a single shared currency.** Once migration succeeds,
hundreds of organisms author simultaneously at `CELL_STATES` per cell (`authored→5910`, nearly the whole band),
draining collective energy faster than royalty returns it → mass starvation. Authoring is thus a
tragedy-of-the-commons in the shared energy pool: individually rational, collectively bankrupting when
synchronous. The spatial decoupling is necessary and now proven achievable, but insufficient alone — the next
lever is a **throttle on the collective rate of energy→territory conversion** (an author cost that scales with
canvas already owned, a scarcer prerequisite than raw energy, or a slower migration pull), so that authoring
remains profitable for a specialist minority (the division of labour) without becoming a synchronous colony-wide
drain. `GENESIS_CANVAS`/`GENESIS_CANVAS_SEED` are kept as instruments (default-OFF); the default economy is
byte-identical and was re-verified with no regression.

**The design loop is closed and the load-bearing assumption fails: in-lifetime STDP is net-negative (Exp 30,
2026-07-16).** The 17-lever economy search (Exp 13–29) never validated the assumption underneath it — that a
GENESIS brain learns within its lifetime. Under the strategic pivot (Rule 18 / `Docs/Ascent.md`), a
compile-time learning-ablation control (`GENESIS_NOLEARN`, deletes STDP Phase 3, byte-identical when off) was
A/B'd against the learning-on default. Ablating learning is strictly better: population stays flat at ~599
instead of decaying to ~423, the brain holds ~25.8k neurons/synapses instead of shedding 34 % to ~17.4k, and
reading solve-rate roughly doubles (~23 %→~51 %). The long-standing "sustains but decays" pattern is therefore
causally attributed to STDP driving the DNA-decoded (already-good) weights toward noise — plasticity as ruled
here is destructive, not constructive. This falsifies the current *learning rule*, not yet the substrate: the
repairable candidates are wrong-sign/wrong-target plasticity, unamortised STDP metabolic cost, and a task
(next-symbol prediction) that a fixed reflex already solves so a changing weight only adds variance. The
mandated next step is diagnostic (isolate cost from weight-effect; test on a within-lifetime-changing task
where only a real learner can win), not another economy mechanic. Until a plasticity rule is shown to help,
the engine is treated as reflex-evolution-only. `GENESIS_NOLEARN` is retained as a permanent A/B instrument;
the default (learning-on) path is unchanged.

**STDP diagnosed and first repair partially works — the problem is credit assignment (Exp 31–32, 2026-07-16).**
Diagnostic ablations (`GENESIS_STDP_COSTONLY`, `GENESIS_STDP_DIV`) established that the STDP sign is correct
(Hebbian) and that net-negativity has three causes: a bang-bang step (~12 % of the weight range per event) that
slams good decoded weights to the rail (fixed by small steps), an unamortised metabolic cost that can starve the
bootstrap, and — the root — the fact that plain STDP is *unsupervised* and cannot tell a correct prediction from
a wrong one, so it drifts good weights toward task-irrelevant coincidences. The indicated fix, three-factor
neuromodulated plasticity (`GENESIS_STDP3`: scale the weight update by the organism's own reading reward, a
Rule-9 autotelic and biologically faithful signal), was built and, with small steps, became **the first learning
rule to beat the no-learning baseline** — reading comprehension reached ~78 % vs ~51 % for ablation early in the
run, demonstrating that constructive in-lifetime learning is achievable on this substrate (the kill-criterion
remains un-triggered). It does not yet hold, decaying to ~29 %, because the neuromodulator gates the *timing* of
plasticity but not its *direction*: a reward magnitude is not an error signal, so full-gain learning still
reinforces every coincident synapse regardless of which ones caused the correct output. The well-posed next step
is a credit-assigning third factor (reward-modulated eligibility that potentiates synapses onto neurons driving
the *correct* vocal bits and depresses those driving wrong bits) — a true reward-modulated STDP. All diagnostic
and repair flags are retained as instruments; the default path is byte-identical.

**Credit-assigning STDP holds above ablation, then the remap test exposes its limit — STDP prunes but cannot
RECRUIT (Exp 33–34, 2026-07-17/18).** Exp 33 built the credit-assigning third factor (`GENESIS_STDP3C`: a
per-vocal-bit signed eligibility trace, +1/−1/0 from the read's own per-bit correctness, multiplying each
Phase-3 vocal-bit update) and it became the first learning rule to **durably beat ablation** (steady solve-rate
60 % vs NOLEARN 51 % over 400 k ticks, no shedding, no pop decay). But that task — next-symbol prediction — is
one a *fixed reflex also solves, so it does not prove the substrate can LEARN a genuinely new mapping. Exp 34
built the affirmative test (`Ascent.md` §4 step 2, never built before): `GENESIS_REMAP` (default-OFF,
compile-time gated, byte-identical off) makes the reading-reward target **swap two vocal bits** on a wall-clock
phase that is on **no sensory input**, so a fixed genome cannot pre-encode it and only in-lifetime plasticity
can track it. Measured in a survival-decoupled sandbox (`tests/remap_sandbox_probe.py`, driving the real kernel
with a frozen, energy-pinned cohort so *only weights change*), the result is a **decisive negative**: in swapped
phases the learner's swap-bit accuracy is **~40 %, flat, with no within-phase recovery and no cumulative gain
across phase-cycles — indistinguishable from the NOLEARN ~42 %**, while the unchanged bits hold 99 % (the cohort
is healthy; only the bits that require *learning* fail). The mechanism is exactly the pre-registered prediction:
STDP (even credit-assigned) updates a synapse only on a **post-synaptic spike**, so it can LTD-*prune* a
wrong-firing pathway but cannot **recruit** a silent-but-wanted neuron (no spike → no eligibility → no gradient).
Exp 33's win is therefore real but **narrow — it tunes/prunes an already-firing reflex, it does not construct a
new input→output mapping** (the difference between tuning a circuit and building one; building is what reasoning,
Rule 6, requires). This does **not** trigger the kill-criterion; it localises the defect — **the rule carries a
REWARD signal, not an ERROR signal** — and fixes the next step as a *substrate change to the plasticity rule*
(a target/teaching current that depolarises wanted-silent vocal neurons so their afferents become LTP-eligible),
not another economy lever. `GENESIS_REMAP` and the sandbox probe are retained as permanent instruments; the
default path is byte-identical (re-verified). Full account: `Docs/Ascent.md` §4f, `Result.md` Exp 34.

**The teaching signal repairs it — the substrate CONSTRUCTS a new mapping in-lifetime (Exp 35, 2026-07-18).**
The pre-registered fix was built: `GENESIS_STDP_TARGET` (default-OFF, compile-time gated, byte-identical off), a
local **delta rule** on the reading-eye→vocal-bit synapses applied on a rewarded read — for each vocal bit b,
`err_b = target_b − output_b`, and each synapse from an *active* eye input onto vocal neuron b is nudged by
`err_b`. `err_b=+1` (a *wanted-but-silent* neuron) **potentiates that neuron's active eye afferents with no
post-synaptic spike required** — the recruitment gradient credit-assigned STDP structurally cannot supply — while
`err_b=−1` depresses a fired-but-unwanted route. This is the local, biologically-plausible teaching/error current
of dendritic-error / predictive-coding SNNs (a "should-fire" signal to the apical dendrite), not backprop; it is
autotelic (target = the org's own read target, Rule 9) and constant-free (reuses `STDP_DIV`/`CELL_STATES`, Rule
17). In the same sandbox the result is decisive: `STDP_TARGET` **re-tracks the swap 56 % → ~99 % within ~2000
ticks at every phase flip** (the recovery curve absent under STDP3C), re-learning faster each cycle, with the
unchanged bits held at 99 %, while NOLEARN and STDP3C stay flat ~40 %. This is the **first in-lifetime
construction of a new input→output mapping** in the project — the substrate can *build* a pathway, not only tune
or prune an already-firing one — the affirmative form of criterion B on a reflex-proof task, and the first
concrete evidence the substrate can support the circuit-*construction* that reasoning (Rule 6) requires. Honest
scope: proven in the isolated sandbox (frozen, energy-pinned cohort on the seeded 2-bit cross-fabric); its value
on the **live** economy over deep time, and its generalisation to *evolved* topology, are the pre-registered next
tests. `GENESIS_STDP_TARGET` is retained as a permanent instrument; the default path is byte-identical
(re-verified). Full account: `Docs/Ascent.md` §4g, `Result.md` Exp 35.

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

**Full-curriculum injection + UI-inject consistency (2026-07-18).** Two fixes to the survival scaffold
(Ascent §5 — Books is now a *survival scaffold*, not the mind path). (1) The dashboard "Inject" button
formerly called `inject_curriculum_file`, which SCATTERS word fragments as confetti — the exact
net-negative layout Exp 11 retired — contradicting the live economy. It now lays the selected book as one
**contiguous scroll** (`inject_contiguous_library`), matching the engine. (2) A new
`inject_curriculum_sequence` (books_of_genesis.py) lays the **whole ordered curriculum ladder**
(`DEFAULT_CURRICULUM`: `00_Graded` → `00_Ascent` → `Math/01_Digits` → `Math/02_Addition` →
`02_Basic_Words` → `03_Phrases`) concatenated into a single contiguous scroll, **bootstrap-head-first** so
a cold colony still ignites (the tiling recurs from the FULL stream, keeping the `00_Graded` runs foothold
dense — never tiling only the hard tail, the Exp-20 cliff). Gated by `GENESIS_CURRICULUM` / the live
`g_curriculum` toggle (dashboard "Full curriculum" checkbox + "Inject Full Curriculum" button); default OFF
lays the single `BOOK_NAME` scroll exactly as before (byte-identical, pure driver change, no kernel/cache
impact). **Live-verified:** the full curriculum **cold-ignites cleanly** (t≈7k: pop=597, reads=175,
`refuge=0` — no floor-riding) and **sustains** (pop=599–600, ext=0) — the key risk (a hard-tail-dominated
scroll cliffing the colony) is avoided by the bootstrap-first order. Steady solve-rate is lower than the
single-book baseline (~24 vs ~137 reads/window) because the colony now spreads across the repeat-free hard
tail (arithmetic/phrases) it cannot yet solve — the honest expected state (Exp 20: minds camp the easy band
until the learning machinery can climb), not a regression: the scaffold keeps the colony alive *and*
presents the whole difficulty gradient for when construction-capable learning (Exp 35) can climb it.

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
