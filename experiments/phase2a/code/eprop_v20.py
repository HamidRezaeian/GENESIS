#!/usr/bin/env python
"""
Exp-P2A-01 v20: Buffer Parameter Sweep
======================================
۳ تنظیم مختلف buffer را تست می‌کنیم:
- Config A: Buffer ملایم (refill=2.0, cost=0.5)
- Config B: Buffer متوسط (refill=1.0, cost=1.0)
- Config C: Buffer strict (refill=0.5, cost=2.0)

هدف: پیدا کردن sweet spot که buffer کمک کند نه hinder.
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIGS = {
    'A_gentle': {
        'refill_rate': 2.0,
        'update_cost': 0.5,
        'capacity': 50.0,
        'eta': 0.05,
    },
    'B_moderate': {
        'refill_rate': 1.0,
        'update_cost': 1.0,
        'capacity': 50.0,
        'eta': 0.05,
    },
    'C_strict': {
        'refill_rate': 0.5,
        'update_cost': 2.0,
        'capacity': 50.0,
        'eta': 0.05,
    },
}

COMMON_CONFIG = {
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
    'tau_e': 20.0,
    'beta': 5.0,
    'max_weight': 5.0,
    'max_grad': 1.0,
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
        beta = COMMON_CONFIG['beta']
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
        self.weights += delta_w
        self.weights = np.clip(self.weights, -max_weight, max_weight)
        return delta_w


class PlasticityBuffer:
    def __init__(self, capacity=50.0, refill_rate=0.5, update_cost=1.0):
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


def encode_input(pulse, input_t3, n_input):
    x = np.zeros(n_input)
    if pulse == 1:
        x[:10] = 1.0
    if input_t3 == 1:
        x[10:20] = 1.0
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


def run_organism(arm, input_pulses, targets, config, buffer_config, seed):
    """Run one organism with specified buffer config."""
    
    T1 = COMMON_CONFIG['T1']
    T2 = COMMON_CONFIG['T2']
    T_out = COMMON_CONFIG['T_out']
    readout_window = COMMON_CONFIG['readout_window']
    n_hidden = COMMON_CONFIG['n_hidden']
    n_output = COMMON_CONFIG['n_output']
    tau_e = COMMON_CONFIG['tau_e']
    eta = buffer_config['eta']
    
    # Network
    hidden = LIFPool(n_hidden, theta=COMMON_CONFIG['theta'], dv=COMMON_CONFIG['dv'], du=COMMON_CONFIG['du'])
    output_layer = OutputLayer(n_output, tau_out=COMMON_CONFIG['tau_out'])
    
    # Synapses
    syn_in = SynapticLayer(COMMON_CONFIG['n_input'], n_hidden,
                           connectivity=COMMON_CONFIG['connectivity'],
                           w_scale=COMMON_CONFIG['w_scale'], seed=seed)
    syn_rec = SynapticLayer(n_hidden, n_hidden,
                            connectivity=COMMON_CONFIG['recurrent_connectivity'],
                            w_scale=COMMON_CONFIG['w_scale'], seed=seed+1)
    syn_out = SynapticLayer(n_hidden, n_output,
                            connectivity=COMMON_CONFIG['connectivity'],
                            w_scale=COMMON_CONFIG['w_scale'], seed=seed+2)
    
    # Buffer
    buffer = None
    if arm == 'A1_buffered':
        buffer = PlasticityBuffer(
            capacity=buffer_config['capacity'],
            refill_rate=buffer_config['refill_rate'],
            update_cost=buffer_config['update_cost']
        )
    
    all_predictions = []
    all_targets = []
    total_updates = 0
    blocked_updates = 0
    loss_history = []
    hidden_spike_history = []
    
    for t in range(len(input_pulses)):
        pulse = input_pulses[t]
        input_t3 = input_pulses[t - T1] if t >= T1 else 0
        x = encode_input(pulse, input_t3, COMMON_CONFIG['n_input'])
        
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
                
                L_hidden = -(syn_out.weights.T @ error)
                L_hidden = np.clip(L_hidden, -COMMON_CONFIG['max_grad'], COMMON_CONFIG['max_grad'])
                
                can_update = True
                if buffer is not None:
                    can_update = buffer.can_update()
                    if not can_update:
                        blocked_updates += 1
                
                if can_update:
                    syn_in.apply_update(L_hidden, eta, COMMON_CONFIG['max_weight'], COMMON_CONFIG['max_grad'])
                    syn_rec.apply_update(L_hidden, eta, COMMON_CONFIG['max_weight'], COMMON_CONFIG['max_grad'])
                    
                    if len(hidden_spike_history) > 0:
                        s_hidden_avg = np.mean(hidden_spike_history, axis=0)
                    else:
                        s_hidden_avg = s_hidden
                    
                    delta_out = -eta * np.outer(error, s_hidden_avg)
                    delta_out = np.clip(delta_out, -COMMON_CONFIG['max_grad'], COMMON_CONFIG['max_grad'])
                    syn_out.weights += delta_out
                    syn_out.weights = np.clip(syn_out.weights, -COMMON_CONFIG['max_weight'], COMMON_CONFIG['max_weight'])
                    
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
    mean_loss = np.mean(loss_history[-100:]) if loss_history else 0.0
    
    return {
        'arm': arm,
        'seed': seed,
        'balanced_accuracy': float(bal_acc),
        'updates': int(total_updates),
        'blocked_updates': int(blocked_updates),
        'mean_loss': float(mean_loss),
    }


def run_buffer_config(config_name, buffer_config):
    """Run all 3 arms with specified buffer config."""
    
    print(f"\n{'='*70}")
    print(f"Buffer Config: {config_name}")
    print(f"  refill_rate: {buffer_config['refill_rate']}")
    print(f"  update_cost: {buffer_config['update_cost']}")
    print(f"  capacity: {buffer_config['capacity']}")
    print(f"  eta: {buffer_config['eta']}")
    print(f"{'='*70}")
    
    arms = ['A1_buffered', 'A2_nolearn', 'A3_coupled']
    results = {}
    
    for arm in arms:
        print(f"\nRunning {arm}...")
        arm_results = []
        
        for seed_idx in range(COMMON_CONFIG['n_seeds']):
            seed = COMMON_CONFIG['random_seed'] + seed_idx
            input_pulses, targets = generate_temporal_xor(
                COMMON_CONFIG['n_ticks'], COMMON_CONFIG['T1'], COMMON_CONFIG['T2'], 
                COMMON_CONFIG['T_out'], COMMON_CONFIG['pulse_prob'], seed
            )
            
            result = run_organism(arm, input_pulses, targets, COMMON_CONFIG, buffer_config, seed)
            arm_results.append(result)
            
            buf_info = ""
            if arm == 'A1_buffered':
                buf_info = f", blocked={result['blocked_updates']}"
            print(f"  seed {seed}: bal_acc={result['balanced_accuracy']:.3f}, "
                  f"loss={result['mean_loss']:.3f}{buf_info}")
        
        results[arm] = {
            'mean_bal_acc': float(np.mean([r['balanced_accuracy'] for r in arm_results])),
            'mean_loss': float(np.mean([r['mean_loss'] for r in arm_results])),
            'total_updates': int(np.mean([r['updates'] for r in arm_results])),
            'total_blocked': int(np.mean([r['blocked_updates'] for r in arm_results])),
            'seeds': arm_results,
        }
    
    # Analysis
    a1 = results['A1_buffered']
    a2 = results['A2_nolearn']
    a3 = results['A3_coupled']
    
    print(f"\n{'='*70}")
    print(f"Results for {config_name}:")
    print(f"{'='*70}")
    print(f"{'Arm':<20} {'Bal Acc':<12} {'Loss':<12} {'Updates':<10} {'Blocked':<10}")
    print("-" * 70)
    for arm in arms:
        r = results[arm]
        print(f"{arm:<20} {r['mean_bal_acc']:<12.3f} "
              f"{r['mean_loss']:<12.3f} {r['total_updates']:<10} "
              f"{r['total_blocked']:<10}")
    
    # Block rate
    if a1['total_updates'] + a1['total_blocked'] > 0:
        block_rate = a1['total_blocked'] / (a1['total_updates'] + a1['total_blocked'])
        print(f"\nBlock rate: {block_rate:.1%}")
    
    # Key metrics
    delta_a1_a3 = (a1['mean_bal_acc'] - a3['mean_bal_acc']) * 100
    delta_a1_a2 = (a1['mean_bal_acc'] - a2['mean_bal_acc']) * 100
    delta_a3_a2 = (a3['mean_bal_acc'] - a2['mean_bal_acc']) * 100
    
    print(f"\nKey deltas:")
    print(f"  A1 (buffered) - A3 (coupled): {delta_a1_a3:+.2f} pp")
    print(f"  A1 (buffered) - A2 (nolearn): {delta_a1_a2:+.2f} pp")
    print(f"  A3 (coupled) - A2 (nolearn):  {delta_a3_a2:+.2f} pp")
    
    return results


def main():
    print("=" * 70)
    print("Exp-P2A-01 v20: Buffer Parameter Sweep")
    print("=" * 70)
    print("Testing 3 buffer configurations:")
    print("  A (Gentle):   refill=2.0, cost=0.5")
    print("  B (Moderate): refill=1.0, cost=1.0")
    print("  C (Strict):   refill=0.5, cost=2.0")
    
    all_results = {}
    
    for config_name, buffer_config in CONFIGS.items():
        results = run_buffer_config(config_name, buffer_config)
        all_results[config_name] = results
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY: All Buffer Configs")
    print(f"{'='*70}")
    print(f"\n{'Config':<15} {'A1 Bal Acc':<12} {'A2 Bal Acc':<12} {'A3 Bal Acc':<12} {'A1-A3':<10} {'Block%':<10}")
    print("-" * 80)
    
    for config_name, results in all_results.items():
        a1 = results['A1_buffered']
        a2 = results['A2_nolearn']
        a3 = results['A3_coupled']
        
        delta = (a1['mean_bal_acc'] - a3['mean_bal_acc']) * 100
        total = a1['total_updates'] + a1['total_blocked']
        block_pct = (a1['total_blocked'] / total * 100) if total > 0 else 0
        
        print(f"{config_name:<15} {a1['mean_bal_acc']:<12.3f} "
              f"{a2['mean_bal_acc']:<12.3f} {a3['mean_bal_acc']:<12.3f} "
              f"{delta:+.2f} pp    {block_pct:.1f}%")
    
    # Best config
    print(f"\n{'='*70}")
    print("Best Config:")
    print(f"{'='*70}")
    
    best_config = max(all_results.items(), 
                      key=lambda x: x[1]['A1_buffered']['mean_bal_acc'])
    best_name, best_results = best_config
    best_a1 = best_results['A1_buffered']
    best_a2 = best_results['A2_nolearn']
    
    print(f"  {best_name}")
    print(f"  A1 balanced accuracy: {best_a1['mean_bal_acc']:.3f}")
    print(f"  A2 balanced accuracy: {best_a2['mean_bal_acc']:.3f}")
    print(f"  Delta: {(best_a1['mean_bal_acc'] - best_a2['mean_bal_acc'])*100:+.2f} pp")
    
    if best_a1['mean_bal_acc'] - best_a2['mean_bal_acc'] >= 0.05:
        print(f"\n  ✅ PASS: A1 > A2 by ≥ 5pp")
    else:
        print(f"\n  ❌ FAIL: A1 not significantly better than A2")
        print(f"  → Consider: simpler task, different architecture, or null result")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v20_buffer_sweep_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'version': 'v20 (buffer parameter sweep)',
        'configs': CONFIGS,
        'results': all_results,
        'best_config': best_name,
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    print("=" * 70)


if __name__ == '__main__':
    main()