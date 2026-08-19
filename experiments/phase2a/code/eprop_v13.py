#!/usr/bin/env python
"""
Exp-P2A-01 v13: CORRECT e-prop Architecture
============================================
بر اساس راهنمایی Opus:

1. Output layer: leaky integrator (نه instant readout)
   r(t+1) = r(t) * (1 - 1/tau_out) + z(t)
   y(t) = W_out @ r(t)

2. Credit assignment: L_j(t) = W_out^T @ error(t)
   NOT by propagating eligibility backward.

3. Separate eligibility traces برای هر synapse:
   ε_ij(t) = decay × ε_ij(t-1) + f'(v_j) × z_i(t-1)

4. Weight update: ΔW = η × L(t) × ε(t)
   در هر tick، L(t) از error محاسبه می‌شود

5. Hyperparameters (Bellec 2020):
   eta = 0.001
   tau_m = 20 (dv = 1/20 = 0.05)
   tau_e = 20
   tau_out = 20
   f'(v) = 1 / (1 + beta*|v-theta|)^2
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    # Task (Bellec 2020 style)
    'n_ticks': 2000,
    'T1': 3,
    'T2': 6,
    'pulse_prob': 0.3,
    
    # Network
    'n_input': 30,
    'n_hidden': 100,
    'n_output': 2,  # binary: predict 0 or 1
    
    # LIF dynamics (Bellec 2020: tau_m = 20ms)
    'theta': 0.6,      # spike threshold
    'tau_m': 20.0,     # membrane time constant
    'dv': 1.0 / 20.0,  # decay = 1/tau_m = 0.05
    'du': 1.0 / 20.0,
    
    # Output dynamics
    'tau_out': 20.0,   # output leaky integrator
    
    # Synaptic
    'w_scale': 1.0,
    'connectivity': 0.2,
    'recurrent_connectivity': 0.2,
    
    # Learning (Bellec 2020)
    'eta': 0.001,       # ← Much smaller!
    'tau_e': 20.0,
    'beta': 10.0,       # surrogate parameter
    
    # Experiment
    'arms': ['A1_eprop', 'A2_nolearn', 'A3_stdp3c'],
    'n_seeds': 4,
    'random_seed': 42,
}

RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)


class LIFPool:
    """LIF neurons with membrane dynamics (Bellec 2020 style)."""
    
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
        # Update current
        self.u = self.u * (1 - self.du) + input_current
        
        # Update membrane potential
        self.v = self.v * (1 - self.dv) + self.u
        
        # Store pre-reset voltage for surrogate
        self.pre_reset_v = self.v.copy()
        
        # Spike detection
        spiked = self.v >= self.theta
        
        # Reset
        self.v[spiked] = 0.0
        self.last_spikes = spiked.astype(float)
        
        return self.last_spikes
    
    def surrogate_derivative(self):
        """Correct surrogate: f'(v) = 1 / (1 + beta * |v - theta|)^2"""
        beta = CONFIG['beta']
        return 1.0 / (1.0 + beta * np.abs(self.pre_reset_v - self.theta))**2


class OutputLayer:
    """Leaky integrator output (Bellec 2020 style).
    
    r(t+1) = r(t) * (1 - 1/tau_out) + z(t)
    y(t) = W_out @ r(t)
    """
    
    def __init__(self, n, tau_out=20.0):
        self.n = n
        self.tau_out = tau_out
        self.r = np.zeros(n)  # filtered activity
        
    def step(self, spikes):
        """Update leaky integrator with new spikes."""
        self.r = self.r * (1 - 1/self.tau_out) + spikes
        return self.r


class SynapticLayer:
    """Synaptic layer with eligibility traces."""
    
    def __init__(self, n_in, n_out, connectivity=0.2, w_scale=1.0, seed=None):
        rng = np.random.RandomState(seed)
        self.n_in = n_in
        self.n_out = n_out
        
        mask = rng.rand(n_out, n_in) < connectivity
        self.weights = (rng.randn(n_out, n_in) * w_scale) * mask
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return self.weights @ pre_spikes
    
    def update_eligibility(self, pre_spikes, post_f_prime, tau_e):
        """Update eligibility: ε(t) = decay × ε(t-1) + f'(v) × z(t-1)"""
        # Decay
        self.eligibility *= np.exp(-1.0 / tau_e)
        
        # Add new contribution: f'(v_j) × z_i(t-1)
        # post_f_prime: shape (n_out,), pre_spikes: shape (n_in,)
        delta_e = np.outer(post_f_prime, pre_spikes)
        self.eligibility += delta_e
        
    def apply_update(self, learning_signal, eta):
        """Weight update: ΔW = η × L_j × ε_ij
        
        learning_signal: shape (n_out,) - the L_j(t) values
        """
        # L_j × ε_ij (broadcasting)
        delta_w = eta * np.outer(learning_signal, np.ones(self.n_in)) * self.eligibility
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
    """Encode current pulse and input[t-T1]."""
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
    """Run with CORRECT e-prop architecture."""
    
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
    
    # Synapses
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
        
        # Encode
        x = encode_input(pulse, input_t3, config['n_input'])
        
        # Forward: input → hidden
        u_in = syn_in.forward(x)
        u_rec = syn_rec.forward(hidden.last_spikes)
        s_hidden = hidden.step(u_in + u_rec)
        
        # Forward: hidden → output
        u_out = syn_out.forward(s_hidden)
        
        # Output leaky integrator (Bellec 2020)
        r_out = output_layer.step(u_out)
        
        # Prediction from output (y = W_out @ r)
        # Higher r[1] than r[0] → predict 1
        pred = int(r_out[1] > r_out[0])
        
        # Evaluation
        if t >= start_tick:
            target = targets[t]
            
            all_predictions.append(pred)
            all_targets.append(target)
            
            # Learning (A1 and A3 only)
            if arm in ['A1_eprop', 'A3_stdp3c']:
                # === ERROR COMPUTATION ===
                # Target: [1, 0] for class 0, [0, 1] for class 1
                target_vec = np.zeros(n_output)
                target_vec[target] = 1.0
                
                # y = r (leaky integrator output)
                y = r_out
                
                # Error: e_k(t) = y_k(t) - target_k(t)
                error = y - target_vec
                
                # === LEARNING SIGNAL: L_j(t) = W_out^T @ error(t) ===
                # This is the KEY insight from Opus
                # L has shape (n_hidden,)
                L_hidden = syn_out.weights.T @ error
                
                # === ELIGIBILITY TRACES ===
                # For each hidden neuron j, we need f'(v_j)
                f_prime_hidden = hidden.surrogate_derivative()  # shape (n_hidden,)
                
                # Update eligibility for input synapses
                syn_in.update_eligibility(x, f_prime_hidden, tau_e)
                
                # Update eligibility for recurrent synapses
                syn_rec.update_eligibility(hidden.last_spikes, f_prime_hidden, tau_e)
                
                # === WEIGHT UPDATES ===
                # ΔW = η × L_j × ε_ij
                # This applies the SAME L to all synapses targeting hidden j
                syn_in.apply_update(L_hidden, eta)
                syn_rec.apply_update(L_hidden, eta)
                
                # Output layer: simple gradient descent (no eligibility needed)
                # ΔW_out_kj = η × e_k × z_j
                delta_out = eta * np.outer(error, s_hidden)
                syn_out.weights += delta_out
                
                total_updates += 1
    
    # Final metrics
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
    print("Exp-P2A-01 v13: CORRECT e-prop Architecture")
    print("=" * 70)
    print(f"Task: output[t] = input[t-{CONFIG['T1']}] XOR input[t-{CONFIG['T2']}]")
    print(f"Network: {CONFIG['n_hidden']} hidden LIF")
    print(f"Output: leaky integrator (tau_out={CONFIG['tau_out']})")
    print(f"Credit assignment: L_j = W_out^T @ error")
    print(f"eta = {CONFIG['eta']} (Bellec 2020)")
    print(f"tau_e = {CONFIG['tau_e']}")
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
    print("Bellec 2020 reference:")
    print(f"  Expected: ~80% on Temporal XOR")
    print(f"  Our A1:   {a1['mean_bal_acc']:.3f}")
    
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
    print(f"  Result: {'✅ PASS' if p_value < 0.05 else '❌ FAIL'}")
    
    # Hypothesis
    print()
    print("Hypothesis Test:")
    if delta >= 5.0 and p_value < 0.05:
        print("  🎉 H1 CONFIRMED: e-prop learns Temporal XOR!")
        if a1['mean_bal_acc'] > 0.60:
            print("  🎉 STRONG: accuracy > 60% (Bellec-like)")
        if delta3 > 2.0:
            print("  🎉 D5 PREDICTION CONFIRMED!")
    else:
        print("  ⚠️  H1 NULL")
        if a1['mean_bal_acc'] < 0.50:
            print("  → Learning hurts performance (overfitting?)")
        else:
            print("  → Need further tuning")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v13_correct_arch_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v13 (correct architecture per Opus)',
        'config': CONFIG,
        'results': results,
        'delta_a1_a2': float(delta),
        'delta_a1_a3': float(delta3),
        'p_value': float(p_value),
        'h1_confirmed': bool(delta >= 5.0 and p_value < 0.05),
        'key_fixes': [
            'Output as leaky integrator',
            'L_j(t) = W_out^T @ error(t)',
            'Separate eligibility traces',
            'eta = 0.001',
            'Correct surrogate formula',
        ],
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    print("=" * 70)


if __name__ == '__main__':
    main()