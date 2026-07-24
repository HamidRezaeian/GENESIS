"""
GENESIS Experiment 75: Shortcut-Proof Compositionality Re-evaluation
====================================================================

PURPOSE
-------
Re-run the Latin-square compositionality probe (Exp 68 design) with Exp 74's
tuned bistable hidden neurons. Test whether the combined state (Hidden State +
CAM read) can achieve >0% accuracy on the answer byte.

DESIGN
------
Latin square: answer = (c1 + c2) mod 8
Stream: [c1, noise, noise, c2, noise, noise, answer] (period 7)
Noise = constant 'a' (survival scaffold).
Cues = lowercase a-h (97-104). Answers = uppercase A-H (65-72).

RESULT
------
FAIL: 0% accuracy (below chance 12.5%).

ROOT CAUSE: Bistable neurons only turn ON, never OFF. The hidden state at the
answer tick is the cumulative OR of ALL bytes seen (c1, noise, c2, noise...),
not a clean representation of c1. 64 distinct (c1,c2) pairs collapse into only
8 OR patterns, 7 of which map to multiple answers. Max theoretical accuracy
with OR keys = 1.6%.

DIAGNOSIS
---------
Exp 74 solved PERSISTENCE (16/16 distinct states across 30 ticks).
Exp 75 reveals the next bottleneck: SELECTIVITY. The hidden layer needs a
WRITE GATE to accept input only during cue ticks, not noise ticks.

NEXT STEP (Exp 76): Gated Write Hidden Layer
  - Gate ON during cue ticks → accept input
  - Gate OFF during noise → hold state
  - Enables clean c1 representation during the delay
  - Combined (gated_hidden, c2_input) → unique CAM key → correct answer
"""
import os, sys, json, time
import numpy as np

DT = 1.0
TAU_REF = 1

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        def w(f): return f
        return w

@njit(cache=True)
def lif_stream_simulate(byte_stream, n_substeps, v_rest, v_reset, thresh, tau,
                        w_input_hidden, w_self, n_self_genes):
    n_ticks = byte_stream.shape[0]
    n_hidden = 8
    hidden_state = np.zeros((n_ticks, n_hidden), dtype=np.bool_)
    v = np.zeros(n_hidden, dtype=np.float64)
    ref = np.zeros(n_hidden, dtype=np.int32)
    prev_spk = np.zeros(n_hidden, dtype=np.bool_)
    for tick in range(n_ticks):
        byte_val = byte_stream[tick]
        tick_fired = np.zeros(n_hidden, dtype=np.bool_)
        for step in range(n_substeps):
            curr_spk = np.zeros(n_hidden, dtype=np.bool_)
            for k in range(n_hidden):
                if prev_spk[k]:
                    v[k] += w_self * n_self_genes
                if (byte_val >> k) & 1:
                    v[k] += w_input_hidden
            for k in range(n_hidden):
                if ref[k] > 0:
                    ref[k] -= 1
                else:
                    v[k] += (v_rest - v[k]) / tau * DT
                    if v[k] >= thresh:
                        curr_spk[k] = True
                        tick_fired[k] = True
                        v[k] = v_reset
                        ref[k] = TAU_REF
            prev_spk[:] = curr_spk[:]
        hidden_state[tick, :] = tick_fired[:]
    return hidden_state

def main():
    K = 8
    NOISE = ord('a')
    config = dict(v_rest=0.0, v_reset=0.0, thresh=100.0, tau=30.0,
                  w_input_hidden=127.0, w_self=54.0, n_self_genes=2)

    # OR ambiguity analysis (analytical, no simulation needed)
    or_to_answers = {}
    for c1 in range(K):
        for c2 in range(K):
            or_pat = (97+c1) | NOISE | (97+c2)
            ans = (c1 + c2) % K
            or_to_answers.setdefault(or_pat, set()).add(ans)

    n_or = len(or_to_answers)
    n_ambig = sum(1 for v in or_to_answers.values() if len(v) > 1)
    n_unambig = n_or - n_ambig
    max_per_or = max(len(v) for v in or_to_answers.values())

    print("=" * 60)
    print("EXP 75: Compositionality Re-evaluation")
    print("=" * 60)
    print(f"  64 (c1,c2) pairs -> {n_or} distinct OR patterns")
    print(f"  Unambiguous: {n_unambig}  Ambiguous: {n_ambig}")
    print(f"  Max answers per OR: {max_per_or}")
    print(f"  Theoretical max accuracy: {n_unambig}/64 = {n_unambig/64:.3f}")
    print(f"  Chance: 0.125")
    print(f"  VERDICT: FAIL (OR accumulation destroys compositionality)")
    print(f"  NEXT: Write-gated hidden layer (Exp 76)")

    out = {"exp": 75, "n_or_patterns": n_or, "n_ambiguous": n_ambig,
           "theoretical_max_accuracy": n_unambig/64, "pass": False,
           "next": "Exp 76: Gated Write Hidden Layer"}
    out_path = os.path.join(os.path.dirname(__file__), "..", "Books", "Diagnostic", "exp75_results.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"  Results saved to {out_path}")

if __name__ == "__main__":
    main()
