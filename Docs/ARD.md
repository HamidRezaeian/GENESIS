# Architecture Requirements Document (ARD)

## 1. System Architecture
GENESIS is split into a **Python Backend (Physics Engine)** and a **JavaScript Frontend (Visualizer)**, connected via a RESTful API.

### 1.1 Backend: The Digital Physics Engine (`genesis_engine.py`)
The backend is a pure, custom-built simulation engine compiled down to machine code using **Numba `@njit`**. It models a 1D Memory Space (RAM) where organisms are execution threads.
- **The Universe:** A 1D NumPy array representing Memory (Opcodes).
- **Entities:** Execution Threads (Registers: A, B, C, D, IP, Energy, etc.).
- **Core Loop (Tick):** 
  - Each thread executes the Opcode at its Instruction Pointer (IP).
  - Energy is consumed or rewarded purely based on the physical consequences of the executed opcode (e.g., EAT command on an energy block).
  - Threads that deplete their energy are culled.
  - Threads that execute `SPAWN` successfully reproduce.
- **Execution Speed:** Can exceed 120,000 cycles per second natively on CPU.

### 1.2 Frontend: The Observation Deck (`index.html` & `server.py`)
- **Server:** FastAPI / Python's `http.server` providing `/api/state` and `/api/control`.
- **Client:** Vanilla JavaScript rendering the 1D Memory Array as a 2D Grid.
- **Rendering:** Uses an offscreen HTML5 Canvas for blazing fast pixel manipulation (mapping Opcodes to RGB values).
- **State Synchronization:** The frontend polls `/api/state` every 100ms.

## 2. Core Mathematical Mechanisms
### 2.1 The Free Energy Principle (FEP)
Survival is directly tied to predictive accuracy.
`Energy_Delta = Reward_Constant * (1.0 - Prediction_Error) - Metabolism_Cost`

### 2.2 Structural Complexity Costs
Brains are not free. Thermodynamic laws enforce minimal complexity.
`Cost = (Nodes_Count + Edges_Count) * Synapse_Cost`

### 2.3 Multi-Agent Backpropagation (Differentiable Communication)
To solve the Symbol Grounding problem without supervision, gradients are passed *between* agents.
- **Forward:** Node A emits `Signal_x`. Node B receives `Signal_x` and computes `Action_y`.
- **Loss:** Node B incurs `Loss` based on environmental survival.
- **Backward:** Node B calculates `dLoss / dSignal_x` and sends this gradient back to Node A. Node A uses it to update its weights, learning to "speak" accurately.

## 3. Data Flow
1. User adjusts slider on Frontend.
2. Frontend sends GET request (e.g., `/api/settings?mutation_rate=0.2`).
3. Backend parses request, updates global simulation constants.
4. Simulation tick runs.
5. Frontend fetches `/api/state`, receives JSON graph structure.
6. D3.js updates node positions; HTML5 Canvas renders them.
