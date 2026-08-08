#!/usr/bin/env python
"""
Exp-P2A-01 v10: Temporal XOR با Input Encoding قوی‌تر
======================================================
Fixes:
1. Input encoding: rate coding (10 neurons)
2. Trace tracking: کل experiment (نه فقط 50 اول)
3. Activity diagnostics: hidden/output spike rates
4. Surrogate margin تنظیم
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    # Task (Bellec 2020 style)
    'n_ticks': 1000,
    'T1': 3,
    'T2': 6,
    'pulse_prob': 0.3,
    
    # Network
    'n_input': 10,      # ← FIX: more input neurons
    'n_hidden': 100,
    'n_output': 10,     # ← FIX: more output neurons
    'vth': 1.0,
    'dv': 0.2,
    'du': 0.2,
    'w_scale': 1.5,
    'connectivity': 0.15,
    'recurrent_connectivity': 0.2,
    
    # Learning
    'eta': 0.01,
    'tau_e': 15,
    'surrogate_margin': 1.0,  # ← FIX: wider margin
    
    # Experiment
    'arms': ['A1_eprop', 'A2_nolearn', 'A3_stdp3c'],
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
        
    def step(self, input_current):
        self.u = self.u * (1 - self.du) + input_current
        self.v = self.v * (1 - self.dv) + self.u
        spiked = self.v >= self.vth
        self.v[spiked] = 0.0
        self.last_spikes = spiked.astype(float)
        return self.last_spikes


class SynapticLayer:
    def __init__(self, n_in, n_out, connectivity=0.15, w_scale=1.5, vth=1.0, seed=None):
        rng = np.random.RandomState(seed)
        self.n_in = n_in
        self.n_out = n_out
        self.vth = vth
        
        mask = rng.rand(n_out, n_in) < connectivity
        self.weights = (rng.randn(n_out, n_in) * w_scale) * mask
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return self.weights @ pre_spikes
    
    def update_eligibility(self, pre_spikes, post_spikes, post_voltage, tau_e, margin=1.0):
        """e-prop eligibility with robust surrogate."""
        self.eligibility *= np.exp(-1.0 / tau_e)
        
        # Surrogate derivative: non-zero near threshold
        f_prime = np.maximum(0, 1 - np.abs(post_voltage - self.vth) / margin)
        
        # Outer product
        delta_e = np.outer(post_spikes * f_prime, pre_spikes)
        self.eligibility += delta_e
        
    def apply_update(self, neuromodulator, eta):
        delta_w = eta * neuromodulator * self.eligibility
        self.weights += delta_w
        return delta_w


def generate_temporal_xor(n_ticks, T1, T2, pulse_prob, seed):
    """Generate Temporal XOR task."""
    rng = np.random.RandomState(seed)
    
    # Input pulses
    input_pulses = (rng.rand(n_ticks) < pulse_prob).astype(int)
    
    # Output: XOR
    target = np.zeros(n_ticks, dtype=int)
    for t in range(max(T1, T2), n_ticks):
        target[t] = input_pulses[t - T1] ^ input_pulses[t - T2]
    
    return input_pulses, target


def encode_input_pulse(pulse, n_input):
    """Encode pulse: first 5 neurons fire if pulse=1, else silence."""
    x = np.zeros(n_input)
    if pulse == 1:
        x[:5] = 1.0  # 5 neurons fire
    return x


def run_organism(arm, input_pulses, targets, config, seed):
    """Run one organism with robust tracking."""
    
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
    
    # State tracking
    correct = 0
    total = 0
    total_updates = 0
    trace_magnitudes = []  # ← track ALL ticks
    hidden_spike_counts = []
    output_spike_counts = []
    
    for t in range(len(input_pulses)):
        pulse = input_pulses[t]
        
        # Encode input (stronger)
        x = encode_input_pulse(pulse, config['n_input'])
        
        # Forward with recurrent
        u_input = syn1.forward(x)
        u_recurrent = syn_rec.forward(hidden.last_spikes)
        s_hidden = hidden.step(u_input + u_recurrent)
        
        u_out = syn2.forward(s_hidden)
        s_out = output.step(u_out)
        
        # Track activity
        hidden_spike_counts.append(np.sum(s_hidden))
        output_spike_counts.append(np.sum(s_out))
        
        # Evaluation (after T2)
        if t >= start_tick:
            target = targets[t]
            
            # Prediction: majority vote from output neurons
            # First 5 neurons = predict 0, last 5 = predict 1
            pred_0_votes = np.sum(s_out[:5])
            pred_1_votes = np.sum(s_out[5:])
            
            # If no spikes, use voltage
            if pred_0_votes + pred_1_votes == 0:
                pred = int(output.v[5:].mean() > output.v[:5].mean())
            else:
                pred = int(pred_1_votes > pred_0_votes)
            
            is_correct = (pred == target)
            
            if is_correct:
                correct += 1
            total += 1
            
            # Learning
            if arm in ['A1_eprop', 'A3_stdp3c']:
                # Update eligibility
                syn1.update_eligibility(x, s_hidden, hidden.v, config['tau_e'], margin)
                syn_rec.update_eligibility(s_hidden, s_hidden, hidden.v, config['tau_e'], margin)
                syn2.update_eligibility(s_hidden, s_out, output.v, config['tau_e'], margin)
                
                # Track trace (ALL ticks, not just first 50)
                trace_magnitudes.append(np.abs(syn2.eligibility).max())
                
                # Neuromodulator from error
                # Target: first 5 neurons for 0, last 5 for 1
                target_spikes = np.zeros(config['n_output'])
                if target == 1:
                    target_spikes[5:] = 1.0
                else:
                    target_spikes[:5] = 1.0
                
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
        'trace_max': float(max(trace_magnitudes)) if trace_magnitudes else 0.0,
        'trace_mean': float(np.mean(trace_magnitudes)) if trace_magnitudes else 0.0,
        'hidden_spike_rate': float(np.mean(hidden_spike_counts)),
        'output_spike_rate': float(np.mean(output_spike_counts)),
    }


def main():
    print("=" * 70)
    print("Exp-P2A-01 v10: Temporal XOR with Robust Tracking")
    print("=" * 70)
    print(f"Task: output[t] = input[t-{CONFIG['T1']}] XOR input[t-{CONFIG['T2']}]")
    print(f"Network: {CONFIG['n_hidden']} hidden, {CONFIG['n_output']} output")
    print(f"Input encoding: rate coding (5 neurons per pulse)")
    print(f"Surrogate margin: {CONFIG['surrogate_margin']}")
    print(f"Seeds: {CONFIG['n_seeds']} per arm")
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
            
            print(f"  seed {seed}: acc={result['accuracy']:.3f}, "
                  f"trace_max={result['trace_max']:.4f}, "
                  f"hidden_rate={result['hidden_spike_rate']:.2f}, "
                  f"out_rate={result['output_spike_rate']:.2f}")
        
        results.append({
            'arm': arm,
            'mean_acc': float(np.mean([r['accuracy'] for r in arm_results])),
            'std_acc': float(np.std([r['accuracy'] for r in arm_results])),
            'mean_trace': float(np.mean([r['trace_max'] for r in arm_results])),
            'mean_hidden_rate': float(np.mean([r['hidden_spike_rate'] for r in arm_results])),
            'mean_output_rate': float(np.mean([r['output_spike_rate'] for r in arm_results])),
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
    print(f"{'Arm':<20} {'Acc':<8} {'Trace':<10} {'Hid Rate':<10} {'Out Rate':<10}")
    print("-" * 65)
    for r in results:
        print(f"{r['arm']:<20} {r['mean_acc']:<8.3f} "
              f"{r['mean_trace']:<10.4f} "
              f"{r['mean_hidden_rate']:<10.2f} "
              f"{r['mean_output_rate']:<10.2f}")
    
    # Diagnostics
    print()
    print("Activity Diagnostics:")
    print("-" * 50)
    print(f"  Hidden spike rate: {a1['mean_hidden_rate']:.2f} per tick")
    print(f"  Output spike rate: {a1['mean_output_rate']:.2f} per tick")
    
    if a1['mean_hidden_rate'] < 1.0:
        print(f"  ⚠️  Hidden activity VERY LOW — network not active enough")
    elif a1['mean_output_rate'] < 0.5:
        print(f"  ⚠️  Output activity LOW — hard to make predictions")
    else:
        print(f"  ✅ Activity levels reasonable")
    
    print()
    print("Diagnostic (Opus check #1): eligibility_trace > 0?")
    if a1['mean_trace'] > 0.001:
        print(f"  ✅ A1 trace_max = {a1['mean_trace']:.4f} > 0")
    else:
        print(f"  ❌ A1 trace_max = {a1['mean_trace']:.4f} ≈ 0")
    
    print()
    print("Gate A (delta >= +5pp):")
    delta = (a1['mean_acc'] - a2['mean_acc']) * 100
    print(f"  A1 vs A2 = {delta:+.2f} pp")
    print(f"  Result: {'✅ PASS' if delta >= 5.0 else '❌ FAIL'}")
    
    print()
    print("D5 prediction check:")
    delta3 = (a1['mean_acc'] - a3['mean_acc']) * 100
    print(f"  A1 vs A3 = {delta3:+.2f} pp")
    
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
    
    # Hypothesis
    print()
    print("Hypothesis Test:")
    if delta >= 5.0 and p_value < 0.05:
        print("  🎉 H1 CONFIRMED: e-prop learns on Temporal XOR!")
        if delta3 > 2.0:
            print("  🎉 D5 PREDICTION CONFIRMED!")
    else:
        print("  ⚠️  H1 NULL")
        if a1['mean_trace'] < 0.001:
            print("  → Eligibility traces still broken")
        elif a1['mean_hidden_rate'] < 1.0:
            print("  → Network not active enough")
        else:
            print("  → Credit assignment issue")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v10_robust_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v10 (robust tracking + stronger input)',
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