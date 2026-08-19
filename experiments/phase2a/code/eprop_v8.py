#!/usr/bin/env python
"""
Exp-P2A-01 v8: Fix Surrogate Derivative
========================================
مشکل اصلی: f_prime همیشه صفر بود چون فرمول اشتباه بود.
Fix: f_prime = max(0, 1 - |v - vth| / margin)
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    # Task
    'n_ticks': 500,
    'delay_k': 2,
    
    # Network
    'n_input': 20,
    'n_hidden': 50,
    'n_output': 2,
    'vth': 0.5,
    'dv': 0.3,
    'du': 0.3,
    'w_scale': 2.0,
    'connectivity': 0.3,
    'recurrent_connectivity': 0.2,
    
    # Learning
    'eta': 0.01,
    'tau_e': 10,
    'surrogate_margin': 1.0,  # width of pseudo-gradient
    
    # Experiment
    'arms': ['A1_eprop', 'A2_nolearn', 'A3_stdp3c'],
    'n_seeds': 4,
    'random_seed': 42,
}

RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)


class LIFPool:
    def __init__(self, n, vth=0.5, dv=0.3, du=0.3):
        self.n = n
        self.vth = vth
        self.dv = dv
        self.du = du
        self.v = np.zeros(n)
        self.u = np.zeros(n)
        self.last_spikes = np.zeros(n)
        
    def step(self, input_current):
        self.u = self.u * (1 - self.du) + input_current
        self.v = self.v * (1 - self.dv) + self.u
        spiked = self.v >= self.vth
        self.v[spiked] = 0.0
        self.last_spikes = spiked.astype(float)
        return self.last_spikes


class SynapticLayer:
    def __init__(self, n_in, n_out, connectivity=0.3, w_scale=2.0, seed=None):
        rng = np.random.RandomState(seed)
        self.n_in = n_in
        self.n_out = n_out
        self.vth = 0.5  # ← FIX: vth stored
        
        mask = rng.rand(n_out, n_in) < connectivity
        self.weights = (rng.randn(n_out, n_in) * w_scale) * mask
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return self.weights @ pre_spikes
    
    def update_eligibility(self, pre_spikes, post_spikes, post_voltage, tau_e, margin=1.0):
        """e-prop with CORRECT surrogate derivative.
        
        f'(v) = max(0, 1 - |v - vth| / margin)
        
        This is non-zero when v is near vth (within margin).
        """
        # Decay
        self.eligibility *= np.exp(-1.0 / tau_e)
        
        # ← FIX: CORRECT surrogate derivative
        # Non-zero when |v - vth| < margin
        f_prime = np.maximum(0, 1 - np.abs(post_voltage - self.vth) / margin)
        
        # Outer product: post[j] * f'(v_j) * pre[i]
        delta_e = np.outer(post_spikes * f_prime, pre_spikes)
        self.eligibility += delta_e
        
    def apply_update(self, neuromodulator, eta):
        delta_w = eta * neuromodulator * self.eligibility
        self.weights += delta_w
        return delta_w


def generate_sequence(n_ticks, seed):
    rng = np.random.RandomState(seed)
    return rng.randint(0, 2, size=n_ticks)


def encode_input(input_bit, n_input):
    x = np.zeros(n_input)
    if input_bit == 0:
        x[:10] = 1.0
    else:
        x[10:] = 1.0
    return x


def run_organism(arm, sequence, config, seed):
    """Run one organism with FIXED surrogate derivative."""
    
    k = config['delay_k']
    n_hidden = config['n_hidden']
    margin = config['surrogate_margin']
    
    # Network
    hidden = LIFPool(n_hidden, vth=config['vth'], dv=config['dv'], du=config['du'])
    output = LIFPool(config['n_output'], vth=config['vth'], dv=config['dv'], du=config['du'])
    
    # Synapses
    syn1 = SynapticLayer(config['n_input'], n_hidden,
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'], seed=seed)
    syn_rec = SynapticLayer(n_hidden, n_hidden,
                            connectivity=config['recurrent_connectivity'],
                            w_scale=config['w_scale'], seed=seed+1)
    syn2 = SynapticLayer(n_hidden, config['n_output'],
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'], seed=seed+2)
    
    # State
    correct = 0
    total = 0
    total_updates = 0
    total_spikes = 0
    trace_magnitudes = []
    
    for t in range(k, len(sequence)):
        input_bit = sequence[t]
        target_bit = sequence[t - k]
        
        # Encode input
        x = encode_input(input_bit, config['n_input'])
        
        # Forward with recurrent
        u_input = syn1.forward(x)
        u_recurrent = syn_rec.forward(hidden.last_spikes)
        s_hidden = hidden.step(u_input + u_recurrent)
        
        u_out = syn2.forward(s_hidden)
        s_out = output.step(u_out)
        
        total_spikes += np.sum(s_hidden) + np.sum(s_out)
        
        # Prediction
        pred = int(output.v[1] > output.v[0])
        is_correct = (pred == target_bit)
        
        if is_correct:
            correct += 1
        total += 1
        
        # Learning
        if arm in ['A1_eprop', 'A3_stdp3c']:
            # Update eligibility with CORRECT surrogate
            syn1.update_eligibility(x, s_hidden, hidden.v, config['tau_e'], margin)
            syn_rec.update_eligibility(s_hidden, s_hidden, hidden.v, config['tau_e'], margin)
            syn2.update_eligibility(s_hidden, s_out, output.v, config['tau_e'], margin)
            
            # Track trace magnitude
            if len(trace_magnitudes) < 20:
                trace_magnitudes.append(np.abs(syn2.eligibility).max())
            
            # Neuromodulator from error
            target_spikes = np.zeros(config['n_output'])
            target_spikes[target_bit] = 1.0
            error = target_spikes - s_out
            M = float(np.mean(np.abs(error)))
            
            if M > 0:
                syn1.apply_update(M, config['eta'])
                syn_rec.apply_update(M, config['eta'])
                syn2.apply_update(M, config['eta'])
                total_updates += 1
    
    accuracy = correct / total if total > 0 else 0.0
    
    return {
        'arm': arm,
        'seed': seed,
        'accuracy': float(accuracy),
        'updates': int(total_updates),
        'total': total,
        'spikes': int(total_spikes),
        'trace_max': float(max(trace_magnitudes)) if trace_magnitudes else 0.0,
        'trace_mean': float(np.mean(trace_magnitudes)) if trace_magnitudes else 0.0,
    }


def main():
    print("=" * 70)
    print("Exp-P2A-01 v8: FIXED Surrogate Derivative")
    print("=" * 70)
    print(f"Task: Delayed copy (k={CONFIG['delay_k']})")
    print(f"Network: {CONFIG['n_hidden']} hidden LIF + recurrent")
    print(f"Surrogate: f'(v) = max(0, 1 - |v - vth| / {CONFIG['surrogate_margin']})")
    print(f"Seeds: {CONFIG['n_seeds']} per arm")
    print()
    
    results = []
    
    for arm in CONFIG['arms']:
        print(f"Running {arm}...")
        arm_results = []
        
        for seed_idx in range(CONFIG['n_seeds']):
            seed = CONFIG['random_seed'] + seed_idx
            sequence = generate_sequence(CONFIG['n_ticks'], seed)
            
            result = run_organism(arm, sequence, CONFIG, seed)
            arm_results.append(result)
            
            print(f"  seed {seed}: acc={result['accuracy']:.3f}, "
                  f"updates={result['updates']}, "
                  f"trace_max={result['trace_max']:.4f}")
        
        results.append({
            'arm': arm,
            'mean_acc': float(np.mean([r['accuracy'] for r in arm_results])),
            'std_acc': float(np.std([r['accuracy'] for r in arm_results])),
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
    
    print()
    print(f"{'Arm':<20} {'Mean Acc':<12} {'Std':<10} {'Trace Max':<12}")
    print("-" * 60)
    for r in results:
        print(f"{r['arm']:<20} {r['mean_acc']:<12.3f} "
              f"{r['std_acc']:<10.3f} {r['mean_trace']:<12.4f}")
    
    # Diagnostic: trace باید > 0 باشد
    print()
    print("Diagnostic (Opus check #1): eligibility_trace > 0?")
    if a1['mean_trace'] > 0.001:
        print(f"  ✅ A1 trace_max = {a1['mean_trace']:.4f} > 0")
    else:
        print(f"  ❌ A1 trace_max = {a1['mean_trace']:.4f} ≈ 0 (STILL BROKEN)")
    
    print()
    print("Gate A (delta >= +5pp):")
    delta = (a1['mean_acc'] - a2['mean_acc']) * 100
    print(f"  A1 vs A2 = {delta:+.2f} pp")
    print(f"  Bar: +5.00 pp")
    print(f"  Result: {'✅ PASS' if delta >= 5.0 else '❌ FAIL'}")
    
    print()
    print("Sanity check:")
    a2_acc = a2['mean_acc']
    print(f"  A2 (nolearn) accuracy: {a2_acc:.3f}")
    if 0.45 <= a2_acc <= 0.55:
        print(f"  ✅ A2 near chance (50%)")
    
    print()
    print("D5 prediction check:")
    delta3 = (a1['mean_acc'] - a3['mean_acc']) * 100
    print(f"  A1 (buffered) vs A3 (coupled) = {delta3:+.2f} pp")
    
    # Permutation test
    print()
    print("Permutation test (A1 vs A2):")
    a1_accs = [r['accuracy'] for r in a1['seeds']]
    a2_accs = [r['accuracy'] for r in a2['seeds']]
    observed_diff = np.mean(a1_accs) - np.mean(a2_accs)
    combined = a1_accs + a2_accs
    rng = np.random.RandomState(42)
    perm_diffs = []
    for _ in range(1000):
        rng.shuffle(combined)
        perm_diffs.append(np.mean(combined[:len(a1_accs)]) - np.mean(combined[len(a1_accs):]))
    p_value = float(np.mean(np.abs(perm_diffs) >= np.abs(observed_diff)))
    print(f"  p-value: {p_value:.4f}")
    print(f"  Result: {'✅ PASS' if p_value < 0.05 else '❌ FAIL'}")
    
    # Hypothesis
    print()
    print("Hypothesis Test:")
    if delta >= 5.0 and p_value < 0.05:
        print("  🎉 H1 CONFIRMED: e-prop with buffering rescues learning!")
        if delta3 > 2.0:
            print("  🎉 D5 PREDICTION CONFIRMED!")
    else:
        print("  ⚠️  H1 NULL: continue F1-F5 diagnostics")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v8_surrogate_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v8 (fixed surrogate derivative)',
        'config': CONFIG,
        'results': results,
        'delta_a1_a2': float(delta),
        'delta_a1_a3': float(delta3),
        'p_value': float(p_value),
        'h1_confirmed': bool(delta >= 5.0 and p_value < 0.05),
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    print("=" * 70)


if __name__ == '__main__':
    main()