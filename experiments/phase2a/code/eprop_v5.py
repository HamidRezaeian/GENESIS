#!/usr/bin/env python
"""
Exp-P2A-01 v5: e-prop Supervised Learning
==========================================
روش اصلی Bellec et al. 2020:
- Target spike pattern داریم
- Error = target - actual
- Neuromodulator = error signal
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    'n_input': 20,
    'n_hidden': 50,
    'n_output': 2,
    
    'vth': 0.5,
    'dv': 0.3,
    'du': 0.3,
    
    'w_scale': 2.0,
    'connectivity': 0.3,
    
    'n_ticks': 200,
    
    'eta': 0.01,
    'tau_e': 20,
    
    'arms': ['A1_eprop', 'A2_nolearn', 'A3_stdp3c'],
    'n_seeds': 4,
    'random_seed': 42,
}

RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

class LIFPool:
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
        spiked = self.v >= self.vth
        self.v[spiked] = 0.0
        return spiked.astype(float)

class SynapticLayer:
    def __init__(self, n_in, n_out, connectivity=0.3, w_scale=2.0, seed=None):
        rng = np.random.RandomState(seed)
        mask = rng.rand(n_out, n_in) < connectivity
        self.weights = (rng.randn(n_out, n_in) * w_scale) * mask
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return self.weights @ pre_spikes
    
    def update_eligibility(self, pre_spikes, post_spikes, post_voltage, tau_e):
        self.eligibility *= np.exp(-1.0 / tau_e)
        margin = 1.0
        f_prime = (np.abs(post_voltage - 0.5) < margin).astype(float)
        delta_e = np.outer(post_spikes * f_prime, pre_spikes)
        self.eligibility += delta_e
        
    def apply_update(self, neuromodulator, eta):
        delta_w = eta * neuromodulator * self.eligibility
        self.weights += delta_w
        return delta_w

def run_organism(arm, sequence, config, seed):
    """Run one organism with SUPERVISED e-prop."""
    
    hidden = LIFPool(config['n_hidden'], vth=config['vth'], dv=config['dv'], du=config['du'])
    output = LIFPool(config['n_output'], vth=config['vth'], dv=config['dv'], du=config['du'])
    
    syn1 = SynapticLayer(config['n_input'], config['n_hidden'],
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'], seed=seed)
    syn2 = SynapticLayer(config['n_hidden'], config['n_output'],
                         connectivity=config['connectivity'],
                         w_scale=config['w_scale'], seed=seed+1)
    
    correct = 0
    total = 0
    total_updates = 0
    
    for t in range(1, len(sequence)):
        input_bit = sequence[t-1]
        target_bit = sequence[t]
        
        # Encode input
        x = np.zeros(config['n_input'])
        if input_bit == 0:
            x[:10] = 1.0
        else:
            x[10:] = 1.0
        
        # Forward
        u_hidden = syn1.forward(x)
        s_hidden = hidden.step(u_hidden)
        
        u_out = syn2.forward(s_hidden)
        s_out = output.step(u_out)
        
        # --- SUPERVISED TARGET ---
        # Target: if target_bit=0, output[0] should spike
        #         if target_bit=1, output[1] should spike
        target_spikes = np.zeros(config['n_output'])
        target_spikes[target_bit] = 1.0
        
        # Error signal (for neuromodulator)
        error = target_spikes - s_out
        
        # Prediction
        pred = int(s_out[1] > s_out[0]) if s_out.sum() > 0 else int(output.v[1] > output.v[0])
        is_correct = (pred == target_bit)
        
        if is_correct:
            correct += 1
        total += 1
        
        # --- Learning ---
        if arm in ['A1_eprop', 'A3_stdp3c']:
            # Update eligibility
            syn1.update_eligibility(x, s_hidden, hidden.v, config['tau_e'])
            syn2.update_eligibility(s_hidden, s_out, output.v, config['tau_e'])
            
            # Neuromodulator from error
            # M[j] = error[j] for each output neuron
            M_out = error  # shape: (n_output,)
            
            # For hidden layer, use global error signal
            M_global = np.mean(np.abs(error))
            
            # Apply updates with error-based neuromodulator
            syn2.apply_update(M_out.mean(), config['eta'])  # output layer
            syn1.apply_update(M_global, config['eta'])       # hidden layer
            
            total_updates += 1
    
    accuracy = correct / total if total > 0 else 0.0
    
    return {
        'arm': arm,
        'seed': seed,
        'accuracy': float(accuracy),
        'updates': int(total_updates),
        'total': total,
    }

def main():
    print("=" * 70)
    print("Exp-P2A-01 v5: e-prop SUPERVISED Learning")
    print("=" * 70)
    print(f"Task: Predict next bit (supervised with target spikes)")
    print(f"Network: {CONFIG['n_hidden']} hidden LIF")
    print(f"Method: e-prop supervised (Bellec et al. 2020)")
    print(f"Seeds: {CONFIG['n_seeds']} per arm")
    print()
    
    results = []
    
    for arm in CONFIG['arms']:
        print(f"Running {arm}...")
        arm_results = []
        
        for seed_idx in range(CONFIG['n_seeds']):
            seed = CONFIG['random_seed'] + seed_idx
            rng = np.random.RandomState(seed)
            sequence = rng.randint(0, 2, size=CONFIG['n_ticks'])
            
            result = run_organism(arm, sequence, CONFIG, seed)
            arm_results.append(result)
            
            print(f"  seed {seed}: acc={result['accuracy']:.3f}, updates={result['updates']}")
        
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
    filename = RESULTS_DIR / f'exp_p2a_01_v5_{timestamp}.json'
    
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