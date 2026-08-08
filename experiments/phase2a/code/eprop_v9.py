#!/usr/bin/env python
"""
Exp-P2A-01 v9: Temporal XOR Benchmark (Bellec et al. 2020)
==========================================================
این task در paper اصلی e-prop استفاده شده.
اگر e-prop ما روی این task کار نکند، قطعاً implementation مشکل دارد.

Task:
- هر tick، input pulse (0 یا 1) دریافت می‌کنیم
- output باید XOR(input[t-T1], input[t-T2]) باشد
- در paper: T1=15, T2=30 (طولانی)
- برای simplicity: T1=3, T2=6 (کوتاه‌تر)

Reference: Bellec et al. 2020, "A solution to the learning dilemma 
           for recurrent networks of spiking neurons", Nature Communications
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    # Task (Bellec 2020 style)
    'n_ticks': 1000,
    'T1': 3,       # first delay
    'T2': 6,       # second delay
    'pulse_prob': 0.3,  # probability of input pulse per tick
    
    # Network (Bellec 2020 style: ~100 neurons)
    'n_input': 1,
    'n_hidden': 100,
    'n_output': 1,  # XOR output: single binary
    'vth': 1.0,
    'dv': 0.2,  # slower decay for longer memory
    'du': 0.2,
    'w_scale': 1.0,
    'connectivity': 0.1,
    'recurrent_connectivity': 0.2,
    
    # Learning
    'eta': 0.005,
    'tau_e': 15,  # eligibility decay (must exceed T2=6)
    'surrogate_margin': 0.5,
    
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
    def __init__(self, n_in, n_out, connectivity=0.1, w_scale=1.0, seed=None):
        rng = np.random.RandomState(seed)
        self.n_in = n_in
        self.n_out = n_out
        self.vth = 1.0
        
        mask = rng.rand(n_out, n_in) < connectivity
        self.weights = (rng.randn(n_out, n_in) * w_scale) * mask
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return self.weights @ pre_spikes
    
    def update_eligibility(self, pre_spikes, post_spikes, post_voltage, tau_e, margin=0.5):
        self.eligibility *= np.exp(-1.0 / tau_e)
        f_prime = np.maximum(0, 1 - np.abs(post_voltage - self.vth) / margin)
        delta_e = np.outer(post_spikes * f_prime, pre_spikes)
        self.eligibility += delta_e
        
    def apply_update(self, neuromodulator, eta):
        delta_w = eta * neuromodulator * self.eligibility
        self.weights += delta_w
        return delta_w


def generate_temporal_xor(n_ticks, T1, T2, pulse_prob, seed):
    """Generate Temporal XOR task (Bellec 2020 style)."""
    rng = np.random.RandomState(seed)
    
    # Input pulses (sparse)
    input_pulses = (rng.rand(n_ticks) < pulse_prob).astype(int)
    
    # Output: XOR of input at t-T1 and t-T2
    target = np.zeros(n_ticks, dtype=int)
    for t in range(max(T1, T2), n_ticks):
        target[t] = input_pulses[t - T1] ^ input_pulses[t - T2]
    
    return input_pulses, target


def run_organism(arm, input_pulses, targets, config, seed):
    """Run one organism on Temporal XOR task."""
    
    T1 = config['T1']
    T2 = config['T2']
    start_tick = max(T1, T2)
    n_hidden = config['n_hidden']
    margin = config['surrogate_margin']
    
    # Network
    hidden = LIFPool(n_hidden, vth=config['vth'], dv=config['dv'], du=config['du'])
    output = LIFPool(1, vth=config['vth'], dv=config['dv'], du=config['du'])  # single output neuron
    
    # Synapses
    syn1 = SynapticLayer(1, n_hidden,
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'], seed=seed)
    syn_rec = SynapticLayer(n_hidden, n_hidden,
                            connectivity=config['recurrent_connectivity'],
                            w_scale=config['w_scale'], seed=seed+1)
    syn2 = SynapticLayer(n_hidden, 1,
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'], seed=seed+2)
    
    # State
    correct = 0
    total = 0
    total_updates = 0
    trace_magnitudes = []
    
    # For prediction: use voltage (higher = predict 1)
    for t in range(len(input_pulses)):
        pulse = input_pulses[t]
        
        # Encode: spike if pulse
        x = np.array([float(pulse)])
        
        # Forward with recurrent
        u_input = syn1.forward(x)
        u_recurrent = syn_rec.forward(hidden.last_spikes)
        s_hidden = hidden.step(u_input + u_recurrent)
        
        u_out = syn2.forward(s_hidden)
        s_out = output.step(u_out)
        
        # Evaluation (only after T2)
        if t >= start_tick:
            target = targets[t]
            
            # Prediction: output voltage above threshold = predict 1
            pred = int(output.v[0] >= config['vth'] * 0.7)  # threshold for prediction
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
                
                # Track trace
                if len(trace_magnitudes) < 50:
                    trace_magnitudes.append(np.abs(syn2.eligibility).max())
                
                # Neuromodulator from error
                target_spikes = np.array([float(target)])
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
    }


def main():
    print("=" * 70)
    print("Exp-P2A-01 v9: Temporal XOR Benchmark (Bellec 2020)")
    print("=" * 70)
    print(f"Task: output[t] = input[t-{CONFIG['T1']}] XOR input[t-{CONFIG['T2']}]")
    print(f"Network: {CONFIG['n_hidden']} hidden LIF + recurrent")
    print(f"Pulse prob: {CONFIG['pulse_prob']}")
    print(f"Eligibility tau: {CONFIG['tau_e']}")
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
    
    # Bellec baseline: آنها ~80% accuracy گرفتند
    print()
    print("Bellec 2020 reference:")
    print(f"  Expected: ~80% (Bellec et al. 2020 on similar task)")
    print(f"  Our A1:   {a1['mean_acc']:.3f}")
    
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
    print("Sanity check:")
    a2_acc = a2['mean_acc']
    print(f"  A2 (nolearn) accuracy: {a2_acc:.3f}")
    # در XOR random، 50% baseline است
    if 0.45 <= a2_acc <= 0.55:
        print(f"  ✅ A2 near chance (50%) — baseline valid")
    else:
        print(f"  ⚠️  A2 not at chance (task may have structure)")
    
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
        print("  🎉 H1 CONFIRMED: e-prop learns on Bellec benchmark!")
        if a1['mean_acc'] > 0.60:
            print("  🎉 STRONG: accuracy > 60% (meaningful learning)")
        if delta3 > 2.0:
            print("  🎉 D5 PREDICTION CONFIRMED!")
    else:
        print("  ⚠️  H1 NULL on Bellec benchmark")
        if a1['mean_trace'] > 0.001:
            print("  → Eligibility traces work but credit assignment fails")
            print("  → Need deeper e-prop debugging")
        else:
            print("  → Eligibility traces still broken")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v9_temporal_xor_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v9 (Temporal XOR benchmark)',
        'config': CONFIG,
        'results': results,
        'delta_a1_a2': float(delta),
        'delta_a1_a3': float(delta3),
        'p_value': float(p_value),
        'h1_confirmed': bool(delta >= 5.0 and p_value < 0.05),
        'bellec_reference': '~80% (Bellec et al. 2020)',
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    print("=" * 70)


if __name__ == '__main__':
    main()