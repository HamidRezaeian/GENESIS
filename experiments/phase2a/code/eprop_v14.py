#!/usr/bin/env python
"""
Exp-P2A-01 v14: Numerical Stability Fixes
==========================================
مشکلات v13:
1. Overflow در surrogate derivative
2. Overflow در matmul (weights explode)
3. Invalid values (NaN/Inf)

Fixes:
1. Clip weights بعد از هر update
2. Clip learning signal
3. Stable surrogate derivative
4. Smaller weight initialization
5. Gradient clipping
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    # Task
    'n_ticks': 2000,
    'T1': 3,
    'T2': 6,
    'pulse_prob': 0.3,
    
    # Network
    'n_input': 30,
    'n_hidden': 100,
    'n_output': 2,
    
    # LIF dynamics
    'theta': 0.6,
    'tau_m': 20.0,
    'dv': 1.0 / 20.0,
    'du': 1.0 / 20.0,
    
    # Output
    'tau_out': 20.0,
    
    # Synaptic (smaller initialization)
    'w_scale': 0.1,  # ← Much smaller!
    'connectivity': 0.2,
    'recurrent_connectivity': 0.2,
    
    # Learning
    'eta': 0.001,
    'tau_e': 20.0,
    'beta': 10.0,
    
    # Stability
    'max_weight': 5.0,       # ← Clip weights
    'max_grad': 1.0,         # ← Clip gradients
    'max_learning_signal': 1.0,  # ← Clip L
    
    # Experiment
    'arms': ['A1_eprop', 'A2_nolearn', 'A3_stdp3c'],
    'n_seeds': 4,
    'random_seed': 42,
}

RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)


class LIFPool:
    def __init__(self, n, theta=0.6, dv=0.05, du=0.05):
        self.n = n
        self.theta = theta
        self.dv = dv
        self.du = du
        self.v = np.zeros(n)
        self.u = np.zeros(n)
        self.last_spikes = np.zeros(n)
        self.pre_reset_v = np.zeros(n)
        
    def step(self, input_current):
        # Clip input current to prevent overflow
        input_current = np.clip(input_current, -10, 10)
        
        self.u = self.u * (1 - self.du) + input_current
        self.v = self.v * (1 - self.dv) + self.u
        
        # Clip voltage to prevent overflow
        self.v = np.clip(self.v, -5, 5)
        
        self.pre_reset_v = self.v.copy()
        
        spiked = self.v >= self.theta
        self.v[spiked] = 0.0
        self.last_spikes = spiked.astype(float)
        
        return self.last_spikes
    
    def surrogate_derivative(self):
        """Stable surrogate: f'(v) = 1 / (1 + beta * |v - theta|)^2
        
        With clipping to prevent overflow.
        """
        beta = CONFIG['beta']
        diff = np.abs(self.pre_reset_v - self.theta)
        
        # Clip diff to prevent overflow
        diff = np.clip(diff, 0, 10)
        
        # Compute safely
        denominator = 1.0 + beta * diff
        f_prime = 1.0 / (denominator ** 2)
        
        # Clip to [0, 1]
        f_prime = np.clip(f_prime, 0, 1)
        
        return f_prime


class OutputLayer:
    def __init__(self, n, tau_out=20.0):
        self.n = n
        self.tau_out = tau_out
        self.r = np.zeros(n)
        
    def step(self, spikes):
        self.r = self.r * (1 - 1/self.tau_out) + spikes
        # Clip to prevent overflow
        self.r = np.clip(self.r, 0, 5)
        return self.r


class SynapticLayer:
    def __init__(self, n_in, n_out, connectivity=0.2, w_scale=0.1, seed=None):
        rng = np.random.RandomState(seed)
        self.n_in = n_in
        self.n_out = n_out
        
        mask = rng.rand(n_out, n_in) < connectivity
        # Smaller initialization
        self.weights = (rng.randn(n_out, n_in) * w_scale) * mask
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        result = self.weights @ pre_spikes
        # Clip to prevent overflow
        return np.clip(result, -10, 10)
    
    def update_eligibility(self, pre_spikes, post_f_prime, tau_e):
        self.eligibility *= np.exp(-1.0 / tau_e)
        
        # Clip f_prime to prevent overflow
        post_f_prime = np.clip(post_f_prime, 0, 1)
        
        delta_e = np.outer(post_f_prime, pre_spikes)
        self.eligibility += delta_e
        
        # Clip eligibility to prevent overflow
        self.eligibility = np.clip(self.eligibility, -5, 5)
        
    def apply_update(self, learning_signal, eta, max_weight=5.0, max_grad=1.0):
        """Weight update with gradient clipping."""
        # Clip learning signal
        learning_signal = np.clip(learning_signal, -max_grad, max_grad)
        
        # Compute update
        delta_w = eta * np.outer(learning_signal, np.ones(self.n_in)) * self.eligibility
        
        # Clip gradient
        delta_w = np.clip(delta_w, -max_grad, max_grad)
        
        # Apply
        self.weights += delta_w
        
        # Clip weights to prevent explosion
        self.weights = np.clip(self.weights, -max_weight, max_weight)
        
        return delta_w


def generate_temporal_xor(n_ticks, T1, T2, pulse_prob, seed):
    rng = np.random.RandomState(seed)
    input_pulses = (rng.rand(n_ticks) < pulse_prob).astype(int)
    target = np.zeros(n_ticks, dtype=int)
    for t in range(max(T1, T2), n_ticks):
        target[t] = input_pulses[t - T1] ^ input_pulses[t - T2]
    return input_pulses, target


def encode_input(pulse, input_t3, n_input):
    x = np.zeros(n_input)
    if pulse == 1:
        x[:5] = 1.0
    if input_t3 == 1:
        x[10:15] = 1.0
    return x


def balanced_accuracy(predictions, targets):
    pos_mask = (targets == 1)
    neg_mask = (targets == 0)
    
    tpr = np.mean(predictions[pos_mask] == 1) if np.sum(pos_mask) > 0 else 0.0
    tnr = np.mean(predictions[neg_mask] == 0) if np.sum(neg_mask) > 0 else 0.0
    
    return (tpr + tnr) / 2


def run_organism(arm, input_pulses, targets, config, seed):
    """Run with numerical stability."""
    
    T1 = config['T1']
    T2 = config['T2']
    start_tick = max(T1, T2)
    n_hidden = config['n_hidden']
    n_output = config['n_output']
    tau_e = config['tau_e']
    eta = config['eta']
    
    # Network
    hidden = LIFPool(n_hidden, theta=config['theta'], dv=config['dv'], du=config['du'])
    output_layer = OutputLayer(n_output, tau_out=config['tau_out'])
    
    # Synapses (smaller initialization)
    syn_in = SynapticLayer(config['n_input'], n_hidden,
                           connectivity=config['connectivity'],
                           w_scale=config['w_scale'], seed=seed)
    syn_rec = SynapticLayer(n_hidden, n_hidden,
                            connectivity=config['recurrent_connectivity'],
                            w_scale=config['w_scale'], seed=seed+1)
    syn_out = SynapticLayer(n_hidden, n_output,
                            connectivity=config['connectivity'],
                            w_scale=config['w_scale'], seed=seed+2)
    
    # State
    all_predictions = []
    all_targets = []
    total_updates = 0
    
    for t in range(len(input_pulses)):
        pulse = input_pulses[t]
        input_t3 = input_pulses[t - T1] if t >= T1 else 0
        
        x = encode_input(pulse, input_t3, config['n_input'])
        
        # Forward
        u_in = syn_in.forward(x)
        u_rec = syn_rec.forward(hidden.last_spikes)
        s_hidden = hidden.step(u_in + u_rec)
        
        u_out = syn_out.forward(s_hidden)
        r_out = output_layer.step(u_out)
        
        pred = int(r_out[1] > r_out[0])
        
        if t >= start_tick:
            target = targets[t]
            
            all_predictions.append(pred)
            all_targets.append(target)
            
            if arm in ['A1_eprop', 'A3_stdp3c']:
                # Error
                target_vec = np.zeros(n_output)
                target_vec[target] = 1.0
                y = r_out
                error = y - target_vec
                
                # Clip error
                error = np.clip(error, -1, 1)
                
                # Learning signal: L_j = W_out^T @ error
                L_hidden = syn_out.weights.T @ error
                
                # Clip learning signal
                L_hidden = np.clip(L_hidden, -config['max_learning_signal'], 
                                   config['max_learning_signal'])
                
                # Eligibility
                f_prime_hidden = hidden.surrogate_derivative()
                
                syn_in.update_eligibility(x, f_prime_hidden, tau_e)
                syn_rec.update_eligibility(hidden.last_spikes, f_prime_hidden, tau_e)
                
                # Weight updates with clipping
                syn_in.apply_update(L_hidden, eta, 
                                    config['max_weight'], config['max_grad'])
                syn_rec.apply_update(L_hidden, eta,
                                     config['max_weight'], config['max_grad'])
                
                # Output layer update
                delta_out = eta * np.outer(error, s_hidden)
                delta_out = np.clip(delta_out, -config['max_grad'], config['max_grad'])
                syn_out.weights += delta_out
                syn_out.weights = np.clip(syn_out.weights, 
                                          -config['max_weight'], config['max_weight'])
                
                total_updates += 1
    
    predictions = np.array(all_predictions)
    targets_arr = np.array(all_targets)
    
    bal_acc = balanced_accuracy(predictions, targets_arr)
    reg_acc = np.mean(predictions == targets_arr)
    
    return {
        'arm': arm,
        'seed': seed,
        'balanced_accuracy': float(bal_acc),
        'regular_accuracy': float(reg_acc),
        'updates': int(total_updates),
    }


def main():
    print("=" * 70)
    print("Exp-P2A-01 v14: Numerical Stability Fixes")
    print("=" * 70)
    print(f"Task: output[t] = input[t-{CONFIG['T1']}] XOR input[t-{CONFIG['T2']}]")
    print(f"Network: {CONFIG['n_hidden']} hidden LIF")
    print(f"Stability: weight clipping, gradient clipping, stable surrogate")
    print(f"eta = {CONFIG['eta']}, w_scale = {CONFIG['w_scale']}")
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
            
            print(f"  seed {seed}: bal_acc={result['balanced_accuracy']:.3f}, "
                  f"reg_acc={result['regular_accuracy']:.3f}")
        
        results.append({
            'arm': arm,
            'mean_bal_acc': float(np.mean([r['balanced_accuracy'] for r in arm_results])),
            'mean_reg_acc': float(np.mean([r['regular_accuracy'] for r in arm_results])),
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
    print(f"{'Arm':<20} {'Bal Acc':<12} {'Reg Acc':<12}")
    print("-" * 50)
    for r in results:
        print(f"{r['arm']:<20} {r['mean_bal_acc']:<12.3f} {r['mean_reg_acc']:<12.3f}")
    
    print()
    print("Gate A (delta >= +5pp):")
    delta = (a1['mean_bal_acc'] - a2['mean_bal_acc']) * 100
    print(f"  A1 vs A2 = {delta:+.2f} pp")
    print(f"  Result: {'✅ PASS' if delta >= 5.0 else '❌ FAIL'}")
    
    print()
    print("D5 prediction check:")
    delta3 = (a1['mean_bal_acc'] - a3['mean_bal_acc']) * 100
    print(f"  A1 vs A3 = {delta3:+.2f} pp")
    
    # Permutation test
    print()
    print("Permutation test (A1 vs A2):")
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
    else:
        print("  ⚠️  H1 NULL")
        if a1['mean_bal_acc'] > 0.50:
            print("  → Learning direction correct but weak")
        else:
            print("  → Still broken")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v14_stable_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v14 (numerical stability)',
        'config': CONFIG,
        'results': results,
        'delta_a1_a2': float(delta),
        'delta_a1_a3': float(delta3),
        'p_value': float(p_value),
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    print("=" * 70)


if __name__ == '__main__':
    main()