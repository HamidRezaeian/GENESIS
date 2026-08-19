#!/usr/bin/env python
"""
Sanity Check from Opus: Single-Sample Improvement Verification (FIXED)
=======================================================================
Fix: broadcasting error در dW_out
"""

import numpy as np

def sanity_check():
    """Single-sample gradient descent verification."""
    
    print("=" * 70)
    print("Sanity Check from Opus: Single-Sample Improvement (FIXED)")
    print("=" * 70)
    
    np.random.seed(42)
    
    # Small network for debug
    n_in, n_h, n_out = 2, 10, 2
    dv = 0.05
    tau_e_decay = 1.0 - dv
    theta = 0.5
    eta = 0.01  # Bellec 2020 range
    
    # Weight init
    W_in  = np.random.randn(n_h,  n_in)  * 0.1
    W_rec = np.random.randn(n_h,  n_h)   * 0.1 / np.sqrt(n_h)
    W_out = np.random.randn(n_out, n_h)  * 0.1
    
    def surrogate(v, thr=0.5, beta=5.0):
        return 1.0 / (1.0 + beta * np.abs(v - thr))**2
    
    def softmax(x):
        e = np.exp(x - x.max())
        return e / e.sum()
    
    def run_trial(W_in, W_rec, W_out, bit_A, bit_B, T=12):
        """Run one trial and return gradients."""
        target_class = int(bit_A) ^ int(bit_B)
        T1, T2, T_out = 3, 6, 9
        
        v = np.zeros(n_h)
        z = np.zeros(n_h)
        r = np.zeros(n_out)
        eps_in  = np.zeros_like(W_in)
        eps_rec = np.zeros_like(W_rec)
        
        dW_in  = np.zeros_like(W_in)
        dW_rec = np.zeros_like(W_rec)
        dW_out = np.zeros_like(W_out)
        
        loss = 0.0
        pred = -1
        
        for t in range(T):
            # Input
            x = np.zeros(n_in)
            if t == T1: x[0] = bit_A
            if t == T2: x[1] = bit_B
            
            # Forward
            I = W_in @ x + W_rec @ z
            v = (1 - dv) * v + dv * (I / dv)
            
            z_new = (v >= theta).astype(float)
            v[z_new == 1] -= theta
            
            fp = surrogate(v + z_new * theta)
            
            # Eligibility trace update
            eps_in  = tau_e_decay * eps_in  + fp[:, None] * x[None, :]
            eps_rec = tau_e_decay * eps_rec + fp[:, None] * z[None, :]
            
            z = z_new
            
            # Output leaky integrator
            r = (1 - dv) * r + dv * (W_out @ z)
            
            # Error ONLY at T_out (mask!)
            if t == T_out:
                y = softmax(r)
                target = np.zeros(n_out)
                target[target_class] = 1.0
                error = y - target
                loss = -np.log(y[target_class] + 1e-8)
                pred = int(y.argmax())
                
                # Learning signal
                L = W_out.T @ error
                
                # Weight updates
                dW_in  += L[:, None] * eps_in
                dW_rec += L[:, None] * eps_rec
                # ← FIXED: use np.outer for correct broadcasting
                dW_out += np.outer(error, z)  # error: (n_out,), z: (n_h,) → (n_out, n_h)
        
        return pred, loss, dW_in, dW_rec, dW_out
    
    # Run sanity check
    bit_A, bit_B = 1.0, 0.0
    target = int(bit_A) ^ int(bit_B)
    
    pred_before, loss_before, dW_in, dW_rec, dW_out = run_trial(
        W_in, W_rec, W_out, bit_A, bit_B
    )
    
    print(f"\nBefore gradient step:")
    print(f"  pred={pred_before}, loss={loss_before:.4f}, target={target}")
    print(f"  |dW_in|  = {np.abs(dW_in).max():.6f}")
    print(f"  |dW_rec| = {np.abs(dW_rec).max():.6f}")
    print(f"  |dW_out| = {np.abs(dW_out).max():.6f}")
    
    # Apply gradient step
    W_in  -= eta * dW_in
    W_rec -= eta * dW_rec
    W_out -= eta * dW_out
    
    pred_after, loss_after, _, _, _ = run_trial(
        W_in, W_rec, W_out, bit_A, bit_B
    )
    
    print(f"\nAfter gradient step:")
    print(f"  pred={pred_after}, loss={loss_after:.4f}")
    print(f"  Loss change = {loss_after - loss_before:+.6f}")
    
    # Verification
    print(f"\n{'='*70}")
    print("Verification:")
    print(f"{'='*70}")
    
    if loss_after < loss_before:
        print(f"  ✅ Loss decreased: {loss_before:.4f} → {loss_after:.4f}")
        print(f"     → Credit assignment direction is CORRECT")
        print(f"     → Gradient descent is working")
    elif loss_after > loss_before:
        print(f"  ❌ Loss increased: {loss_before:.4f} → {loss_after:.4f}")
        print(f"     → Gradient direction is WRONG")
        print(f"     → Need to invert sign")
    else:
        print(f"  ⚠️  Loss unchanged: {loss_before:.4f}")
        print(f"     → dW is zero or too small")
    
    # Check gradient magnitudes
    print(f"\nGradient magnitudes:")
    if np.abs(dW_in).max() > 1e-6:
        print(f"  ✅ dW_in non-zero: {np.abs(dW_in).max():.6f}")
    else:
        print(f"  ❌ dW_in ≈ 0: eligibility trace broken")
    
    if np.abs(dW_out).max() > 1e-6:
        print(f"  ✅ dW_out non-zero: {np.abs(dW_out).max():.6f}")
    else:
        print(f"  ❌ dW_out ≈ 0: r_out or error broken")
    
    print(f"{'='*70}")

if __name__ == '__main__':
    sanity_check()