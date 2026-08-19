#!/usr/bin/env python
"""
2-Neuron XOR Test v3 (FIXED)
=============================
Fix: dW_out با leaky integrator output (r) به جای raw spikes (z2)
"""

import numpy as np

def two_neuron_xor_test_v3():
    """XOR with leaky integrator output for dW_out."""
    
    print("=" * 70)
    print("2-Neuron XOR Test v3 (FIXED)")
    print("=" * 70)
    print("Network: 2 input → 5 hidden LIF → 2 output (softmax)")
    print("Task: XOR of two bits presented at t=1 and t=2")
    print("Fix: dW_out uses leaky integrator (r), not raw spikes (z2)")
    print("=" * 70)
    
    np.random.seed(42)
    
    n_in, n_h, n_out = 2, 5, 2
    dv = 0.05
    theta = 0.5
    eta = 0.1
    beta = 5.0
    tau_out = 10.0  # leaky integrator time constant
    
    W_in  = np.random.randn(n_h, n_in)  * 0.3
    W_out = np.random.randn(n_out, n_h) * 0.3
    
    def surrogate(v, thr=0.5, beta=5.0):
        return 1.0 / (1.0 + beta * np.abs(v - thr))**2
    
    def softmax(x):
        e = np.exp(x - x.max())
        return e / e.sum()
    
    # XOR training data
    xor_data = [
        ([1, 0], 1),
        ([0, 1], 1),
        ([0, 0], 0),
        ([1, 1], 0),
    ]
    
    print(f"\nTraining data:")
    for inp, target in xor_data:
        print(f"  Input {inp} → Target {target}")
    
    print(f"\n{'Epoch':>6} | {'Loss':>8} | {'Acc':>6} | {'z2 sum':>8} | {'r sum':>8}")
    print("-" * 55)
    
    losses, accs = [], []
    
    for epoch in range(300):
        epoch_loss, correct = 0, 0
        z2_sums, r_sums = [], []
        
        for inp, target_class in xor_data:
            # Reset state
            v = np.zeros(n_h)
            r = np.zeros(n_out)  # leaky integrator
            eps_in = np.zeros_like(W_in)
            
            dW_in = np.zeros_like(W_in)
            dW_out = np.zeros_like(W_out)
            loss = None
            
            # t=1: Input A
            x1 = np.zeros(n_in)
            x1[0] = inp[0]
            
            I1 = W_in @ x1
            v = (1 - dv) * v + dv * (I1 / dv)
            z1 = (v >= theta).astype(float)
            fp1 = surrogate(v)
            v[z1 == 1] -= theta
            eps_in = (1 - dv) * eps_in + fp1[:, None] * x1[None, :]
            
            # t=2: Input B
            x2 = np.zeros(n_in)
            x2[1] = inp[1]
            
            I2 = W_in @ x2
            v = (1 - dv) * v + dv * (I2 / dv)
            z2 = (v >= theta).astype(float)
            fp2 = surrogate(v)
            v[z2 == 1] -= theta
            eps_in = (1 - dv) * eps_in + fp2[:, None] * x2[None, :]
            
            # ← FIX: Leaky integrator accumulates over time
            r = (1 - 1/tau_out) * r + (W_out @ z1) / tau_out
            r = (1 - 1/tau_out) * r + (W_out @ z2) / tau_out
            
            z2_sums.append(np.sum(z2))
            r_sums.append(np.sum(r))
            
            # t=3: Output
            y = softmax(r)
            
            target = np.zeros(n_out)
            target[target_class] = 1.0
            error = y - target
            loss = -np.log(y[target_class] + 1e-9)
            
            L = W_out.T @ error
            dW_in  += L[:, None] * eps_in
            
            # ← FIX: dW_out uses r (leaky integrator), not z2
            dW_out += np.outer(error, r)  # ← r instead of z2!
            
            pred = int(y.argmax())
            correct += int(pred == target_class)
            epoch_loss += loss
        
        # Update weights
        W_in  -= eta * dW_in
        W_out -= eta * dW_out
        
        avg_loss = epoch_loss / 4
        acc = correct / 4
        losses.append(avg_loss)
        accs.append(acc)
        
        if epoch % 50 == 0:
            avg_z2 = np.mean(z2_sums)
            avg_r = np.mean(r_sums)
            print(f"{epoch:>6} | {avg_loss:>8.4f} | {acc:>6.2%} | "
                  f"{avg_z2:>8.3f} | {avg_r:>8.3f}")
    
    # Final result
    print()
    print("=" * 70)
    print("Result:")
    print("=" * 70)
    
    final_loss = losses[-1]
    final_acc = accs[-1]
    
    print(f"Final loss: {final_loss:.4f}")
    print(f"Final accuracy: {final_acc:.2%}")
    
    if final_acc > 0.8:
        print(f"\n✅ SUCCESS: e-prop learned XOR!")
        print(f"   → Problem was in dW_out using raw spikes")
        print(f"   → Leaky integrator fixes the issue")
        print(f"   → Next: Apply this fix to full Temporal XOR task")
    elif final_acc > 0.5:
        print(f"\n⚠️  PARTIAL: Some learning but not complete")
        print(f"   → May need more epochs or higher eta")
    else:
        print(f"\n❌ FAILURE: e-prop still cannot learn XOR")
        print(f"   → Problem is deeper in eligibility trace")
        print(f"   → Consider Norse diagnostic")
    
    print("=" * 70)

if __name__ == '__main__':
    two_neuron_xor_test_v3()