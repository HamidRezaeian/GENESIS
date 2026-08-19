#!/usr/bin/env python
"""
Positive Control: e-prop روی XOR بدون Metabolic Constraint
============================================================
اگر این کار کند:
  → Implementation درست است
  → Task درست است
  → می‌توانیم null result با constraint بگیریم

اگر کار نکند:
  → Implementation هنوز مشکل دارد
  → باید debug بیشتر کنیم
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

CONFIG = {
    # Task
    'n_ticks': 5000,  # Longer for better learning
    'T1': 3,
    'T2': 6,
    'T_out': 9,
    'pulse_prob': 0.3,
    
    # Network
    'n_input': 30,
    'n_hidden': 100,
    'n_output': 2,
    
    # LIF dynamics
    'theta': 0.3,
    'tau_m': 20.0,
    'dv': 0.05,
    'du': 0.05,
    
    # Output
    'tau_out': 20.0,
    'readout_window': 5,
    
    # Synaptic
    'w_scale': 1.0,
    'connectivity': 0.3,
    'recurrent_connectivity': 0.2,
    
    # Learning
    'eta': 0.05,
    'tau_e': 20.0,
    'beta': 5.0,
    
    # Stability
    'max_weight': 5.0,
    'max_grad': 1.0,
    
    # Experiment
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
        self.weights += delta_w
        self.weights = np.clip(self.weights, -max_weight, max_weight)
        return delta_w


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
    """Encode current pulse and input[t-T1]."""
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


def run_eprop_no_constraint(input_pulses, targets, seed):
    """Run e-prop WITHOUT metabolic constraint (positive control)."""
    
    T1 = CONFIG['T1']
    T2 = CONFIG['T2']
    T_out = CONFIG['T_out']
    readout_window = CONFIG['readout_window']
    n_hidden = CONFIG['n_hidden']
    n_output = CONFIG['n_output']
    tau_e = CONFIG['tau_e']
    eta = CONFIG['eta']
    
    # Network
    hidden = LIFPool(n_hidden, theta=CONFIG['theta'], dv=CONFIG['dv'], du=CONFIG['du'])
    output_layer = OutputLayer(n_output, tau_out=CONFIG['tau_out'])
    
    # Synapses
    syn_in = SynapticLayer(CONFIG['n_input'], n_hidden,
                           connectivity=CONFIG['connectivity'],
                           w_scale=CONFIG['w_scale'], seed=seed)
    syn_rec = SynapticLayer(n_hidden, n_hidden,
                            connectivity=CONFIG['recurrent_connectivity'],
                            w_scale=CONFIG['w_scale'], seed=seed+1)
    syn_out = SynapticLayer(n_hidden, n_output,
                            connectivity=CONFIG['connectivity'],
                            w_scale=CONFIG['w_scale'], seed=seed+2)
    
    # State
    all_predictions = []
    all_targets = []
    loss_history = []
    hidden_spike_history = []
    
    for t in range(len(input_pulses)):
        pulse = input_pulses[t]
        input_t3 = input_pulses[t - T1] if t >= T1 else 0
        x = encode_input(pulse, input_t3, CONFIG['n_input'])
        
        # Forward
        u_in = syn_in.forward(x)
        u_rec = syn_rec.forward(hidden.last_spikes)
        s_hidden = hidden.step(u_in + u_rec)
        
        hidden_spike_history.append(s_hidden.copy())
        if len(hidden_spike_history) > readout_window:
            hidden_spike_history.pop(0)
        
        u_out = syn_out.forward(s_hidden)
        r_out = output_layer.step(u_out)
        
        # Eligibility in every tick
        f_prime_hidden = hidden.surrogate_derivative()
        syn_in.update_eligibility(x, f_prime_hidden, tau_e)
        syn_rec.update_eligibility(hidden.last_spikes, f_prime_hidden, tau_e)
        
        # Error and update at T_out
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
            
            # Learning signal (gradient descent)
            L_hidden = -(syn_out.weights.T @ error)
            L_hidden = np.clip(L_hidden, -CONFIG['max_grad'], CONFIG['max_grad'])
            
            # ← NO CONSTRAINT: always update
            syn_in.apply_update(L_hidden, eta, CONFIG['max_weight'], CONFIG['max_grad'])
            syn_rec.apply_update(L_hidden, eta, CONFIG['max_weight'], CONFIG['max_grad'])
            
            if len(hidden_spike_history) > 0:
                s_hidden_avg = np.mean(hidden_spike_history, axis=0)
            else:
                s_hidden_avg = s_hidden
            
            delta_out = -eta * np.outer(error, s_hidden_avg)
            delta_out = np.clip(delta_out, -CONFIG['max_grad'], CONFIG['max_grad'])
            syn_out.weights += delta_out
            syn_out.weights = np.clip(syn_out.weights, -CONFIG['max_weight'], CONFIG['max_weight'])
            
            # Reset after trial
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
        'seed': seed,
        'balanced_accuracy': float(bal_acc),
        'mean_loss': float(mean_loss),
        'n_trials': len(all_predictions),
    }


def main():
    print("=" * 70)
    print("Positive Control: e-prop WITHOUT Metabolic Constraint")
    print("=" * 70)
    print(f"Task: Temporal XOR (T1={CONFIG['T1']}, T2={CONFIG['T2']})")
    print(f"Network: {CONFIG['n_hidden']} hidden LIF")
    print(f"eta = {CONFIG['eta']}")
    print(f"Seeds: {CONFIG['n_seeds']}")
    print(f"\nGoal: Verify e-prop can learn XOR without constraint")
    print("=" * 70)
    
    results = []
    
    for seed_idx in range(CONFIG['n_seeds']):
        seed = CONFIG['random_seed'] + seed_idx
        input_pulses, targets = generate_temporal_xor(
            CONFIG['n_ticks'], CONFIG['T1'], CONFIG['T2'], CONFIG['T_out'],
            CONFIG['pulse_prob'], seed
        )
        
        result = run_eprop_no_constraint(input_pulses, targets, seed)
        results.append(result)
        
        print(f"  seed {seed}: bal_acc={result['balanced_accuracy']:.3f}, "
              f"loss={result['mean_loss']:.3f}")
    
    # Analysis
    print()
    print("=" * 70)
    print("Results Analysis")
    print("=" * 70)
    
    mean_acc = np.mean([r['balanced_accuracy'] for r in results])
    std_acc = np.std([r['balanced_accuracy'] for r in results])
    mean_loss = np.mean([r['mean_loss'] for r in results])
    
    print()
    print(f"Mean balanced accuracy: {mean_acc:.3f} ± {std_acc:.3f}")
    print(f"Mean loss: {mean_loss:.3f}")
    print(f"Random baseline: 0.500")
    
    print()
    print("Positive Control Check:")
    print("-" * 60)
    
    if mean_acc > 0.60:
        print(f"  ✅ PASS: e-prop learns XOR without constraint")
        print(f"     Accuracy: {mean_acc:.3f} > 0.60")
        print(f"\n  → Implementation is CORRECT")
        print(f"  → Task is VALID")
        print(f"  → Next: Run with constraint to test buffering hypothesis")
        success = True
    elif mean_acc > 0.55:
        print(f"  ⚠️  WEAK: e-prop shows some learning")
        print(f"     Accuracy: {mean_acc:.3f} (55-60%)")
        print(f"\n  → Implementation mostly works")
        print(f"  → May need more training or tuning")
        success = True
    else:
        print(f"  ❌ FAIL: e-prop does NOT learn XOR")
        print(f"     Accuracy: {mean_acc:.3f} ≈ 0.50 (random)")
        print(f"\n  → Implementation still broken")
        print(f"  → Cannot claim null result with constraint")
        print(f"  → Must debug further")
        success = False
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = RESULTS_DIR / f'positive_control_xor_{timestamp}.json'
    
    data = {
        'timestamp': timestamp,
        'test': 'positive_control_xor_no_constraint',
        'config': CONFIG,
        'results': results,
        'mean_accuracy': float(mean_acc),
        'std_accuracy': float(std_acc),
        'mean_loss': float(mean_loss),
        'success': success,
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    print("=" * 70)
    
    if success:
        print("\n🎉 Positive control PASSED!")
        print("   Next step: Run Exp-P2A-01 with constraint (A1 vs A3)")
    else:
        print("\n❌ Positive control FAILED!")
        print("   Must debug implementation before null result claim")
    
    print("=" * 70)


if __name__ == '__main__':
    main()