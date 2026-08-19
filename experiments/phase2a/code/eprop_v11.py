#!/usr/bin/env python
"""
Exp-P2A-01 v11: FIX Pre-Reset Voltage Tracking
===============================================
مشکل اصلی: post_voltage بعد از reset گرفته می‌شد.
Fix: pre_reset_voltage را ذخیره می‌کنیم.
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
    'n_input': 10,
    'n_hidden': 100,
    'n_output': 10,
    'vth': 1.0,
    'dv': 0.2,
    'du': 0.2,
    'w_scale': 1.5,
    'connectivity': 0.15,
    'recurrent_connectivity': 0.2,
    
    # Learning
    'eta': 0.01,
    'tau_e': 15,
    'surrogate_margin': 1.0,
    
    # Experiment
    'arms': ['A1_eprop', 'A2_nolearn', 'A3_stdp3c'],
    'n_seeds': 4,
    'random_seed': 42,
}

RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)


class LIFPool:
    """LIF with pre-reset voltage tracking."""
    
    def __init__(self, n, vth=1.0, dv=0.2, du=0.2):
        self.n = n
        self.vth = vth
        self.dv = dv
        self.du = du
        self.v = np.zeros(n)
        self.u = np.zeros(n)
        self.last_spikes = np.zeros(n)
        self.pre_reset_v = np.zeros(n)  # ← NEW: track voltage before reset
        
    def step(self, input_current):
        self.u = self.u * (1 - self.du) + input_current
        self.v = self.v * (1 - self.dv) + self.u
        
        # ← NEW: Store voltage BEFORE reset
        self.pre_reset_v = self.v.copy()
        
        # Spike detection
        spiked = self.v >= self.vth
        
        # Reset
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
    
    def update_eligibility(self, pre_spikes, post_spikes, pre_reset_voltage, tau_e, margin=1.0):
        """e-prop with CORRECT surrogate derivative (uses pre-reset voltage).
        
        f'(v) = max(0, 1 - |v_pre_reset - vth| / margin)
        
        When v_pre_reset >= vth (neuron spiked):
          f_prime = max(0, 1 - |v_pre_reset - vth| / margin)
                  = max(0, 1 - (v_pre_reset - vth) / margin)
        
        For v_pre_reset close to vth, f_prime is large.
        """
        # Decay
        self.eligibility *= np.exp(-1.0 / tau_e)
        
        # ← FIX: Use pre-reset voltage
        # For spiked neurons: v_pre_reset >= vth, so |v_pre_reset - vth| = v_pre_reset - vth
        f_prime = np.maximum(0, 1 - np.abs(pre_reset_voltage - self.vth) / margin)
        
        # Outer product: post[j] * f'(v_j) * pre[i]
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


def encode_input_pulse(pulse, n_input):
    x = np.zeros(n_input)
    if pulse == 1:
        x[:5] = 1.0
    return x


def run_organism(arm, input_pulses, targets, config, seed):
    """Run one organism with CORRECT pre-reset voltage tracking."""
    
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
    correct = 0
    total = 0
    total_updates = 0
    trace_magnitudes = []
    hidden_spike_counts = []
    output_spike_counts = []
    f_prime_samples = []  # track surrogate values
    
    for t in range(len(input_pulses)):
        pulse = input_pulses[t]
        
        # Encode input
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
        
        # Track f_prime samples (diagnostic)
        if len(f_prime_samples) < 100 and np.sum(s_out) > 0:
            # Compute f_prime for output layer
            fp = np.maximum(0, 1 - np.abs(output.pre_reset_v - config['vth']) / margin)
            f_prime_samples.append(fp.max())
        
        # Evaluation
        if t >= start_tick:
            target = targets[t]
            
            # ← FIX: Prediction از pre-reset voltage (نه spike count یا post-reset v)
            # Higher pre_reset_v in output[5:] than output[:5] means predict 1
            pred = int(output.pre_reset_v[5:].mean() > output.pre_reset_v[:5].mean())
            is_correct = (pred == target)
            
            if is_correct:
                correct += 1
            total += 1
            
            # Learning
            if arm in ['A1_eprop', 'A3_stdp3c']:
                # ← FIX: Pass pre_reset_voltage (not v)
                syn1.update_eligibility(x, s_hidden, hidden.pre_reset_v, config['tau_e'], margin)
                syn_rec.update_eligibility(s_hidden, s_hidden, hidden.pre_reset_v, config['tau_e'], margin)
                syn2.update_eligibility(s_hidden, s_out, output.pre_reset_v, config['tau_e'], margin)
                
                # Track trace
                trace_magnitudes.append(np.abs(syn2.eligibility).max())
                
                # Neuromodulator from error
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
        'trace_mean': float(np.mean(trace_magnitudes[-100:])) if trace_magnitudes else 0.0,
        'hidden_spike_rate': float(np.mean(hidden_spike_counts)),
        'output_spike_rate': float(np.mean(output_spike_counts)),
        'f_prime_max': float(max(f_prime_samples)) if f_prime_samples else 0.0,
    }


def main():
    print("=" * 70)
    print("Exp-P2A-01 v11: FIXED Pre-Reset Voltage Tracking")
    print("=" * 70)
    print(f"Task: output[t] = input[t-{CONFIG['T1']}] XOR input[t-{CONFIG['T2']}]")
    print(f"Network: {CONFIG['n_hidden']} hidden, {CONFIG['n_output']} output")
    print(f"FIX: use pre_reset_voltage for surrogate derivative")
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
                  f"f_prime={result['f_prime_max']:.3f}, "
                  f"hid={result['hidden_spike_rate']:.1f}")
        
        results.append({
            'arm': arm,
            'mean_acc': float(np.mean([r['accuracy'] for r in arm_results])),
            'std_acc': float(np.std([r['accuracy'] for r in arm_results])),
            'mean_trace': float(np.mean([r['trace_max'] for r in arm_results])),
            'mean_f_prime': float(np.mean([r['f_prime_max'] for r in arm_results])),
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
    print(f"{'Arm':<20} {'Acc':<8} {'Trace':<10} {'f_prime':<10} {'Hid Rate':<10}")
    print("-" * 70)
    for r in results:
        print(f"{r['arm']:<20} {r['mean_acc']:<8.3f} "
              f"{r['mean_trace']:<10.4f} "
              f"{r['mean_f_prime']:<10.3f} "
              f"{r['mean_hidden_rate']:<10.1f}")
    
    # Diagnostics
    print()
    print("Critical Diagnostic: Surrogate Derivative (f_prime):")
    print("-" * 50)
    print(f"  A1 mean f_prime max: {a1['mean_f_prime']:.3f}")
    if a1['mean_f_prime'] > 0.01:
        print(f"  ✅ f_prime is NON-ZERO (surrogate working)")
    else:
        print(f"  ❌ f_prime still ≈ 0 (surrogate broken)")
    
    print()
    print("Diagnostic (Opus check #1): eligibility_trace > 0?")
    if a1['mean_trace'] > 0.001:
        print(f"  ✅ A1 trace_max = {a1['mean_trace']:.4f} > 0")
        print(f"     🎉 ELIGIBILITY TRACES FINALLY WORK!")
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
        if a1['mean_acc'] > 0.60:
            print("  🎉 STRONG: accuracy > 60% (Bellec-like performance)")
        if delta3 > 2.0:
            print("  🎉 D5 PREDICTION CONFIRMED!")
    elif a1['mean_trace'] > 0.001:
        print("  📊 Eligibility traces now work, but learning not yet visible")
        print("     → Check credit assignment and neuromodulator timing")
        print("     → May need longer training or larger learning rate")
    else:
        print("  ⚠️  H1 NULL — need more debugging")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v11_prereset_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v11 (pre-reset voltage fix)',
        'config': CONFIG,
        'results': results,
        'delta_a1_a2': float(delta),
        'delta_a1_a3': float(delta3),
        'p_value': float(p_value),
        'h1_confirmed': bool(delta >= 5.0 and p_value < 0.05),
        'key_fix': 'pre_reset_voltage tracking for surrogate derivative',
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    print("=" * 70)


if __name__ == '__main__':
    main()