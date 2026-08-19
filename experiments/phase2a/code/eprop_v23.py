#!/usr/bin/env python
"""
Exp-P2A-01 v23: Fixing Eligibility Trace Contamination
======================================================
باگ کشف شده در v22:
در v22، ورودی‌های تاخیری (pulse_t_T1 و pulse_t_T2) در هر تیک به شبکه داده می‌شدند.
این باعث می‌شد Eligibility Trace آن‌ها با سیگنال‌های نامربوط "آلوده" شود.
وقتی سیگنال خطا می‌رسید، گرادیان اشتباه محاسبه می‌شد.

اصلاح v23:
ورودی‌های تاخیری فقط در زمان‌های خاص (Time-Locked) فعال می‌شوند تا Eligibility Trace پاک بماند.
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    'n_ticks': 3000,
    'T1': 3,   
    'T2': 6,   
    'T_out': 9,
    
    'pulse_prob': 0.3,
    
    'n_input': 30,
    'n_hidden': 100,
    'n_output': 2,
    
    'theta': 0.3,
    'tau_m': 20.0,
    'dv': 0.05,
    'du': 0.05,
    
    'tau_out': 20.0,
    'readout_window': 5,
    
    'w_scale': 1.0,
    'connectivity': 0.3,
    'recurrent_connectivity': 0.2,
    
    'eta': 0.01,          
    'tau_e': 20.0,
    'beta': 5.0,
    'max_grad': 1.0,      
    'max_weight': 5.0,    
    
    'plasticity_pool_capacity': 50.0,
    'refill_rate': 1.0,
    'update_cost': 1.0,
    
    'arms': ['A1_buffered', 'A2_nolearn', 'A3_coupled'],
    'n_seeds': 8,
    'random_seed': 42,
}

RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

class LIFPool:
    def __init__(self, n, theta=0.3, dv=0.05, du=0.05):
        self.n = n
        self.theta = theta
        self.dv = dv
        self.du = du
        self.v = np.zeros(n)
        self.u = np.zeros(n)
        self.last_spikes = np.zeros(n)
        self.pre_reset_v = np.zeros(n)
        
    def step(self, input_current):
        input_current = np.clip(input_current, -10, 10)
        self.u = self.u * (1 - self.du) + input_current
        self.v = self.v * (1 - self.dv) + self.u
        self.v = np.clip(self.v, -5, 5)
        self.pre_reset_v = self.v.copy()
        spiked = self.v >= self.theta
        self.v[spiked] = 0.0
        self.last_spikes = spiked.astype(float)
        return self.last_spikes
    
    def reset(self):
        self.v[:] = 0.0
        self.u[:] = 0.0
        self.last_spikes[:] = 0.0
        self.pre_reset_v[:] = 0.0
    
    def surrogate_derivative(self):
        beta = CONFIG['beta']
        diff = np.abs(self.pre_reset_v - self.theta)
        diff = np.clip(diff, 0, 10)
        denominator = 1.0 + beta * diff
        f_prime = 1.0 / (denominator ** 2)
        f_prime = np.clip(f_prime, 0, 1)
        return f_prime

class OutputLayer:
    def __init__(self, n, tau_out=20.0):
        self.n = n
        self.tau_out = tau_out
        self.r = np.zeros(n)
        
    def step(self, spikes):
        self.r = self.r * (1 - 1/self.tau_out) + spikes
        self.r = np.clip(self.r, 0, 5)
        return self.r
    
    def reset(self):
        self.r[:] = 0.0

class SynapticLayer:
    def __init__(self, n_in, n_out, connectivity=0.3, w_scale=1.0, seed=None):
        rng = np.random.RandomState(seed)
        self.n_in = n_in
        self.n_out = n_out
        mask = rng.rand(n_out, n_in) < connectivity
        self.weights = (rng.randn(n_out, n_in) * w_scale) * mask
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return np.clip(self.weights @ pre_spikes, -10, 10)
    
    def update_eligibility(self, pre_spikes, post_f_prime, tau_e):
        self.eligibility *= np.exp(-1.0 / tau_e)
        post_f_prime = np.clip(post_f_prime, 0, 1)
        delta_e = np.outer(post_f_prime, pre_spikes)
        self.eligibility += delta_e
        self.eligibility = np.clip(self.eligibility, -5, 5)
    
    def reset_eligibility(self):
        self.eligibility[:] = 0.0
        
    def apply_update(self, learning_signal, eta, max_weight=5.0, max_grad=1.0):
        learning_signal = np.clip(learning_signal, -max_grad, max_grad)
        delta_w = eta * np.outer(learning_signal, np.ones(self.n_in)) * self.eligibility
        delta_w = np.clip(delta_w, -max_grad, max_grad)
        self.weights -= delta_w  
        self.weights = np.clip(self.weights, -max_weight, max_weight)
        return delta_w

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

def generate_temporal_xor(n_ticks, T1, T2, T_out, pulse_prob, seed):
    rng = np.random.RandomState(seed)
    input_pulses = (rng.rand(n_ticks) < pulse_prob).astype(int)
    targets = np.full(n_ticks, -1, dtype=int)
    for t in range(T_out, n_ticks):
        if t % T_out == 0:
            if t - T1 >= 0 and t - T2 >= 0:
                targets[t] = input_pulses[t - T1] ^ input_pulses[t - T2]
    return input_pulses, targets

def encode_input(t, pulse_t, T1, T2, T_out, n_input):
    """
    اصلاح v23: ورودی‌های تاخیری فقط در زمان‌های خاص فعال می‌شوند.
    این کار از "آلودگی" Eligibility Trace جلوگیری می‌کند.
    """
    x = np.zeros(n_input)
    if pulse_t == 1:
        x[:10] = 1.0
    
    # ورودی اول (T1) باید در زمان (T_out - T1) قبل از Target فعال شود
    if (t % T_out) == (T_out - T1):
        if pulse_t == 1:
            x[10:20] = 1.0
            
    # ورودی دوم (T2) باید در زمان (T_out - T2) قبل از Target فعال شود
    if (t % T_out) == (T_out - T2):
        if pulse_t == 1:
            x[20:30] = 1.0
            
    return x

def balanced_accuracy(predictions, targets):
    valid = targets != -1
    preds = predictions[valid]
    tgts = targets[valid]
    pos_mask = (tgts == 1)
    neg_mask = (tgts == 0)
    tpr = np.mean(preds[pos_mask] == 1) if np.sum(pos_mask) > 0 else 0.0
    tnr = np.mean(preds[neg_mask] == 0) if np.sum(neg_mask) > 0 else 0.0
    return (tpr + tnr) / 2

def run_organism(arm, input_pulses, targets, config, seed):
    T1 = config['T1']
    T2 = config['T2']
    T_out = config['T_out']
    readout_window = config['readout_window']
    n_hidden = config['n_hidden']
    n_output = config['n_output']
    tau_e = config['tau_e']
    eta = config['eta']
    
    hidden = LIFPool(n_hidden, theta=config['theta'], dv=config['dv'], du=config['du'])
    output_layer = OutputLayer(n_output, tau_out=config['tau_out'])
    
    syn_in = SynapticLayer(config['n_input'], n_hidden,
                           connectivity=config['connectivity'],
                           w_scale=config['w_scale'], seed=seed)
    syn_rec = SynapticLayer(n_hidden, n_hidden,
                            connectivity=config['recurrent_connectivity'],
                            w_scale=config['w_scale'], seed=seed+1)
    syn_out = SynapticLayer(n_hidden, n_output,
                            connectivity=config['connectivity'],
                            w_scale=config['w_scale'], seed=seed+2)
    
    buffer = None
    if arm == 'A1_buffered':
        buffer = PlasticityBuffer(
            capacity=config['plasticity_pool_capacity'],
            refill_rate=config['refill_rate'],
            update_cost=config['update_cost']
        )
    
    all_predictions = []
    all_targets = []
    total_updates = 0
    blocked_updates = 0
    loss_history = []
    hidden_spike_history = []
    
    for t in range(len(input_pulses)):
        pulse_t = input_pulses[t]
        
        # اصلاح v23: استفاده از encode_input جدید
        x = encode_input(t, pulse_t, T1, T2, T_out, config['n_input'])
        
        u_in = syn_in.forward(x)
        u_rec = syn_rec.forward(hidden.last_spikes)
        s_hidden = hidden.step(u_in + u_rec)
        
        hidden_spike_history.append(s_hidden.copy())
        if len(hidden_spike_history) > readout_window:
            hidden_spike_history.pop(0)
        
        u_out = syn_out.forward(s_hidden)
        r_out = output_layer.step(u_out)
        
        if arm in ['A1_buffered', 'A3_coupled']:
            f_prime_hidden = hidden.surrogate_derivative()
            syn_in.update_eligibility(x, f_prime_hidden, tau_e)
            syn_rec.update_eligibility(hidden.last_spikes, f_prime_hidden, tau_e)
        
        if targets[t] != -1:
            target = targets[t]
            y = softmax(r_out)
            pred = int(y.argmax())
            all_predictions.append(pred)
            all_targets.append(target)
            
            target_vec = np.zeros(n_output)
            target_vec[target] = 1.0
            error = y - target_vec
            loss = -np.log(y[target] + 1e-8)
            loss_history.append(loss)
            
            if arm in ['A1_buffered', 'A3_coupled']:
                M_t = float(np.max(np.abs(error)))
                
                if buffer is not None:
                    buffer.refill(M_t)
                
                L_hidden = syn_out.weights.T @ error  
                L_hidden = np.clip(L_hidden, -config['max_grad'], config['max_grad'])
                
                can_update = True
                if buffer is not None:
                    can_update = buffer.can_update()
                    if not can_update:
                        blocked_updates += 1
                
                if can_update:
                    syn_in.apply_update(L_hidden, eta, 
                                               config['max_weight'], config['max_grad'])
                    syn_rec.apply_update(L_hidden, eta, 
                                                config['max_weight'], config['max_grad'])
                    
                    if len(hidden_spike_history) > 0:
                        s_hidden_avg = np.mean(hidden_spike_history, axis=0)
                    else:
                        s_hidden_avg = s_hidden
                    
                    delta_out = eta * np.outer(error, s_hidden_avg) 
                    delta_out = np.clip(delta_out, -config['max_grad'], config['max_grad'])
                    syn_out.weights -= delta_out  
                    syn_out.weights = np.clip(syn_out.weights, 
                                              -config['max_weight'], config['max_weight'])
                    
                    total_updates += 1
                    
                    if buffer is not None:
                        buffer.spend()
                
                hidden.reset()
                output_layer.reset()
                syn_in.reset_eligibility()
                syn_rec.reset_eligibility()
                hidden_spike_history = []
    
    predictions = np.array(all_predictions)
    targets_arr = np.array(all_targets)
    bal_acc = balanced_accuracy(predictions, targets_arr)
    reg_acc = np.mean(predictions == targets_arr) if len(predictions) > 0 else 0.0
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
        'regular_accuracy': float(reg_acc),
        'updates': int(total_updates),
        'blocked_updates': int(blocked_updates),
        'mean_loss': float(mean_loss),
        'n_trials': len(all_predictions),
        'buffer_stats': buffer_stats,
    }

def main():
    print("=" * 70)
    print("Exp-P2A-01 v23: Fixing Eligibility Trace Contamination")
    print("=" * 70)
    print("Fix applied:")
    print("  Time-Locked Input Encoding: Delayed inputs are now only presented at specific")
    print("  times (t % T_out == T_out - T1) to prevent Eligibility Trace contamination.")
    print(f"Arms: {', '.join(CONFIG['arms'])}")
    print(f"Seeds: {CONFIG['n_seeds']} per arm")
    print()
    
    results = []
    
    for arm in CONFIG['arms']:
        print(f"Running {arm}...")
        arm_results = []
        
        for seed_idx in range(CONFIG['n_seeds']):
            seed = CONFIG['random_seed'] + seed_idx
            input_pulses, targets = generate_temporal_xor(
                CONFIG['n_ticks'], CONFIG['T1'], CONFIG['T2'], CONFIG['T_out'],
                CONFIG['pulse_prob'], seed
            )
            
            result = run_organism(arm, input_pulses, targets, CONFIG, seed)
            arm_results.append(result)
            
            buf_info = ""
            if result['buffer_stats']:
                buf_info = (f", blocked={result['buffer_stats']['blocked_updates']}, "
                          f"pool={result['buffer_stats']['final_pool']:.1f}")
            print(f"  seed {seed}: bal_acc={result['balanced_accuracy']:.3f}, "
                  f"loss={result['mean_loss']:.3f}, "
                  f"updates={result['updates']}{buf_info}")
        
        results.append({
            'arm': arm,
            'mean_bal_acc': float(np.mean([r['balanced_accuracy'] for r in arm_results])),
            'mean_reg_acc': float(np.mean([r['regular_accuracy'] for r in arm_results])),
            'mean_loss': float(np.mean([r['mean_loss'] for r in arm_results])),
            'total_updates': int(np.mean([r['updates'] for r in arm_results])),
            'total_blocked': int(np.mean([r['blocked_updates'] for r in arm_results])),
            'seeds': arm_results,
        })
    
    # Analysis
    print()
    print("=" * 70)
    print("Results Analysis")
    print("=" * 70)
    
    a1 = next(r for r in results if r['arm'] == 'A1_buffered')
    a2 = next(r for r in results if r['arm'] == 'A2_nolearn')
    a3 = next(r for r in results if r['arm'] == 'A3_coupled')
    
    print()
    print(f"{'Arm':<20} {'Bal Acc':<10} {'Loss':<10} {'Updates':<10} {'Blocked':<10}")
    print("-" * 65)
    for r in results:
        print(f"{r['arm']:<20} {r['mean_bal_acc']:<10.3f} "
              f"{r['mean_loss']:<10.3f} {r['total_updates']:<10} "
              f"{r['total_blocked']:<10}")
    
    # Key comparisons
    print()
    print("D5 Prediction Test (Buffered vs Coupled):")
    print("-" * 60)
    delta_buffer = (a1['mean_bal_acc'] - a3['mean_bal_acc']) * 100
    print(f"  A1 (buffered) - A3 (coupled) = {delta_buffer:+.2f} pp")
    
    print()
    print("Phase 1 Reproduction (learning hurts without buffering?):")
    print("-" * 60)
    delta_a3_a2 = (a3['mean_bal_acc'] - a2['mean_bal_acc']) * 100
    print(f"  A3 (coupled) - A2 (nolearn) = {delta_a3_a2:+.2f} pp")
    if delta_a3_a2 < -2.0:
        print(f"  ✅ Phase 1 reproduced: learning without buffering hurts!")
    
    print()
    print("Gate A (buffered vs nolearn):")
    delta_gate = (a1['mean_bal_acc'] - a2['mean_bal_acc']) * 100
    print(f"  A1 vs A2 = {delta_gate:+.2f} pp")
    print(f"  Bar: +5.00 pp")
    print(f"  Result: {'✅ PASS' if delta_gate >= 5.0 else '❌ FAIL'}")
    
    # Buffer activity
    print()
    print("Buffer Activity:")
    print("-" * 60)
    print(f"  A1 blocked: {a1['total_blocked']}")
    print(f"  A1 successful: {a1['total_updates']}")
    if a1['total_updates'] + a1['total_blocked'] > 0:
        block_rate = a1['total_blocked'] / (a1['total_updates'] + a1['total_blocked'])
        print(f"  Block rate: {block_rate:.1%}")
    
    # Permutation tests
    print()
    print("Permutation Tests:")
    print("-" * 60)
    
    def permutation_test(arm1, arm2, label):
        accs1 = [r['balanced_accuracy'] for r in arm1['seeds']]
        accs2 = [r['balanced_accuracy'] for r in arm2['seeds']]
        observed_diff = np.mean(accs1) - np.mean(accs2)
        combined = accs1 + accs2
        rng = np.random.RandomState(42)
        perm_diffs = []
        for _ in range(1000):
            rng.shuffle(combined)
            perm_diffs.append(np.mean(combined[:len(accs1)]) - np.mean(combined[len(accs1):]))
        p_value = float(np.mean(np.abs(perm_diffs) >= np.abs(observed_diff)))
        sig = "✅" if p_value < 0.05 else "❌"
        print(f"  {label}: Δ = {observed_diff*100:+.2f} pp, p = {p_value:.4f} {sig}")
        return p_value
    
    p_a1_a3 = permutation_test(a1, a3, "A1 vs A3")
    p_a1_a2 = permutation_test(a1, a2, "A1 vs A2")
    p_a3_a2 = permutation_test(a3, a2, "A3 vs A2")
    
    # Hypothesis
    print()
    print("Hypothesis Tests:")
    print("-" * 60)
    
    if delta_buffer > 2.0 and p_a1_a3 < 0.05:
        print("  🎉 H1 + D5 CONFIRMED!")
        print("     Buffering rescues learning under metabolic constraint")
    elif delta_gate >= 5.0 and p_a1_a2 < 0.05:
        print("  🎉 Gate A PASSED")
        if delta_a3_a2 < -2.0:
            print("  🎉 Phase 1 reproduced + buffering helps")
    elif delta_a3_a2 < -2.0:
        print("  ✅ Phase 1 reproduced (learning hurts)")
        print("  ⚠️  But buffering did not rescue (needs tuning?)")
    else:
        print("  ⚠️  Inconclusive results")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v23_eligibility_fix_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v23 (Eligibility Trace Contamination Fix)',
        'config': CONFIG,
        'results': results,
        'delta_a1_a3': float(delta_buffer),
        'delta_a1_a2': float(delta_gate),
        'delta_a3_a2': float(delta_a3_a2),
        'p_a1_a3': float(p_a1_a3),
        'p_a1_a2': float(p_a1_a2),
        'p_a3_a2': float(p_a3_a2),
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    print("=" * 70)

if __name__ == '__main__':
    main()