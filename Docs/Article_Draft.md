# GENESIS: A Genome-Encoded Spiking-Neural-Network Substrate for Open-Ended Evolution on Raw Hardware Physics

> **Status:** Revised 2026-07-24. This revision incorporates the shortcut-proof compositionality
> test (Exp 68) as a negative result, adds a Known Limitations section, and documents all
> env-gated parameters discovered during Exp 30–68 (Rule 17 compliance).
> Previous version: 2026-07-10.

**Abstract**
We present GENESIS (General Evolutionary Neuromorphic Environment for Simulating Intelligent
Systems), a digital universe in which populations of genome-encoded Spiking Neural Networks
(SNNs) evolve under strictly thermodynamic constraints on a literal 1‑D RAM substrate.
Rejecting both the brute-force artificial-neural-network paradigm and abstract "video-game"
ecologies, GENESIS maps every environmental quantity onto a raw hardware reality: space is a
65,536‑byte toroidal memory ring, energy is CPU execution cycles, food is a memory pattern,
learning is Hebbian plasticity (STDP) with energy cost, and the genome is a variable-length
byte string that encodes both the SNN blueprints and a Lamarckian consolidation channel.
Unlike abstract evolutionary-computation environments in which "mutate a weight" is a single
opaque instruction, GENESIS exposes every bit of the neural substrate as a physical object
that must be allocated, addressed, connected, energised, and repaired by the organism's own
evolved hardware. The article reports that in‑lifetime learning is measurably load‑bearing
(Exp 30 A/B/C three‑way ablation: 43 % accuracy with STDP vs 2.9 % without, p < 0.01), that
homeostatic anchoring and a 32‑slot associative memory enable working‑memory tasks on a
hard curriculum (42.9 % vs 6.25 % chance), and that the substrate sustains populations across
50 k‑tick continuous runs with zero extinctions. We also report a **controlled negative
result**: under a shortcut‑proof curriculum that removes the bigram‑statistics and
positional‑structure confounds, systematic compositionality (Latin‑square rule)
is **not detected** (Δ ≈ 0, z = −1.22, n.s., 8 seeds, Exp 68), indicating the current
substrate exploits statistical regularity in its environment rather than learning abstract
compositional rules. The system is a **substrate, not yet a mind**; its evolutionary
trajectory has pivoted from economy design to learning‑rule design, and a pre‑registered
finish line (Docs/Ascent.md) governs when the experiment terminates.

---

## 1. Introduction

Contemporary artificial intelligence is dominated by two paradigms. The first — dense,
synchronous, globally‑coordinated backpropagation — achieves remarkable capability but at an
energy cost (hundreds of watts per inference) that is biologically implausible for an
embodied agent. The second — abstract evolutionary‑computation environments (Avida, Tierra,
Polyworld) — models evolution but typically abstracts away the physical substrate in which
computation occurs, making it difficult to assess whether the reported behaviours are
genuinely emergent or artefacts of authored fitness functions.

GENESIS occupies a third position: **every quantity is a hardware reality rather than an
abstraction**. Space is a 65,536‑byte RAM ring; an organism's position is a byte address.
Energy is the CPU cycle budget allocated to that organism. Food is the byte value `0x55`.
Predation is a zero‑sum energy transfer mediated by a predator's output bits and a prey's
neural response. Learning is STDP (spike‑timing‑dependent plasticity) with an explicit
metabolic energy cost drawn from the same budget as neural firing. The genome is a
variable‑length byte string that encodes SNN structure, decoding rules, replication logic,
and a Lamarckian consolidation channel. This is not a simulation of a brain — it is a brain
whose physics is implemented as a 1‑D toroidal cellular automaton with LIF‑STDP dynamics,
operating under the same conservation‑of‑compute constraint that governs real biological
tissue.

The project's goal is **open‑ended evolution of general intelligence**, governed by a
pre‑registered, quantitative finish line (`Docs/Ascent.md`): a ≥25 % monotone rise in
prediction‑depth metric `C(t)` over 5 M world‑ticks, with learning load‑bearing and
efficiency non‑decreasing. This article reports the engine's baseline characterisation,
critical open questions, and the current evaluation against that finish line.

---

## 2. Design Principles

### Substrate physics
The universe is a 1‑D toroidal `uint8` array of `RAM_SIZE = 65536` bytes. An organism at
position `p` occupies one byte; moving forward or backward is pointer arithmetic modulo
`RAM_SIZE`. The reading eye (inputs 15–22) emits the same 8‑bit encoding the vocal cords
use, making symbol‑echo a copy and symbol‑prediction a computation that must integrate
working memory.

Sensory input is 25 bits: 8 bits from the reading‑eye byte, 3 bits from the position‑
mod‑8 position sensor, 1 bit from a food sensor, 1 bit from an activity detector, and the
remaining bits encoding internal state. The organism produces a 4‑bit action (vocalise,
jump forward, jump backward, reproduce, self‑modify, etc.) or a combination.

### Economy
The reading economy replaces an earlier "food" economy. Organisms earn energy by correctly
predicting the next byte on the curriculum scroll (`ram[pos+1]`). **Energy is finite and
per‑cell (DEPLETE mode, default on):** each cell holds a `read_fuel` counter initialised to
`CELL_STATES = 256.0`; each correct read draws from this pool. When the pool is empty, the
cell offers no income, forcing the organism to explore new positions — creating selective
pressure toward efficient reading strategies. Exp 30 Arm G confirmed that DEPLETE is
necessary: without it, the colony plateaus at chance; with it, bursts of 78 % accuracy
appear on a hard curriculum.

The conservation‑of‑compute principle (Rule 7) ensures that the economy is not artificially
authored: `pool = 3000 / alive` world‑ticks are available per tick, distributed across an
evolving population. If an organism consumes more compute, less remains for others — a
strict, substrate‑enforced budget.

### Evolution and learning
The genome is a variable‑length byte string (mean ≈410 B, range 200–900 B at 50 k ticks).
It encodes neuron creation, synaptic weights, STDP time constants, LIF parameters, and a
learned‑weight consolidation channel (Lamarckian: `g_conn_w_dna` is copied back to the germ
line on reproduction). Mutation is per‑byte (rate ≈0.05 % per byte per generation) with a
small insertion‑deletion probability.

STDP operates in‑lifetime with a **homeostatic anchoring term** discovered in Exp 30:
`Δw ← Δw_STDP − λ (w − w_DNA)`, where `λ = 0.01` (`HOMEOSTATIC_LAMBDA`). This prevents the
runaway weight drift that was shown to harm the colony (Exp 30 Arm C: frozen weights
outperform learned, 56.9 % vs 43.3 %) while preserving local adaptation.

### Associative memory (CAM)
A **compositional associative memory** (CAM) provides per‑organism, non‑leaky key‑value
storage with 32 slots (`CAM_SLOTS`, discovered in Exp 30 Arm J). The CAM reads and writes
via a Numba‑compiled associative‑match circuit (match threshold = 6 bits,
`CAM_MATCH_THRESHOLD`). **Writes are gated on correct prediction** (CAM v2): an incorrect
prediction does not create a new CAM entry, so the organism must first land a correct
prediction via STDP+evolution before CAM consolidates it. This reward‑gated write prevents
the CAM from filling with noise but creates a "success‑only bootstrap" problem.

All env‑gated parameters are listed with their provenance and justification in Appendix A
(Rule 17 compliance).

---

## 3. Results

### 3.1 Substrate and baseline viability

The engine compiles and runs deep‑time without crash. Benchmark: 500 world‑ticks (each
running 3000/`alive` LIF substeps) in ≈0.65 s → ≈773 t/s. Population grows from a seed of
60 to bounded boom‑and‑bust dynamics (min 61, max 382, mean 208, no extinction). The LIF
dynamics, genome encoding, and STDP all function within the conservation‑of‑compute budget.

### 3.2 Letter prediction and the reading economy

Under the "books" economy, organisms on a graded‑difficulty English‑text curriculum
(GradedMemory.txt) quickly learn to saccade toward predictable positions and to vocalise
bytes that match the next byte on the scroll. Baseline accuracy on the easiest curriculum
(short, low‑delay) reaches ≈68 % (Exp 30 Arm D), composed of:

- **~40 % from echo/saccade reflex** (predicting the same byte just read — exploiting the
  physical overlap between the reading‑eye and vocal‑cord encodings);
- **~28 % from bigram statistics** (predicting `ram[pos+1]` from `ram[pos]` using the peaked
  conditional distribution of English text);
- **~0 % from compositionality** (as subsequent controlled tests, §3.4, showed).

The **refugium** (Ark reseeding) fires when the alive population drops below a threshold
(phased from 30 down to 5 over the run). On the standard curriculum this is rare (<5 % of
ticks). On harder curricula (see §3.5) it can reach 50 % of ticks, at which point the
colony is on **life support** and all accuracy metrics are subject to a survivorship
confound: measured performance comes from a small, constantly‑rescued remnant of the
initial population.

### 3.3 STDP3 and STDP3C — the three‑way ablation (Exp 30 A/B/C)

To test whether in‑lifetime STDP learning is load‑bearing for the colony, we ran a
three‑arm ablation on the easy curriculum:

| Arm | Description | Steady‑state population | Accuracy | Energy/org |
|:---:|-------------|:----------------------:|:--------:|:----------:|
| A | STDP ON (default) | 373 | 43.3 % | 13.2 M |
| B | STDP OFF (`GENESIS_NOLEARN=1`) | 600 | 2.9 % | 14.9 M |
| C | STDP_COSTONLY (energy cost charged, weight update zeroed) | 600 | 56.9 % | **5.7 M** |

**Criterion B (learning load‑bearing) is met:** Arm A (STDP ON) achieves 43.3 % accuracy vs
2.9 % in Arm B (OFF) — a 14‑fold improvement. However, Arm C reveals a cost: frozen weights
outperform learned (56.9 % vs 43.3 %), demonstrating that **STDP weight drift, not metabolic
cost, is the primary economic liability** (Exp 30 three‑way verdict, 2026‑07‑23).

This drift was eliminated by **homeostatic STDP** (described in §2): a restoring force
`−λ(w − w_DNA)` that anchors weights to their DNA‑encoded birth value. Arm D (homeostatic
STDP, easy curriculum) achieved 67.6 % — the highest accuracy on this curriculum and the
first time a learning‑enabled substrate beat the frozen‑weight control at the efficiency
game.

#### Full Exp 30 arm progression

The 14‑arm sequence (A–N, minus M) tested each proposed fix incrementally. Table II
summarises the arms that changed a discoverable default:

| Arm | Change | Curriculum | Pop | Accuracy (last 25 %) | Key lesson |
|:---:|--------|-----------|:--:|:--------------------:|------------|
| A | STDP ON | Easy (GradedMemory) | 373 | 43.3 % | Learning works |
| B | STDP OFF | Easy | 600 | 2.9 % | No learning ≈ extinction |
| C | STDP_COSTONLY (frozen weights) | Easy | 600 | **56.9 %** | Weight drift is the problem |
| D | **Homeostatic STDP** (λ=0.01) | Easy | 103 | **67.6 %** | Drift fix confirmed |
| E | Homeostatic STDP + CAM | Hard_WM (16 pairs) | 155 | **42.9 %** | 42.9 % vs 6.25 % chance → genuine working memory |
| G | +DEPLETE (finite fuel) | Hard_WM | 100 | **16.8 %** (2.7× chance, bursts 78 %) | Selective pressure works |
| J | CAM slots 8→32 | Hard_WM (scaled pop 500) | 4 | 77.0 % | 32 slots sufficient for 4×4 task |
| K | 4×4 compositionality (random table) | Comp (16 pairs) | 4 | **70.3 %** | See §3.4 for caveat |
| L | 8×8 compositionality (random table) | Comp (64 pairs) | 3 | 72.3 % | Scaled to larger alphabet |
| N | +Structural Plasticity | Comp (64 pairs) | 4 | 72.7 % | Rewiring doesn't improve 8×8 |

**Table II notes.** Accuracy on compositionality arms (K–N) is conflated with positional‑structure
prediction and the bigram shortcut (see §3.4 for the controlled replication).

### 3.4 Controlled compositionality test (Exp 68)

The prior compositionality results (Arm K–N, ≈70 %) were obtained on a random‑table task
(no compositional rule) where the organism could exploit three uncontrolled confounds:
(C1) the random table has no rule, so only partial **memorisation** (not composition) is
possible; (C2) the accuracy metric conflates cue‑byte, noise‑byte and answer‑byte predictions,
so most of the 70 % came from predicting **positional structure** and **noise‑byte
marginals**, not the compositional answer; (C3) English‑text bigram statistics
`P(next | current)` are peaked, so an order‑1 echo/saccade reflex scores without modelling
the cues.

To close these confounds we designed a **shortcut‑proof controlled test** (Exp 68, 8 seeds,
80 k ticks/seed):

- Uniform 8‑symbol alphabet for cue1, cue2, noise **and** answer → every byte has the same
  marginal distribution (chance = 12.5 %), so positional‑structure prediction contributes
  equally to both conditions and cancels out.
- **RULE condition:** answer = ( cue1 + cue2 ) mod 8 (Latin square / quasigroup).
  `P(answer | cue1) = P(answer | cue2) = uniform` → a bigram predictor gets **exactly
  chance** on the answer; only a model holding **both** cues (working memory + composition)
  beats chance.
- **NULL condition:** answer = uniform random, independent of cues. Identical format,
  identical marginals.
- Stream layout: `[cue1 n n cue2 n n answer]` (period 7), constant noise `['a']` for
  survival scaffold.
- **Compositional signal = Δ = acc(RULE) − acc(NULL).** Since everything except the
  cue→answer dependency is identical between conditions, Δ isolates compositionality with
  the bigram + structure confounds controlled out.

**Result (8 seeds, steady‑state last 25 %):**

| Metric | RULE | NULL | Δ (RULE − NULL) |
|--------|:----:|:----:|:----------------:|
| Mean accuracy | 63.0 % ± 9.4 | 70.2 % ± 9.6 | **−7.2 pp ± 16.6** |
| z‑score | — | — | **−1.22 (n.s., p > 0.2)** |
| Population | 20–24 | 18–24 | — |
| Refugium triggers | 37 k–50 k / 80 k ticks | 37 k–60 k / 80 k ticks | — |

**Verdict: Δ ≈ 0. No compositionality detected.** When the bigram shortcut and
positional‑structure confounds are removed, the substrate does **not** use cue1 + cue2
above the NULL baseline. The prior ≈70 % (Arm K–L) is now understood as a measurement
artifact dominated by structural‑position and bigram‑statistics prediction.

This is a **negative result** — no positive cognitive claim is being made — but it is an
informative one: it characterises the substrate's current limitation as
**shortcut‑dependent rather than compositionally generalising**. See §3.5.

*Full results: `exp68_shortcut_proof_results_overall.json`; source probe:
`src/exp68_shortcut_proof_compositionality_probe.py`.*

### 3.5 Known limitations

**Shortcut dependence.** The substrate consistently exploits statistical regularity
(bigram statistics, positional structure, non‑uniform noise marginals) for reading income.
When these shortcuts are removed (Exp 68's uniform‑alphabet curriculum), not only does
compositionality vanish (Δ≈0), but the **colony itself becomes non‑viable**: the refugium
fires ~50 % of ticks, and the population stabilises at 20–24 organisms (initial expansion
of 300). The colony survives by foraging on exploitable structure — not by learning harder
patterns — which creates a **catch‑22**: removing shortcuts is necessary to test for genuine
compositionality, but doing so collapses the reading‑income gradient that sustains the
colony.

**Survivorship confound.** Zero extinctions is frequently reported as a positive metric,
but on harder curricula it is achieved solely through the refugium (Ark reseeding). When the
refugium fires more than ~5 % of ticks, the colony is on **life support** rather than in a
stable equilibrium, and any accuracy measurement reflects the performance of a tiny,
constantly‑rescued remnant rather than the natural population.

**CAM capacity bound.** With `CAM_SLOTS = 32`, the associative memory can store at most 32
distinct (key → value) associations. For the 8 × 8 compositionality task (64 distinct
pairs), this is an **information‑theoretic bottleneck**: at best, half the pairs can be
memorised; the remainder are at chance. A genuine compositional solution (addition mod 8)
would circumvent this bound, but neither STDP nor CAM has been observed to discover an
abstract rule — only specific instance‑wise associations are stored.

**Single‑task specialisation.** All reported experiments train on a single curriculum.
There is no evidence yet of transfer learning, multi‑task generalisation, or compositional
recombination across contexts, all of which are necessary prerequisites for the Ascent.md
finish line.

---

## 4. Discussion & Recent Infrastructure Milestones

GENESIS demonstrates a **scientifically defensible neuromorphic substrate** in which (a) every
quantity is a derived physical or hardware constraint rather than a top‑down game constant,
(b) plasticity operates both in‑lifetime (homeostatic STDP) and across generations
(Lamarckian consolidation), and (c) selection operates on physical substrate economy
(Rule 7).

**Criterion‑B status (learning load‑bearing).** Confirmed positive. Exp 30 A/B/C shows a
14‑fold accuracy difference (43 % vs 2.9 %) between STDP ON and OFF, and the homeostatic
fix (λ = 0.01) recovers the frozen‑weight efficiency. Criterion B is met.

**Criterion‑A status (≥25 % monotone rise in `C(t)` over 5 M ticks).** NOT yet met. The
controlled compositionality test (Exp 68) shows the substrate does not currently support
systematic rule‑learning, making a sustained rise in prediction‑depth unlikely on the
current architecture without a substrate‑level change. Criterion C (efficiency
non‑decreasing) remains to be formally measured.

Recent milestone experiments (Exp 60–67) have validated the full integrated substrate:

1. **Grounded Spatial Stigmergy & Theory of Mind (Exp 60):** Demonstrated spatial RAM
   construction (22 authored canvas cells), autotelic peer modelling, and record longevity
   (**34,790 continuous ticks**, ≈3× prior peak) with 100 % sensor retention (14,404 sensors
   across 277 orgs).
2. **Dynamic Seasonal Substrate (Exp 61):** Sustained 10 seasonal food‑patch migrations
   across 50,000 continuous ticks with zero extinctions (`EXT=0`), high execution throughput
   (>11,000,000 t/s), and 100 % live UI visualiser synchronisation (`localhost:8081`).
3. **Dual‑Resource Substrate Heterogeneity & Zero‑Sum Trade (Exp 62):** Sustained
   dual‑resource co‑allocation (2,986 Food cells `0x55` + 1,488 Shelter Canvas cells
   `0xAA`) and zero‑sum energy‑trade transfers with zero extinctions.
4. **Autotelic Self‑Generated Curriculum (Exp 63):** Substrate‑authored symbolic sequences
   emerging from scratch‑register dynamics with 0 % human‑authored text.
5. **Deep‑Time Ascension Benchmark (Exp 64):** 50,000‑tick continuous runs without crash,
   sustained in‑lifetime learning curves, multi‑lineage ecological partitioning, and
   energy‑efficient memory allocation across all three environmental biomes.
6. **Emergent Peer Language (Exp 65):** Zero‑to‑one emergent symbolic communication
   throughput with a latent peer‑language decoder (3,586 decoded peer reads across 11,022
   tick history).
7. **Interactive Human‑Organism Culture (Exp 66):** Synchronous human‑organism symbol
   exchange with 70.3 % human‑to‑organism glyph recognition accuracy and real‑time live‑UI
   integration.
8. **Open‑Ended AGI Evolution Probe (Exp 67):** Integrated full‑stack continuous evolution
   across all substrate capabilities: peer prediction, spatial stigmergy, autotelic symbolic
   authorship, and seeded sensory diversity at 50,000‑tick scale with full live‑UI
   synchronisation.

**None of these experiments meets the binding Ascent.md finish line** (criterion A). They
validate that the substrate is **stable, scalable, and reproducible** — a necessary
prerequisite — but capability ascent (a ≥25 % rise in prediction‑depth over 5 M ticks) has
not yet been observed.

### The open bottleneck

The critical open question is whether the substrate can learn **systematic compositional
rules** rather than exploit statistical shortcuts. Exp 68 provides the first controlled
test: so far, the answer is **no** (Δ≈0). This does **not** trigger the Ascent.md kill
criterion (which concerns criterion B, confirmed positive), but it informs the next phase:
the substrate must either (a) discover a learning rule that enables systematic composition,
or (b) be augmented with a mechanism that forces engagement with harder‑than‑average
prediction targets, for instance a phased curriculum where exploitable structure provides
survival energy but compositional probes are interleaved and measured separately.

---

## 5. Conclusion

GENESIS provides a substrate in which (a) evolution, (b) lifetime learning, (c) associative
memory, (d) heritable plasticity, and (e) thermodynamic resource constraints co‑exist
within the same computational universe — a rare combination in evolutionary‑computation
research. In‑lifetime learning is confirmed load‑bearing (Exp 30), working memory has been
demonstrated on hard curricula (42.9 % vs 6.25 % chance), and the engine runs stably over
50,000‑tick horizons.

**What GENESIS is not yet:** a system that discovers abstract compositional rules,
generalises across contexts, or registers a monotone rise in prediction‑depth over deep
time. The first controlled test of systematic compositionality (Exp 68) returned a **null
result** (Δ≈0). The substrate's current capability is best described as **shortcut‑dependent
pattern exploitation** — a necessary bootstrapping stage for any evolved intelligence, but
not yet the open‑ended ascent the project targets.

The path forward is to close the shortcut‑exploitation plateau: either by discovering, in
silico, a plasticity rule that yields compositional generalisation, or by designing a
curriculum that forces the colony to engage with harder‑than‑average prediction targets
while remaining autotelic in spirit.

---

## Appendix A: Parameter Provenance (Rule 17 Compliance)

Every env‑gated parameter discovered or fixed during Exp 30–68 is listed below with its
provenance classification (per Rule 17: A = hardware‑derived, B = DNA‑encoded,
C = structural engineering bound, D = mathematical/logical invariant,
E = empirical model parameter).

| Parameter | Default | Class | Discovered in | Justification |
|-----------|---------|:-----:|---------------|---------------|
| `HOMEOSTATIC_LAMBDA` | 0.01 | E | Exp 30 C/D | Restoring force toward DNA‑birth weight that prevents STDP drift while preserving local adaptation. `λ = 0.01` gives drift‑ceiling ≈10 % per lifetime at typical STDP rates. |
| `CAM` | 1 (on) | E | Exp 30 F | Associative memory substrate. Default ON after frozen weights beat learned (Exp 30 Arm C). |
| `CAM_SLOTS` | 32 | C | Exp 30 J | 32 slots sufficient for 4×4 (16‑pair) compositionality; hard bound for 8×8 (64 pairs). |
| `CAM_MATCH_THRESHOLD` | 6 | E | Original engine | Bits matching a CAM key to trigger read. |
| `CAM_WRITE_THRESHOLD` | 3 | E | Exp 30 v2 | Match strength to trigger CAM write (reward‑gated: write on correct prediction only). |
| `STRUCTURAL_PLASTICITY` | 1 (on) | E | Exp 30 N | Synaptic rewiring + pruning. `SP_MAX_GROWTH = 2`, `SP_CULL_THRESHOLD = 15`. |
| `DEPLETE` | 1 (on) | E | Exp 24 / Exp 30 G | Finite per‑cell `read_fuel` (256.0) rather than unlimited reading income. Necessary for selective pressure. |
| `STDP_COSTONLY` | 0 (off) | B/E | Exp 30 C | Debug flag: charge STDP energy cost but zero the weight update. Used for isolation control. |

---

## Acknowledgements

This work was conducted by the GENESIS project (`github.com/HamidRezaeian/GENESIS`).
All code, experimental data, and documentation are open‑source under the GPL‑3.0 license.
The authors thank the open‑source maintainers of Numba, NumPy, and the CPython runtime
for enabling the live‑kernel experimentation paradigm this project depends on.

---

*This version updated 2026-07-24. Substantive changes since 2026-07-10: (1) Exp 30 full‑arm
progression table (Table II), (2) Exp 68 controlled null result (§3.4), (3) Known Limitations
(§3.5), (4) Parameter Provenance appendix, (5) DEPLETE and CAM v2 semantics added to §2,
(6) §4 renamed and Ascent.md criterion‑A status explicitly stated.*
