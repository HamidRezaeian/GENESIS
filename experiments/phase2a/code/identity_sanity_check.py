#!/usr/bin/env python
"""
Identity Mapping Sanity Check from Opus (FIXED)
================================================
Fix: broadcasting error در dW_out
"""

import numpy as np

def identity_sanity_check():
    """Simple identity mapping test."""
    
    print("=" * 70)
    print("Identity Mapping Sanity Check (from Opus, FIXED)")
    print("=" * 70)
    
    np.random.seed(0)
    
    # Network: 2 input → 5 hidden → 2 output
    n_in, n_h, n_out = 2, 5, 2
    dv = 0.05
    theta = 0.5
    eta = 0.05
    
    W_in  = np.random.randn(n_h, n_in)  * 0.3
    W_out = np.random.randn(n_out, n_h) * 0.3
    
    def surrogate(v, thr=0.5, beta=5.0):
        return 1.0 / (1.0 + beta * np.abs(v - thr))**2
    
    def softmax(x):
        e = np.exp(x - x.max())
        return e / e.sum()
    
    def run_identity_trial(W_in, W_out, input_class):
        T = 5
        v = np.zeros(n_h)
        r = np.zeros(n_out)
        eps_in = np.zeros_like(W_in)
        
        x_input = np.zeros(n_in)
        x_input[input_class] = 1.0
        
        dW_in = np.zeros_like(W_in)
        dW_out = np.zeros_like(W_out)
        loss = None
        
        for t in range(T):
            x = x_input if t == 1 else np.zeros(n_in)
            I = W_in @ x
            v = (1 - dv) * v + dv * (I / dv)
            z = (v >= theta).astype(float)
            fp = surrogate(v + z * theta)
            v[z == 1] -= theta
            
            eps_in = (1 - dv) * eps_in + fp[:, None] * x[None, :]
            r = (1 - dv) * r + dv * (W_out @ z)
            
            if t == 3:   # output time
                y = softmax(r)
                target = np.zeros(n_out)
                target[input_class] = 1.0
                error = y - target
                loss = -np.log(y[input_class] + 1e-9)
                L = W_out.T @ error
                dW_in  += L[:, None] * eps_in
                # ← FIXED: use np.outer(error, z) instead of error[:, None] * r[None, :]
                dW_out += np.outer(error, z)  # error: (n_out,), z: (n_h,) → (n_out, n_h)
        
        return y.argmax(), loss, dW_in, dW_out
    
    # Training
    print(f"\nTraining identity mapping:")
    print(f"{'Epoch':>6} | {'Loss':>8} | {'Acc':>6}")
    print("-" * 30)
    
    losses, accs = [], []
    for epoch in range(50):
        epoch_loss, correct = 0, 0
        for cls in [0, 0, 1, 1, 0, 1]:   # 6 samples
            pred, loss, dW_in, dW_out = run_identity_trial(W_in, W_out, cls)
            W_in  -= eta * dW_in
            W_out -= eta * dW_out
            epoch_loss += loss
            correct += int(pred == cls)
        avg_loss = epoch_loss / 6
        acc = correct / 6
        losses.append(avg_loss)
        accs.append(acc)
        if epoch % 10 == 0:
            print(f"{epoch:>6} | {avg_loss:>8.4f} | {acc:>6.2%}")
    
    # Final result
    print(f"\n{'='*70}")
    print("Result:")
    print(f"{'='*70}")
    
    final_acc = accs[-1]
    final_loss = losses[-1]
    
    print(f"Final loss: {final_loss:.4f}")
    print(f"Final accuracy: {final_acc:.2%}")
    
    if final_acc > 0.8:
        print(f"\n✅ Identity mapping LEARNED!")
        print(f"   → e-prop implementation is CORRECT")
        print(f"   → Problem is in XOR task complexity or eta")
        print(f"   → Next: increase eta or use Adam for XOR")
    elif final_acc > 0.5:
        print(f"\n⚠️  Weak learning — eta or epochs may be insufficient")
        print(f"   → Double eta and try again")
    else:
        print(f"\n❌ Identity mapping NOT learned — implementation broken")
        print(f"   → Problem in eligibility trace or W_out update")
    
    print(f"{'='*70}")

if __name__ == '__main__':
    identity_sanity_check()