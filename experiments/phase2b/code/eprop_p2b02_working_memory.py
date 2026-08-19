#!/usr/bin/env python
"""
Exp-P2B-02: Working Memory Module for Temporal Credit Assignment
=================================================================
Pre-registration (Rule 2):
  H1: With WM, accuracy on DMS task > 80% (delay=10 ticks)
  H2: Without WM, accuracy on DMS task < 60% (delay=10 ticks)
  H3: WM accuracy degrades gracefully with metabolic constraint
      (at 50% block, WM accuracy > 70%)
  Success = H1 AND H2 AND H3

Motivation (Phase 2B, Step B2):
Phase 2A showed e-prop struggles with temporal gaps (noise problem).
This experiment tests whether a working memory module (neurons with
slow membrane time constants) can bridge longer temporal gaps.

Biological parallel: Prefrontal cortex working memory neurons show
persistent activity during delay periods.

Design:
  - Task: Delayed Match-to-Sample (DMS)
    - Sample at t=3 (A or B stimulus)
    - Delay: t=4 to t=12 (9 ticks)
    - Test at t=13 (A or B stimulus)
    - Response at t=13: match or non-match?
  - Architecture:
    - Without WM: 2→50→2 (standard LIF, tau_mem=20)
    - With WM: 2→50→2 + 20 WM neurons (tau_mem=200)
  - Conditions: 0%, 50%, 75% block
  - 5 seeds per condition
"""

import numpy as np
import json
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path

CONFIG = {
    'trial_length': 16,
    'n_trials': 500,
    'T_sample': 3,
    'T_test': 13,
    'delay_ticks': 9,  # t=4 to t=12
    
    'n_input': 2,
    'n_output': 2,  # match vs non-match
    
    'theta': 1.0,
    'tau_mem_fast': 20.0,   # standard LIF
    'tau_mem_slow': 200.0,  # working memory LIF
    'tau_syn': 20.0,
    
    'tau_e': 15.0,  
    'beta': 1.0,
    
    'eta': 0.01,
    'w_scale': 0.5,
    
    # Architectures
    'architectures': [
        {'label': 'no_WM', 'n_hidden': 50, 'n_wm': 0},
        {'label': 'with_WM', 'n_hidden': 50, 'n_wm': 20},
    ],
    
    # Metabolic conditions
    'conditions': [
        {'label': 'unconstrained', 'T_block_pct': 0,  'budget_fraction': 1.0},
        {'label': 'moderate',      'T_block_pct': 50, 'budget_fraction': 0.50},
        {'label': 'heavy',         'T_block_pct': 75, 'budget_fraction': 0.25},
    ],
    
    'n_seeds': 5,
    'random_seed': 42,
}

RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)


class LIFNeuron:
    """Single LIF neuron with configurable time constant."""
    def __init__(self, theta=1.0, tau_mem=20.0, tau_syn=20.0):
        self.theta = theta
        self.dt_tau_mem = 1.0 / tau_mem
        self.dt_tau_syn = 1.0 / tau_syn
        self.v = 0.0
        self.i_syn = 0.0
        self.last_spike = 0.0
        self.pre_reset_v = 0.0
        
    def step(self, i_in):
        self.i_syn = self.i_syn * (1 - self.dt_tau_syn) + i_in
        self.v = self.v * (1 - self.dt_tau_mem) + self.i_syn
        
        self.pre_reset_v = self.v
        if self.v >= self.theta:
            self.v = 0.0
            self.last_spike = 1.0
        else:
            self.last_spike = 0.0
        return self.last_spike
    
    def reset(self):
        self.v = 0.0
        self.i_syn = 0.0
        self.last_spike = 0.0
        self.pre_reset_v = 0.0
    
    def surrogate_derivative(self, beta):
        diff = abs(self.pre_reset_v - self.theta)
        f_prime = 1.0 / (1.0 + beta * diff)
        return min(f_prime, 1.0)


class LIFPopulation:
    """Population of LIF neurons with same time constant."""
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


def generate_dms_trial(rng):
    """Generate a Delayed Match-to-Sample trial."""
    sample = rng.randint(0, 2)  # 0 or 1
    test = rng.randint(0, 2)    # 0 or 1
    is_match = int(sample == test)
    return sample, test, is_match


def run_organism(config, seed, n_hidden, n_wm, update_budget):
    """Run one organism with optional working memory module."""
    T_sample = config['T_sample']
    T_test = config['T_test']
    trial_length = config['trial_length']
    n_trials = config['n_trials']
    
    # Build network
    hidden = LIFPopulation(n_hidden, theta=config['theta'], 
                           tau_mem=config['tau_mem_fast'], tau_syn=config['tau_syn'])
    
    wm = None
    if n_wm > 0:
        wm = LIFPopulation(n_wm, theta=config['theta'],
                          tau_mem=config['tau_mem_slow'], tau_syn=config['tau_syn'])
    
    # Synaptic layers
    syn_in = SynapticLayer(config['n_input'], n_hidden, 
                           w_scale=config['w_scale'], seed=seed)
    
    if n_wm > 0:
        syn_wm_in = SynapticLayer(config['n_input'], n_wm,
                                 w_scale=config['w_scale'], seed=seed+10)
        syn_wm_hidden = SynapticLayer(n_wm, n_hidden,
                                     w_scale=config['w_scale'], seed=seed+11)
    
    syn_out = SynapticLayer(n_hidden, config['n_output'],
                            w_scale=config['w_scale'], seed=seed+2)
    
    correct = 0
    total = 0
    updates_used = 0
    updates_blocked = 0
    loss_history = []
    
    rng = np.random.RandomState(seed)
    
    for trial in range(n_trials):
        sample, test, is_match = generate_dms_trial(rng)
        
        hidden.reset()
        if wm is not None:
            wm.reset()
        syn_in.reset_eligibility()
        if n_wm > 0:
            syn_wm_in.reset_eligibility()
            syn_wm_hidden.reset_eligibility()
        
        for t in range(trial_length):
            # Input encoding
            x = np.zeros(config['n_input'])
            if t == T_sample:
                x[sample] = 1.0  # Present sample stimulus
            if t == T_test:
                x[test] = 1.0    # Present test stimulus
            
            # Forward pass
            i_in = syn_in.forward(x)
            
            if n_wm > 0:
                # Working memory receives input directly
                i_wm = syn_wm_in.forward(x)
                wm.step(i_wm)
                
                # Working memory projects to hidden
                i_wm_to_hidden = syn_wm_hidden.forward(wm.last_spikes)
                hidden.step(i_in + i_wm_to_hidden)
            else:
                hidden.step(i_in)
            
            # Update eligibility traces
            f_prime_hidden = hidden.surrogate_derivative(config['beta'])
            syn_in.update_eligibility(x, f_prime_hidden, config['tau_e'])
            
            if n_wm > 0:
                f_prime_wm = wm.surrogate_derivative(config['beta'])
                syn_wm_in.update_eligibility(x, f_prime_wm, config['tau_e'])
                syn_wm_hidden.update_eligibility(wm.last_spikes, f_prime_hidden, config['tau_e'])
            
            # Output at test time
            if t == T_test:
                out_logits = syn_out.weights @ hidden.last_spikes
                y = softmax(out_logits)
                pred = int(y.argmax())
                if pred == is_match:
                    correct += 1
                total += 1
                
                target_vec = np.zeros(config['n_output'])
                target_vec[is_match] = 1.0
                error = y - target_vec
                loss = -np.log(y[is_match] + 1e-8)
                loss_history.append(loss)
                
                # Metabolic constraint
                if updates_used < update_budget:
                    L_hidden = syn_out.weights.T @ error
                    L_hidden = np.clip(L_hidden, -1.0, 1.0)
                    
                    syn_in.apply_update(L_hidden, config['eta'])
                    
                    if n_wm > 0:
                        L_wm = syn_wm_hidden.weights.T @ L_hidden
                        L_wm = np.clip(L_wm, -1.0, 1.0)
                        syn_wm_in.apply_update(L_wm, config['eta'])
                        syn_wm_hidden.apply_update(L_hidden, config['eta'])
                    
                    delta_out = config['eta'] * np.outer(error, hidden.last_spikes)
                    delta_out = np.clip(delta_out, -1.0, 1.0)
                    syn_out.weights -= delta_out
                    
                    updates_used += 1
                else:
                    updates_blocked += 1
                
                break
    
    acc = correct / total if total > 0 else 0.0
    mean_loss = np.mean(loss_history[-100:]) if loss_history else 0.0
    
    return {
        'seed': seed,
        'n_hidden': n_hidden,
        'n_wm': n_wm,
        'update_budget': update_budget,
        'accuracy': float(acc),
        'loss': float(mean_loss),
        'updates_used': int(updates_used),
        'updates_blocked': int(updates_blocked),
        'n_trials': total,
    }


def plot_results(results, config):
    """Plot WM vs no-WM comparison."""
    fig, ax = plt.subplots(figsize=(10, 7))
    
    t_blocks = [c['T_block_pct'] for c in config['conditions']]
    
    for arch in config['architectures']:
        label = arch['label']
        mean_accs = [results[label][c['label']]['mean_accuracy'] for c in config['conditions']]
        std_accs = [results[label][c['label']]['std_accuracy'] for c in config['conditions']]
        
        ax.errorbar(t_blocks, mean_accs, yerr=std_accs, marker='o',
                    linewidth=2, capsize=5, label=label)
    
    ax.axhline(y=0.5, color='gray', linestyle='-', alpha=0.3, label='Random')
    ax.set_xlabel('Metabolic Constraint (T_block %)')
    ax.set_ylabel('Accuracy')
    ax.set_title('Phase 2B-02: Working Memory for Temporal Tasks')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0.4, 1.0)
    
    plot_path = RESULTS_DIR / 'exp_p2b_02_working_memory.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    return plot_path


def main():
    print("=" * 70)
    print("Exp-P2B-02: Working Memory for Temporal Credit Assignment")
    print("=" * 70)
    print("Pre-registration (Rule 2):")
    print("  H1: With WM, DMS accuracy > 80% (delay=9 ticks)")
    print("  H2: Without WM, DMS accuracy < 60%")
    print("  H3: WM at 50% block > 70%")
    print("  Success = H1 AND H2 AND H3")
    print()
    print("Task: Delayed Match-to-Sample")
    print(f"  Sample at t={CONFIG['T_sample']}, Test at t={CONFIG['T_test']}")
    print(f"  Delay: {CONFIG['delay_ticks']} ticks")
    print()
    print("Architectures:")
    for arch in CONFIG['architectures']:
        print(f"  {arch['label']}: {arch['n_hidden']} hidden + {arch['n_wm']} WM")
    print("=" * 70)
    print()
    
    results = {}
    
    for arch in CONFIG['architectures']:
        arch_label = arch['label']
        n_hidden = arch['n_hidden']
        n_wm = arch['n_wm']
        
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
                result = run_organism(CONFIG, seed, n_hidden, n_wm, budget)
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
    print("\n" + "=" * 80)
    print("RESULTS: Working Memory Effect")
    print("=" * 80)
    print(f"{'Architecture':<15} | {'0%':<15} | {'50%':<15} | {'75%':<15}")
    print("-" * 80)
    
    for arch_label in results:
        accs = [results[arch_label][c['label']]['mean_accuracy'] for c in CONFIG['conditions']]
        stds = [results[arch_label][c['label']]['std_accuracy'] for c in CONFIG['conditions']]
        print(f"{arch_label:<15} | {accs[0]:.3f}±{stds[0]:.3f} | "
              f"{accs[1]:.3f}±{stds[1]:.3f} | {accs[2]:.3f}±{stds[2]:.3f}")
    
    # Hypothesis testing
    print("\n" + "=" * 70)
    print("HYPOTHESIS TESTING")
    print("=" * 70)
    
    # H1: With WM, accuracy > 80%
    wm_acc = results['with_WM']['unconstrained']['mean_accuracy']
    H1_pass = wm_acc > 0.80
    print(f"H1 (WM acc > 80%): actual={wm_acc*100:.1f}% → {'✅ PASS' if H1_pass else '❌ FAIL'}")
    
    # H2: Without WM, accuracy < 60%
    no_wm_acc = results['no_WM']['unconstrained']['mean_accuracy']
    H2_pass = no_wm_acc < 0.60
    print(f"H2 (no-WM acc < 60%): actual={no_wm_acc*100:.1f}% → {'✅ PASS' if H2_pass else '❌ FAIL'}")
    
    # H3: WM at 50% block > 70%
    wm_acc_50 = results['with_WM']['moderate']['mean_accuracy']
    H3_pass = wm_acc_50 > 0.70
    print(f"H3 (WM at 50% > 70%): actual={wm_acc_50*100:.1f}% → {'✅ PASS' if H3_pass else '❌ FAIL'}")
    
    print()
    if H1_pass and H2_pass and H3_pass:
        print("🎉 SUCCESS: Working memory enables temporal credit assignment!")
        print("   → WM neurons bridge the delay period effectively.")
        print("   → Phase 2B hypothesis SUPPORTED")
    elif H1_pass and not H2_pass:
        print("⚠️  PARTIAL: WM helps, but no-WM also works.")
        print("   → Delay may be too short. Try longer delays.")
    elif not H1_pass and H2_pass:
        print("⚠️  PARTIAL: No-WM fails as expected, but WM also fails.")
        print("   → WM implementation may need tuning.")
    else:
        print("❌ FAIL: Working memory does not help.")
        print("   → Fundamental limitation or implementation issue.")
    
    # Plot
    plot_path = plot_results(results, CONFIG)
    print(f"\n📊 Plot: {plot_path}")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2b_02_working_memory_{timestamp}.json'
    
    json_data = {
        'timestamp': timestamp,
        'experiment': 'Exp-P2B-02',
        'version': 'Working Memory for Temporal Credit Assignment',
        'pre_registration': {
            'H1': "WM accuracy > 80%",
            'H2': "No-WM accuracy < 60%",
            'H3': "WM at 50% block > 70%",
            'wm_acc': float(wm_acc),
            'no_wm_acc': float(no_wm_acc),
            'wm_acc_50': float(wm_acc_50),
            'H1_pass': bool(H1_pass),
            'H2_pass': bool(H2_pass),
            'H3_pass': bool(H3_pass),
            'success': bool(H1_pass and H2_pass and H3_pass),
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