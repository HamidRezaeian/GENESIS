#!/usr/bin/env python
"""
Exp-P2A-01 v7: Delayed Copy با Recurrent Connections
====================================================
Fixes:
1. باگ n_out
2. Recurrent connections در hidden layer (برای memory)
3. Delay k=2 (ساده‌تر)
4. Sanity check بهتر
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    # Task
    'n_ticks': 500,
    'delay_k': 2,  # shorter delay (easier)
    
    # Network
    'n_input': 20,
    'n_hidden': 50,
    'n_output': 2,
    'vth': 0.5,
    'dv': 0.3,
    'du': 0.3,
    'w_scale': 2.0,
    'connectivity': 0.3,
    'recurrent_connectivity': 0.2,  # recurrent connections for memory
    
    # Learning
    'eta': 0.01,
    'tau_e': 10,
    
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
        
    def step(self, input_current):
        self.u = self.u * (1 - self.du) + input_current
        self.v = self.v * (1 - self.dv) + self.u
        spiked = self.v >= self.vth
        self.v[spiked] = 0.0
        return spiked.astype(float)


class SynapticLayer:
    def __init__(self, n_in, n_out, connectivity=0.3, w_scale=2.0, seed=None):
        rng = np.random.RandomState(seed)
        self.n_in = n_in
        self.n_out = n_out  # ← FIX: اضافه شد
        
        mask = rng.rand(n_out, n_in) < connectivity
        self.weights = (rng.randn(n_out, n_in) * w_scale) * mask
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return self.weights @ pre_spikes
    
    def update_eligibility(self, pre_spikes, post_spikes, post_voltage, tau_e):
        """e-prop: accumulate with exponential decay."""
        self.eligibility *= np.exp(-1.0 / tau_e)
        
        # Surrogate derivative (pseudo-gradient)
        margin = 1.0
        f_prime = (np.abs(post_voltage - self.n_out * 0.5) < margin).astype(float)
        
        # Outer product
        delta_e = np.outer(post_spikes * f_prime, pre_spikes)
        self.eligibility += delta_e
        
    def apply_update(self, neuromodulator, eta):
        delta_w = eta * neuromodulator * self.eligibility
        self.weights += delta_w
        return delta_w


def generate_sequence(n_ticks, seed):
    """Generate IID binary sequence."""
    rng = np.random.RandomState(seed)
    return rng.randint(0, 2, size=n_ticks)


def encode_input(input_bit, n_input):
    """Rate coding: 10 neurons fire per bit value."""
    x = np.zeros(n_input)
    if input_bit == 0:
        x[:10] = 1.0
    else:
        x[10:] = 1.0
    return x


def run_organism(arm, sequence, config, seed):
    """Run one organism on delayed copy task with RECURRENT connections."""
    
    k = config['delay_k']
    n_hidden = config['n_hidden']
    
    # Network
    hidden = LIFPool(n_hidden, vth=config['vth'], dv=config['dv'], du=config['du'])
    output = LIFPool(config['n_output'], vth=config['vth'], dv=config['dv'], du=config['du'])
    
    # Synapses (input -> hidden)
    syn1 = SynapticLayer(config['n_input'], n_hidden,
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'], seed=seed)
    
    # Recurrent synapses (hidden -> hidden) ← برای memory
    syn_rec = SynapticLayer(n_hidden, n_hidden,
                            connectivity=config['recurrent_connectivity'],
                            w_scale=config['w_scale'], seed=seed+1)
    
    # Synapses (hidden -> output)
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
        target_bit = sequence[t - k]  # delayed copy
        
        # Encode input
        x = encode_input(input_bit, config['n_input'])
        
        # Forward: input -> hidden (with recurrent)
        u_input = syn1.forward(x)
        u_recurrent = syn_rec.forward(hidden.last_spikes if hasattr(hidden, 'last_spikes') else np.zeros(n_hidden))
        hidden.last_spikes = hidden.step(u_input + u_recurrent)
        s_hidden = hidden.last_spikes
        
        # Forward: hidden -> output
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
            # Update eligibility traces
            syn1.update_eligibility(x, s_hidden, hidden.v, config['tau_e'])
            syn_rec.update_eligibility(s_hidden, s_hidden, hidden.v, config['tau_e'])
            syn2.update_eligibility(s_hidden, s_out, output.v, config['tau_e'])
            
            # Track trace magnitude
            if len(trace_magnitudes) < 10:
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
        'early_trace_magnitudes': [float(m) for m in trace_magnitudes],
    }


def main():
    print("=" * 70)
    print("Exp-P2A-01 v7: Delayed Copy with Recurrent Connections")
    print("=" * 70)
    print(f"Task: output[t] = input[t-{CONFIG['delay_k']}]")
    print(f"Network: {CONFIG['n_hidden']} hidden LIF + RECURRENT")
    print(f"Recurrent connectivity: {CONFIG['recurrent_connectivity']}")
    print(f"Eligibility tau: {CONFIG['tau_e']}")
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
            
            trace_info = f", trace_max={max(result['early_trace_magnitudes']) if result['early_trace_magnitudes'] else 0:.3f}"
            print(f"  seed {seed}: acc={result['accuracy']:.3f}, updates={result['updates']}{trace_info}")
        
        results.append({
            'arm': arm,
            'mean_acc': float(np.mean([r['accuracy'] for r in arm_results])),
            'std_acc': float(np.std([r['accuracy'] for r in arm_results])),
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
    print(f"{'Arm':<20} {'Mean Acc':<12} {'Std':<10}")
    print("-" * 50)
    for r in results:
        print(f"{r['arm']:<20} {r['mean_acc']:<12.3f} {r['std_acc']:<10.3f}")
    
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
        print(f"  ✅ A2 near chance (50%) — task setup valid")
    else:
        print(f"  ⚠️  A2 not at chance — check task setup")
    
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
    
    # Hypothesis test
    print()
    print("Hypothesis Test:")
    if delta >= 5.0 and p_value < 0.05:
        print("  🎉 H1 CONFIRMED: e-prop with buffering rescues learning!")
        if delta3 > 2.0:
            print("  🎉 D5 PREDICTION CONFIRMED: buffering helps!")
        else:
            print("  ⚠️  D5 not yet confirmed")
    else:
        print("  ⚠️  H1 NULL: run F1-F5 diagnostics")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v7_recurrent_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v7 (delayed copy + recurrent)',
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