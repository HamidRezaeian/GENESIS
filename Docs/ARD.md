# Architecture Requirements Document (ARD)

## 1. System Architecture
GENESIS is split into a **Python Backend (Physics Engine)** and a **JavaScript Frontend (Visualizer)**, connected via a RESTful API.

### 1.1 Backend: The Physics Engine (`genesis_engine.py`)
The backend is a pure, custom-built simulation engine. It does **not** rely on heavy ML frameworks like PyTorch or TensorFlow, ensuring maximum control over the gradient mathematics.
- **Entities:** `Node` (Organism) and `Edge` (Interaction/Observation).
- **The Graph:** Managed as a dynamic list of nodes and edges.
- **The Brain (`DynamicBrain`):** A custom, structurally mutating Multi-Layer Perceptron.
  - Implements its own manual Forward Pass and manual Backpropagation (`backward()`).
  - Capable of structural growth (adding hidden neurons).
- **Core Loop (Tick):**
  1. Environmental Energy injection.
  2. Forward Pass (Nodes predict the environment).
  3. Energy Accounting (Bonus for accuracy, penalty for size/metabolism).
  4. Backpropagation (Weight updates via Gradient Descent).
  5. Culling (Death of nodes with Energy <= 0).
  6. Reproduction (Asexual division with genetic mutation).
  7. Graph Maintenance (Breaking/forming edges).

### 1.2 Frontend: The Observation Deck (`index.html` & `server.py`)
- **Server:** Python's built-in `http.server` handles GET requests for `/api/state` and serves `index.html`.
- **Client:** Uses vanilla JavaScript and `D3.js` for rendering.
- **Rendering:** Uses HTML5 Canvas for performance (capable of rendering thousands of nodes at 60 FPS).
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
