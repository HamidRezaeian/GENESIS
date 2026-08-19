#!/usr/bin/env python
"""
Test بدون Recurrent: Isolate کردن مشکل
=======================================
اگر بدون recurrent کار کند: مشکل در recurrent است
اگر بدون recurrent کار نکند: مشکل در eligibility یا task است
"""

import numpy as np

def no_recurrent_test():
    """e-prop بدون recurrent connections."""
    
    print("=" * 70)
    print("No Recurrent Test: Isolate Problem")
    print("=" * 70)
    print("Network: 2 input → 10 hidden LIF → 2 output (NO recurrent)")
    print("Task: XOR of two bits at t=1 and t=2")
    print("If works: problem is in recurrent connections")
    print("If fails: problem is in eligibility trace")
    print("=" * 70)
    
    np.random.seed(42)
    
    n_in, n_h, n_out = 2, 10, 2
    dv = 0.05
    theta = 0.3  # lower threshold
    eta = 0.05
    beta = 5.0
    max_grad = 1.0
    max_weight = 5.0
    
    # Larger initial weights to ensure spiking
    W_in  = np.random.randn(n_h, n_in)  * 0.5
    W_out = np.random.randn(n_out, n_h) * 0.5
    
    def surrogate(v, thr=0.3, beta=5.0):
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
            
            # t=2: Input B (NO recurrent - just W_in @ x2)
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
        
        # Gradient clipping
        dW_in = np.clip(dW_in, -max_grad, max_grad)
        dW_out = np.clip(dW_out, -max_grad, max_grad)
        
        # Gradient descent: W -= eta * gradient
        # Note: error = y - target, so gradient = error * activity
        # For gradient descent: W -= eta * gradient
        W_in  -= eta * dW_in
        W_out -= eta * dW_out
        
        # Weight clipping
        W_in = np.clip(W_in, -max_weight, max_weight)
        W_out = np.clip(W_out, -max_weight, max_weight)
        
        avg_loss = epoch_loss / 4
        acc = correct / 4
        losses.append(avg_loss)
        accs.append(acc)
        
        if epoch % 100 == 0 or epoch < 5:
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
    
    if final_acc > 0.9:
        print(f"\n✅ SUCCESS: e-prop works WITHOUT recurrent!")
        print(f"   → Problem is in recurrent connections")
        print(f"   → Fix: check eligibility trace for recurrent")
        return "recurrent_problem"
    elif final_acc > 0.7:
        print(f"\n⚠️  PARTIAL: Works without recurrent but not perfectly")
        print(f"   → May need tuning")
        return "partial"
    else:
        print(f"\n❌ FAILURE: e-prop fails even WITHOUT recurrent")
        print(f"   → Problem is in eligibility trace or task")
        print(f"   → Consider Norse diagnostic")
        return "fundamental_problem"
    
    print("=" * 70)

if __name__ == '__main__':
    result = no_recurrent_test()
    print(f"\nDiagnosis: {result}")