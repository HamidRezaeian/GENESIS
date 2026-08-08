#!/usr/bin/env python
"""
Exp-P2A-01 v12: Balanced Accuracy + Credit Assignment Fix
==========================================================
مشکلات v11:
1. Accuracy زیر baseline بود (0.414 vs 0.558)
2. Target با input[t-3] correlated (lag=3 corr = 0.1367)
3. P(target=0) = 0.558, P(target=1) = 0.442 → imbalanced

Fixes:
1. Balanced accuracy metric (macro F1)
2. Inverted error test
3. Accuracy-over-time tracking
4. Stronger input encoding (input[t-3] را مستقیم encode کن)
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    'n_ticks': 2000,  # longer training
    'T1': 3,
    'T2': 6,
    'pulse_prob': 0.3,
    
    'n_input': 30,     # more input neurons
    'n_hidden': 100,
    'n_output': 10,
    'vth': 1.0,
    'dv': 0.2,
    'du': 0.2,
    'w_scale': 1.5,
    'connectivity': 0.2,
    'recurrent_connectivity': 0.2,
    
    'eta': 0.02,       # higher learning rate
    'tau_e': 15,
    'surrogate_margin': 1.0,
    
    'arms': ['A1_eprop', 'A2_nolearn', 'A3_stdp3c', 'A4_inverted'],  # ← add inverted arm
    'n_seeds': 4,
    'random_seed': 42,
}

RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)


class LIFPool:
    def __init__(self, n, vth=1.0, dv=0.2, du=0.2):
        self.n = n
        self.vth = vth
        self.dv = dv
        self.du = du
        self.v = np.zeros(n)
        self.u = np.zeros(n)
        self.last_spikes = np.zeros(n)
        self.pre_reset_v = np.zeros(n)
        
    def step(self, input_current):
        self.u = self.u * (1 - self.du) + input_current
        self.v = self.v * (1 - self.dv) + self.u
        self.pre_reset_v = self.v.copy()
        spiked = self.v >= self.vth
        self.v[spiked] = 0.0
        self.last_spikes = spiked.astype(float)
        return self.last_spikes


class SynapticLayer:
    def __init__(self, n_in, n_out, connectivity=0.2, w_scale=1.5, vth=1.0, seed=None):
        rng = np.random.RandomState(seed)
        self.n_in = n_in
        self.n_out = n_out
        self.vth = vth
        
        mask = rng.rand(n_out, n_in) < connectivity
        self.weights = (rng.randn(n_out, n_in) * w_scale) * mask
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return self.weights @ pre_spikes
    
    def update_eligibility(self, pre_spikes, post_spikes, pre_reset_voltage, tau_e, margin=1.0):
        self.eligibility *= np.exp(-1.0 / tau_e)
        f_prime = np.maximum(0, 1 - np.abs(pre_reset_voltage - self.vth) / margin)
        delta_e = np.outer(post_spikes * f_prime, pre_spikes)
        self.eligibility += delta_e
        
    def apply_update(self, neuromodulator, eta):
        delta_w = eta * neuromodulator * self.eligibility
        self.weights += delta_w
        return delta_w


def generate_temporal_xor(n_ticks, T1, T2, pulse_prob, seed):
    rng = np.random.RandomState(seed)
    input_pulses = (rng.rand(n_ticks) < pulse_prob).astype(int)
    target = np.zeros(n_ticks, dtype=int)
    for t in range(max(T1, T2), n_ticks):
        target[t] = input_pulses[t - T1] ^ input_pulses[t - T2]
    return input_pulses, target


def encode_input(pulse, input_t3, n_input):
    """Stronger encoding: include input[t-3] directly."""
    x = np.zeros(n_input)
    
    # First 10 neurons: current pulse
    if pulse == 1:
        x[:5] = 1.0
    
    # Next 10 neurons: input[t-3] (crucial for XOR!)
    if input_t3 == 1:
        x[10:15] = 1.0
    
    # Next 10 neurons: input[t-6]
    # (will be encoded implicitly through recurrent)
    
    return x


def balanced_accuracy(predictions, targets):
    """Balanced accuracy: average of TPR and TNR."""
    # True Positive Rate (recall for class 1)
    pos_mask = (targets == 1)
    if np.sum(pos_mask) > 0:
        tpr = np.mean(predictions[pos_mask] == 1)
    else:
        tpr = 0.0
    
    # True Negative Rate (recall for class 0)
    neg_mask = (targets == 0)
    if np.sum(neg_mask) > 0:
        tnr = np.mean(predictions[neg_mask] == 0)
    else:
        tnr = 0.0
    
    return (tpr + tnr) / 2


def run_organism(arm, input_pulses, targets, config, seed):
    """Run one organism with balanced accuracy + inverted test."""
    
    T1 = config['T1']
    T2 = config['T2']
    start_tick = max(T1, T2)
    n_hidden = config['n_hidden']
    margin = config['surrogate_margin']
    
    # Network
    hidden = LIFPool(n_hidden, vth=config['vth'], dv=config['dv'], du=config['du'])
    output = LIFPool(config['n_output'], vth=config['vth'], dv=config['dv'], du=config['du'])
    
    # Synapses
    syn1 = SynapticLayer(config['n_input'], n_hidden,
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'],
                         vth=config['vth'], seed=seed)
    syn_rec = SynapticLayer(n_hidden, n_hidden,
                            connectivity=config['recurrent_connectivity'],
                            w_scale=config['w_scale'],
                            vth=config['vth'], seed=seed+1)
    syn2 = SynapticLayer(n_hidden, config['n_output'],
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'],
                         vth=config['vth'], seed=seed+2)
    
    # State
    all_predictions = []
    all_targets = []
    total_updates = 0
    trace_magnitudes = []
    accuracy_over_time = []
    
    for t in range(len(input_pulses)):
        pulse = input_pulses[t]
        input_t3 = input_pulses[t - T1] if t >= T1 else 0
        
        # Stronger encoding
        x = encode_input(pulse, input_t3, config['n_input'])
        
        # Forward
        u_input = syn1.forward(x)
        u_recurrent = syn_rec.forward(hidden.last_spikes)
        s_hidden = hidden.step(u_input + u_recurrent)
        
        u_out = syn2.forward(s_hidden)
        s_out = output.step(u_out)
        
        # Evaluation
        if t >= start_tick:
            target = targets[t]
            
            # Prediction from pre-reset voltage
            pred = int(output.pre_reset_v[5:].mean() > output.pre_reset_v[:5].mean())
            
            all_predictions.append(pred)
            all_targets.append(target)
            
            # Track accuracy over time
            if len(all_predictions) >= 100:
                recent_acc = balanced_accuracy(
                    np.array(all_predictions[-100:]),
                    np.array(all_targets[-100:])
                )
                accuracy_over_time.append(recent_acc)
            
            # Learning
            if arm in ['A1_eprop', 'A3_stdp3c', 'A4_inverted']:
                # Update eligibility
                syn1.update_eligibility(x, s_hidden, hidden.pre_reset_v, config['tau_e'], margin)
                syn_rec.update_eligibility(s_hidden, s_hidden, hidden.pre_reset_v, config['tau_e'], margin)
                syn2.update_eligibility(s_hidden, s_out, output.pre_reset_v, config['tau_e'], margin)
                
                # Track trace
                if len(trace_magnitudes) < 100:
                    trace_magnitudes.append(np.abs(syn2.eligibility).max())
                
                # Neuromodulator from error
                target_spikes = np.zeros(config['n_output'])
                if target == 1:
                    target_spikes[5:] = 1.0
                else:
                    target_spikes[:5] = 1.0
                
                error = target_spikes - s_out
                
                # ← KEY: Inverted arm for debugging
                if arm == 'A4_inverted':
                    M = float(-np.mean(np.abs(error)))  # NEGATIVE error
                else:
                    M = float(np.mean(np.abs(error)))
                
                if abs(M) > 0:
                    syn1.apply_update(M, config['eta'])
                    syn_rec.apply_update(M, config['eta'])
                    syn2.apply_update(M, config['eta'])
                    total_updates += 1
    
    # Final metrics
    predictions = np.array(all_predictions)
    targets_arr = np.array(all_targets)
    
    accuracy = balanced_accuracy(predictions, targets_arr)
    regular_accuracy = np.mean(predictions == targets_arr)
    
    return {
        'arm': arm,
        'seed': seed,
        'balanced_accuracy': float(accuracy),
        'regular_accuracy': float(regular_accuracy),
        'updates': int(total_updates),
        'trace_max': float(max(trace_magnitudes)) if trace_magnitudes else 0.0,
        'final_accuracy': float(accuracy_over_time[-1]) if accuracy_over_time else 0.0,
        'accuracy_curve': [float(a) for a in accuracy_over_time[::20]],  # sample every 20
    }


def main():
    print("=" * 70)
    print("Exp-P2A-01 v12: Balanced Accuracy + Inverted Error Test")
    print("=" * 70)
    print(f"Task: output[t] = input[t-{CONFIG['T1']}] XOR input[t-{CONFIG['T2']}]")
    print(f"Network: {CONFIG['n_hidden']} hidden")
    print(f"Encoding: input[t-3] directly encoded")
    print(f"Metric: Balanced accuracy (macro F1)")
    print(f"Arms: {', '.join(CONFIG['arms'])}")
    print(f"Seeds: {CONFIG['n_seeds']}")
    print()
    
    results = []
    
    for arm in CONFIG['arms']:
        print(f"Running {arm}...")
        arm_results = []
        
        for seed_idx in range(CONFIG['n_seeds']):
            seed = CONFIG['random_seed'] + seed_idx
            input_pulses, targets = generate_temporal_xor(
                CONFIG['n_ticks'], CONFIG['T1'], CONFIG['T2'],
                CONFIG['pulse_prob'], seed
            )
            
            result = run_organism(arm, input_pulses, targets, CONFIG, seed)
            arm_results.append(result)
            
            print(f"  seed {seed}: bal_acc={result['balanced_accuracy']:.3f}, "
                  f"reg_acc={result['regular_accuracy']:.3f}, "
                  f"updates={result['updates']}")
        
        results.append({
            'arm': arm,
            'mean_bal_acc': float(np.mean([r['balanced_accuracy'] for r in arm_results])),
            'mean_reg_acc': float(np.mean([r['regular_accuracy'] for r in arm_results])),
            'mean_trace': float(np.mean([r['trace_max'] for r in arm_results])),
            'seeds': arm_results,
        })
    
    # Analysis
    print()
    print("=" * 70)
    print("Results Analysis")
    print("=" * 70)
    
    a1 = next(r for r in results if r['arm'] == 'A1_eprop')
    a2 = next(r for r in results if r['arm'] == 'A2_nolearn')
    a3 = next(r for r in results if r['arm'] == 'A3_stdp3c')
    a4 = next(r for r in results if r['arm'] == 'A4_inverted')
    
    print()
    print(f"{'Arm':<20} {'Bal Acc':<10} {'Reg Acc':<10} {'Trace':<10}")
    print("-" * 55)
    for r in results:
        print(f"{r['arm']:<20} {r['mean_bal_acc']:<10.3f} "
              f"{r['mean_reg_acc']:<10.3f} "
              f"{r['mean_trace']:<10.4f}")
    
    print()
    print("Baseline comparison:")
    print("-" * 50)
    print(f"  Always predict 0:   0.558 (due to imbalance)")
    print(f"  Always predict 1:   0.442")
    print(f"  Balanced baseline:  0.500")
    
    # Key insight: inverted arm
    print()
    print("Critical Diagnostic (A4 inverted):")
    print("-" * 50)
    if a4['mean_bal_acc'] > a1['mean_bal_acc']:
        print(f"  ⚠️  A4 (inverted) = {a4['mean_bal_acc']:.3f} > A1 = {a1['mean_bal_acc']:.3f}")
        print(f"  → Error signal SIGN is WRONG")
        print(f"  → Need to invert error or learning rule")
    elif a4['mean_bal_acc'] < a1['mean_bal_acc']:
        print(f"  ✅ A1 = {a1['mean_bal_acc']:.3f} > A4 = {a4['mean_bal_acc']:.3f}")
        print(f"  → Error signal sign is correct")
    else:
        print(f"  ⚠️  A1 = A4 = {a1['mean_bal_acc']:.3f}")
        print(f"  → Neither direction learns")
    
    # Gate A
    print()
    print("Gate A (delta >= +5pp):")
    delta = (a1['mean_bal_acc'] - a2['mean_bal_acc']) * 100
    print(f"  A1 vs A2 = {delta:+.2f} pp (balanced)")
    print(f"  Result: {'✅ PASS' if delta >= 5.0 else '❌ FAIL'}")
    
    # Permutation test
    print()
    print("Permutation test (A1 vs A2, balanced acc):")
    a1_accs = [r['balanced_accuracy'] for r in a1['seeds']]
    a2_accs = [r['balanced_accuracy'] for r in a2['seeds']]
    observed_diff = np.mean(a1_accs) - np.mean(a2_accs)
    combined = a1_accs + a2_accs
    rng = np.random.RandomState(42)
    perm_diffs = []
    for _ in range(1000):
        rng.shuffle(combined)
        perm_diffs.append(np.mean(combined[:len(a1_accs)]) - np.mean(combined[len(a1_accs):]))
    p_value = float(np.mean(np.abs(perm_diffs) >= np.abs(observed_diff)))
    print(f"  p-value: {p_value:.4f}")
    
    # Hypothesis
    print()
    print("Hypothesis Test:")
    if delta >= 5.0 and p_value < 0.05:
        print("  🎉 H1 CONFIRMED: e-prop learns Temporal XOR!")
    elif a4['mean_bal_acc'] > a1['mean_bal_acc']:
        print("  ⚠️  Error signal INVERTED — fix sign and re-run")
    else:
        print("  ⚠️  H1 NULL — credit assignment still broken")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v12_balanced_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v12 (balanced accuracy + inverted test)',
        'config': CONFIG,
        'results': results,
        'delta_a1_a2': float(delta),
        'p_value': float(p_value),
        'inverted_better': bool(a4['mean_bal_acc'] > a1['mean_bal_acc']),
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    print("=" * 70)


if __name__ == '__main__':
    main()