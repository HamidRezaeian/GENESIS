

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