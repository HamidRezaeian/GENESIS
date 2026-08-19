# e-prop Limitations (Experimental Findings)

## Finding 1: Noise Fragility
Standard e-prop with eligibility traces fails at just 5% input noise.

### Attempted Solutions:
- **Sparse encoding (v26):** Made it worse (credit dilution + underfitting)
- **Postsynaptic gate (v27):** Preserved signal at 0% noise but made noise=5% worse (gate collapse)

### Root Cause:
Postsynaptic gate based on firing rate cannot distinguish signal from noise.
In noisy trials, noise neurons fire more than signal neurons, causing gate to 
block signal synapses while allowing noise synapses.

### Required for Robust e-prop:
- Input surprise detection (Acetylcholine-like novelty signal)
- OR hierarchical attention mechanisms
- OR working memory to separate signal from noise

### Implication for Phase 2A:
e-prop alone is insufficient for real-world sparse event-driven systems.
Additional architectural priors (attention, working memory) are required.
This is a measurement science finding, not a failure.