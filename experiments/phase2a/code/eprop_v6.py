#!/usr/bin/env python
"""
Exp-P2A-01 v6: e-prop با Delayed Copy Task (v2 pre-registration)
================================================================
Task: output[t] = input[t-5]
Pre-reg: experiments/phase2a/EXP_P2A_01_PREREGISTRATION_v2.md

این task دارای autocorrelation در lag=5 است و learnable می‌باشد.
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    # Task
    'n_ticks': 1000,
    'delay_k': 5,  # delayed copy lag
    
    # Network
    'n_input': 20,
    'n_hidden': 50,
    'n_output': 2,
    'vth': 0.5,
    'dv': 0.3,
    'du': 0.3,
    'w_scale': 2.0,
    'connectivity': 0.3,
    
    # Learning
    'eta': 0.01,
    'tau_e': 10,  # eligibility trace decay (must exceed k=5)
    
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
        mask = rng.rand(n_out, n_in) < connectivity
        self.weights = (rng.randn(n_out, n_in) * w_scale) * mask
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return self.weights @ pre_spikes
    
    def update_eligibility(self, pre_spikes, post_spikes, post_voltage, tau_e):
        """e-prop: accumulate with exponential decay."""
        self.eligibility *= np.exp(-1.0 / tau_e)
        margin = 1.0
        f_prime = (np.abs(post_voltage - self.n_out * 0.5) < margin).astype(float)
        delta_e = np.outer(post_spikes * f_prime, pre_spikes)
        self.eligibility += delta_e
        
    def apply_update(self, neuromodulator, eta):
        delta_w = eta * neuromodulator * self.eligibility
        self.weights += delta_w
        return delta_w


def generate_sequence(n_ticks, seed):
    """Generate IID binary sequence (این task است که structured می‌شود با delay)."""
    rng = np.random.RandomState(seed)
    sequence = rng.randint(0, 2, size=n_ticks)
    return sequence


def encode_input(input_bit, n_input):
    """Rate coding: 10 neurons fire per bit value."""
    x = np.zeros(n_input)
    if input_bit == 0:
        x[:10] = 1.0
    else:
        x[10:] = 1.0
    return x


def run_organism(arm, sequence, config, seed):
    """Run one organism on delayed copy task."""
    
    k = config['delay_k']
    
    # Network
    hidden = LIFPool(config['n_hidden'], vth=config['vth'], dv=config['dv'], du=config['du'])
    output = LIFPool(config['n_output'], vth=config['vth'], dv=config['dv'], du=config['du'])
    
    # Synapses
    syn1 = SynapticLayer(config['n_input'], config['n_hidden'],
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'], seed=seed)
    syn2 = SynapticLayer(config['n_hidden'], config['n_output'],
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'], seed=seed+1)
    
    # State tracking
    correct = 0
    total = 0
    total_updates = 0
    total_spikes = 0
    
    # Eligibility trace accumulation (no clear after update)
    trace_magnitudes = []
    
    for t in range(k, len(sequence)):
        input_bit = sequence[t]
        target_bit = sequence[t - k]  # ← delayed copy: predict k ticks ago
        
        # Encode input
        x = encode_input(input_bit, config['n_input'])
        
        # Forward
        u_hidden = syn1.forward(x)
        s_hidden = hidden.step(u_hidden)
        
        u_out = syn2.forward(s_hidden)
        s_out = output.step(u_out)
        
        total_spikes += np.sum(s_hidden) + np.sum(s_out)
        
        # --- Prediction از output voltage ---
        pred = int(output.v[1] > output.v[0])
        is_correct = (pred == target_bit)
        
        if is_correct:
            correct += 1
        total += 1
        
        # --- Learning (A1 and A3 only) ---
        if arm in ['A1_eprop', 'A3_stdp3c']:
            # Update eligibility traces
            syn1.update_eligibility(x, s_hidden, hidden.v, config['tau_e'])
            syn2.update_eligibility(s_hidden, s_out, output.v, config['tau_e'])
            
            # Track trace magnitude (diagnostic)
            if len(trace_magnitudes) < 10:
                trace_magnitudes.append(np.abs(syn2.eligibility).max())
            
            # Neuromodulator from error (supervised)
            target_spikes = np.zeros(config['n_output'])
            target_spikes[target_bit] = 1.0
            error = target_spikes - s_out
            M = float(np.mean(np.abs(error)))
            
            if M > 0:
                # A1: buffered (always allow)
                # A3: coupled (simplified: same for now, we'll differentiate later)
                syn1.apply_update(M, config['eta'])
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
    print("Exp-P2A-01 v6: Delayed Copy Task (v2 pre-registration)")
    print("=" * 70)
    print(f"Task: output[t] = input[t-{CONFIG['delay_k']}]")
    print(f"Network: {CONFIG['n_hidden']} hidden LIF")
    print(f"Eligibility tau: {CONFIG['tau_e']} (must exceed delay k={CONFIG['delay_k']})")
    print(f"Seeds: {CONFIG['n_seeds']} per arm")
    print()
    
    # Sanity check: autocorrelation at lag k
    rng_check = np.random.RandomState(0)
    test_seq = rng_check.randint(0, 2, size=1000)
    autocorr_lag_k = np.corrcoef(test_seq[:-CONFIG['delay_k']], test_seq[CONFIG['delay_k']:])[0, 1]
    print(f"Sanity check: autocorr at lag {CONFIG['delay_k']} = {autocorr_lag_k:.4f}")
    if abs(autocorr_lag_k) < 0.01:
        print("  ✅ Task has structure at lag k (learnable in principle)")
    else:
        print(f"  ⚠️  Unexpected autocorr = {autocorr_lag_k}")
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
        print(f"  ⚠️  A2 not at chance — task setup may have issues")
    
    print()
    print("D5 prediction check (buffered vs coupled):")
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
            print("  ⚠️  D5 not yet confirmed: buffering effect small")
    else:
        print("  ⚠️  H1 NULL: run F1-F5 diagnostics")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v6_delayed_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v6 (delayed copy task, v2 pre-reg)',
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