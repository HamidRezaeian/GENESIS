#!/usr/bin/env python
"""
Exp-P2A-01 v25: Noise Sweep & Metabolic Failure Point Detection
================================================================
هدف (Measurement Science):
سنجش مقاومت e-prop با محدودیت متابولیک در برابر نویز ورودی.
نقطه‌ای که دقت A1 به زیر ۷۰٪ می‌رسد = "Metabolic Failure Point".

این آزمایش مشخص می‌کند که آیا این building block برای scale-up به AGI
قابل‌اعتماد است یا خیر.
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
    
    # معماری گسترده‌تر برای نویز معنادار
    'n_input': 10,    # نورون 0=A, نورون 1=B, نورون‌های 2-9=نویز
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
    
    # پارامترهای جدید v25
    'noise_levels': [0.0, 0.05, 0.1, 0.2, 0.3, 0.5],
    'failure_threshold': 0.70,  # آستانه شکست (۷۰٪ دقت)
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
            x = np.zeros(config['n_input'])
            
            # سیگنال‌های اصلی
            if t == T_A and A == 1: x[0] = 1.0
            if t == T_B and B == 1: x[1] = 1.0
            
            # نویز: اسپایک تصادفی روی نورون‌های 2 تا 9
            if noise_level > 0:
                if rng.rand() < noise_level:
                    noise_neuron = rng.randint(2, config['n_input'])
                    x[noise_neuron] = 1.0
            
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
    """نقطه‌ای که دقت از آستانه شکست عبور می‌کند."""
    for i, acc in enumerate(accuracies):
        if acc < threshold:
            return noise_levels[i]
    return None  # سیستم در هیچ نویزی شکست نخورد

def plot_results(sweep_data, config):
    """رسم منحنی تحمل نویز."""
    plt.figure(figsize=(10, 6))
    
    noise_levels = config['noise_levels']
    
    for arm_name in ['A1_buffered', 'A2_nolearn', 'A3_coupled']:
        accs = [sweep_data[str(nl)][arm_name]['mean_accuracy'] for nl in noise_levels]
        plt.plot(noise_levels, accs, marker='o', linewidth=2, label=arm_name)
    
    plt.axhline(y=config['failure_threshold'], color='r', linestyle='--', 
                label=f'Failure Threshold ({config["failure_threshold"]*100:.0f}%)')
    plt.xlabel('Noise Level (probability of random spike)')
    plt.ylabel('Balanced Accuracy')
    plt.title('Noise Tolerance: e-prop under Metabolic Constraint')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xscale('log')
    plt.xticks(noise_levels, [str(nl) for nl in noise_levels])
    
    plot_path = RESULTS_DIR / 'exp_p2a_01_v25_noise_tolerance.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    return plot_path

def main():
    print("=" * 70)
    print("Exp-P2A-01 v25: Noise Sweep & Metabolic Failure Point")
    print("=" * 70)
    print(f"Noise Levels: {CONFIG['noise_levels']}")
    print(f"Seeds per condition: {CONFIG['n_seeds']}")
    print(f"Failure Threshold: {CONFIG['failure_threshold']*100:.0f}%")
    print(f"Architecture: {CONFIG['n_input']} inputs, {CONFIG['n_hidden']} hidden")
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
    
    # Failure Point Detection
    print()
    print("=" * 70)
    print("Failure Point Analysis")
    print("=" * 70)
    
    failure_points = {}
    noise_levels = CONFIG['noise_levels']
    
    for arm in CONFIG['arms']:
        accs = [sweep_data[str(nl)][arm]['mean_accuracy'] for nl in noise_levels]
        fp = find_failure_point(noise_levels, accs, CONFIG['failure_threshold'])
        failure_points[arm] = fp
        if fp is not None:
            print(f"  {arm}: FAILS at noise = {fp}")
        else:
            print(f"  {arm}: ✅ ROBUST up to max noise ({max(noise_levels)})")
    
    # Buffer Efficiency Analysis
    print()
    print("Buffer Efficiency (Successful Updates / Total Attempts):")
    for nl in noise_levels:
        a1_data = sweep_data[str(nl)]['A1_buffered']
        total_attempts = a1_data['mean_updates'] + a1_data['mean_blocked']
        if total_attempts > 0:
            efficiency = a1_data['mean_updates'] / total_attempts
            print(f"  noise={nl}: {efficiency*100:.1f}% efficient")
    
    # Plot
    print()
    plot_path = plot_results(sweep_data, CONFIG)
    print(f"📊 Plot saved: {plot_path}")
    
    # Save JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v25_noise_sweep_{timestamp}.json'
    
    # آماده‌سازی داده‌ها برای JSON (حذف seeds حجیم)
    json_data = {
        'timestamp': timestamp,
        'version': 'v25 (Noise Sweep)',
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
    
    # نتیجه‌گیری استراتژیک
    print("\n🎯 Strategic Assessment for AGI Path:")
    a1_fp = failure_points.get('A1_buffered')
    if a1_fp is None:
        print("  ✅ Building block is ROBUST: can handle max tested noise (50%)")
        print("  → Next: Scale up to deeper temporal dependencies or multi-layer SNN")
    elif a1_fp >= 0.2:
        print("  ⚠️  Building block shows MODERATE tolerance (fails at ~{:.0f}% noise)".format(a1_fp*100))
        print("  → Next: Add selective attention or noise-filtering mechanism")
    else:
        print("  ❌ Building block is FRAGILE (fails at {:.0f}% noise)".format(a1_fp*100))
        print("  → Next: Requires architectural priors (Working Memory) for real-world AGI")

if __name__ == '__main__':
    main()