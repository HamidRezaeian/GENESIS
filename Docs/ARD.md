# Architecture Requirements Document (ARD)

## 1. System Architecture
GENESIS is split into a **Python Backend (Physics Engine)** and a **JavaScript/React Frontend (Observation Deck)**, connected via a RESTful API.

### 1.1 Backend: Neuromorphic Physics Engine (`neuromorphic_engine.py` & `genesis_lab.py`)
The backend is a biologically plausible Spiking Neural Network (SNN) simulator compiled down to machine code using **Numba `@njit`**. It models a 2D Euclidean Grid where organisms possess neural architectures. The legacy 1D Tierra-style memory soup has been fully deprecated in favor of True SNNs.
- **The Universe:** A 64x64 Toroidal 2D Grid populated by Thermodynamic Food (`1.0` to `255.0` energy) and active Organisms.
- **Organisms:** Neural agents utilizing Leaky Integrate-and-Fire (LIF) physics. The genome size (`GENOME_SZ`) is exactly 752 bytes, which encodes the weight matrices (`w_ih`, `w_ho`, `w_hh`) and neural hyperparameters (Thresholds, Tau constants).
- **Core Loop (Tick):** 
  - Each organism executes 5 sub-steps (`n_lif_steps = 5`) per world-tick.
  - Action potentials (Spikes) propagate through the network.
  - **Memory Synapses (Phase 43):** Hidden-layer spikes reverberate with a 0.5ms delay via a recurrent 16x16 weight matrix (`w_hh`), granting short-term working memory.
  - "Energy" (ATP) is burnt per spike. Foraging and photosynthesis replenish ATP.
  - Reproduction is Lamarckian: organisms pass down their dynamically learned synaptic weights to their offspring.
- **Hebbian Learning:** Synapses adjust dynamically in real-time via Spike-Timing Dependent Plasticity (STDP).

### 1.2 Frontend: The Observation Deck (`app.js` & `server.py`)
- **Server:** FastAPI providing `/api/state`, `/api/oracle`, and `/api/analyze`.
- **Client:** Vanilla JavaScript rendering the 2D Grid.
- **Rendering:** Uses an offscreen HTML5 Canvas. Food is rendered in Green, active organisms in Hot Pink, and the Elite Ancestor in Gold.
- **The Brain Analyzer:** A specialized UI modal that fetches a decompiled view of the SNN's topological weights.
- **The Oracle Terminal:** A real-time UI component allowing the user to broadcast ASCII characters into the simulation's sensory inputs and read the decoded vocal outputs of the Elite organism.

## 2. Core Biological Mechanisms
### 2.1 Thermodynamic ATP & The Reaper
There is no explicit "fitness function" beyond ATP survival:
1. **Foraging:** Organisms must spatially navigate the 2D grid to absorb localized energy (Food).
2. **Mitosis:** Once an organism hits the reproduction threshold (e.g. 20,000 ATP), it replicates.
3. **Senescence:** Organisms suffer increasing metabolic drag as they age.

### 2.2 The Elite Ark
To guarantee strictly ascending evolution across mass extinction events, the system tracks the longest-surviving lineage. When global extinction occurs, the universe is re-seeded using the DNA of the most successful organism from the prior era.

### 2.3 The Oracle Bottleneck (I/O)
To introduce a cognitive bottleneck, the environment broadcasts an 8-bit signal (from the user).
- **Sensory & Vocal:** Organisms possess 8 sensory neurons listening to the Oracle, and 8 output neurons acting as Vocal Cords.
- **Cognitive Bounty:** The physics engine rewards massive ATP injections (e.g., +10,000) for solving thermodynamic logical challenges (such as predicting `Oracle + 1`). This explicitly forces the network to evolve multi-layer logic gates and sequential prediction over time.

### 2.4 The 20W Architectural Paradigm (Rule 11)
The human brain achieves ~20W efficiency through massive, slow parallelism (~86 billion neurons at ~200 Hz). The GENESIS engine strictly rejects Von Neumann sequential computation and forces organisms into sparse, distributed Spiking Neural Networks. Organisms must evolve to minimize unnecessary spiking (which costs ATP) while maintaining high predictive accuracy, directly mimicking the thermodynamic constraints of organic intelligence.
