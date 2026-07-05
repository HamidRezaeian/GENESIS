# Architecture Requirements Document (ARD)

## 1. System Architecture
GENESIS is split into a **Python Backend (Physics Engine)** and a **JavaScript Frontend (Visualizer)**, connected via a RESTful API.

### 1.1 Backend: The Turing-Neumann Engine (`turing_engine.py` & `genesis_lab.py`)
The backend is a pure, custom-built Turing-complete simulation engine compiled down to machine code using **Numba `@njit`**. It models a 1D Memory Space (RAM) where organisms are execution threads. The old Graph Physics (`genesis_engine.py`) has been fully deprecated and removed.
- **The Universe:** A 1D NumPy array representing Memory (Opcodes) acting as the primordial soup.
- **Entities:** Execution Threads. Each thread has an Instruction Pointer (IP) and 4 Registers (A, B, C, D).
- **Core Loop (Tick):** 
  - Each thread executes the Opcode at its IP.
  - "Energy" is fundamentally defined as CPU Execution Cycles.
  - Opcodes perform memory reads/writes, arithmetic, and jumping.
  - Threads reproduce physically by copying their bytecode and executing `SPLIT` or `ALLOC`.
- **Execution Speed:** Exceeds 100,000 cycles per second natively on CPU.

### 1.2 Frontend: The Observation Deck (`index.html` & `server.py`)
- **Server:** FastAPI / Python's `http.server` providing `/api/state` and `/api/control`.
- **Client:** Vanilla JavaScript rendering the 1D Memory Array as a 2D Grid.
- **Rendering:** Uses an offscreen HTML5 Canvas for blazing fast pixel manipulation (mapping Opcodes to RGB values).
- **State Synchronization:** The frontend polls `/api/state` every 100ms.

## 2. Core Mathematical Mechanisms
### 2.1 Informational Physics & The Reaper
There is no explicit "fitness function". Survival is strictly determined by:
1. **Replication Speed:** Algorithms that duplicate their DNA using fewer cycles spread faster.
2. **Thermodynamic Capacity Cap:** A stochastic "Reaper" kills random IPs when the maximum thermodynamic limit (Max IPs) is reached, enforcing a brutal spatial-temporal competition.

### 2.2 Thermodynamic Radiation
The environment constantly experiences cosmic radiation (random byte flips in memory) based on a `noise_rate`. This acts as the evolutionary mutagen and forces organisms to evolve structural robustness and error correction.

### 2.4 Cryptographic Molecules (The I/O Bottleneck)
To introduce an I/O intelligence bottleneck without hardcoding a fitness function, the environment spawns "Cryptographic Molecules" (`254`).
- **Structure:** `[254, X, Y, Z]` (Where X and Y are random bytes, and Z is the answer slot).
- **Physical Law:** The bond can only be broken by executing the `CATALYZE` Opcode when `Z == (X + Y) % 256`.
- **Time Dilation Reward:** Successful catalysis grants the solving Thread an immediate **10,000 Bonus Cycles**, allowing it to hyper-replicate.

### 2.5 The Autotelic Phase (Future Physics)
Once basic Turing Completeness is proven, the Cryptographic Molecules will be removed. The universe will transition to a Zero-Sum Thermodynamic Ecosystem:
- **Zero-Sum Energy:** A fixed amount of energy cycles through the universe. Energy can only be acquired by stealing it from other IPs, absorbing dead IPs, or cooperative trading.
- **Open Memory Architecture:** IPs will have the physical ability to read/write into shared memory spaces, allowing for the evolution of Communication, Deception, and Cooperative Colonies.
- **Entropy as the Ultimate Enemy:** Extreme cosmic radiation will force organisms to evolve complex DNA error-correction (Check-sums, Parity) and immune systems, driving the emergence of self-awareness (the ability to read and repair one's own code).

### 2.6 The Tierra Trap Avoidance (Rule 10)
The physics engine must be designed so that blind, fast replication is NOT the globally optimal survival strategy. If the environment only rewards copy speed, evolution produces hyper-optimized viruses, not AGI. The physical laws must contain inherent complexities (e.g., non-linear resource processing, environmental hazards requiring predictive modeling) that make computational intelligence a thermodynamic necessity for long-term survival.

### 2.7 The 20W Architectural Paradigm (Rule 11)
The human brain achieves ~20W efficiency through massive, slow parallelism (~86 billion neurons at ~200 Hz), not high-speed sequential execution. While the Turing engine uses sequential opcodes, the architecture must observe and select for organisms that invent parallel, cooperative, or multi-threaded sub-routines (e.g., multi-cellular IP clusters sharing memory). Pure Von Neumann brute-force sequential speed diverges from the biological blueprint for energy-efficient AGI.

## 3. Data Flow
1. User adjusts slider on Frontend.
2. Frontend sends GET request (e.g., `/api/settings?mutation_rate=0.2`).
3. Backend parses request, updates global simulation constants.
4. Simulation tick runs.
5. Frontend fetches `/api/state`, receives JSON graph structure.
6. D3.js updates node positions; HTML5 Canvas renders them.
