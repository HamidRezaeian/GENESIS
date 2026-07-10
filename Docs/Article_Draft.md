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
sustains ~773 world-ticks/s while holding a population in bounded, boom-and-bust dynamics
(mean ≈ 208 organisms, no extinction over 500 ticks). We further introduce two mechanisms
aimed at the project's Prime Directive — a ~20 W, brain-like efficiency target: (i)
**Lamarckian consolidation**, blending each organism's STDP-learned weights into its
offspring's genome so plasticity is partially heritable, and (ii) a **fossil pool with
horizontal gene transfer**, which recovers extinct universes by recombining preserved elite
genomes rather than cloning one. We are explicit that emergent cognition — unsupervised
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
- **Food = memory.** The byte `0x55`, seeded into empty cells; consuming one yields
  `CYCLES_PER_EAT_GAIN = 1024` cycles.
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
Energy is CPU cycles, drawn per action from a reserve capped at `ATP_MAX = 10⁶`: synapse
read 1, movement 3, per-step idle metabolism `0.1 × n_neurons`, and a viscosity stall costs
`n_neurons`. Reproduction costs `genome_length` cycles to copy the genome, then splits the
remaining energy in half with the child; an organism dies at energy ≤ 0.
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

---

## 4. Discussion
GENESIS demonstrates a **substrate**, not yet a mind. Its contribution is a physics engine in
which (a) every quantity is a hardware reality rather than an abstraction, (b) the learning
algorithm itself is an evolvable, DNA-encoded object, and (c) plasticity is both lifetime
(STDP) and partially heritable (Lamarckian consolidation), giving evolution a memory channel
across generations. The conservation-of-compute budget and synaptic-density viscosity are
concrete mechanisms intended to make the ~20 W, sparse-parallel regime the only survivable
one — the central hypothesis of the project.

We are deliberately conservative about cognition. The engine provides vocal cords, hearing,
an Oracle channel and heritable memory, but we have **not** measured emergent language,
logic-gate formation, or a survival advantage from learning over a non-learning control.
Prior revisions of this document reported such results for engines that have since been
deleted; those claims do not transfer to the current substrate and have been removed.

## 5. Future Work
1. **Demonstrate learning efficacy:** a controlled task where STDP + Lamarckian memory
   measurably beat a plasticity-ablated control.
2. **Real-time entropy:** re-decode or otherwise expose living phenotypes to radiation, so
   error-correction is selected in-lifetime, not only in the germline.
3. **Autotelic transition (Rule 9):** replace human-supplied food/oracle/curriculum with
   agent-generated survival problems (predation, trade, defence).
4. **Efficiency selection (Rule 7):** show that, at equal capability, lower CPU/RAM lineages
   win, using the newly-exposed efficiency metric.
5. **Deep-time robustness:** characterise stability across millions of ticks and many
   Ark/fossil recovery cycles.
