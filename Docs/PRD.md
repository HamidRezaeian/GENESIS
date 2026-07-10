# Product Requirements Document (PRD)

> **Status:** Reflects the live SNN engine as of 2026-07-10. Capability claims are marked
> **[implemented]**, **[scaffold]** (present but human-in-the-loop), or **[goal]** (target,
> not yet demonstrated) to keep this document honest per Rule 16.

## 1. Project Overview
**Name:** GENESIS Digital Universe
**Vision:** Evolve a biological-style Spiking Neural Network that mirrors the human brain —
genuine learning, reasoning and long-term memory — at the ~20 W efficiency of biology
(Rule 6), through thermodynamic and evolutionary pressure rather than programmed behaviour.
**Tagline:** Intelligence from Thermodynamics.

## 2. Core Philosophy
Intelligence is the byproduct of a system minimising surprise and conserving energy (CPU
cycles + RAM footprint) in a hostile substrate. GENESIS enforces this on **raw hardware
realities** (Rule 15): space is RAM addresses, energy is execution cycles, food is pristine
memory, hazards are computational drag. Organisms are genome-encoded SNNs that must wire
themselves (via STDP) into efficient survival circuits or starve.

## 3. Target Capabilities
1. **Self-organisation [implemented]** — genome-seeded synapses adapt in-lifetime via STDP.
2. **Computational efficiency [scaffold]** — computational viscosity penalises dense
   genomes; a true CPU-cycle/RAM efficiency metric per lineage is still a goal.
3. **Darwinian evolution [implemented]** — heredity of DNA-encoded topology + receptor
   chemistry, mutation (point/indel/duplication), selection by starvation.
4. **Evolvable neuro-physics [implemented]** — receptor "proteins" let each organism evolve
   its own STDP rates, thresholds and resting/reset potentials (meta-learning, Rule 17).
5. **Open-ended topology [implemented]** — organisms grow hidden neurons/synapses from raw
   DNA against a shared global heap; the only ceiling is universe RAM.
6. **Emergent communication & logic [goal]** — vocal cords + neighbour hearing + the Oracle
   channel provide the substrate; unsupervised language/logic is a target, not yet proven.
7. **Long-term memory & reasoning [goal]** — the Prime Directive; requires memory that
   survives reproduction (currently only lifetime synaptic state).

## 4. User Experience & Dashboard (`public/`, WebSocket :8085)
- **Real-time visualiser [implemented]:** the folded 1D RAM substrate rendered on an HTML5
  canvas (food green, organisms blue, vocalising organisms yellow, curriculum text purple).
- **KPIs & extinction chart [implemented]:** cycles, population, extinction count, Elite age.
- **Brain Analyzer [implemented]:** D3 decompilation of the Elite genome's synapse graph.
- **Oracle Terminal Uplink [scaffold]:** broadcast an ASCII character into the universe and
  read back the Elite's vocal-cord output.
- **Library of Genesis [scaffold]:** inject curriculum text as byte patterns into the RAM.

## 5. Success Metrics
- **Stability [partially met]:** populations reach a dynamic equilibrium under the global
  cycle pool; deep-time robustness across many extinction/Ark cycles is still being proven.
- **Learning convergence [goal]:** measurable in-lifetime STDP improvement on a task.
- **Emergent, unprompted strategy [goal]:** behaviours never rewarded by the environment
  (cooperation, migration, communication) — the Autotelic Imperative (Rule 9).
- **Efficiency selection [goal]:** at equal capability, fewer CPU cycles / smaller RAM
  footprint must win (Rule 7).
