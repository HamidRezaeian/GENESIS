

# RULE: STRICT PHYSICS MATH VERIFICATION & NO MAGIC NUMBERS

Whenever modifying or introducing a new mechanic in the physics engine (`genesis_lab.py`, `neuromorphic_engine.py`), the agent MUST explicitly follow these steps BEFORE writing code:

1. **Rule 17 Classification Check**: Every single numeric parameter must be classified. If it is an Empirical Model Parameter (Category E), it MUST NOT be hardcoded as a magic number. It MUST be exposed via `os.environ.get("GENESIS_...", "default_value")` so it is visible, documented, and not silently tuned.
2. **Rule 13 Substrate Grounding**: Any metabolic cost or penalty MUST scale physically with the organism's footprint (neurons, synapses, mass, activity). Flat penalties for massive organisms are biologically and mathematically invalid.

# RULE: EVOLUTION SPEED LIMITS (CODE VS. PHYSICS)

When the user requests to "speed up evolution" or "maximize speed":
1. The agent MUST NOT artificially tune physics constants (e.g., mutation rate, organism energy, seasonal length) to force faster adaptation. Physics constants are derived from the substrate (Rule 17) and must remain biologically and mathematically honest.
2. The agent MUST achieve faster evolution purely by optimizing the Python/Numba codebase (e.g., using `python-performance-optimization` skill, vectorization, reducing memory allocation, avoiding Python loops in JIT contexts). Speed must come from computational efficiency, not from breaking the simulated physics.

# RULE: NO HARDCODED ABSOLUTE PATHS

When writing scripts, tests, or scratch files:
1. The agent MUST NOT hardcode absolute file paths (e.g., `C:\Users\...` or `/home/...`) directly into the code.
2. Paths MUST be resolved dynamically. For workspace-relative imports, the agent should run the script from the project root and use relative resolution like `sys.path.append(os.path.abspath("src"))` or calculate paths relative to `os.environ.get("PYTHONPATH")`.
3. Temporary scratch scripts must be written as if they are part of a portable, version-controlled repository.

# RULE: MANDATORY FRONTEND (UI) AND BACKEND (genesis_lab.py) SYNCHRONIZATION

Whenever modifying the state loop, metrics, feature flags, or telemetric outputs in `src/genesis_lab.py` or `src/neuromorphic_engine.py`, the agent MUST ensure that:
1. **Atomic Frontend Co-Update (ZERO REMINDERS)**: Whenever introducing or modifying a RAM byte value (e.g. `0xAA` Shelter Canvas), telemetric metric, or feature flag in the engine, the agent MUST update `public/app.js` (canvas pixel color mappings, legend handlers, and state parsers) and `public/index.html` (legend badges and KPI tiles) IN THE EXACT SAME TASK, without waiting for user prompts.
2. **Latest Experiment Default**: Default environment settings in `src/genesis_lab.py` MUST align with the project's latest benchmarked experiment state (e.g. Grounded Spatial Stigmergy, Decoupled Theory of Mind, WMEM, Scratchpad) rather than legacy scaffold defaults.
3. **WebSocket Telemetry Contract**: The `state` broadcast payload emitted over WebSocket (`ws://<host>:8085`) continuously includes all live engine metrics (`reads`, `pred`, `peer`, `sensors`, `actuators`) and active feature flags (`PEER`, `EVOSENSE`, `EVOACT`, `REMAP`, `WMEM`, `SCRATCH`, `NICHE`, `GROUNDED`, `STIGMERGY`, `CANVAS`).
4. **Observation Deck Integrity**: The Vanilla-JS frontend (`public/`) remains fully coupled to `genesis_lab.py` without schema drift, correctly rendering live RAM canvas states, KPI tiles, feature flag indicators, and Brain Analyzer decompilations.
5. **Honest UI Telemetry**: The UI visualizer must never mock or decouple from live backend states; all surfaced signals must originate directly from real engine execution.