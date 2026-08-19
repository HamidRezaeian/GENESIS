## 3.2 Working Memory Does Not Extend Temporal Credit Assignment (Exp-P2B-02)

### Motivation

e-prop relies on eligibility traces that decay exponentially with time 
constant τ_e. For temporal tasks with long delays, this decay should 
prevent learning. We hypothesized that adding working memory (WM) neurons 
with slow membrane time constants could bridge these temporal gaps.

### Experimental Design

**Task:** Delayed Match-to-Sample (DMS)
- Sample stimulus at t=3
- Delay period (9 or 29 ticks)
- Test stimulus at t=13 or t=33
- Binary response: match vs. non-match

**Architectures:**
- no_WM: 2→50→2 LIF (τ_mem=20)
- with_WM: 2→50→2 LIF + 20 WM neurons (τ_mem=50)

**Conditions:** 0%, 50%, 75% metabolic blocking

### Results

| Architecture | 0% Block | 50% Block | 75% Block |
|--------------|----------|-----------|-----------|
| **Experiment 1 (9-tick delay)** |
| no_WM | 91.3% | 92.4% | 85.3% |
| with_WM | 75.5% | 74.0% | 63.3% |
| **Experiment 2 (29-tick delay)** |
| no_WM | 91.6% | 92.3% | 90.3% |
| with_WM | 68.8% | 68.0% | 79.0% |

### Key Findings

**Finding 1: no_WM succeeds even with 29-tick delay**
Despite eligibility trace decay of exp(-29/15) ≈ 14%, no_WM maintains 
91.6% accuracy. This suggests that:
- Multiple spikes during the delay refresh eligibility traces
- Persistent sub-threshold activity in LIF neurons preserves information
- The task remains learnable through standard e-prop mechanisms

**Finding 2: WM neurons do not help (and may hurt)**
with_WM performs worse than no_WM in both experiments. Possible explanations:
- WM neurons introduce noise into the hidden layer
- Eligibility traces for WM synapses decay too slowly, creating interference
- The explicit WM architecture disrupts the natural temporal dynamics of e-prop

### Interpretation

These results suggest that e-prop with standard LIF neurons already has 
an implicit form of working memory through:
1. **Eligibility trace persistence:** Traces decay slowly enough to bridge 
   moderate temporal gaps
2. **Sub-threshold integration:** Membrane potentials can maintain 
   information without explicit persistent spiking
3. **Multiple spike refreshment:** Neurons that spike multiple times 
   during the delay keep their eligibility traces active

### Implications for Biologically-Plausible AGI

These findings suggest that explicit working memory modules may not be 
necessary for local learning rules like e-prop. Instead, the temporal 
structure of the learning rule itself provides implicit memory.

This contrasts with backpropagation-based systems, which require explicit 
recurrent connections or external memory modules (LSTM, Transformers) to 
handle temporal tasks.

### Limitations

- Task simplicity: DMS with 2 stimuli may be too easy
- No distractors: Real working memory tasks include interference
- Fixed delay: Variable delays might reveal limitations

## Data Availability

Code: `experiments/phase2b/code/eprop_p2b02_working_memory.py`
Results: `experiments/phase2b/results/exp_p2b_02*_*.json`