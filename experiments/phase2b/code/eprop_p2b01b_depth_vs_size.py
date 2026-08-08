#!/usr/bin/env python
"""
Exp-P2B-01b: Depth vs. Size Control
====================================
Pre-registration (Rule 2):
  H1: 3-layer [100,50] > 2-layer [150] at 75% block
      (depth helps, not just size)
  H2: 2-layer [150] > 2-layer [50] at 75% block
      (size helps)
  Success = H1 AND H2

Purpose: Disentangle the effect of depth vs. width.
If H1 fails, then metabolic tolerance comes from redundancy,
not hierarchical processing.
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
    
    'n_input': 2,
    'n_output': 2,
    
    'theta': 1.0,
    'tau_mem': 20.0,
    'tau_syn': 20.0,
    
    'tau_e': 15.0,  
    'beta': 1.0,
    
    'eta': 0.01,
    'w_scale': 0.5,
    
    # Architectures to compare
    'architectures': [
        {'label': '2-layer [50]', 'hidden_sizes': [50]},
        {'label': '2-layer [150]', 'hidden_sizes': [150]},  # CONTROL: same size as 3-layer
        {'label': '3-layer [100,50]', 'hidden_sizes': [100, 50]},
    ],
    
    # Focus on the critical region
    'conditions': [
        {'label': 'unconstrained', 'T_block_pct': 0,  'budget_fraction': 1.0},
        {'label': 'heavy',         'T_block_pct': 75, 'budget_fraction': 0.25},
        {'label': 'extreme',       'T_block_pct': 90, 'budget_fraction': 0.10},
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
    
    def update_eligibility(self, pre_spikes, post_f_prime, tau_e):
        self.eligibility *= np.exp(-1.0 / tau_e)
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


def build_network(hidden_sizes, n_input, n_output, w_scale, seed):
    """Build a multi-layer SNN."""
    layers = []
    synapses = []
    
    prev_size = n_input
    for i, h_size in enumerate(hidden_sizes):
        layer = LIFNetwork(h_size)
        syn = SynapticLayer(prev_size, h_size, w_scale=w_scale, seed=seed+i)
        layers.append(layer)
        synapses.append(syn)
        prev_size = h_size
    
    output_syn = SynapticLayer(prev_size, n_output, w_scale=w_scale, seed=seed+len(hidden_sizes))
    
    return layers, synapses, output_syn


def run_organism(config, seed, hidden_sizes, update_budget):
    """Run one organism with given architecture and update budget."""
    T_A = config['T_A']
    T_B = config['T_B']
    T_target = config['T_target']
    trial_length = config['trial_length']
    n_trials = config['n_trials']
    
    layers, synapses, output_syn = build_network(
        hidden_sizes, config['n_input'], config['n_output'], 
        config['w_scale'], seed
    )
    
    correct = 0
    total = 0
    updates_used = 0
    updates_blocked = 0
    loss_history = []
    
    rng = np.random.RandomState(seed)
    
    for trial in range(n_trials):
        A = rng.randint(0, 2)
        B = rng.randint(0, 2)
        target = A ^ B
        
        for layer in layers:
            layer.reset()
        for syn in synapses:
            syn.reset_eligibility()
        
        for t in range(trial_length):
            x = np.zeros(config['n_input'])
            if t == T_A and A == 1: x[0] = 1.0
            if t == T_B and B == 1: x[1] = 1.0
            
            current_input = x
            for layer, syn in zip(layers, synapses):
                i_in = syn.forward(current_input)
                layer.step(i_in)
                current_input = layer.last_spikes
            
            prev_spikes = x
            for layer, syn in zip(layers, synapses):
                f_prime = layer.surrogate_derivative(config['beta'])
                syn.update_eligibility(prev_spikes, f_prime, config['tau_e'])
                prev_spikes = layer.last_spikes
            
            if t == T_target:
                out_logits = output_syn.weights @ current_input
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
                
                if updates_used < update_budget:
                    L = output_syn.weights.T @ error
                    L = np.clip(L, -1.0, 1.0)
                    
                    delta_out = config['eta'] * np.outer(error, current_input)
                    delta_out = np.clip(delta_out, -1.0, 1.0)
                    output_syn.weights -= delta_out
                    
                    for i in range(len(synapses)-1, -1, -1):
                        synapses[i].apply_update(L, config['eta'])
                        if i > 0:
                            L = synapses[i].weights.T @ L
                            L = np.clip(L, -1.0, 1.0)
                    
                    updates_used += 1
                else:
                    updates_blocked += 1
                            
                break
                
    acc = correct / total if total > 0 else 0.0
    mean_loss = np.mean(loss_history[-100:]) if loss_history else 0.0
    
    return {
        'seed': seed,
        'architecture': hidden_sizes,
        'update_budget': update_budget,
        'accuracy': float(acc),
        'loss': float(mean_loss),
        'updates_used': int(updates_used),
        'updates_blocked': int(updates_blocked),
        'n_trials': total,
    }


def plot_comparison(results, config):
    """Plot depth vs size comparison."""
    fig, ax = plt.subplots(figsize=(10, 7))
    
    t_blocks = [c['T_block_pct'] for c in config['conditions']]
    
    colors = {'2-layer [50]': 'blue', '2-layer [150]': 'green', '3-layer [100,50]': 'red'}
    
    for arch_label, arch_results in results.items():
        mean_accs = [arch_results[c['label']]['mean_accuracy'] for c in config['conditions']]
        std_accs = [arch_results[c['label']]['std_accuracy'] for c in config['conditions']]
        
        ax.errorbar(t_blocks, mean_accs, yerr=std_accs, marker='o', 
                    linewidth=2, capsize=5, label=arch_label, color=colors[arch_label])
    
    ax.axhline(y=0.5, color='gray', linestyle='-', alpha=0.3, label='Random')
    ax.axhline(y=0.7, color='r', linestyle=':', alpha=0.5, label='Collapse threshold')
    
    ax.set_xlabel('Metabolic Constraint (T_block %)')
    ax.set_ylabel('Accuracy')
    ax.set_title('Phase 2B-01b: Depth vs Size')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0.4, 1.0)
    ax.set_xlim(-5, 95)
    
    plot_path = RESULTS_DIR / 'exp_p2b_01b_depth_vs_size.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    return plot_path


def main():
    print("=" * 70)
    print("Exp-P2B-01b: Depth vs. Size Control")
    print("=" * 70)
    print("Pre-registration (Rule 2):")
    print("  H1: 3-layer [100,50] > 2-layer [150] at 75% block")
    print("      (depth helps, not just size)")
    print("  H2: 2-layer [150] > 2-layer [50] at 75% block")
    print("      (size helps)")
    print("  Success = H1 AND H2")
    print()
    print("Architectures:")
    for arch in CONFIG['architectures']:
        total_neurons = sum(arch['hidden_sizes'])
        print(f"  {arch['label']}: {total_neurons} total hidden neurons")
    print()
    print("=" * 70)
    print()
    
    results = {}
    
    for arch in CONFIG['architectures']:
        arch_label = arch['label']
        hidden_sizes = arch['hidden_sizes']
        
        print(f"\n{'='*50}")
        print(f"Architecture: {arch_label}")
        print(f"{'='*50}")
        
        results[arch_label] = {}
        
        for cond in CONFIG['conditions']:
            label = cond['label']
            budget = int(500 * cond['budget_fraction'])
            
            print(f"\n  --- {label} (budget={budget}) ---")
            
            seed_results = []
            for seed_idx in range(CONFIG['n_seeds']):
                seed = CONFIG['random_seed'] + seed_idx
                result = run_organism(CONFIG, seed, hidden_sizes, budget)
                seed_results.append(result)
                print(f"    seed {seed}: acc={result['accuracy']:.3f}")
            
            mean_acc = np.mean([r['accuracy'] for r in seed_results])
            std_acc = np.std([r['accuracy'] for r in seed_results])
            
            results[arch_label][label] = {
                'T_block_pct': cond['T_block_pct'],
                'update_budget': budget,
                'mean_accuracy': float(mean_acc),
                'std_accuracy': float(std_acc),
                'seeds': seed_results,
            }
            
            print(f"    → Mean: {mean_acc:.3f} ± {std_acc:.3f}")
    
    # Results table
    print("\n" + "=" * 90)
    print("RESULTS: Depth vs Size")
    print("=" * 90)
    print(f"{'Architecture':<20} | {'0%':<15} | {'75%':<15} | {'90%':<15}")
    print("-" * 90)
    
    for arch_label in results:
        acc_0 = results[arch_label]['unconstrained']['mean_accuracy']
        acc_75 = results[arch_label]['heavy']['mean_accuracy']
        acc_90 = results[arch_label]['extreme']['mean_accuracy']
        print(f"{arch_label:<20} | {acc_0:.3f}±{results[arch_label]['unconstrained']['std_accuracy']:.3f} | "
              f"{acc_75:.3f}±{results[arch_label]['heavy']['std_accuracy']:.3f} | "
              f"{acc_90:.3f}±{results[arch_label]['extreme']['std_accuracy']:.3f}")
    
    # Hypothesis testing
    print("\n" + "=" * 70)
    print("HYPOTHESIS TESTING")
    print("=" * 70)
    
    # H1: 3-layer [100,50] > 2-layer [150] at 75% block
    acc_3layer_75 = results['3-layer [100,50]']['heavy']['mean_accuracy']
    acc_2layer_150_75 = results['2-layer [150]']['heavy']['mean_accuracy']
    H1_pass = acc_3layer_75 > acc_2layer_150_75
    delta_H1 = (acc_3layer_75 - acc_2layer_150_75) * 100
    print(f"H1 (3-layer > 2-layer[150] at 75%): "
          f"3-layer={acc_3layer_75*100:.1f}%, 2-layer[150]={acc_2layer_150_75*100:.1f}% "
          f"(Δ={delta_H1:+.1f}pp) → {'✅ PASS' if H1_pass else '❌ FAIL'}")
    
    # H2: 2-layer [150] > 2-layer [50] at 75% block
    acc_2layer_50_75 = results['2-layer [50]']['heavy']['mean_accuracy']
    H2_pass = acc_2layer_150_75 > acc_2layer_50_75
    delta_H2 = (acc_2layer_150_75 - acc_2layer_50_75) * 100
    print(f"H2 (2-layer[150] > 2-layer[50] at 75%): "
          f"2-layer[150]={acc_2layer_150_75*100:.1f}%, 2-layer[50]={acc_2layer_50_75*100:.1f}% "
          f"(Δ={delta_H2:+.1f}pp) → {'✅ PASS' if H2_pass else '❌ FAIL'}")
    
    print()
    if H1_pass and H2_pass:
        print("🎉 SUCCESS: Both depth AND size help!")
        print("   → Depth provides additional benefit beyond size alone.")
        print("   → Hierarchical processing is metabolically advantageous.")
    elif H1_pass and not H2_pass:
        print("⚠️  UNEXPECTED: Depth helps but size doesn't.")
        print("   → This contradicts intuition. Check implementation.")
    elif not H1_pass and H2_pass:
        print("⚠️  PARTIAL: Size helps but depth doesn't.")
        print("   → Metabolic tolerance comes from redundancy, not hierarchy.")
        print("   → This is still valuable: simpler architectures work.")
    else:
        print("❌ FAIL: Neither depth nor size helps at 75% block.")
        print("   → Fundamental limitation of e-prop under extreme constraint.")
    
    # Plot
    plot_path = plot_comparison(results, CONFIG)
    print(f"\n📊 Plot: {plot_path}")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2b_01b_depth_vs_size_{timestamp}.json'
    
    json_data = {
        'timestamp': timestamp,
        'experiment': 'Exp-P2B-01b',
        'version': 'Depth vs Size Control',
        'pre_registration': {
            'H1': "3-layer [100,50] > 2-layer [150] at 75%",
            'H2': "2-layer [150] > 2-layer [50] at 75%",
            'acc_3layer_75': float(acc_3layer_75),
            'acc_2layer_150_75': float(acc_2layer_150_75),
            'acc_2layer_50_75': float(acc_2layer_50_75),
            'H1_pass': bool(H1_pass),
            'H2_pass': bool(H2_pass),
            'success': bool(H1_pass and H2_pass),
        },
        'config': CONFIG,
        'results': {
            arch_label: {
                cond_label: {
                    'T_block_pct': data['T_block_pct'],
                    'update_budget': data['update_budget'],
                    'mean_accuracy': data['mean_accuracy'],
                    'std_accuracy': data['std_accuracy'],
                }
                for cond_label, data in conds.items()
            }
            for arch_label, conds in results.items()
        },
    }
    
    with open(filename, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"💾 Saved: {filename}")
    print("=" * 70)


if __name__ == '__main__':
    main()