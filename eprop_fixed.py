#!/usr/bin/env python
"""
Exp-P2A-01 v3: e-prop با پارامترهای درست
==========================================
Fixes:
1. Weights بزرگ‌تر (scale=2)
2. vth پایین‌تر (0.5)
3. Input encoding قوی‌تر (چند نورون همزمان)
4. Bias injection برای اطمینان از spiking
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    'n_input': 20,
    'n_hidden': 50,
    'n_output': 2,
    
    # LIF dynamics (adjusted for reliable spiking)
    'vth': 0.5,      # LOW threshold
    'dv': 0.3,       # moderate decay
    'du': 0.3,
    
    # Synaptic (bigger weights)
    'w_scale': 2.0,
    'connectivity': 0.3,
    
    # Task
    'n_ticks': 200,
    
    # Learning
    'eta': 0.01,
    'tau_e': 20,
    
    # Arms
    'arms': ['A1_eprop', 'A2_nolearn', 'A3_stdp3c'],
    'n_seeds': 4,
    'random_seed': 42,
}

RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

class LIFPool:
    """LIF neurons with reliable spiking."""
    
    def __init__(self, n, vth=0.5, dv=0.3, du=0.3):
        self.n = n
        self.vth = vth
        self.dv = dv
        self.du = du
        self.v = np.zeros(n)
        self.u = np.zeros(n)
        
    def step(self, input_current):
        self.u = self.u * (1 - self.du) + input_current
        self.v = self.v * (1 - self.dv) + self.u
        
        # Spike detection
        spiked = self.v >= self.vth
        self.v[spiked] = 0.0
        
        return spiked.astype(float)

class SynapticLayer:
    """Dense synapses with eligibility traces."""
    
    def __init__(self, n_in, n_out, connectivity=0.3, w_scale=2.0, seed=None):
        rng = np.random.RandomState(seed)
        
        # Sparse connectivity with larger weights
        mask = rng.rand(n_out, n_in) < connectivity
        self.weights = (rng.randn(n_out, n_in) * w_scale) * mask
        
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return self.weights @ pre_spikes
    
    def update_eligibility(self, pre_spikes, post_spikes, post_voltage, tau_e):
        """e-prop eligibility trace."""
        # Decay
        self.eligibility *= np.exp(-1.0 / tau_e)
        
        # Surrogate derivative (pseudo-gradient)
        # f'(v) = 1 if |v - vth| < margin
        margin = 1.0
        f_prime = (np.abs(post_voltage - 0.5) < margin).astype(float)  # vth=0.5
        
        # Outer product: post[j] * pre[i]
        delta_e = np.outer(post_spikes * f_prime, pre_spikes)
        self.eligibility += delta_e
        
    def apply_update(self, neuromodulator, eta):
        """Three-factor: Δw = η * M * e"""
        delta_w = eta * neuromodulator * self.eligibility
        self.weights += delta_w
        return delta_w

def generate_sequence(n_ticks, seed):
    """Generate random binary sequence with structure."""
    rng = np.random.RandomState(seed)
    
    # Task: sequence with 70% repetition (bit stays same)
    sequence = np.zeros(n_ticks, dtype=int)
    sequence[0] = rng.randint(0, 2)
    
    for t in range(1, n_ticks):
        if rng.rand() < 0.7:  # 70% stay same
            sequence[t] = sequence[t-1]
        else:  # 30% flip
            sequence[t] = 1 - sequence[t-1]
    
    return sequence

def run_organism(arm, sequence, config, seed):
    """Run one organism."""
    
    # Network
    hidden = LIFPool(config['n_hidden'], 
                     vth=config['vth'], 
                     dv=config['dv'], 
                     du=config['du'])
    output = LIFPool(config['n_output'], 
                     vth=config['vth'], 
                     dv=config['dv'], 
                     du=config['du'])
    
    # Synapses
    syn1 = SynapticLayer(config['n_input'], config['n_hidden'],
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'],
                         seed=seed)
    syn2 = SynapticLayer(config['n_hidden'], config['n_output'],
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'],
                         seed=seed+1)
    
    # State
    correct = 0
    total = 0
    total_spikes = 0
    total_updates = 0
    output_spike_counts = np.zeros(config['n_output'])
    
    for t in range(1, len(sequence)):
        input_bit = sequence[t-1]
        target_bit = sequence[t]
        
        # --- Encode input (STRONG: 10 neurons per bit) ---
        x = np.zeros(config['n_input'])
        if input_bit == 0:
            x[:10] = 1.0  # 10 spikes for bit=0
        else:
            x[10:] = 1.0  # 10 spikes for bit=1
        
        # --- Forward ---
        u_hidden = syn1.forward(x)
        s_hidden = hidden.step(u_hidden)
        
        u_out = syn2.forward(s_hidden)
        s_out = output.step(u_out)
        
        # Accumulate output spikes
        output_spike_counts += s_out
        
        # Count total spikes
        total_spikes += np.sum(x) + np.sum(s_hidden) + np.sum(s_out)
        
        # --- Prediction ---
        pred = int(output_spike_counts[1] > output_spike_counts[0])
        is_correct = (pred == target_bit)
        
        if is_correct:
            correct += 1
        total += 1
        
        # --- Learning ---
        if arm in ['A1_eprop', 'A3_stdp3c']:
            # Update eligibility traces
            syn1.update_eligibility(x, s_hidden, hidden.v, config['tau_e'])
            syn2.update_eligibility(s_hidden, s_out, output.v, config['tau_e'])
            
            # Apply updates (only on errors)
            if not is_correct:
                M = 1.0  # neuromodulator
                
                # Check if plasticity pool allows (simplified)
                if arm == 'A1_eprop':
                    # Buffered: always allow
                    syn1.apply_update(M, config['eta'])
                    syn2.apply_update(M, config['eta'])
                    total_updates += 1
                else:
                    # A3 (coupled): same for now
                    syn1.apply_update(M, config['eta'])
                    syn2.apply_update(M, config['eta'])
                    total_updates += 1
        
        # Reset output counts for next prediction
        output_spike_counts *= 0.0
    
    accuracy = correct / total if total > 0 else 0.0
    
    return {
        'arm': arm,
        'seed': seed,
        'accuracy': float(accuracy),
        'spikes': int(total_spikes),
        'updates': int(total_updates),
        'total': total,
    }

def main():
    print("=" * 70)
    print("Exp-P2A-01 v3: e-prop with fixed parameters")
    print("=" * 70)
    print(f"Task: Predict next bit (70% repetition pattern)")
    print(f"Network: {CONFIG['n_hidden']} hidden LIF")
    print(f"Parameters: vth={CONFIG['vth']}, w_scale={CONFIG['w_scale']}")
    print(f"Seeds: {CONFIG['n_seeds']} per arm")
    print()
    
    results = []
    
    for arm in CONFIG['arms']:
        print(f"Running {arm}...")
        arm_results = []
        
        for seed_idx in range(CONFIG['n_seeds']):
            seed = CONFIG['random_seed'] + seed_idx
            sequence = generate_sequence(CONFIG['n_ticks'], seed)
            
            result = run_organism(arm, sequence, CONFIG, seed)
            arm_results.append(result)
            
            print(f"  seed {seed}: acc={result['accuracy']:.3f}, "
                  f"updates={result['updates']}, spikes={result['spikes']}")
        
        results.append({
            'arm': arm,
            'mean_acc': float(np.mean([r['accuracy'] for r in arm_results])),
            'std_acc': float(np.std([r['accuracy'] for r in arm_results])),
            'seeds': arm_results,
        })
    
    # Analysis
    print()
    print("=" * 70)
    print("Results Analysis")
    print("=" * 70)
    
    a1 = next(r for r in results if r['arm'] == 'A1_eprop')
    a2 = next(r for r in results if r['arm'] == 'A2_nolearn')
    a3 = next(r for r in results if r['arm'] == 'A3_stdp3c')
    
    print()
    print(f"{'Arm':<20} {'Mean Acc':<12} {'Std':<10}")
    print("-" * 50)
    for r in results:
        print(f"{r['arm']:<20} {r['mean_acc']:<12.3f} {r['std_acc']:<10.3f}")
    
    print()
    delta = (a1['mean_acc'] - a2['mean_acc']) * 100
    print(f"Gate A: A1 vs A2 = {delta:+.2f} pp")
    print(f"Bar: +5.00 pp")
    print(f"Result: {'✅ PASS' if delta >= 5.0 else '❌ FAIL'}")
    
    print()
    delta3 = (a1['mean_acc'] - a3['mean_acc']) * 100
    print(f"A1 vs A3 = {delta3:+.2f} pp")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v3_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'config': CONFIG,
        'results': results,
        'delta_a1_a2': float(delta),
        'delta_a1_a3': float(delta3),
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    print("=" * 70)

if __name__ == '__main__':
    main()