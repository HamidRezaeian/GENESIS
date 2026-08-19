#!/usr/bin/env python
"""
Exp-P2A-01 v24: The Crucial Experiment (Minimalist Temporal XOR)
================================================================
هدف: اثبات یا رد توانایی e-prop در یادگیری گپ زمانی (Temporal Gap)
بدون دخالت نویز پس‌زمینه یا معماری پیچیده.

تغییرات بنیادین:
1. حذف نویز: فقط 2 ورودی (A در t=3، B در t=6).
2. Trial-Based: هر 10 تیک یک تریال کامل است و همه چیز ریست می‌شود.
3. Membrane Readout: خروجی از پتانسیل غشا (v) در t=9 خوانده می‌شود نه اسپایک.
4. Surrogate Gradient پهن‌تر (beta=1.0) برای انتقال بهتر گرادیان.
"""

import numpy as np
import json
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
    'beta': 1.0,    # Wider gradient for better credit assignment
    
    'eta': 0.01,
    'w_scale': 0.5,
    
    'plasticity_pool_capacity': 50.0,
    'refill_rate': 1.0,
    'update_cost': 1.0,
    
    'arms': ['A1_buffered', 'A2_nolearn', 'A3_coupled'],
    'n_seeds': 8,
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
        
    def reset(self):
        pass

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

def run_organism(arm, config, seed):
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
            x = np.zeros(config['n_input'])
            if t == T_A and A == 1: x[0] = 1.0
            if t == T_B and B == 1: x[1] = 1.0
            
            i_in = syn_in.forward(x)
            i_rec = syn_rec.forward(hidden.last_spikes)
            hidden.step(i_in + i_rec)
            
            if arm in ['A1_buffered', 'A3_coupled']:
                f_prime = hidden.surrogate_derivative(config['beta'])
                syn_in.update_eligibility(x, f_prime, config['tau_e'])
                syn_rec.update_eligibility(hidden.last_spikes, f_prime, config['tau_e'])
                
            if t == T_target:
                # Membrane potential readout for stability
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
                            
                break # End of trial
                
    bal_acc = correct / total if total > 0 else 0.0
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
        'balanced_accuracy': float(bal_acc),
        'regular_accuracy': float(bal_acc),
        'updates': int(total_updates),
        'blocked_updates': int(blocked_updates),
        'mean_loss': float(mean_loss),
        'n_trials': total,
        'buffer_stats': buffer_stats,
    }

def main():
    print("=" * 70)
    print("Exp-P2A-01 v24: Minimalist Temporal XOR (Isolating e-prop)")
    print("=" * 70)
    print("Changes in v24:")
    print("  1. Minimal 2-input architecture (Neuron 0 at T=3, Neuron 1 at T=6)")
    print("  2. Explicit trial resets to prevent eligibility trace contamination")
    print("  3. Wider surrogate gradient (beta=1.0) for better credit assignment")
    print("  4. Linear readout on membrane potential (hidden.v) instead of spikes")
    print(f"Arms: {', '.join(CONFIG['arms'])}")
    print(f"Seeds: {CONFIG['n_seeds']} per arm, {CONFIG['n_trials']} trials each")
    print()
    
    results = []
    
    for arm in CONFIG['arms']:
        print(f"Running {arm}...")
        arm_results = []
        
        for seed_idx in range(CONFIG['n_seeds']):
            seed = CONFIG['random_seed'] + seed_idx
            result = run_organism(arm, CONFIG, seed)
            arm_results.append(result)
            
            buf_info = ""
            if result['buffer_stats']:
                buf_info = (f", blocked={result['buffer_stats']['blocked_updates']}")
            print(f"  seed {seed}: acc={result['balanced_accuracy']:.3f}, "
                  f"loss={result['mean_loss']:.3f}, "
                  f"updates={result['updates']}{buf_info}")
        
        results.append({
            'arm': arm,
            'mean_bal_acc': float(np.mean([r['balanced_accuracy'] for r in arm_results])),
            'mean_loss': float(np.mean([r['mean_loss'] for r in arm_results])),
            'total_updates': int(np.mean([r['updates'] for r in arm_results])),
            'total_blocked': int(np.mean([r['blocked_updates'] for r in arm_results])),
            'seeds': arm_results,
        })
    
    print()
    print("=" * 70)
    print("Results Analysis")
    print("=" * 70)
    
    a1 = next(r for r in results if r['arm'] == 'A1_buffered')
    a2 = next(r for r in results if r['arm'] == 'A2_nolearn')
    a3 = next(r for r in results if r['arm'] == 'A3_coupled')
    
    print(f"{'Arm':<20} {'Acc':<10} {'Loss':<10} {'Updates':<10} {'Blocked':<10}")
    print("-" * 65)
    for r in results:
        print(f"{r['arm']:<20} {r['mean_bal_acc']:<10.3f} "
              f"{r['mean_loss']:<10.3f} {r['total_updates']:<10} "
              f"{r['total_blocked']:<10}")
              
    delta_buffer = (a1['mean_bal_acc'] - a3['mean_bal_acc']) * 100
    delta_gate = (a1['mean_bal_acc'] - a2['mean_bal_acc']) * 100
    
    print(f"\nA1 vs A3 (Buffer effect): {delta_buffer:+.2f} pp")
    print(f"A1 vs A2 (Gate A):        {delta_gate:+.2f} pp")
    
    if a1['mean_bal_acc'] > 0.75:
        print("\n✅ SUCCESS: Minimalist e-prop CAN learn temporal XOR!")
        print("   Action: Proceed to scale up complexity.")
    else:
        print("\n❌ NULL RESULT: e-prop fails even on minimalist temporal XOR.")
        print("   Conclusion: Standard e-prop is fundamentally unsuited for this temporal gap without working memory priors.")
        print("   Action: Record as definitive Null Result for Phase 2A (Measurement Science).")

    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v24_minimalist_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v24 (Minimalist Crucial Experiment)',
        'config': CONFIG,
        'results': results,
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    print("=" * 70)

if __name__ == '__main__':
    main()