#!/usr/bin/env python
"""
Exp-P2A-01 v27: Postsynaptic-Gated e-prop (Dense Input + Binary Gate)
=====================================================================
Pre-registration (Rule 2):
  H1: noise=5% → accuracy ≥ 76.8%  [+10pp vs v25=66.8%]
  H2: noise=0% → accuracy ≥ 88.7%  [≥98% of v25=90.7%]
  Success = H1 AND H2

Changes from v25 (ONLY ONE CHANGE):
  + Postsynaptic binary gate: G_j = (a_bar_post[j] > median(a_bar_post))
  - Input: 2-neuron dense (SAME as v25, undoing v26 sparse)
  - eta: 0.01 (SAME as v25)
  - n_trials: 500 (SAME as v25)
  - NO surprise gate (deferred to v28 if needed)

Failure attribution:
  H1 fail + H2 pass → gate insufficient → v28: surprise gate
  H2 fail + H1 pass → gate blocks signal → theta_gate too high
  Both fail → fundamental issue → stop and reassess
  Both pass → proceed to metabolic constraint test

Biological justification:
  G_j models Back-propagating Action Potentials (BAP):
  synaptic plasticity only occurs when postsynaptic neuron is active.
  Reference: Sjöström & Häusser (2006), Nature Neuroscience.
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
    
    # Dense input (SAME as v25 - undoing v26 sparse)
    'n_input': 10,    # neurons 0,1 = signal; neurons 2-9 = noise channels
    'n_hidden': 50,
    'n_output': 2,
    
    'theta': 1.0,
    'tau_mem': 20.0,
    'tau_syn': 20.0,
    
    'tau_e': 15.0,  
    'beta': 1.0,
    
    # Postsynaptic Gating (THE ONLY NEW THING in v27)
    'use_postsynaptic_gate': True,
    'tau_gate': 200.0,  # >> trial_length for stable running mean
    
    'eta': 0.01,        # SAME as v25
    'w_scale': 0.5,
    
    'plasticity_pool_capacity': 50.0,
    'refill_rate': 1.0,
    'update_cost': 1.0,
    
    'arms': ['A1_buffered', 'A2_nolearn', 'A3_coupled'],
    'n_seeds': 5,
    'random_seed': 42,
    
    'noise_levels': [0.0, 0.05, 0.1, 0.2, 0.3, 0.5],
    'failure_threshold': 0.70,
    
    # Pre-registration (Opus recommended)
    'H1_threshold': 0.768,  # v25 noise=5% (66.8%) + 10pp
    'H2_threshold': 0.887,  # v25 noise=0% (90.7%) - 2pp
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
    
    def update_eligibility(self, pre_spikes, post_f_prime, tau_e, 
                           postsynaptic_gate=None):
        """
        Standard e-prop eligibility update with optional postsynaptic gate.
        
        If postsynaptic_gate is provided (shape n_out):
          eps[i,j] += G_j * f'(v_j) * z_i
        Otherwise:
          eps[i,j] += f'(v_j) * z_i  (standard e-prop)
        """
        self.eligibility *= np.exp(-1.0 / tau_e)
        
        if postsynaptic_gate is not None:
            # Gate: only update eligibility for active postsynaptic neurons
            gated_f_prime = post_f_prime * postsynaptic_gate
            delta_e = np.outer(gated_f_prime, pre_spikes)
        else:
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
    use_gate = config['use_postsynaptic_gate']
    
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
    
    # Postsynaptic gate state
    tau_gate = config['tau_gate']
    beta_gate = np.exp(-1.0 / tau_gate)
    a_bar_post = np.zeros(config['n_hidden'])  # running mean of firing rate
    theta_gate = 0.0  # will be set to median after first trial
    
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
        
        # Compute gate for this trial (based on previous trials' activity)
        if use_gate and trial > 0:
            theta_gate = np.median(a_bar_post)
            G = (a_bar_post > theta_gate).astype(float)
        else:
            G = np.ones(config['n_hidden'])  # first trial: all gates open
        
        spike_count_this_trial = np.zeros(config['n_hidden'])
        
        for t in range(trial_length):
            # Dense input encoding (SAME as v25)
            x = np.zeros(config['n_input'])
            if t == T_A and A == 1: x[0] = 1.0
            if t == T_B and B == 1: x[1] = 1.0
            
            # Noise on dedicated channels (neurons 2-9)
            if noise_level > 0:
                for i in range(2, config['n_input']):
                    if rng.rand() < noise_level:
                        x[i] = 1.0
            
            i_in = syn_in.forward(x)
            i_rec = syn_rec.forward(hidden.last_spikes)
            hidden.step(i_in + i_rec)
            
            # Track spikes for gate update
            spike_count_this_trial += hidden.last_spikes
            
            if arm in ['A1_buffered', 'A3_coupled']:
                f_prime = hidden.surrogate_derivative(config['beta'])
                
                # Eligibility update with postsynaptic gate
                gate = G if use_gate else None
                syn_in.update_eligibility(x, f_prime, config['tau_e'], 
                                          postsynaptic_gate=gate)
                syn_rec.update_eligibility(hidden.last_spikes, f_prime, config['tau_e'],
                                          postsynaptic_gate=gate)
                
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
        
        # Update running mean at END of trial (not each tick)
        if use_gate:
            firing_rate_this_trial = spike_count_this_trial / trial_length
            a_bar_post = beta_gate * a_bar_post + (1 - beta_gate) * firing_rate_this_trial
                
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
    
    for arm_name in ['A1_buffered', 'A2_nolearn', 'A3_coupled']:
        accs = [sweep_data[str(nl)][arm_name]['mean_accuracy'] for nl in noise_levels]
        plt.plot(noise_levels, accs, marker='o', linewidth=2, label=f'v27 {arm_name}')
    
    # v25 reference (dense, no gate)
    v25_a1 = {0.0: 0.907, 0.05: 0.668, 0.1: 0.590, 0.2: 0.526, 0.3: 0.524, 0.5: 0.507}
    plt.plot(noise_levels, [v25_a1[nl] for nl in noise_levels], 
             'k--', alpha=0.5, label='v25 A1 (no gate)')
    
    plt.axhline(y=config['H1_threshold'], color='g', linestyle='--', 
                label=f'H1 ({config["H1_threshold"]*100:.1f}%)')
    plt.axhline(y=config['H2_threshold'], color='b', linestyle=':', 
                label=f'H2 ({config["H2_threshold"]*100:.1f}%)')
    plt.axhline(y=config['failure_threshold'], color='r', linestyle='-.', 
                label=f'Failure ({config["failure_threshold"]*100:.0f}%)')
    
    plt.xlabel('Noise Level')
    plt.ylabel('Accuracy')
    plt.title('v27: Postsynaptic Gate (Dense Input) vs v25 (No Gate)')
    plt.legend(loc='lower left')
    plt.grid(True, alpha=0.3)
    plt.ylim(0.4, 1.0)
    
    plot_path = RESULTS_DIR / 'exp_p2a_01_v27_postsynaptic_gate.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    return plot_path


def main():
    print("=" * 70)
    print("Exp-P2A-01 v27: Postsynaptic-Gated e-prop")
    print("=" * 70)
    print("Pre-registration (Rule 2):")
    print(f"  H1: noise=5% → acc ≥ {CONFIG['H1_threshold']*100:.1f}%")
    print(f"  H2: noise=0% → acc ≥ {CONFIG['H2_threshold']*100:.1f}%")
    print(f"  Success = H1 AND H2")
    print()
    print("Changes from v25: + postsynaptic binary gate ONLY")
    print(f"  Gate: binary, theta = median(a_bar_post)")
    print(f"  tau_gate = {CONFIG['tau_gate']} (>> trial_length)")
    print(f"  Input: {CONFIG['n_input']} neurons (2 signal + 8 noise)")
    print(f"  eta = {CONFIG['eta']}, trials = {CONFIG['n_trials']}")
    print("=" * 70)
    print()
    
    sweep_data = {}
    
    for nl in CONFIG['noise_levels']:
        print(f"\n--- Noise Level: {nl} ---")
        sweep_data[str(nl)] = {}
        
        for arm in CONFIG['arms']:
            print(f"  {arm}:", end=" ", flush=True)
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
                  f"upd={mean_updates:.0f}, blk={mean_blocked:.0f}")
    
    # Results table
    print("\n" + "=" * 90)
    print("RESULTS (v27 - Postsynaptic Gate)")
    print("=" * 90)
    print(f"{'Noise':<8} | {'A1_buffered':<12} | {'A2_nolearn':<12} | {'A3_coupled':<12} | {'v25 A1 ref':<12}")
    print("-" * 90)
    
    v25_ref = {0.0: 0.907, 0.05: 0.668, 0.1: 0.590, 0.2: 0.526, 0.3: 0.524, 0.5: 0.507}
    for nl in CONFIG['noise_levels']:
        a1 = sweep_data[str(nl)]['A1_buffered']['mean_accuracy']
        a2 = sweep_data[str(nl)]['A2_nolearn']['mean_accuracy']
        a3 = sweep_data[str(nl)]['A3_coupled']['mean_accuracy']
        ref = v25_ref.get(nl, 0)
        delta = (a1 - ref) * 100
        print(f"{nl:<8.2f} | {a1:<12.3f} | {a2:<12.3f} | {a3:<12.3f} | {ref:<8.3f} ({delta:+.1f}pp)")
    print("=" * 90)
    
    # Hypothesis testing
    print("\n" + "=" * 70)
    print("HYPOTHESIS TESTING")
    print("=" * 70)
    
    a1_noise_0 = sweep_data['0.0']['A1_buffered']['mean_accuracy']
    a1_noise_005 = sweep_data['0.05']['A1_buffered']['mean_accuracy']
    
    H1_pass = a1_noise_005 >= CONFIG['H1_threshold']
    H2_pass = a1_noise_0 >= CONFIG['H2_threshold']
    
    print(f"H1 (noise=5% ≥ {CONFIG['H1_threshold']*100:.1f}%): "
          f"actual={a1_noise_005*100:.1f}% → {'✅ PASS' if H1_pass else '❌ FAIL'}")
    print(f"H2 (noise=0% ≥ {CONFIG['H2_threshold']*100:.1f}%): "
          f"actual={a1_noise_0*100:.1f}% → {'✅ PASS' if H2_pass else '❌ FAIL'}")
    
    print()
    if H1_pass and H2_pass:
        print("🎉 SUCCESS: Postsynaptic gate improves noise tolerance without regression!")
        print("   → Next: Proceed to metabolic constraint test at scale")
    elif not H1_pass and H2_pass:
        print("⚠️  PARTIAL: Gate preserves signal but doesn't fix noise.")
        print("   → Next: v28 with surprise-driven input gate")
    elif H1_pass and not H2_pass:
        print("⚠️  PARTIAL: Gate helps noise but blocks signal.")
        print("   → Next: Lower theta_gate (use 25th percentile instead of median)")
    else:
        print("❌ FAIL: Both hypotheses rejected.")
        print("   → STOP. Reassess: Is noise robustness needed for Phase 2A?")
        print("   → Phase 2A hypothesis is about METABOLIC CONSTRAINT, not noise.")
    
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
            print(f"  {arm}: ✅ ROBUST up to max noise")
    
    # Plot
    plot_path = plot_results(sweep_data, CONFIG)
    print(f"\n📊 Plot: {plot_path}")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'exp_p2a_01_v27_postsynaptic_gate_{timestamp}.json'
    
    json_data = {
        'timestamp': timestamp,
        'version': 'v27 (Postsynaptic Gate, Dense Input)',
        'pre_registration': {
            'H1': f"noise=5% acc ≥ {CONFIG['H1_threshold']}",
            'H2': f"noise=0% acc ≥ {CONFIG['H2_threshold']}",
            'H1_result': float(a1_noise_005),
            'H2_result': float(a1_noise_0),
            'H1_pass': bool(H1_pass),
            'H2_pass': bool(H2_pass),
            'success': bool(H1_pass and H2_pass),
        },
        'config': {k: v for k, v in CONFIG.items() if k != 'seeds'},
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