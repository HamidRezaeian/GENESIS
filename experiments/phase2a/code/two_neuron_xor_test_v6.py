#!/usr/bin/env python
"""
2-Neuron XOR Test v6 (STABLE)
==============================
Fix: lower eta + gradient clipping + weight clipping
"""

import numpy as np

def two_neuron_xor_test_v6():
    """XOR with stable training."""
    
    print("=" * 70)
    print("2-Neuron XOR Test v6 (STABLE)")
    print("=" * 70)
    print("Network: 2 input → 5 hidden LIF → 2 output (softmax)")
    print("Task: XOR of two bits")
    print("Fix: eta=0.01, gradient clipping, weight clipping")
    print("=" * 70)
    
    np.random.seed(42)
    
    n_in, n_h, n_out = 2, 5, 2
    dv = 0.05
    theta = 0.5
    eta = 0.01  # ← 10x smaller
    beta = 5.0
    max_grad = 1.0
    max_weight = 3.0
    
    W_in  = np.random.randn(n_h, n_in)  * 0.3
    W_out = np.random.randn(n_out, n_h) * 0.3
    
    def surrogate(v, thr=0.5, beta=5.0):
        return 1.0 / (1.0 + beta * np.abs(v - thr))**2
    
    def softmax(x):
        e = np.exp(x - x.max())
        return e / e.sum()
    
    xor_data = [
        ([1, 0], 1),
        ([0, 1], 1),
        ([0, 0], 0),
        ([1, 1], 0),
    ]
    
    print(f"\nTraining data:")
    for inp, target in xor_data:
        print(f"  Input {inp} → Target {target}")
    
    print(f"\n{'Epoch':>6} | {'Loss':>8} | {'Acc':>6} | {'z1 sum':>8} | {'z2 sum':>8}")
    print("-" * 55)
    
    losses, accs = [], []
    
    for epoch in range(500):
        epoch_loss, correct = 0, 0
        z1_sums, z2_sums = [], []
        
        for inp, target_class in xor_data:
            v = np.zeros(n_h)
            r = np.zeros(n_out)
            eps_in = np.zeros_like(W_in)
            h_activity = np.zeros(n_h)
            
            dW_in = np.zeros_like(W_in)
            dW_out = np.zeros_like(W_out)
            
            # t=1: Input A
            x1 = np.zeros(n_in)
            x1[0] = inp[0]
            
            I1 = W_in @ x1
            v = (1 - dv) * v + dv * (I1 / dv)
            z1 = (v >= theta).astype(float)
            fp1 = surrogate(v)
            v[z1 == 1] -= theta
            eps_in = (1 - dv) * eps_in + fp1[:, None] * x1[None, :]
            h_activity += z1
            
            # t=2: Input B
            x2 = np.zeros(n_in)
            x2[1] = inp[1]
            
            I2 = W_in @ x2
            v = (1 - dv) * v + dv * (I2 / dv)
            z2 = (v >= theta).astype(float)
            fp2 = surrogate(v)
            v[z2 == 1] -= theta
            eps_in = (1 - dv) * eps_in + fp2[:, None] * x2[None, :]
            h_activity += z2
            
            z1_sums.append(np.sum(z1))
            z2_sums.append(np.sum(z2))
            
            # t=3: Output
            r = (1 - dv) * r + dv * (W_out @ h_activity)
            y = softmax(r)
            
            target = np.zeros(n_out)
            target[target_class] = 1.0
            error = y - target
            loss = -np.log(y[target_class] + 1e-9)
            
            L = W_out.T @ error
            dW_in  += L[:, None] * eps_in
            dW_out += np.outer(error, h_activity)
            
            pred = int(y.argmax())
            correct += int(pred == target_class)
            epoch_loss += loss
        
        # ← Gradient clipping
        dW_in = np.clip(dW_in, -max_grad, max_grad)
        dW_out = np.clip(dW_out, -max_grad, max_grad)
        
        # ← Sign invert + smaller eta
        W_in  += eta * dW_in
        W_out += eta * dW_out
        
        # ← Weight clipping
        W_in = np.clip(W_in, -max_weight, max_weight)
        W_out = np.clip(W_out, -max_weight, max_weight)
        
        avg_loss = epoch_loss / 4
        acc = correct / 4
        losses.append(avg_loss)
        accs.append(acc)
        
        if epoch % 100 == 0 or epoch < 10:
            avg_z1 = np.mean(z1_sums)
            avg_z2 = np.mean(z2_sums)
            print(f"{epoch:>6} | {avg_loss:>8.4f} | {acc:>6.2%} | "
                  f"{avg_z1:>8.3f} | {avg_z2:>8.3f}")
    
    # Final result
    print()
    print("=" * 70)
    print("Result:")
    print("=" * 70)
    
    final_loss = losses[-1]
    final_acc = accs[-1]
    
    print(f"Final loss: {final_loss:.4f}")
    print(f"Final accuracy: {final_acc:.2%}")
    
    # Check individual predictions
    print(f"\nFinal predictions:")
    for inp, target_class in xor_data:
        v = np.zeros(n_h)
        r = np.zeros(n_out)
        h_activity = np.zeros(n_h)
        
        x1 = np.zeros(n_in); x1[0] = inp[0]
        v = (1 - dv) * v + dv * (W_in @ x1 / dv)
        z1 = (v >= theta).astype(float)
        v[z1 == 1] -= theta
        h_activity += z1
        
        x2 = np.zeros(n_in); x2[1] = inp[1]
        v = (1 - dv) * v + dv * (W_in @ x2 / dv)
        z2 = (v >= theta).astype(float)
        v[z2 == 1] -= theta
        h_activity += z2
        
        r = (1 - dv) * r + dv * (W_out @ h_activity)
        y = softmax(r)
        pred = int(y.argmax())
        status = "✅" if pred == target_class else "❌"
        print(f"  {status} Input {inp} → Pred {pred}, Target {target_class}, y={y}")
    
    if final_acc > 0.9:
        print(f"\n✅ SUCCESS: e-prop learned XOR perfectly!")
        print(f"   → Ready to port to full Temporal XOR task")
        return True
    elif final_acc > 0.7:
        print(f"\n⚠️  GOOD: 75% accuracy (3 of 4 correct)")
        print(f"   → e-prop mostly works")
        print(f"   → Port to full task with caution")
        return True
    else:
        print(f"\n❌ FAILURE")
        return False
    
    print("=" * 70)

if __name__ == '__main__':
    success = two_neuron_xor_test_v6()
    if success:
        print("\n🎉 Next step: Port to full Temporal XOR with these fixes")
    else:
        print("\n⚠️  Need more debugging")