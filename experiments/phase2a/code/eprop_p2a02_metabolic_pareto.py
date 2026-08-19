#!/usr/bin/env python
"""
Exp-P2A-02: Metabolic Pareto Frontier
======================================
Pre-registration (Rule 2):
  H1: At T_block < 50%, accuracy > 85%
  H2: At T_block = 90%, accuracy > 70% (still better than random)
  Success = H1 AND H2

Hypothesis: Buffering trades accuracy for metabolic savings.
This experiment maps the Pareto frontier of that tradeoff.

Design:
  - 5 conditions: T_block = 0%, 25%, 50%, 75%, 90%
  - noise = 0% (noise problem set aside per Opus consultation)
  - Task: Temporal XOR (same as v24)
  - Measure: accuracy, update_count, blocked_count

Biological interpretation:
  T_block represents the fraction of learning opportunities the brain
  must skip due to metabolic constraints. The Pareto frontier shows
  how much accuracy is sacrificed at each level of metabolic constraint.
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
    'n_hidden': 50,
    'n_output': 2,
    
    'theta': 1.0,
    'tau_mem': 20.0,
    'tau_syn': 20.0,
    
    'tau_e': 15.0,  
    'beta': 1.0,
    
    'eta': 0.01,
    'w_scale': 0.5,
    
    # Metabolic constraint conditions
    # T_block_pct controls what fraction of updates are blocked
    # Implemented via update_budget (max allowed updates per run)
    'conditions': [
        {'label': 'unconstrained', 'T_block_pct': 0,  'update_budget': 500},
        {'label': 'light',         'T_block_pct': 25, 'update_budget': 375},
        {'label': 'moderate',      'T_block_pct': 50, 'update_budget': 250},
        {'label': 'heavy',         'T_block_pct': 75, 'update_budget': 125},
        {'label': 'extreme',       'T_block_pct': 90, 'update_budget': 50},
    ],
    
    'n_seeds': 5,
    'random_seed': 42,
    
    # Pre-registration thresholds
    'H1_threshold': 0.85,  # accuracy at T_block < 50%
    'H2_threshold': 0.70,  # accuracy at T_block = 90%
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


def run_organism(config, seed, update_budget):
    """
    Run one organism with a fixed update budget.
    update_budget = max number of weight updates allowed.
    When budget is exhausted, learning stops but inference continues.
    """
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
        
        hidden.reset()
        syn_in.reset_eligibility()
        syn_rec.reset_eligibility()
        
        for t in range(trial_length):
            x = np.zeros(config['n_input'])
            if t == T_A and A == 1: x[0] = 1.0
            if t == T_B and B == 1: x[1] = 1.0
            
            i_in = syn_in.forward(x)
            i_rec = syn_rec.forward(hidden.last_spikes)
            hidden.step(i_in + i_rec)
            
            # Always update eligibility traces (cheap, local)
            f_prime = hidden.surrogate_derivative(config['beta'])
            syn_in.update_eligibility(x, f_prime, config['tau_e'])
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
                
                # Metabolic constraint: check update budget
                if updates_used < update_budget:
                    # Compute learning signal
                    L_hidden = syn_out.weights.T @ error  
                    L_hidden = np.clip(L_hidden, -1.0, 1.0)
                    
                    # Apply updates
                    syn_in.apply_update(L_hidden, config['eta'])
                    syn_rec.apply_update(L_hidden, config['eta'])
                    
                    delta_out = config['eta'] * np.outer(error, hidden.v) 
                    delta_out = np.clip(delta_out, -1.0, 1.0)
                    syn_out.weights -= delta_out  
                    
                    updates_used += 1
                else:
                    # Budget exhausted - block update
                    updates_blocked += 1
                            
                break
                
    acc = correct / total if total > 0 else 0.0
    mean_loss = np.mean(loss_history[-100:]) if loss_history else 0.0
    
    return {
        'seed': seed,
        'update_budget': update_budget,
        'accuracy': float(acc),
        'loss': float(mean_loss),
        'updates_used': int(updates_used),
        'updates_blocked': int(updates_blocked),
        'n_trials': total,
    }


def plot_pareto(results_by_condition, config):
    """Plot the metabolic Pareto frontier."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Left: Accuracy vs T_block
    t_blocks = [c['T_block_pct'] for c in config['conditions']]
    mean_accs = [results_by_condition[c['label']]['mean_accuracy'] for c in config['conditions']]
    std_accs = [results_by_condition[c['label']]['std_accuracy'] for c in config['conditions']]
    
    ax1.errorbar(t_blocks, mean_accs, yerr=std_accs, marker='o', linewidth=2, 
                 capsize=5, label='Mean ± Std')
    ax1.axhline(y=config['H1_threshold'], color='g', linestyle='--', 
                label=f'H1 threshold ({config["H1_threshold"]*100:.0f}%)')
    ax1.axhline(y=config['H2_threshold'], color='r', linestyle=':', 
                label=f'H2 threshold ({config["H2_threshold"]*100:.0f}%)')
    ax1.axhline(y=0.5, color='gray', linestyle='-', alpha=0.3, label='Random (50%)')
    ax1.set_xlabel('Metabolic Constraint (T_block %)')
    ax1.set_ylabel('Accuracy')
    ax1.set_title('Metabolic Pareto Frontier')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0.4, 1.0)
    ax1.set_xlim(-5, 95)
    
    # Right: Accuracy vs Updates Used
    updates_used = [results_by_condition[c['label']]['mean_updates_used'] for c in config['conditions']]
    
    ax2.scatter(updates_used, mean_accs, s=100, zorder=5)
    for i, c in enumerate(config['conditions']):
        ax2.annotate(c['label'], (updates_used[i], mean_accs[i]), 
                     textcoords="offset points", xytext=(5, 5), fontsize=9)
    ax2.axhline(y=config['H1_threshold'], color='g', linestyle='--', alpha=0.5)
    ax2.axhline(y=config['H2_threshold'], color='r', linestyle=':', alpha=0.5)
    ax2.axhline(y=0.5, color='gray', linestyle='-', alpha=0.3)
    ax2.set_xlabel('Updates Used (metabolic cost)')
    ax2.set_ylabel('Accuracy')
    ax2.set_title('Accuracy vs Metabolic Cost')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0.4, 1.0)
    
    plt.tight_layout()
    plot_path = RESULTS_DIR / 'exp_p2a_02_metabolic_pareto.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    return plot_path


def main():
    print("=" * 70)
    print("Exp-P2A-02: Metabolic Pareto Frontier")
    print("=" * 70)
    print("Pre-registration (Rule 2):")
    print(f"  H1: T_block < 50% → accuracy > {CONFIG['H1_threshold']*100:.0f}%")
    print(f"  H2: T_block = 90% → accuracy > {CONFIG['H2_threshold']*100:.0f}%")
    print(f"  Success = H1 AND H2")
    print()
    print("Conditions:")
    for c in CONFIG['conditions']:
        print(f"  {c['label']:<15} T_block={c['T_block_pct']:>3}%  budget={c['update_budget']}")
    print()
    print(f"Task: Temporal XOR (noise=0%)")
    print(f"Architecture: {CONFIG['n_input']}→{CONFIG['n_hidden']}→{CONFIG['n_output']}")
    print(f"Seeds: {CONFIG['n_seeds']} per condition")
    print("=" * 70)
    print()
    
    results_by_condition = {}
    
    for cond in CONFIG['conditions']:
        label = cond['label']
        budget = cond['update_budget']
        print(f"\n--- Condition: {label} (budget={budget}) ---")
        
        seed_results = []
        for seed_idx in range(CONFIG['n_seeds']):
            seed = CONFIG['random_seed'] + seed_idx
            result = run_organism(CONFIG, seed, budget)
            seed_results.append(result)
            print(f"  seed {seed}: acc={result['accuracy']:.3f}, "
                  f"used={result['updates_used']}, blocked={result['updates_blocked']}")
        
        mean_acc = np.mean([r['accuracy'] for r in seed_results])
        std_acc = np.std([r['accuracy'] for r in seed_results])
        mean_updates = np.mean([r['updates_used'] for r in seed_results])
        mean_blocked = np.mean([r['updates_blocked'] for r in seed_results])
        mean_loss = np.mean([r['loss'] for r in seed_results])
        
        results_by_condition[label] = {
            'T_block_pct': cond['T_block_pct'],
            'update_budget': budget,
            'mean_accuracy': float(mean_acc),
            'std_accuracy': float(std_acc),
            'mean_updates_used': float(mean_updates),
            'mean_updates_blocked': float(mean_blocked),
            'mean_loss': float(mean_loss),
            'seeds': seed_results,
        }
        
        print(f"  → Mean: acc={mean_acc:.3f} ± {std_acc:.3f}")
    
    # Results table
    print("\n" + "=" * 80)
    print("METABOLIC PARETO FRONTIER RESULTS")
    print("=" * 80)
    print(f"{'Condition':<15} | {'T_block%':<10} | {'Accuracy':<12} | {'Updates':<10} | {'Blocked':<10}")
    print("-" * 80)
    
    for cond in CONFIG['conditions']:
        label = cond['label']
        r = results_by_condition[label]
        print(f"{label:<15} | {r['T_block_pct']:<10} | "
              f"{r['mean_accuracy']:.3f}±{r['std_accuracy']:.3f} | "
              f"{r['mean_updates_used']:<10.0f} | {r['mean_updates_blocked']:<10.0f}")
    print("=" * 80)
    
    # Hypothesis testing
    print("\n" + "=" * 70)
    print("HYPOTHESIS TESTING")
    print("=" * 70)
    
    # H1: accuracy at T_block < 50% (conditions: unconstrained, light)
    h1_conditions = ['unconstrained', 'light']
    h1_accs = [results_by_condition[c]['mean_accuracy'] for c in h1_conditions]
    h1_min = min(h1_accs)
    H1_pass = h1_min > CONFIG['H1_threshold']
    
    # H2: accuracy at T_block = 90% (condition: extreme)
    h2_acc = results_by_condition['extreme']['mean_accuracy']
    H2_pass = h2_acc > CONFIG['H2_threshold']
    
    print(f"H1 (T_block<50% → acc>{CONFIG['H1_threshold']*100:.0f}%): "
          f"min_acc={h1_min*100:.1f}% → {'✅ PASS' if H1_pass else '❌ FAIL'}")
    print(f"H2 (T_block=90% → acc>{CONFIG['H2_threshold']*100:.0f}%): "
          f"acc={h2_acc*100:.1f}% → {'✅ PASS' if H2_pass else '❌ FAIL'}")
    
    print()
    if H1_pass and H2_pass:
        print("🎉 SUCCESS: Metabolic constraint has a manageable accuracy cost.")
        print("   The Pareto frontier shows graceful degradation.")
        print("   → Phase 2A hypothesis SUPPORTED")
    elif H1_pass and not H2_pass:
        print("⚠️  PARTIAL: Light constraint is fine, but extreme constraint breaks learning.")
        print("   → There is a critical threshold beyond which learning collapses.")
    elif not H1_pass and H2_pass:
        print("⚠️  UNEXPECTED: Even light constraint hurts, but extreme doesn't.")
        print("   → Check implementation for bugs.")
    else:
        print("❌ FAIL: Metabolic constraint severely impairs learning at all levels.")
        print("   → Phase 2A hypothesis NOT supported under these conditions.")
    
    # Pareto analysis
    print("\n" + "=" * 70)
    print("PARETO ANALYSIS")
    print("=" * 70)
    
    # Find the "knee" of the curve (where accuracy drops most steeply)
    t_blocks = [results_by_condition[c['label']]['T_block_pct'] for c in CONFIG['conditions']]
    accs = [results_by_condition[c['label']]['mean_accuracy'] for c in CONFIG['conditions']]
    
    for i in range(1, len(accs)):
        delta_acc = (accs[i-1] - accs[i]) * 100
        delta_block = t_blocks[i] - t_blocks[i-1]
        slope = delta_acc / delta_block if delta_block > 0 else 0
        print(f"  {t_blocks[i-1]}% → {t_blocks[i]}%: Δacc = {delta_acc:+.1f}pp "
              f"(slope = {slope:.2f} pp/% block)")
    
    # Plot
    plot_path = plot_pareto(results_by_condition, CONFIG)
    print(f"\n📊 Plot: {plot_path}")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_02_metabolic_pareto_{timestamp}.json'
    
    json_data = {
        'timestamp': timestamp,
        'experiment': 'Exp-P2A-02',
        'version': 'Metabolic Pareto Frontier',
        'pre_registration': {
            'H1': f"T_block<50% → acc > {CONFIG['H1_threshold']}",
            'H2': f"T_block=90% → acc > {CONFIG['H2_threshold']}",
            'H1_result': float(h1_min),
            'H2_result': float(h2_acc),
            'H1_pass': bool(H1_pass),
            'H2_pass': bool(H2_pass),
            'success': bool(H1_pass and H2_pass),
        },
        'config': {k: v for k, v in CONFIG.items()},
        'results': {
            label: {
                'T_block_pct': data['T_block_pct'],
                'update_budget': data['update_budget'],
                'mean_accuracy': data['mean_accuracy'],
                'std_accuracy': data['std_accuracy'],
                'mean_updates_used': data['mean_updates_used'],
                'mean_updates_blocked': data['mean_updates_blocked'],
                'mean_loss': data['mean_loss'],
            }
            for label, data in results_by_condition.items()
        },
    }
    
    with open(filename, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"💾 Saved: {filename}")
    print("=" * 70)


if __name__ == '__main__':
    main()