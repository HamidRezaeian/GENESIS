#!/usr/bin/env python
"""
Exp-P2B-03: Neuromodulatory Gating for Noise Robustness
=========================================================
Pre-registration (Rule 2):
  H1: With ACh gate, accuracy at 5% noise > 80%
      (vs Phase 2A baseline of 66.8%)
  H2: With ACh gate, accuracy at 0% noise > 85%
      (no regression from baseline 90.7%)
  Success = H1 AND H2

Motivation (Phase 2B, Step B3):
Phase 2A (v25-v27) showed e-prop is fragile to 5% noise.
Postsynaptic gates and sparse encoding failed to fix this.

This experiment tests acetylcholine (ACh) analog gating:
- ACh signals novelty/surprise
- Only unexpected inputs create eligibility traces
- Predictable noise is filtered out

Biological justification:
  Hasselmo et al. (1992): ACh modulates cortical associative memory.
  ACh is high during novel stimuli, low during familiar stimuli.
  This gates synaptic plasticity to only learn surprising inputs.

Design:
  - Task: Temporal XOR with noise (same as Phase 2A v25)
  - ACh mechanism: dz_i = max(0, z_i - z_bar_i)
    - z_bar_i is running mean of input neuron activity
    - Only spikes above baseline create eligibility traces
  - Comparison: baseline (no gate) vs ACh gate
  - Noise levels: 0%, 5%, 10%
"""

import numpy as np
import json
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path

CONFIG = {
    'trial_length': 10,
    'n_trials': 500,
    'T_A': 3,
    'T_B': 6,
    'T_target': 9,
    
    'n_input': 10,  # 2 signal + 8 noise channels
    'n_hidden': 50,
    'n_output': 2,
    
    'theta': 1.0,
    'tau_mem': 20.0,
    'tau_syn': 20.0,
    
    'tau_e': 15.0,  
    'beta': 1.0,
    
    'eta': 0.01,
    'w_scale': 0.5,
    
    # ACh gating parameters
    'tau_adapt': 100.0,  # running mean time constant for input
    'use_ach_gate': True,
    
    'conditions': [
        {'label': 'no_gate_0',   'noise': 0.0,  'use_gate': False},
        {'label': 'no_gate_5',   'noise': 0.05, 'use_gate': False},
        {'label': 'ach_gate_0',  'noise': 0.0,  'use_gate': True},
        {'label': 'ach_gate_5',  'noise': 0.05, 'use_gate': True},
        {'label': 'ach_gate_10', 'noise': 0.10, 'use_gate': True},
    ],
    
    'n_seeds': 5,
    'random_seed': 42,
}

RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)


class LIFNetwork:
    def __init__(self, n, theta=1.0, tau_mem=20.0, tau_syn=20.0):
        self.n = n
        self.theta = theta
        self.dt_tau_mem = 1.0 / tau_mem
        self.dt_tau_syn = 1.0 / tau_syn
        self.v = np.zeros(n)
        self.i_syn = np.zeros(n)
        self.last_spikes = np.zeros(n)
        self.pre_reset_v = np.zeros(n)
        
    def step(self, i_in):
        self.i_syn = self.i_syn * (1 - self.dt_tau_syn) + i_in
        self.v = self.v * (1 - self.dt_tau_mem) + self.i_syn
        
        self.pre_reset_v = self.v.copy()
        spiked = self.v >= self.theta
        self.v[spiked] = 0.0
        self.last_spikes = spiked.astype(float)
        return self.last_spikes
    
    def reset(self):
        self.v[:] = 0.0
        self.i_syn[:] = 0.0
        self.last_spikes[:] = 0.0
        self.pre_reset_v[:] = 0.0
    
    def surrogate_derivative(self, beta):
        diff = np.abs(self.pre_reset_v - self.theta)
        f_prime = 1.0 / (1.0 + beta * diff)
        return np.clip(f_prime, 0, 1)


class SynapticLayer:
    def __init__(self, n_in, n_out, w_scale=0.5, seed=None):
        rng = np.random.RandomState(seed)
        self.n_in = n_in
        self.n_out = n_out
        self.weights = rng.randn(n_out, n_in) * w_scale
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return self.weights @ pre_spikes
    
    def update_eligibility(self, pre_spikes, post_f_prime, tau_e, ach_gate=None):
        """
        Update eligibility trace with optional ACh gating.
        
        If ach_gate is provided:
          eps[i,j] += f'(v_j) * dz_i * ach_gate_i
        where dz_i = max(0, z_i - z_bar_i) is the surprise signal.
        """
        self.eligibility *= np.exp(-1.0 / tau_e)
        
        if ach_gate is not None:
            # Only surprising inputs create eligibility traces
            gated_pre = pre_spikes * ach_gate
            delta_e = np.outer(post_f_prime, gated_pre)
        else:
            delta_e = np.outer(post_f_prime, pre_spikes)
        
        self.eligibility += delta_e
        
    def reset_eligibility(self):
        self.eligibility[:] = 0.0
        
    def apply_update(self, learning_signal, eta, max_grad=1.0):
        learning_signal = np.clip(learning_signal, -max_grad, max_grad)
        delta_w = eta * np.outer(learning_signal, np.ones(self.n_in)) * self.eligibility
        delta_w = np.clip(delta_w, -max_grad, max_grad)
        self.weights -= delta_w  


def softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


def run_organism(config, seed, noise_level, use_gate):
    T_A = config['T_A']
    T_B = config['T_B']
    T_target = config['T_target']
    trial_length = config['trial_length']
    n_trials = config['n_trials']
    
    hidden = LIFNetwork(config['n_hidden'], theta=config['theta'], 
                        tau_mem=config['tau_mem'], tau_syn=config['tau_syn'])
    
    syn_in = SynapticLayer(config['n_input'], config['n_hidden'], 
                           w_scale=config['w_scale'], seed=seed)
    syn_rec = SynapticLayer(config['n_hidden'], config['n_hidden'], 
                            w_scale=config['w_scale'] * 0.5, seed=seed+1)
    syn_out = SynapticLayer(config['n_hidden'], config['n_output'], 
                            w_scale=config['w_scale'], seed=seed+2)
    
    # ACh state: running mean of input activity
    tau_adapt = config['tau_adapt']
    gamma_adapt = np.exp(-1.0 / tau_adapt)
    z_bar_input = np.zeros(config['n_input'])
    
    correct = 0
    total = 0
    loss_history = []
    
    rng = np.random.RandomState(seed)
    
    for trial in range(n_trials):
        A = rng.randint(0, 2)
        B = rng.randint(0, 2)
        target = A ^ B
        
        hidden.reset()
        syn_in.reset_eligibility()
        syn_rec.reset_eligibility()
        
        for t in range(trial_length):
            x = np.zeros(config['n_input'])
            if t == T_A and A == 1: x[0] = 1.0
            if t == T_B and B == 1: x[1] = 1.0
            
            # Noise on dedicated channels
            if noise_level > 0:
                for i in range(2, config['n_input']):
                    if rng.rand() < noise_level:
                        x[i] = 1.0
            
            # Compute ACh surprise signal
            if use_gate:
                # Surprise: how much above baseline is this spike?
                dz = np.maximum(0, x - z_bar_input)
                # Normalize: only count as surprise if significantly above baseline
                ach_gate = (dz > 0.5).astype(float)
                # Update running mean
                z_bar_input = gamma_adapt * z_bar_input + (1 - gamma_adapt) * x
            else:
                ach_gate = None
            
            i_in = syn_in.forward(x)
            i_rec = syn_rec.forward(hidden.last_spikes)
            hidden.step(i_in + i_rec)
            
            f_prime = hidden.surrogate_derivative(config['beta'])
            syn_in.update_eligibility(x, f_prime, config['tau_e'], ach_gate)
            syn_rec.update_eligibility(hidden.last_spikes, f_prime, config['tau_e'])
            
            if t == T_target:
                out_logits = syn_out.weights @ hidden.v
                y = softmax(out_logits)
                pred = int(y.argmax())
                if pred == target:
                    correct += 1
                total += 1
                
                target_vec = np.zeros(config['n_output'])
                target_vec[target] = 1.0
                error = y - target_vec
                loss = -np.log(y[target] + 1e-8)
                loss_history.append(loss)
                
                L_hidden = syn_out.weights.T @ error
                L_hidden = np.clip(L_hidden, -1.0, 1.0)
                
                syn_in.apply_update(L_hidden, config['eta'])
                syn_rec.apply_update(L_hidden, config['eta'])
                
                delta_out = config['eta'] * np.outer(error, hidden.v)
                delta_out = np.clip(delta_out, -1.0, 1.0)
                syn_out.weights -= delta_out
                
                break
    
    acc = correct / total if total > 0 else 0.0
    mean_loss = np.mean(loss_history[-100:]) if loss_history else 0.0
    
    return {
        'seed': seed,
        'noise_level': noise_level,
        'use_gate': use_gate,
        'accuracy': float(acc),
        'loss': float(mean_loss),
        'n_trials': total,
    }


def plot_results(results, config):
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Group by gate type
    no_gate = {c['noise']: results[c['label']]['mean_accuracy'] 
               for c in config['conditions'] if not c['use_gate']}
    ach_gate = {c['noise']: results[c['label']]['mean_accuracy'] 
                for c in config['conditions'] if c['use_gate']}
    
    # Plot no_gate
    if no_gate:
        noises = sorted(no_gate.keys())
        accs = [no_gate[n] for n in noises]
        ax.plot(noises, accs, 'b-o', linewidth=2, label='No Gate (baseline)')
    
    # Plot ach_gate
    if ach_gate:
        noises = sorted(ach_gate.keys())
        accs = [ach_gate[n] for n in noises]
        ax.plot(noises, accs, 'r-s', linewidth=2, label='ACh Gate')
    
    ax.axhline(y=0.5, color='gray', linestyle='-', alpha=0.3, label='Random')
    ax.axhline(y=0.7, color='orange', linestyle=':', alpha=0.5, label='Acceptable threshold')
    
    ax.set_xlabel('Noise Level')
    ax.set_ylabel('Accuracy')
    ax.set_title('Phase 2B-03: Neuromodulatory Gating (ACh)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0.4, 1.0)
    
    plot_path = RESULTS_DIR / 'exp_p2b_03_neuromodulation.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    return plot_path


def main():
    print("=" * 70)
    print("Exp-P2B-03: Neuromodulatory Gating (ACh) for Noise Robustness")
    print("=" * 70)
    print("Pre-registration (Rule 2):")
    print("  H1: ACh gate at 5% noise > 80% (vs baseline 66.8%)")
    print("  H2: ACh gate at 0% noise > 85% (no regression)")
    print("  Success = H1 AND H2")
    print()
    print("Mechanism: dz_i = max(0, z_i - z_bar_i)")
    print("  Only surprising inputs create eligibility traces")
    print("  Predictable noise is filtered out")
    print("=" * 70)
    print()
    
    results = {}
    
    for cond in CONFIG['conditions']:
        label = cond['label']
        noise = cond['noise']
        use_gate = cond['use_gate']
        
        print(f"\n--- {label} (noise={noise}, gate={'ON' if use_gate else 'OFF'}) ---")
        
        seed_results = []
        for seed_idx in range(CONFIG['n_seeds']):
            seed = CONFIG['random_seed'] + seed_idx
            result = run_organism(CONFIG, seed, noise, use_gate)
            seed_results.append(result)
            print(f"  seed {seed}: acc={result['accuracy']:.3f}")
        
        mean_acc = np.mean([r['accuracy'] for r in seed_results])
        std_acc = np.std([r['accuracy'] for r in seed_results])
        mean_loss = np.mean([r['loss'] for r in seed_results])
        
        results[label] = {
            'noise': noise,
            'use_gate': use_gate,
            'mean_accuracy': float(mean_acc),
            'std_accuracy': float(std_acc),
            'mean_loss': float(mean_loss),
            'seeds': seed_results,
        }
        
        print(f"  → Mean: {mean_acc:.3f} ± {std_acc:.3f}")
    
    # Results table
    print("\n" + "=" * 80)
    print("RESULTS: Neuromodulatory Gating")
    print("=" * 80)
    print(f"{'Condition':<15} | {'Noise':<8} | {'Gate':<6} | {'Accuracy':<15}")
    print("-" * 80)
    
    for cond in CONFIG['conditions']:
        label = cond['label']
        r = results[label]
        gate_str = 'ON' if r['use_gate'] else 'OFF'
        print(f"{label:<15} | {r['noise']:<8.2f} | {gate_str:<6} | "
              f"{r['mean_accuracy']:.3f}±{r['std_accuracy']:.3f}")
    
    # Hypothesis testing
    print("\n" + "=" * 70)
    print("HYPOTHESIS TESTING")
    print("=" * 70)
    
    # H1: ACh gate at 5% noise > 80%
    ach_5_acc = results['ach_gate_5']['mean_accuracy']
    H1_pass = ach_5_acc > 0.80
    baseline_5_acc = results['no_gate_5']['mean_accuracy']
    print(f"H1 (ACh at 5% > 80%): actual={ach_5_acc*100:.1f}% "
          f"(baseline={baseline_5_acc*100:.1f}%) → {'✅ PASS' if H1_pass else '❌ FAIL'}")
    
    # H2: ACh gate at 0% noise > 85%
    ach_0_acc = results['ach_gate_0']['mean_accuracy']
    H2_pass = ach_0_acc > 0.85
    baseline_0_acc = results['no_gate_0']['mean_accuracy']
    print(f"H2 (ACh at 0% > 85%): actual={ach_0_acc*100:.1f}% "
          f"(baseline={baseline_0_acc*100:.1f}%) → {'✅ PASS' if H2_pass else '❌ FAIL'}")
    
    print()
    if H1_pass and H2_pass:
        print("🎉 SUCCESS: ACh gating solves noise robustness!")
        print("   → Neuromodulatory mechanisms can filter predictable noise.")
        print("   → This solves the Phase 2A noise fragility problem.")
    elif H1_pass and not H2_pass:
        print("⚠️  PARTIAL: ACh helps with noise but hurts clean performance.")
        print("   → Gate threshold may need tuning.")
    elif not H1_pass and H2_pass:
        print("⚠️  PARTIAL: ACh preserves clean performance but doesn't fix noise.")
        print("   → Surprise detection may need different implementation.")
    else:
        print("❌ FAIL: ACh gating does not help.")
        print("   → Noise robustness may require fundamentally different approach.")
    
    # Plot
    plot_path = plot_results(results, CONFIG)
    print(f"\n📊 Plot: {plot_path}")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2b_03_neuromodulation_{timestamp}.json'
    
    json_data = {
        'timestamp': timestamp,
        'experiment': 'Exp-P2B-03',
        'version': 'Neuromodulatory Gating (ACh)',
        'pre_registration': {
            'H1': "ACh at 5% noise > 80%",
            'H2': "ACh at 0% noise > 85%",
            'ach_5_acc': float(ach_5_acc),
            'ach_0_acc': float(ach_0_acc),
            'baseline_5_acc': float(baseline_5_acc),
            'baseline_0_acc': float(baseline_0_acc),
            'H1_pass': bool(H1_pass),
            'H2_pass': bool(H2_pass),
            'success': bool(H1_pass and H2_pass),
        },
        'config': CONFIG,
        'results': {
            label: {
                'noise': data['noise'],
                'use_gate': data['use_gate'],
                'mean_accuracy': data['mean_accuracy'],
                'std_accuracy': data['std_accuracy'],
                'mean_loss': data['mean_loss'],
            }
            for label, data in results.items()
        },
    }
    
    with open(filename, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"💾 Saved: {filename}")
    print("=" * 70)


if __name__ == '__main__':
    main()