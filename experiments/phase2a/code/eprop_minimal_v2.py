#!/usr/bin/env python
"""
Exp-P2A-01 v2: e-prop با fixes
================================
Fixes:
1. Output spike tracking (buffer)
2. Predict از output activity (نه input)
3. Task ساده‌تر (copy previous bit)
4. JSON bool fix
5. Eligibility decay instead of clear
"""

import numpy as np
import json
import os
from datetime import datetime
from pathlib import Path

# ============================================================================
# Configuration
# ============================================================================

CONFIG = {
    'n_neurons': 100,
    'n_input': 20,
    'n_output': 2,
    'connectivity': 0.2,
    
    'vth': 20,
    'dv': 0.3,
    'du': 0.3,
    
    'n_ticks': 500,  # کوتاه برای تست
    'noise_rate': 0.1,
    
    'eta': 0.005,
    'tau_e': 20,
    
    'energy_per_spike': 23.6e-12,
    'initial_reserves': 1000.0,  # زیاد برای زنده ماندن
    'income_per_correct': 2.0,
    'cost_per_tick': 0.001,
    'plasticity_cost_per_update': 0.01,
    
    'arms': ['A1_eprop', 'A2_nolearn', 'A3_stdp3c'],
    'n_seeds': 4,
    'random_seed': 42,
}

RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

# ============================================================================
# Task: Copy Previous Bit (trivially learnable)
# ============================================================================

def generate_sequence(n_ticks, noise_rate, seed):
    """Generate random binary sequence."""
    rng = np.random.RandomState(seed)
    sequence = rng.randint(0, 2, size=n_ticks)
    # Add noise (flip bits)
    flip_mask = rng.rand(n_ticks) < noise_rate
    sequence[flip_mask] = 1 - sequence[flip_mask]
    return sequence

# ============================================================================
# LIF Neuron Pool
# ============================================================================

class LIFPool:
    def __init__(self, n_neurons, vth=20, dv=0.3, du=0.3, seed=None):
        self.n = n_neurons
        self.vth = vth
        self.dv = dv
        self.du = du
        self.v = np.zeros(n_neurons)
        self.u = np.zeros(n_neurons)
        self.last_spikes = np.zeros(n_neurons)  # track spikes
        
    def step(self, input_current):
        """Update one time step, track spikes."""
        self.u = self.u * (1 - self.du) + input_current
        self.v = self.v * (1 - self.dv) + self.u
        spiked = self.v >= self.vth
        self.v[spiked] = 0.0
        self.last_spikes = spiked.astype(float)
        return self.last_spikes

# ============================================================================
# Synaptic Layer with Eligibility Traces
# ============================================================================

class SynapticLayer:
    def __init__(self, n_in, n_out, connectivity=0.2, seed=None):
        rng = np.random.RandomState(seed)
        self.n_in = n_in
        self.n_out = n_out
        
        mask = rng.rand(n_out, n_in) < connectivity
        self.weights = (rng.rand(n_out, n_in) * 0.5 - 0.25) * mask  # smaller init
        self.eligibility = np.zeros((n_out, n_in))
        
    def forward(self, pre_spikes):
        return self.weights @ pre_spikes
    
    def update_eligibility(self, pre_spikes, post_spikes, post_voltage, tau_e):
        """e-prop: accumulate eligibility with decay."""
        # Decay
        self.eligibility *= np.exp(-1.0 / tau_e)
        
        # Surrogate derivative
        f_prime = np.maximum(0, 1 - np.abs(post_voltage - self.n_out * 0.5) / 5)
        
        # Outer product
        delta_e = np.outer(post_spikes * f_prime, pre_spikes)
        self.eligibility += delta_e
        
    def apply_update(self, neuromodulator, eta):
        """Three-factor update: Δw = η * M * e"""
        delta_w = eta * neuromodulator * self.eligibility
        self.weights += delta_w
        # Don't clear - let decay handle it
        return delta_w

# ============================================================================
# Metabolic Pools
# ============================================================================

class MetabolicPools:
    def __init__(self, initial_reserves, buffered=True):
        self.survival_pool = initial_reserves
        self.plasticity_pool = initial_reserves if buffered else 0
        self.buffered = buffered
        self.alive = True
        
    def tick_survival(self, cost):
        self.survival_pool -= cost
        if self.survival_pool <= 0:
            self.alive = False
        return self.alive
    
    def tick_plasticity(self, cost):
        if self.buffered:
            self.plasticity_pool -= cost
            return self.plasticity_pool > 0
        else:
            self.survival_pool -= cost
            if self.survival_pool <= 0:
                self.alive = False
            return self.alive
    
    def reward(self, amount):
        self.survival_pool += amount

# ============================================================================
# Organism
# ============================================================================

class Organism:
    def __init__(self, arm, config, seed):
        self.arm = arm
        self.config = config
        self.rng = np.random.RandomState(seed)
        
        # Network
        self.input_layer = LIFPool(config['n_input'], seed=seed)
        self.hidden_layer = LIFPool(config['n_neurons'], 
                                    vth=config['vth'],
                                    dv=config['dv'],
                                    du=config['du'],
                                    seed=seed+1)
        self.output_layer = LIFPool(config['n_output'], seed=seed+2)
        
        # Synapses
        self.syn_in_hidden = SynapticLayer(config['n_input'], 
                                           config['n_neurons'],
                                           connectivity=config['connectivity'],
                                           seed=seed+3)
        self.syn_hidden_out = SynapticLayer(config['n_neurons'],
                                            config['n_output'],
                                            connectivity=config['connectivity'],
                                            seed=seed+4)
        
        # Pools
        buffered = (arm == 'A1_eprop')
        self.pools = MetabolicPools(config['initial_reserves'], buffered=buffered)
        
        # Output spike buffer (for prediction)
        self.output_spike_counts = np.zeros(config['n_output'])
        
        # Stats
        self.ticks_survived = 0
        self.correct_predictions = 0
        self.total_predictions = 0
        self.total_spikes = 0
        self.total_updates = 0
        
    def encode_input(self, input_bit):
        """Rate coding: 10 neurons fire for bit=1, 10 for bit=0."""
        input_spikes = np.zeros(self.config['n_input'])
        # First 10 neurons encode "bit=1"
        input_spikes[:10] = float(input_bit)
        # Last 10 neurons encode "bit=0"  
        input_spikes[10:] = float(1 - input_bit)
        return input_spikes
    
    def predict(self):
        """Predict based on output spike counts."""
        # Use spike counts accumulated over recent ticks
        return int(self.output_spike_counts[0] > self.output_spike_counts[1])
    
    def step(self, input_bit):
        """Run one tick."""
        if not self.pools.alive:
            return False
        
        config = self.config
        
        # Survival cost
        if not self.pools.tick_survival(config['cost_per_tick']):
            return False
        
        # Encode input
        input_spikes = self.encode_input(input_bit)
        
        # Forward pass
        hidden_current = self.syn_in_hidden.forward(input_spikes)
        hidden_spikes = self.hidden_layer.step(hidden_current)
        
        output_current = self.syn_hidden_out.forward(hidden_spikes)
        output_spikes = self.output_layer.step(output_current)
        
        # Accumulate output spikes (for prediction)
        self.output_spike_counts += output_spikes
        
        # Count total spikes
        n_spikes = np.sum(input_spikes) + np.sum(hidden_spikes) + np.sum(output_spikes)
        self.total_spikes += n_spikes
        
        # Update eligibility traces
        if self.arm in ['A1_eprop', 'A3_stdp3c']:
            self.syn_in_hidden.update_eligibility(
                input_spikes, hidden_spikes, self.hidden_layer.v, config['tau_e']
            )
            self.syn_hidden_out.update_eligibility(
                hidden_spikes, output_spikes, self.output_layer.v, config['tau_e']
            )
        
        self.ticks_survived += 1
        return True
    
    def learn(self, target_bit):
        """Apply learning rule after observing target."""
        config = self.config
        
        # Prediction
        pred = self.predict()
        correct = (pred == target_bit)
        
        if correct:
            self.correct_predictions += 1
            self.pools.reward(config['income_per_correct'])
        
        self.total_predictions += 1
        
        # Reset output spike counts for next prediction
        self.output_spike_counts *= 0.0
        
        # Learning
        if self.arm == 'A1_eprop':
            # Neuromodulator: stronger signal for errors
            M = 1.0 if not correct else 0.2
            
            if self.pools.tick_plasticity(config['plasticity_cost_per_update']):
                self.syn_in_hidden.apply_update(M, config['eta'])
                self.syn_hidden_out.apply_update(M, config['eta'])
                self.total_updates += 1
                
        elif self.arm == 'A3_stdp3c':
            M = 1.0 if not correct else 0.2
            
            if self.pools.tick_plasticity(config['plasticity_cost_per_update']):
                self.syn_in_hidden.apply_update(M, config['eta'])
                self.syn_hidden_out.apply_update(M, config['eta'])
                self.total_updates += 1
        
        # A2: no learning
        
        return correct

# ============================================================================
# Run single organism
# ============================================================================

def run_organism(arm, sequence, config, seed):
    """Run one organism."""
    org = Organism(arm, config, seed)
    
    for t in range(1, len(sequence)):
        input_bit = sequence[t-1]
        target_bit = sequence[t]  # predict next bit
        
        if not org.step(input_bit):
            break
        
        org.learn(target_bit)
    
    accuracy = (org.correct_predictions / org.total_predictions 
                if org.total_predictions > 0 else 0.0)
    
    return {
        'arm': arm,
        'seed': seed,
        'ticks_survived': org.ticks_survived,
        'correct': org.correct_predictions,
        'total': org.total_predictions,
        'accuracy': float(accuracy),
        'spikes': int(org.total_spikes),
        'updates': int(org.total_updates),
        'energy_used': float(org.total_spikes * config['energy_per_spike']),
        'died': bool(not org.pools.alive),
    }

# ============================================================================
# Run experiment
# ============================================================================

def run_experiment(config):
    """Run full experiment."""
    print("=" * 70)
    print("Exp-P2A-01 v2: e-prop with fixes")
    print("=" * 70)
    print(f"Task: Copy previous bit (trivially learnable)")
    print(f"Network: {config['n_neurons']} hidden LIF")
    print(f"Seeds: {config['n_seeds']} per arm")
    print()
    
    all_results = []
    
    for arm in config['arms']:
        print(f"Running {arm}...")
        arm_results = []
        
        for seed_idx in range(config['n_seeds']):
            seed = config['random_seed'] + seed_idx
            sequence = generate_sequence(
                config['n_ticks'],
                config['noise_rate'],
                seed
            )
            
            result = run_organism(arm, sequence, config, seed)
            arm_results.append(result)
            
            status = "✓" if not result['died'] else "✗"
            print(f"  seed {seed}: acc={result['accuracy']:.3f}, "
                  f"updates={result['updates']}, {status}")
        
        all_results.append({
            'arm': arm,
            'seeds': arm_results,
            'mean_accuracy': float(np.mean([r['accuracy'] for r in arm_results])),
            'std_accuracy': float(np.std([r['accuracy'] for r in arm_results])),
            'mean_ticks': float(np.mean([r['ticks_survived'] for r in arm_results])),
            'deaths': int(sum(1 for r in arm_results if r['died'])),
        })
    
    return all_results

# ============================================================================
# Analyze
# ============================================================================

def analyze_results(results, config):
    """Analyze against pre-registered bars."""
    print()
    print("=" * 70)
    print("Results Analysis")
    print("=" * 70)
    
    a1 = next(r for r in results if r['arm'] == 'A1_eprop')
    a2 = next(r for r in results if r['arm'] == 'A2_nolearn')
    a3 = next(r for r in results if r['arm'] == 'A3_stdp3c')
    
    print()
    print("Summary:")
    print("-" * 70)
    print(f"{'Arm':<20} {'Mean Acc':<12} {'Std':<10} {'Deaths':<10}")
    print("-" * 70)
    for r in results:
        print(f"{r['arm']:<20} {r['mean_accuracy']:<12.3f} "
              f"{r['std_accuracy']:<10.3f} {r['deaths']:<10}")
    
    print()
    print("Gate A (delta >= +5pp):")
    delta = (a1['mean_accuracy'] - a2['mean_accuracy']) * 100
    print(f"A1 vs A2: {delta:+.2f} pp")
    print(f"Bar: +5.00 pp")
    print(f"Result: {'✅ PASS' if delta >= 5.0 else '❌ FAIL'}")
    
    print()
    print("A1 vs A3:")
    delta3 = (a1['mean_accuracy'] - a3['mean_accuracy']) * 100
    print(f"Delta: {delta3:+.2f} pp")
    
    print()
    print("Permutation test (A1 vs A2):")
    a1_accs = [r['accuracy'] for r in a1['seeds']]
    a2_accs = [r['accuracy'] for r in a2['seeds']]
    observed_diff = np.mean(a1_accs) - np.mean(a2_accs)
    combined = a1_accs + a2_accs
    rng = np.random.RandomState(42)
    perm_diffs = []
    for _ in range(1000):
        rng.shuffle(combined)
        perm_diffs.append(np.mean(combined[:len(a1_accs)]) - np.mean(combined[len(a1_accs):]))
    p_value = float(np.mean(np.abs(perm_diffs) >= np.abs(observed_diff)))
    print(f"p-value: {p_value:.4f}")
    print(f"Result: {'✅ PASS' if p_value < 0.05 else '❌ FAIL'}")
    
    h1_confirmed = bool(delta >= 5.0 and p_value < 0.05)
    
    print()
    print("Hypothesis Test:")
    if h1_confirmed:
        print("🎉 H1 CONFIRMED: e-prop with buffering rescues learning!")
    else:
        print("⚠️  H1 NULL — classify into F1-F5")
    
    print("=" * 70)
    
    return {
        'delta_a1_a2': float(delta),
        'p_value': float(p_value),
        'h1_confirmed': h1_confirmed,  # bool, not bool_
    }

# ============================================================================
# Save
# ============================================================================

def save_results(results, analysis, config):
    """Save to JSON."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v2_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'config': config,
        'results': results,
        'analysis': analysis,
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")

# ============================================================================
# Main
# ============================================================================

def main():
    results = run_experiment(CONFIG)
    analysis = analyze_results(results, CONFIG)
    save_results(results, analysis, CONFIG)
    print("\n✅ Done!")

if __name__ == '__main__':
    main()