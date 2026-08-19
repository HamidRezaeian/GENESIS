#!/usr/bin/env python
"""
Exp-P2B-01: Hierarchical SNN — Does Depth Extend Metabolic Tolerance?
======================================================================
Pre-registration (Rule 2):
  H1: 3-layer SNN has phase transition threshold > 80% block
      (vs 2-layer baseline of ~75%)
  H2: At 50% block, 3-layer accuracy > 2-layer accuracy
  Success = H1 AND H2

Motivation (Phase 2B, Step B1):
Phase 2A showed e-prop has a phase transition at ~75% metabolic block.
This experiment tests whether deeper architectures (more layers, more
neurons) can extend this threshold by distributing metabolic load.

Biological parallel: Cortex has 6 layers. Is depth a metabolic adaptation?

Design:
  - 2-layer baseline: 2→50→2 (same as Phase 2A)
  - 3-layer test: 2→100→50→2
  - 5 conditions: 0%, 25%, 50%, 75%, 90% block
  - Task: Temporal XOR (noise=0%)
  - 5 seeds per condition
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
        {'label': '2-layer', 'hidden_sizes': [50], 'update_budget': 500},
        {'label': '3-layer', 'hidden_sizes': [100, 50], 'update_budget': 500},
    ],
    
    # Metabolic constraint conditions
    'conditions': [
        {'label': 'unconstrained', 'T_block_pct': 0,  'budget_fraction': 1.0},
        {'label': 'light',         'T_block_pct': 25, 'budget_fraction': 0.75},
        {'label': 'moderate',      'T_block_pct': 50, 'budget_fraction': 0.50},
        {'label': 'heavy',         'T_block_pct': 75, 'budget_fraction': 0.25},
        {'label': 'extreme',       'T_block_pct': 90, 'budget_fraction': 0.10},
    ],
    
    'n_seeds': 5,
    'random_seed': 42,
    
    # Pre-registration thresholds
    'H1_threshold': 0.80,  # 3-layer threshold > 80%
    'H2_threshold': 0.0,   # 3-layer > 2-layer at 50% block
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
    
    # Input to first hidden layer
    prev_size = n_input
    for i, h_size in enumerate(hidden_sizes):
        layer = LIFNetwork(h_size)
        syn = SynapticLayer(prev_size, h_size, w_scale=w_scale, seed=seed+i)
        layers.append(layer)
        synapses.append(syn)
        prev_size = h_size
    
    # Last hidden to output
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
        
        # Reset all layers
        for layer in layers:
            layer.reset()
        for syn in synapses:
            syn.reset_eligibility()
        
        for t in range(trial_length):
            x = np.zeros(config['n_input'])
            if t == T_A and A == 1: x[0] = 1.0
            if t == T_B and B == 1: x[1] = 1.0
            
            # Forward pass through all layers
            current_input = x
            for i, (layer, syn) in enumerate(zip(layers, synapses)):
                i_in = syn.forward(current_input)
                # Add recurrent input for first layer
                if i == 0 and len(layers) > 0:
                    # Simple recurrent: first layer connects to itself
                    pass  # Skip recurrent for simplicity in B1
                layer.step(i_in)
                current_input = layer.last_spikes
            
            # Update eligibility traces (always, cheap)
            prev_spikes = x
            for i, (layer, syn) in enumerate(zip(layers, synapses)):
                f_prime = layer.surrogate_derivative(config['beta'])
                syn.update_eligibility(prev_spikes, f_prime, config['tau_e'])
                prev_spikes = layer.last_spikes
            
            if t == T_target:
                # Read output
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
                
                # Metabolic constraint: check update budget
                if updates_used < update_budget:
                    # Backprop learning signal through layers
                    L = output_syn.weights.T @ error
                    L = np.clip(L, -1.0, 1.0)
                    
                    # Update output synapse
                    delta_out = config['eta'] * np.outer(error, current_input)
                    delta_out = np.clip(delta_out, -1.0, 1.0)
                    output_syn.weights -= delta_out
                    
                    # Update hidden synapses (reverse order)
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


def find_phase_transition(t_blocks, accs, threshold=0.70):
    """Find the block rate where accuracy drops below threshold."""
    for i, acc in enumerate(accs):
        if acc < threshold:
            return t_blocks[i]
    return None  # Never drops below threshold


def plot_comparison(results, config):
    """Plot 2-layer vs 3-layer Pareto curves."""
    fig, ax = plt.subplots(figsize=(10, 7))
    
    t_blocks = [c['T_block_pct'] for c in config['conditions']]
    
    for arch_label, arch_results in results.items():
        mean_accs = [arch_results[c['label']]['mean_accuracy'] for c in config['conditions']]
        std_accs = [arch_results[c['label']]['std_accuracy'] for c in config['conditions']]
        
        ax.errorbar(t_blocks, mean_accs, yerr=std_accs, marker='o', 
                    linewidth=2, capsize=5, label=arch_label)
    
    ax.axhline(y=0.5, color='gray', linestyle='-', alpha=0.3, label='Random')
    ax.axhline(y=0.7, color='r', linestyle=':', alpha=0.5, label='Collapse threshold')
    
    ax.set_xlabel('Metabolic Constraint (T_block %)')
    ax.set_ylabel('Accuracy')
    ax.set_title('Phase 2B-01: Depth vs Metabolic Tolerance')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0.4, 1.0)
    ax.set_xlim(-5, 95)
    
    plot_path = RESULTS_DIR / 'exp_p2b_01_hierarchical_snn.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    return plot_path


def main():
    print("=" * 70)
    print("Exp-P2B-01: Hierarchical SNN — Depth vs Metabolic Tolerance")
    print("=" * 70)
    print("Pre-registration (Rule 2):")
    print(f"  H1: 3-layer phase transition > {CONFIG['H1_threshold']*100:.0f}% block")
    print(f"  H2: At 50% block, 3-layer > 2-layer")
    print(f"  Success = H1 AND H2")
    print()
    print("Architectures:")
    for arch in CONFIG['architectures']:
        print(f"  {arch['label']}: {arch['hidden_sizes']}")
    print()
    print("Conditions:")
    for c in CONFIG['conditions']:
        print(f"  {c['label']:<15} T_block={c['T_block_pct']:>3}%")
    print()
    print("=" * 70)
    print()
    
    results = {}
    
    for arch in CONFIG['architectures']:
        arch_label = arch['label']
        hidden_sizes = arch['hidden_sizes']
        base_budget = arch['update_budget']
        
        print(f"\n{'='*50}")
        print(f"Architecture: {arch_label} ({hidden_sizes})")
        print(f"{'='*50}")
        
        results[arch_label] = {}
        
        for cond in CONFIG['conditions']:
            label = cond['label']
            budget = int(base_budget * cond['budget_fraction'])
            
            print(f"\n  --- {label} (budget={budget}) ---")
            
            seed_results = []
            for seed_idx in range(CONFIG['n_seeds']):
                seed = CONFIG['random_seed'] + seed_idx
                result = run_organism(CONFIG, seed, hidden_sizes, budget)
                seed_results.append(result)
                print(f"    seed {seed}: acc={result['accuracy']:.3f}")
            
            mean_acc = np.mean([r['accuracy'] for r in seed_results])
            std_acc = np.std([r['accuracy'] for r in seed_results])
            mean_updates = np.mean([r['updates_used'] for r in seed_results])
            mean_blocked = np.mean([r['updates_blocked'] for r in seed_results])
            
            results[arch_label][label] = {
                'T_block_pct': cond['T_block_pct'],
                'update_budget': budget,
                'mean_accuracy': float(mean_acc),
                'std_accuracy': float(std_acc),
                'mean_updates_used': float(mean_updates),
                'mean_updates_blocked': float(mean_blocked),
                'seeds': seed_results,
            }
            
            print(f"    → Mean: {mean_acc:.3f} ± {std_acc:.3f}")
    
    # Results table
    print("\n" + "=" * 90)
    print("RESULTS: 2-Layer vs 3-Layer")
    print("=" * 90)
    
    for arch_label in results:
        print(f"\n{arch_label}:")
        print(f"{'T_block%':<10} | {'Accuracy':<15} | {'Updates':<10} | {'Blocked':<10}")
        print("-" * 60)
        for cond in CONFIG['conditions']:
            label = cond['label']
            r = results[arch_label][label]
            print(f"{r['T_block_pct']:<10} | {r['mean_accuracy']:.3f}±{r['std_accuracy']:.3f} | "
                  f"{r['mean_updates_used']:<10.0f} | {r['mean_updates_blocked']:<10.0f}")
    
    # Hypothesis testing
    print("\n" + "=" * 70)
    print("HYPOTHESIS TESTING")
    print("=" * 70)
    
    # Find phase transition thresholds
    t_blocks = [c['T_block_pct'] for c in CONFIG['conditions']]
    
    thresholds = {}
    for arch_label in results:
        accs = [results[arch_label][c['label']]['mean_accuracy'] for c in CONFIG['conditions']]
        threshold = find_phase_transition(t_blocks, accs, threshold=0.70)
        thresholds[arch_label] = threshold
        if threshold is not None:
            print(f"  {arch_label}: Phase transition at {threshold}% block")
        else:
            print(f"  {arch_label}: No phase transition (robust up to 90%)")
    
    # H1: 3-layer threshold > 80%
    threshold_3layer = thresholds.get('3-layer')
    if threshold_3layer is None:
        H1_pass = True  # No transition means it's robust
        print(f"\nH1 (3-layer threshold > {CONFIG['H1_threshold']*100:.0f}%): "
              f"no transition → ✅ PASS")
    else:
        H1_pass = threshold_3layer > CONFIG['H1_threshold'] * 100
        print(f"\nH1 (3-layer threshold > {CONFIG['H1_threshold']*100:.0f}%): "
              f"actual={threshold_3layer}% → {'✅ PASS' if H1_pass else '❌ FAIL'}")
    
    # H2: At 50% block, 3-layer > 2-layer
    acc_2layer_50 = results['2-layer']['moderate']['mean_accuracy']
    acc_3layer_50 = results['3-layer']['moderate']['mean_accuracy']
    H2_pass = acc_3layer_50 > acc_2layer_50
    delta = (acc_3layer_50 - acc_2layer_50) * 100
    print(f"H2 (3-layer > 2-layer at 50%): "
          f"2-layer={acc_2layer_50*100:.1f}%, 3-layer={acc_3layer_50*100:.1f}% "
          f"(Δ={delta:+.1f}pp) → {'✅ PASS' if H2_pass else '❌ FAIL'}")
    
    print()
    if H1_pass and H2_pass:
        print("🎉 SUCCESS: Depth extends metabolic tolerance!")
        print("   → Hierarchical architectures are more metabolically robust.")
        print("   → Phase 2B hypothesis SUPPORTED")
    elif H1_pass and not H2_pass:
        print("⚠️  PARTIAL: 3-layer is robust but not better at moderate constraint.")
        print("   → Depth helps with extreme constraints only.")
    elif not H1_pass and H2_pass:
        print("⚠️  PARTIAL: 3-layer is better at moderate but still collapses early.")
        print("   → Need more layers or different architecture.")
    else:
        print("❌ FAIL: Depth does not help metabolic tolerance.")
        print("   → Architectural priors alone are insufficient.")
    
    # Plot
    plot_path = plot_comparison(results, CONFIG)
    print(f"\n📊 Plot: {plot_path}")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2b_01_hierarchical_snn_{timestamp}.json'
    
    json_data = {
        'timestamp': timestamp,
        'experiment': 'Exp-P2B-01',
        'version': 'Hierarchical SNN - Depth vs Metabolic Tolerance',
        'pre_registration': {
            'H1': f"3-layer threshold > {CONFIG['H1_threshold']*100:.0f}%",
            'H2': "3-layer > 2-layer at 50% block",
            'thresholds': thresholds,
            'acc_2layer_50': float(acc_2layer_50),
            'acc_3layer_50': float(acc_3layer_50),
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
                    'mean_updates_used': data['mean_updates_used'],
                    'mean_updates_blocked': data['mean_updates_blocked'],
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