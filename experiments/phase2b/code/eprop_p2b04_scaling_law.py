#!/usr/bin/env python
"""
Exp-P2B-04: Metabolic Scaling Law
===================================
Pre-registration (Rule 2):
  H1: Phase transition threshold scales with network size
      (log-log linear relationship, R² > 0.9)
  H2: 400-neuron threshold > 50-neuron threshold + 10pp
  Success = H1 AND H2

Motivation (Phase 2B, Step B4):
Phase 2A found a phase transition at ~75% blocking for 50-neuron networks.
This experiment tests whether this threshold shifts with network size,
establishing a scaling law for metabolic tolerance.

Biological question:
  Do larger brains have higher metabolic tolerance?
  If yes, what is the scaling relationship?

Design:
  - Network sizes: 50, 100, 200, 400 (geometric progression)
  - Task: Temporal XOR (noise=0%, same as Phase 2A)
  - Conditions: 0%, 25%, 50%, 75%, 90% blocking
  - Measure: phase transition threshold for each size
  - Fit: power law (log-log linear regression)

Expected outcome:
  threshold = a * (n_neurons)^b
  
  If b > 0: larger networks have higher metabolic tolerance
  If b ≈ 0: threshold is size-independent
  If b < 0: larger networks have lower tolerance (unlikely)
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
    
    # Network sizes (geometric progression for power law fit)
    'network_sizes': [50, 100, 200, 400],
    
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
    
    # Phase transition detection
    'phase_transition_threshold': 0.70,  # accuracy below which = collapse
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


def run_organism(config, seed, n_hidden, update_budget):
    """Run one organism with given size and update budget."""
    T_A = config['T_A']
    T_B = config['T_B']
    T_target = config['T_target']
    trial_length = config['trial_length']
    n_trials = config['n_trials']
    
    hidden = LIFNetwork(n_hidden, theta=config['theta'], 
                        tau_mem=config['tau_mem'], tau_syn=config['tau_syn'])
    
    syn_in = SynapticLayer(config['n_input'], n_hidden, 
                           w_scale=config['w_scale'], seed=seed)
    syn_rec = SynapticLayer(n_hidden, n_hidden, 
                            w_scale=config['w_scale'] * 0.5, seed=seed+1)
    syn_out = SynapticLayer(n_hidden, config['n_output'], 
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
                
                if updates_used < update_budget:
                    L_hidden = syn_out.weights.T @ error
                    L_hidden = np.clip(L_hidden, -1.0, 1.0)
                    
                    syn_in.apply_update(L_hidden, config['eta'])
                    syn_rec.apply_update(L_hidden, config['eta'])
                    
                    delta_out = config['eta'] * np.outer(error, hidden.v)
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
        'update_budget': update_budget,
        'accuracy': float(acc),
        'loss': float(mean_loss),
        'updates_used': int(updates_used),
        'updates_blocked': int(updates_blocked),
        'n_trials': total,
    }


def find_phase_transition(t_blocks, accs, threshold):
    """Find the block rate where accuracy drops below threshold."""
    for i, acc in enumerate(accs):
        if acc < threshold:
            # Interpolate between previous and current
            if i == 0:
                return t_blocks[i]
            else:
                # Linear interpolation
                prev_acc = accs[i-1]
                prev_block = t_blocks[i-1]
                curr_acc = acc
                curr_block = t_blocks[i]
                
                if prev_acc > threshold and curr_acc < threshold:
                    # Interpolate
                    fraction = (prev_acc - threshold) / (prev_acc - curr_acc)
                    return prev_block + fraction * (curr_block - prev_block)
                else:
                    return curr_block
    return None  # Never drops below threshold


def fit_power_law(sizes, thresholds):
    """Fit power law: threshold = a * size^b using log-log regression."""
    # Filter out None values
    valid_pairs = [(s, t) for s, t in zip(sizes, thresholds) if t is not None]
    
    if len(valid_pairs) < 2:
        return None, None, None, None
    
    log_sizes = np.log([p[0] for p in valid_pairs])
    log_thresholds = np.log([p[1] for p in valid_pairs])
    
    # Linear regression in log-log space
    n = len(log_sizes)
    sum_x = np.sum(log_sizes)
    sum_y = np.sum(log_thresholds)
    sum_xy = np.sum(log_sizes * log_thresholds)
    sum_x2 = np.sum(log_sizes ** 2)
    
    # Slope and intercept
    b = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
    log_a = (sum_y - b * sum_x) / n
    a = np.exp(log_a)
    
    # R² calculation
    y_pred = b * log_sizes + log_a
    ss_res = np.sum((log_thresholds - y_pred) ** 2)
    ss_tot = np.sum((log_thresholds - np.mean(log_thresholds)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return a, b, r_squared, valid_pairs


def plot_scaling_law(results, config):
    """Plot scaling law in log-log space."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Left: Accuracy vs Block Rate for each size
    t_blocks = [c['T_block_pct'] for c in config['conditions']]
    
    for n_hidden in config['network_sizes']:
        accs = [results[n_hidden][c['label']]['mean_accuracy'] for c in config['conditions']]
        ax1.plot(t_blocks, accs, marker='o', linewidth=2, label=f'{n_hidden} neurons')
    
    ax1.axhline(y=config['phase_transition_threshold'], color='r', linestyle='--', 
                label=f'Threshold ({config["phase_transition_threshold"]*100:.0f}%)')
    ax1.set_xlabel('Metabolic Constraint (T_block %)')
    ax1.set_ylabel('Accuracy')
    ax1.set_title('Phase Transition vs Network Size')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0.4, 1.0)
    
    # Right: Log-log plot of threshold vs size
    thresholds = []
    for n_hidden in config['network_sizes']:
        accs = [results[n_hidden][c['label']]['mean_accuracy'] for c in config['conditions']]
        threshold = find_phase_transition(t_blocks, accs, config['phase_transition_threshold'])
        thresholds.append(threshold)
    
    # Fit power law
    a, b, r_squared, valid_pairs = fit_power_law(config['network_sizes'], thresholds)
    
    # Plot data points
    valid_sizes = [p[0] for p in valid_pairs]
    valid_thresholds = [p[1] for p in valid_pairs]
    ax2.scatter(valid_sizes, valid_thresholds, s=100, zorder=5, label='Data')
    
    # Plot fit line
    if a is not None and b is not None:
        x_fit = np.array([min(valid_sizes), max(valid_sizes)])
        y_fit = a * x_fit ** b
        ax2.plot(x_fit, y_fit, 'r--', linewidth=2, 
                label=f'Fit: y = {a:.2f} * x^{b:.2f}\nR² = {r_squared:.3f}')
    
    ax2.set_xlabel('Network Size (neurons)')
    ax2.set_ylabel('Phase Transition Threshold (% block)')
    ax2.set_title('Metabolic Scaling Law (Log-Log)')
    ax2.set_xscale('log')
    ax2.set_yscale('log')
    ax2.legend()
    ax2.grid(True, alpha=0.3, which='both')
    
    plt.tight_layout()
    plot_path = RESULTS_DIR / 'exp_p2b_04_scaling_law.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    return plot_path, thresholds, (a, b, r_squared)


def main():
    print("=" * 70)
    print("Exp-P2B-04: Metabolic Scaling Law")
    print("=" * 70)
    print("Pre-registration (Rule 2):")
    print("  H1: Power law scaling (R² > 0.9)")
    print("  H2: 400-neuron threshold > 50-neuron + 10pp")
    print("  Success = H1 AND H2")
    print()
    print("Network sizes:", CONFIG['network_sizes'])
    print("Conditions:", [c['label'] for c in CONFIG['conditions']])
    print("Task: Temporal XOR (noise=0%)")
    print("=" * 70)
    print()
    
    results = {}
    
    for n_hidden in CONFIG['network_sizes']:
        print(f"\n{'='*50}")
        print(f"Network Size: {n_hidden} neurons")
        print(f"{'='*50}")
        
        results[n_hidden] = {}
        
        for cond in CONFIG['conditions']:
            label = cond['label']
            budget = int(500 * cond['budget_fraction'])
            
            print(f"\n  --- {label} (budget={budget}) ---")
            
            seed_results = []
            for seed_idx in range(CONFIG['n_seeds']):
                seed = CONFIG['random_seed'] + seed_idx
                result = run_organism(CONFIG, seed, n_hidden, budget)
                seed_results.append(result)
                print(f"    seed {seed}: acc={result['accuracy']:.3f}")
            
            mean_acc = np.mean([r['accuracy'] for r in seed_results])
            std_acc = np.std([r['accuracy'] for r in seed_results])
            
            results[n_hidden][label] = {
                'T_block_pct': cond['T_block_pct'],
                'update_budget': budget,
                'mean_accuracy': float(mean_acc),
                'std_accuracy': float(std_acc),
                'seeds': seed_results,
            }
            
            print(f"    → Mean: {mean_acc:.3f} ± {std_acc:.3f}")
    
    # Results table
    print("\n" + "=" * 100)
    print("RESULTS: Metabolic Scaling Law")
    print("=" * 100)
    
    header = f"{'Size':<8}"
    for cond in CONFIG['conditions']:
        header += f" | {cond['label']:<12}"
    print(header)
    print("-" * 100)
    
    for n_hidden in CONFIG['network_sizes']:
        row = f"{n_hidden:<8}"
        for cond in CONFIG['conditions']:
            label = cond['label']
            acc = results[n_hidden][label]['mean_accuracy']
            std = results[n_hidden][label]['std_accuracy']
            row += f" | {acc:.3f}±{std:.3f}  "
        print(row)
    
    # Find phase transitions
    print("\n" + "=" * 70)
    print("PHASE TRANSITION DETECTION")
    print("=" * 70)
    
    t_blocks = [c['T_block_pct'] for c in CONFIG['conditions']]
    thresholds = []
    
    for n_hidden in CONFIG['network_sizes']:
        accs = [results[n_hidden][c['label']]['mean_accuracy'] for c in CONFIG['conditions']]
        threshold = find_phase_transition(t_blocks, accs, CONFIG['phase_transition_threshold'])
        thresholds.append(threshold)
        
        if threshold is not None:
            print(f"  {n_hidden:3d} neurons: Phase transition at {threshold:.1f}% block")
        else:
            print(f"  {n_hidden:3d} neurons: No phase transition (robust up to 90%)")
    
    # Fit power law
    print("\n" + "=" * 70)
    print("POWER LAW FIT")
    print("=" * 70)
    
    plot_path, thresholds, (a, b, r_squared) = plot_scaling_law(results, CONFIG)
    
    if a is not None and b is not None:
        print(f"  Model: threshold = {a:.2f} * (n_neurons)^{b:.2f}")
        print(f"  R² = {r_squared:.3f}")
        print(f"  Interpretation: ", end="")
        if b > 0:
            print(f"Larger networks have HIGHER metabolic tolerance (+{b:.2f} scaling)")
        elif b < 0:
            print(f"Larger networks have LOWER metabolic tolerance ({b:.2f} scaling)")
        else:
            print("Threshold is size-independent")
    
    # Hypothesis testing
    print("\n" + "=" * 70)
    print("HYPOTHESIS TESTING")
    print("=" * 70)
    
    # H1: Power law fit (R² > 0.9)
    if r_squared is not None:
        H1_pass = r_squared > 0.9
        print(f"H1 (Power law R² > 0.9): actual={r_squared:.3f} → {'✅ PASS' if H1_pass else '❌ FAIL'}")
    else:
        H1_pass = False
        print("H1 (Power law R² > 0.9): insufficient data → ❌ FAIL")
    
    # H2: 400 > 50 + 10pp
    if len(thresholds) >= 2 and thresholds[0] is not None and thresholds[-1] is not None:
        threshold_50 = thresholds[0]
        threshold_400 = thresholds[-1]
        delta = threshold_400 - threshold_50
        H2_pass = delta > 10.0
        print(f"H2 (400 > 50 + 10pp): 50={threshold_50:.1f}%, 400={threshold_400:.1f}% "
              f"(Δ={delta:+.1f}pp) → {'✅ PASS' if H2_pass else '❌ FAIL'}")
    else:
        H2_pass = False
        print("H2 (400 > 50 + 10pp): insufficient data → ❌ FAIL")
    
    print()
    if H1_pass and H2_pass:
        print("🎉 SUCCESS: Metabolic tolerance scales with network size!")
        print("   → Larger networks can tolerate more metabolic constraint.")
        print("   → This provides a design principle for scaling biologically-plausible AGI.")
    elif H1_pass and not H2_pass:
        print("⚠️  PARTIAL: Scaling law exists but effect is small.")
        print("   → Size helps, but not dramatically.")
    elif not H1_pass and H2_pass:
        print("⚠️  PARTIAL: 400 > 50 but no clear scaling law.")
        print("   → May need more data points or different model.")
    else:
        print("❌ FAIL: No clear scaling relationship found.")
        print("   → Phase transition threshold may be size-independent.")
        print("   → Or need different experimental design.")
    
    # Biological interpretation
    print("\n" + "=" * 70)
    print("BIOLOGICAL INTERPRETATION")
    print("=" * 70)
    
    if b is not None and b > 0:
        print("Positive scaling (b > 0) suggests:")
        print("  - Larger brains have higher metabolic tolerance")
        print("  - Redundancy and distributed representation help")
        print("  - Consistent with observed scaling in biological systems")
    elif b is not None and b < 0:
        print("Negative scaling (b < 0) suggests:")
        print("  - Larger networks are LESS metabolically efficient")
        print("  - Coordination overhead increases with size")
        print("  - Contradicts biological observations (unexpected)")
    else:
        print("No clear scaling suggests:")
        print("  - Phase transition is a property of the learning rule, not size")
        print("  - All e-prop systems have similar metabolic constraints")
    
    print(f"\n📊 Plot: {plot_path}")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2b_04_scaling_law_{timestamp}.json'
    
    json_data = {
        'timestamp': timestamp,
        'experiment': 'Exp-P2B-04',
        'version': 'Metabolic Scaling Law',
        'pre_registration': {
            'H1': "Power law R² > 0.9",
            'H2': "400-neuron > 50-neuron + 10pp",
            'r_squared': float(r_squared) if r_squared is not None else None,
            'threshold_50': float(thresholds[0]) if thresholds[0] is not None else None,
            'threshold_400': float(thresholds[-1]) if thresholds[-1] is not None else None,
            'H1_pass': bool(H1_pass),
            'H2_pass': bool(H2_pass),
            'success': bool(H1_pass and H2_pass),
        },
        'config': CONFIG,
        'power_law_fit': {
            'a': float(a) if a is not None else None,
            'b': float(b) if b is not None else None,
            'r_squared': float(r_squared) if r_squared is not None else None,
        },
        'results': {
            str(n_hidden): {
                cond_label: {
                    'T_block_pct': data['T_block_pct'],
                    'update_budget': data['update_budget'],
                    'mean_accuracy': data['mean_accuracy'],
                    'std_accuracy': data['std_accuracy'],
                }
                for cond_label, data in conds.items()
            }
            for n_hidden, conds in results.items()
        },
        'phase_transitions': {
            str(n): t for n, t in zip(CONFIG['network_sizes'], thresholds)
        },
    }
    
    with open(filename, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"💾 Saved: {filename}")
    print("=" * 70)


if __name__ == '__main__':
    main()