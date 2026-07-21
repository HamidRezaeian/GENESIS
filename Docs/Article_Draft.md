# GENESIS: A Genome-Encoded Spiking-Neural-Network Substrate for Open-Ended Evolution on Raw Hardware Physics

**Abstract**
We present GENESIS (General Evolutionary Neuromorphic Environment for Simulating Intelligent
Systems), a digital universe in which populations of genome-encoded Spiking Neural Networks
(SNNs) evolve under strictly thermodynamic constraints on a literal 1-D RAM substrate.
Rejecting both the brute-force artificial-neural-network paradigm and abstract "video-game"
ecologies, GENESIS maps every environmental quantity onto a raw hardware reality: space is a
65,536-byte toroidal memory ring, energy is CPU execution cycles, food is a memory byte,
and computational hazard is synaptic-density drag. Each organism is a byte-string genome
decoded into a sparse Leaky-Integrate-and-Fire network with Spike-Timing-Dependent
Plasticity (STDP), whose learning constants — including per-receptor resting potentials —
are themselves DNA-encoded and therefore subject to meta-evolution. We describe the engine's
architecture and physics, and characterise its behaviour: on a single CPU (Numba JIT) it
sustains a high world-tick rate while holding a population in bounded, boom-and-bust dynamics.
Toward the project's Prime Directive — a ~20 W, brain-like efficiency target — we make
efficiency a *selected* rather than merely *measured* property: by charging every neural
operation its honest CPU-cycle cost (removing a legacy discount that made brain size ~10× too
cheap to matter), a leaner brain retains more energy and out-reproduces a costlier one, with
no top-down fitness function. A controlled A/B shows this makes the same food supply sustain
~3× less neural tissue and pushes organisms to the metabolic margin where efficiency decides
survival. We further introduce two heredity mechanisms: **Lamarckian consolidation**, blending
each organism's STDP-learned weights into its offspring's genome so plasticity is partially
heritable, and a **fossil pool with horizontal gene transfer**, which recovers extinct
universes by recombining preserved elite genomes rather than cloning one. We are explicit that emergent cognition — unsupervised
language, logic, and long-horizon reasoning — remains a **goal, not a demonstrated result**;
this paper reports the substrate and its verified mechanisms, and frames the open problems.

---

## 1. Introduction
Artificial General Intelligence research is dominated by two paradigms that both diverge from
biology: massive artificial neural networks that consume kilowatts, and von-Neumann
sequential search. The human brain instead achieves general intelligence with massive, slow,
sparse parallelism at ~20 W. Separately, artificial-life systems (Tierra, Avida) tend to
collapse into the "Replication Trap," where an environment that rewards only copying speed
breeds efficient replicators, not cognition.

GENESIS is an attempt to build a substrate whose *physics* make sparse, efficient neural
computation a thermodynamic necessity for survival, and to let intelligence — if it emerges —
do so from the bottom up. The project passed through three superseded substrates (a
predictive graph model, a 1-D self-replicating opcode soup, and a 2-D grid SNN); this paper
concerns the current and, we argue, most principled substrate: a **genome-encoded SNN on a
literal 1-D RAM ring**, in which no environmental quantity is an abstraction.

---

## 2. Methodology: System Architecture
The engine comprises a Numba-`@njit` SNN core (`neuromorphic_engine.py`) and a state/loop/
server module (`genesis_lab.py`), with a vanilla-JS dashboard over WebSocket (:8085).

### 2.1 The Substrate
- **Space = RAM.** A toroidal `uint8` array of `RAM_SIZE = 65,536` bytes. An organism's
  position is a byte address; motor actions are pointer jumps of ±1 or ±10 (mod `RAM_SIZE`).
- **Food = memory.** The byte `0x55`, seeded into empty cells; consuming one reclaims the cell for
  `CELL_STATES = 2⁸ = 256` cycles — the same derived matter↔energy rate a fully-solved book symbol
  pays (an 8-bit cell's microstate capacity). There is no separate meal constant: food and text share
  one currency, and reading out-earns grazing only by chaining predictions across dense text, not by a
  multiplier.
- **Reading = a saccade over intact text.** Unlike food, a book symbol is *not* consumed by being
  read. A successful decode advances the reading head one cell forward, so an organism **walks a
  passage symbol-to-symbol** — a moving eye. That motion is its own anti-farm (to re-read a cell an
  organism must circle the entire 65,536-byte ring, never worth it), so the text can stay intact: a
  book is not destroyed by reading it, and many readers can pass over the same passage. This makes the
  encounter economy scale with text density rather than hitting a structural cap, and lets a
  next-symbol *prediction* skill emerge from organisms reading forward along a line.
- **Global heap.** Neurons, synapses and genomes for the whole universe occupy flat global
  arrays (capacities 5×10⁵ neurons, 2×10⁶ synapses, 5×10⁶ genome bytes); each organism
  `malloc`s contiguous blocks. Fragmentation is itself a spatial hazard.

### 2.2 Organisms as Genome-Encoded SNNs
A genome is parsed into three record types: `RECEPTOR_MARKER (195)` — a 10-byte plasticity
"protein" (up to 16 per organism); `NEURON_MARKER (162)` — a hidden neuron; and
`GENE_MARKER (161)` — a synapse `(src, dst, weight∈[−128,127])`. Every organism has a fixed
I/O layer of **15 sensory and 14 motor neurons** plus a variable hidden population. Sensors
encode energy, a bias, local crowding, the RAM byte under the pointer, three
neighbour-voice channels and the 8-bit Oracle broadcast; motors encode four pointer-jumps,
consume, reproduce and eight vocal-cord bits.

### 2.3 Neuron, Synapse and Plasticity Model
Neurons follow Leaky-Integrate-and-Fire dynamics (`v += (V_REST − v)/τ`; fire at threshold;
reset to `V_RESET`; refractory `TAU_REF = 1`). Input neurons fire stochastically in
proportion to their sensed value. Synapses adapt by STDP: pre-before-post potentiates,
post-before-pre depresses, with per-receptor amplitudes and time-constants. Two design
choices enforce biological and evolutionary fidelity:
- **Evolvable neuro-physics (meta-learning).** STDP amplitudes/time-constants, thresholds,
  spike-rate ceiling and — as of this revision — **resting and reset potentials** are all
  DNA-encoded per receptor. Organisms therefore evolve the equations of their own learning,
  not merely their topology. There are no global learning constants.
- **Graded plasticity.** Raw receptor amplitudes (0–255) are scaled (`STDP_SCALE = 8`) so a
  single spike changes a weight by ≤ ~12% of its range, preventing the bang-bang saturation
  that a raw additive rule produces against a 256-wide weight range.

### 2.4 Thermodynamics
Energy is CPU cycles, drawn per action from a reserve capped at `ATP_MAX = 10⁶`, and every
cost is an **honest raw-cycle count** — one executed operation debits one cycle, with no
arbitrary discounts: synapse transmission 1, **neuron membrane update 1 × n_spiked per
step** (event-driven — charged per action potential fired, not per neuron present: on a 20 W
substrate the spike is the energy event and an idle neuron draws ~nothing), **STDP weight
update 1** (activity-gated — charged only when a synapse actually potentiates or depresses),
movement 3, and a viscosity stall costs `n_neurons`. Reproduction
costs `genome_length` cycles to copy the genome, then splits the remaining energy in half
with the child; an organism dies at energy ≤ 0.
- **Emergent efficiency selection (Rule 7).** Because neural work is billed at its true rate,
  a leaner brain retains more energy and out-reproduces a costlier one — efficiency is
  selected *thermodynamically*, never by a fitness metric. A prior revision discounted the
  neuron update to `0.1×`, which (we show in §3.3) made brain size ~10× too cheap to be
  selected. The activity-gated form is deliberate: it prices *spiking and plasticity*, not
  the mere *possession* of synapses, so the substrate rewards the 20 W regime of many
  synapses firing sparsely rather than degenerate minimal brains.
- **Conservation of compute.** The per-tick LIF-step budget is global: `steps = 3000 /
  population`. Mass replication dilutes everyone's compute, coupling population to a fixed
  energy budget (bounded, boom-bust dynamics).
- **Computational viscosity (the 20 W pressure).** Stall probability rises with an
  organism's *synaptic density* (synapses/neuron, capped at 0.5), penalising dense genomes
  and rewarding sparse, parallel topologies.
- **Cosmic radiation.** Two bit-flips per tick are applied *inside living genomes* (germline
  mutation), providing heritable entropy that error-correction must out-run.

### 2.5 Heredity, Memory and Recovery
- **Mutation.** Insertion/deletion/gene-duplication (5% each) or point mutation at rate
  `1/genome_length`; the base receptor header (bytes 0–1) is protected so a single flip
  cannot delete a lineage's entire plasticity machinery.
- **Lamarckian consolidation (generational memory).** At reproduction, each synapse's
  inherited DNA weight is blended 50/50 with the weight the parent learned via STDP, so
  plasticity is partially heritable rather than reset each generation.
- **Elite Ark + fossils.** The longest-lived genome is checkpointed; a pool of up to 12
  distinct elite fossils is retained, and on total extinction the universe reseeds by
  crossover (horizontal gene transfer) between two fossils plus mutation.

---

## 3. Results (Engine Characterisation)
All figures are from `tests/smoke_test.py` on a single CPU (Numba 0.61.2 / NumPy 1.26.4).

### 3.1 Throughput and Stability
Seeding 60 Intelligent Ancestors and running 500 world-ticks: the engine sustained
**~773 world-ticks/s** (each tick simulating the whole population's LIF + STDP dynamics),
holding the population in a **bounded oscillation (min 61, max 382, mean ≈ 208) with no
extinction**, at a steady-state footprint of ~6,800 neurons and ~1,960 synapses. The global
cycle pool is the stabilising feedback: rising population lowers per-capita compute and
average energy, throttling reproduction.

### 3.2 Verified Mechanisms
Genome→SNN decoding, evolvable receptor chemistry (now including resting/reset potentials),
graded STDP, synaptic-density viscosity, live-genome radiation, Lamarckian consolidation
(runs on every birth; population remained stable with richer boom-bust dynamics), and the
fossil-pool crossover reseed (fossils accumulate; crossover preserves the protected header;
reseed repopulates) were each verified to be live and correct. See `Result.md` for the
per-mechanism verification.

### 3.3 Efficiency Selection is Emergent, Not Cosmetic
To test whether the physics *select* for the ~20 W paradigm rather than merely *measure* it,
we ran a controlled A/B (Numba 0.66.0 / NumPy 2.4.6) at identical, deliberately food-scarce
settings (respawn rate 0.02, seed 300, 2500 world-ticks), varying only the neuron-update
cost. Under the prior `0.1×` discount the ecosystem coasted on its seed-energy buffer,
sustaining ~20,000 neurons at a near-cap population (~514–592) with abundant energy
(20k–32k). Under honest `1.0×` cost the *same* food supply sustained **~3× less neural
tissue (~6,500 neurons)** and held organisms at the death margin (~3k–5k energy, population
~170–205), with four extinction→Ark-recovery cycles. Thus a leaner brain confers a decisive,
purely thermodynamic reproductive advantage — Rule 7 efficiency is now a first-order
selective force emerging from energy accounting alone, with no top-down fitness term. The
honest engine also ran ~3× faster (fewer neurons plus once-per-tick sensory evaluation),
i.e. the substrate itself became cheaper to simulate. We stress a limit: this establishes a
strong, correctly-signed selection *gradient* on footprint; it does not yet establish
efficiency *at equal capability*, since capability remains unquantified.

### 3.4 Validating the Load-Bearing Assumption: In-Lifetime Learning That Holds Above Ablation
The project's load-bearing assumption (Rule 18; `Docs/Ascent.md`) is that a GENESIS organism's brain
**learns within its lifetime** — that two-factor Hebbian STDP, gated by phenotypic reward, measurably
improves comprehension over a non-learning control. A learning-ablation A/B (`GENESIS_NOLEARN` deletes the
plasticity phase compile-time, byte-identical default) first *falsified* the assumption on the naive rule:
ablating plasticity made the colony *more* stable, kept the brain *larger*, and *doubled* reading solve-rate
(599 flat / 25.8 k neurons / ~51 % vs 596→423 / shed 34 % / ~23 %) — in-lifetime STDP was net-NEGATIVE
(Exp 30). Diagnosis (Exp 31) separated three causes — bang-bang step size, metabolic overhead, and a ROOT
lack of supervision: unsupervised Hebbian coincidence-reinforcement drifts decode-good genetic weights
toward task-irrelevant correlations. A scalar reward-gated rule (three-factor, Exp 32: `GENESIS_STDP3`,
one-tick-eligibility dopamine × the organism's own reading reward) first beat ablation *early* (78 %) but
still drifted (599→251, N 26 267→10 611, solve 78 %→29 %): a reward *magnitude* gates *timing*, not
*direction* — it reinforced wrong-bit drivers as much as right ones. A **per-vocal-bit signed eligibility
trace** (Exp 33: `GENESIS_STDP3C`) assigns the credit direction: each of the 8 vocal bits is scored already
by the reading reward against the target byte, and that per-bit verdict (+1 correct / −1 wrong / 0 silent,
one-tick delayed) multiplies each plasticity update onto a vocal-bit neuron, so LTP consolidates only
correct-bit drivers and LTD reverses onto wrong-bit ones; motor/hidden destinations keep the scalar gate.

| rule | criterion-B A/B (books, 400 k LIF-ticks) | pop | `Universe N` | solve-rate |
|---|---|---|---|---|
| NOLEARN (ablation) | baseline | 599 flat | ~25 900 flat | ~51 % |
| naive STDP (Exp 30) | **fails hard** (ablation better) | 596→423 | shed −34 % | ~23 % |
| scalar-reward STDP (Exp 32) | beats early, drifts below | 599→251 | 26 267→10 611 | 78 %→29 % |
| **credit-assigning STDP (Exp 33)** | **holds above ablation** | 597–599 flat | ~26 050 flat | **72 %→60 %** |

Thus criterion B (learning load-bearing) is met for the first time and *sustained*: a credit-assigning
third factor is the first learning rule to measurably and durably beat not-learning on this substrate, with
no brain shedding and no population decay. A residual early-to-steady drift (72 %→60 %) remains, so
capability criterion A (a sustained ≥25 % rise in prediction-depth) is not yet met; the next target is to
make the *held* capability *rise* (credit-depth coupling or a within-lifetime-remap task), not to add an
economy lever — the search has pivoted from shaping the market to designing the learning rule.

---

## 4. Discussion
GENESIS demonstrates a **substrate**, not yet a mind. Its contribution is a physics engine in
which (a) every quantity is a hardware reality rather than an abstraction, (b) the learning
algorithm itself is an evolvable, DNA-encoded object, and (c) plasticity is both lifetime
(STDP) and partially heritable (Lamarckian consolidation), giving evolution a memory channel
across generations. The conservation-of-compute budget and synaptic-density viscosity are
concrete mechanisms intended to make the ~20 W, sparse-parallel regime the only survivable
one — the central hypothesis of the project.

## 4. Discussion
GENESIS demonstrates a **substrate**, not yet a general mind, but we have now validated its core learning mechanisms. In-lifetime learning is load-bearing: under a moving-optimum task (within-lifetime input-output remapping), credit-assigning plasticity (STDP3C) and error-teaching (STDP_TARGET) measurably recover performance while a plasticity-ablated control fails. Furthermore, in-lifetime learning coupled to external addressable registers (SCRATCH) successfully resolves working-memory tasks of depth N >= 2 under selection. By introducing a depth-rewarded live economy to offset the metabolic tax of recall sensors, we demonstrated a monotonic climb in delay-2 accuracy from 30.8% to 69.5% over 4,000 ticks, with the correct memory slots consolidating to full saturation (excitatory weight 127.00) while wrong slots are actively depressed/inhibited.

## 5. Future Work
1. **Grounded Action Evolution:** Couple this working-memory capability to evolvable effectors and sensors in a structured spatial environment where navigation and construction pay off, moving away from stationary text echoing.
2. **Prediction Markets / Gentle Peer Pred:** Establish a non-lethal peer-prediction coupling to drive the escalation of theory-of-mind and cooperative/adversarial communication.
3. **Real-time entropy:** re-decode or otherwise expose living phenotypes to radiation, so error-correction is selected in-lifetime, not only in the germline.
4. **Efficiency selection (Rule 7):** show that, at equal capability, lower CPU/RAM lineages win, using the newly-exposed efficiency metric.
