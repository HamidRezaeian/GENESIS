#!/usr/bin/env python
"""
Exp-P2A-01 v26: Sparse Input Encoding (Opus Consultation Implementation)
========================================================================
Pre-registration (Rule 2):
  H1: v26 در noise=5% باید accuracy > 76.8% داشته باشد
      (A1_v25 = 66.8% + 10pp improvement threshold)
  H2: v26 در noise=0% باید accuracy > 88.7% داشته باشد
      (A1_v25 = 90.7% - 2pp tolerance)
  Success = H1 AND H2

Changes from v25:
  - Input encoding: 2 dense → 20 sparse (3 of 10 per bit)
  - A encoded on neurons 0-9 (0→[0:3], 1→[3:6])
  - B encoded on neurons 10-19 (0→[10:13], 1→[13:16])
  - Noise on neurons 16-19 (dedicated noise channels)

Biological justification:
  Sparse distributed codes are standard in cortex (Barth & Poulet 2012).
  15% sparsity matches cortical sparse coding estimates.
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
    
    # Sparse Input Encoding (Opus recommendation)
    'n_input': 20,
    'neurons_per_bit': 3,
    'A_zero_range': (0, 3),    # A=0 → neurons 0,1,2
    'A_one_range': (3, 6),     # A=1 → neurons 3,4,5
    'B_zero_range': (10, 13),  # B=0 → neurons 10,11,12
    'B_one_range': (13, 16),   # B=1 → neurons 13,14,15
    'noise_range': (16, 20),   # Noise channels: neurons 16-19
    
    'n_hidden': 50,
    'n_output': 2,
    
    'theta': 1.0,
    'tau_mem': 20.0,
    'tau_syn': 20.0,
    
    'tau_e': 15.0,  
    'beta': 1.0,
    
    'eta': 0.01,
    'w_scale': 0.5,
    
    'plasticity_pool_capacity': 50.0,
    'refill_rate': 1.0,
    'update_cost': 1.0,
    
    'arms': ['A1_buffered', 'A2_nolearn', 'A3_coupled'],
    'n_seeds': 5,
    'random_seed': 42,
    
    'noise_levels': [0.0, 0.05, 0.1, 0.2, 0.3, 0.5],
    'failure_threshold': 0.70,
    
    # Pre-registration thresholds
    'H1_threshold': 0.768,  # A1_v25 (66.8%) + 10pp
    'H2_threshold': 0.887,  # A1_v25 (90.7%) - 2pp
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

class PlasticityBuffer:
    def __init__(self, capacity=50.0, refill_rate=1.0, update_cost=1.0):
        self.pool = capacity / 2
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.update_cost = update_cost
        self.blocked_updates = 0
        self.total_updates = 0
        
    def refill(self, M_t):
        if M_t > 0:
            self.pool = min(self.capacity, self.pool + self.refill_rate * M_t)
    
    def can_update(self):
        return self.pool >= self.update_cost
    
    def spend(self):
        if self.can_update():
            self.pool -= self.update_cost
            self.total_updates += 1
            return True
        else:
            self.blocked_updates += 1
            return False

def softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()

def encode_sparse_input(A, B, t, T_A, T_B, noise_level, rng, config):
    """
    Sparse distributed encoding (Opus recommendation).
    Each bit encoded by 3 out of 10 neurons (15% sparsity).
    Noise applied only to dedicated noise channels (16-19).
    """
    x = np.zeros(config['n_input'])
    
    # Encode A at T_A
    if t == T_A:
        if A == 0:
            start, end = config['A_zero_range']
        else:
            start, end = config['A_one_range']
        x[start:end] = 1.0
    
    # Encode B at T_B
    if t == T_B:
        if B == 0:
            start, end = config['B_zero_range']
        else:
            start, end = config['B_one_range']
        x[start:end] = 1.0
    
    # Noise on dedicated channels only
    if noise_level > 0:
        noise_start, noise_end = config['noise_range']
        n_noise_neurons = noise_end - noise_start
        for i in range(noise_start, noise_end):
            if rng.rand() < noise_level:
                x[i] = 1.0
    
    return x

def run_organism(arm, config, seed, noise_level):
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
    
    buffer = None
    if arm == 'A1_buffered':
        buffer = PlasticityBuffer(
            capacity=config['plasticity_pool_capacity'],
            refill_rate=config['refill_rate'],
            update_cost=config['update_cost']
        )
    
    correct = 0
    total = 0
    total_updates = 0
    blocked_updates = 0
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
            x = encode_sparse_input(A, B, t, T_A, T_B, noise_level, rng, config)
            
            i_in = syn_in.forward(x)
            i_rec = syn_rec.forward(hidden.last_spikes)
            hidden.step(i_in + i_rec)
            
            if arm in ['A1_buffered', 'A3_coupled']:
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
                
                if arm in ['A1_buffered', 'A3_coupled']:
                    M_t = float(np.max(np.abs(error)))
                    if buffer is not None:
                        buffer.refill(M_t)
                    
                    L_hidden = syn_out.weights.T @ error  
                    L_hidden = np.clip(L_hidden, -1.0, 1.0)
                    
                    can_update = True
                    if buffer is not None:
                        can_update = buffer.can_update()
                        if not can_update:
                            blocked_updates += 1
                    
                    if can_update:
                        syn_in.apply_update(L_hidden, config['eta'])
                        syn_rec.apply_update(L_hidden, config['eta'])
                        
                        delta_out = config['eta'] * np.outer(error, hidden.v) 
                        delta_out = np.clip(delta_out, -1.0, 1.0)
                        syn_out.weights -= delta_out  
                        
                        total_updates += 1
                        if buffer is not None:
                            buffer.spend()
                            
                break
                
    acc = correct / total if total > 0 else 0.0
    mean_loss = np.mean(loss_history[-100:]) if loss_history else 0.0
    
    buffer_stats = {}
    if buffer is not None:
        buffer_stats = {
            'final_pool': float(buffer.pool),
            'blocked_updates': buffer.blocked_updates,
            'successful_updates': buffer.total_updates,
        }
    
    return {
        'arm': arm,
        'seed': seed,
        'noise_level': noise_level,
        'accuracy': float(acc),
        'loss': float(mean_loss),
        'updates': int(total_updates),
        'blocked_updates': int(blocked_updates),
        'n_trials': total,
        'buffer_stats': buffer_stats,
    }

def find_failure_point(noise_levels, accuracies, threshold):
    for i, acc in enumerate(accuracies):
        if acc < threshold:
            return noise_levels[i]
    return None

def plot_results(sweep_data, config):
    plt.figure(figsize=(12, 7))
    
    noise_levels = config['noise_levels']
    
    # Plot v26 results
    for arm_name in ['A1_buffered', 'A2_nolearn', 'A3_coupled']:
        accs = [sweep_data[str(nl)][arm_name]['mean_accuracy'] for nl in noise_levels]
        plt.plot(noise_levels, accs, marker='o', linewidth=2, label=f'v26 {arm_name}')
    
    # Reference lines from v25 (for comparison)
    plt.axhline(y=config['H1_threshold'], color='g', linestyle='--', 
                label=f'H1 threshold ({config["H1_threshold"]*100:.1f}%)')
    plt.axhline(y=config['H2_threshold'], color='b', linestyle=':', 
                label=f'H2 threshold ({config["H2_threshold"]*100:.1f}%)')
    plt.axhline(y=config['failure_threshold'], color='r', linestyle='--', 
                label=f'Failure threshold ({config["failure_threshold"]*100:.0f}%)')
    
    plt.xlabel('Noise Level (probability per noise neuron per tick)')
    plt.ylabel('Accuracy')
    plt.title('v26: Sparse Input Encoding - Noise Tolerance')
    plt.legend(loc='lower left')
    plt.grid(True, alpha=0.3)
    plt.ylim(0.4, 1.0)
    
    plot_path = RESULTS_DIR / 'exp_p2a_01_v26_sparse_encoding.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    return plot_path

def main():
    print("=" * 70)
    print("Exp-P2A-01 v26: Sparse Input Encoding (Opus Consultation)")
    print("=" * 70)
    print("Pre-registration:")
    print(f"  H1: noise=5% → accuracy > {CONFIG['H1_threshold']*100:.1f}%")
    print(f"  H2: noise=0% → accuracy > {CONFIG['H2_threshold']*100:.1f}%")
    print(f"  Success = H1 AND H2")
    print()
    print(f"Sparse encoding: {CONFIG['n_input']} inputs, "
          f"{CONFIG['neurons_per_bit']} neurons per bit")
    print(f"Noise channels: neurons {CONFIG['noise_range'][0]}-{CONFIG['noise_range'][1]}")
    print(f"Noise Levels: {CONFIG['noise_levels']}")
    print("=" * 70)
    print()
    
    sweep_data = {}
    
    for nl in CONFIG['noise_levels']:
        print(f"\n--- Noise Level: {nl} ---")
        sweep_data[str(nl)] = {}
        
        for arm in CONFIG['arms']:
            print(f"  {arm}:", end=" ")
            seed_results = []
            
            for seed_idx in range(CONFIG['n_seeds']):
                seed = CONFIG['random_seed'] + seed_idx * 10 + hash(str(nl)) % 10
                result = run_organism(arm, CONFIG, seed, nl)
                seed_results.append(result)
                
            mean_acc = np.mean([r['accuracy'] for r in seed_results])
            mean_loss = np.mean([r['loss'] for r in seed_results])
            mean_updates = np.mean([r['updates'] for r in seed_results])
            mean_blocked = np.mean([r['blocked_updates'] for r in seed_results])
            
            sweep_data[str(nl)][arm] = {
                'mean_accuracy': float(mean_acc),
                'mean_loss': float(mean_loss),
                'mean_updates': float(mean_updates),
                'mean_blocked': float(mean_blocked),
                'seeds': seed_results,
            }
            
            print(f"acc={mean_acc:.3f}, loss={mean_loss:.3f}, "
                  f"updates={mean_updates:.0f}, blocked={mean_blocked:.0f}")
    
    # Results table
    print("\n" + "=" * 90)
    print("NOISE TOLERANCE RESULTS (v26 - Sparse Encoding)")
    print("=" * 90)
    print(f"{'Noise':<10} | {'A1_buffered':<15} | {'A2_nolearn':<15} | {'A3_coupled':<15}")
    print("-" * 90)
    
    for nl in CONFIG['noise_levels']:
        a1 = sweep_data[str(nl)]['A1_buffered']['mean_accuracy']
        a2 = sweep_data[str(nl)]['A2_nolearn']['mean_accuracy']
        a3 = sweep_data[str(nl)]['A3_coupled']['mean_accuracy']
        print(f"{nl:<10.2f} | {a1:<15.3f} | {a2:<15.3f} | {a3:<15.3f}")
    print("=" * 90)
    
    # Hypothesis testing
    print("\n" + "=" * 70)
    print("Hypothesis Testing (Pre-registered)")
    print("=" * 70)
    
    a1_noise_0 = sweep_data['0.0']['A1_buffered']['mean_accuracy']
    a1_noise_005 = sweep_data['0.05']['A1_buffered']['mean_accuracy']
    
    H1_pass = a1_noise_005 > CONFIG['H1_threshold']
    H2_pass = a1_noise_0 > CONFIG['H2_threshold']
    
    print(f"H1 (noise=5% > {CONFIG['H1_threshold']*100:.1f}%): "
          f"actual={a1_noise_005*100:.1f}% → {'✅ PASS' if H1_pass else '❌ FAIL'}")
    print(f"H2 (noise=0% > {CONFIG['H2_threshold']*100:.1f}%): "
          f"actual={a1_noise_0*100:.1f}% → {'✅ PASS' if H2_pass else '❌ FAIL'}")
    
    overall_success = H1_pass and H2_pass
    print(f"\nOverall: {'✅ SUCCESS - Sparse encoding improves noise tolerance' if overall_success else '❌ FAIL - Need postsynaptic gating'}")
    
    # Failure points
    print("\nFailure Point Analysis:")
    failure_points = {}
    for arm in CONFIG['arms']:
        accs = [sweep_data[str(nl)][arm]['mean_accuracy'] for nl in CONFIG['noise_levels']]
        fp = find_failure_point(CONFIG['noise_levels'], accs, CONFIG['failure_threshold'])
        failure_points[arm] = fp
        if fp is not None:
            print(f"  {arm}: FAILS at noise = {fp}")
        else:
            print(f"  {arm}: ✅ ROBUST up to max noise ({max(CONFIG['noise_levels'])})")
    
    # Plot
    plot_path = plot_results(sweep_data, CONFIG)
    print(f"\n📊 Plot saved: {plot_path}")
    
    # Save JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v26_sparse_encoding_{timestamp}.json'
    
    json_data = {
        'timestamp': timestamp,
        'version': 'v26 (Sparse Input Encoding)',
        'pre_registration': {
            'H1': f"noise=5% accuracy > {CONFIG['H1_threshold']}",
            'H2': f"noise=0% accuracy > {CONFIG['H2_threshold']}",
            'H1_result': float(a1_noise_005),
            'H2_result': float(a1_noise_0),
            'H1_pass': bool(H1_pass),
            'H2_pass': bool(H2_pass),
            'overall_success': bool(overall_success),
        },
        'config': CONFIG,
        'sweep_data': {
            nl: {
                arm: {
                    'mean_accuracy': data['mean_accuracy'],
                    'mean_loss': data['mean_loss'],
                    'mean_updates': data['mean_updates'],
                    'mean_blocked': data['mean_blocked'],
                }
                for arm, data in arms.items()
            }
            for nl, arms in sweep_data.items()
        },
        'failure_points': failure_points,
    }
    
    with open(filename, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"💾 Saved: {filename}")
    print("=" * 70)

if __name__ == '__main__':
    main()