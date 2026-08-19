#!/usr/bin/env python
"""
Quick Sign Test: آیا gradient direction اشتباه است؟
"""

import numpy as np

def sign_test():
    """Test: آیا sign invert کردن loss را کاهش می‌دهد؟"""
    
    print("=" * 70)
    print("Quick Sign Test: Gradient Direction")
    print("=" * 70)
    
    np.random.seed(42)
    
    # Small network
    n_in, n_h, n_out = 2, 10, 2
    dv = 0.05
    tau_e_decay = 1.0 - dv
    theta = 0.5
    eta = 0.01
    
    W_in  = np.random.randn(n_h,  n_in)  * 0.1
    W_rec = np.random.randn(n_h,  n_h)   * 0.1 / np.sqrt(n_h)
    W_out = np.random.randn(n_out, n_h)  * 0.1
    
    def surrogate(v, thr=0.5, beta=5.0):
        return 1.0 / (1.0 + beta * np.abs(v - thr))**2
    
    def softmax(x):
        e = np.exp(x - x.max())
        return e / e.sum()
    
    def run_trial(W_in, W_rec, W_out, bit_A, bit_B, sign=+1, T=12):
        """Run one trial with specified sign."""
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
            x = np.zeros(n_in)
            if t == T1: x[0] = bit_A
            if t == T2: x[1] = bit_B
            
            I = W_in @ x + W_rec @ z
            v = (1 - dv) * v + dv * (I / dv)
            
            z_new = (v >= theta).astype(float)
            v[z_new == 1] -= theta
            
            fp = surrogate(v + z_new * theta)
            
            eps_in  = tau_e_decay * eps_in  + fp[:, None] * x[None, :]
            eps_rec = tau_e_decay * eps_rec + fp[:, None] * z[None, :]
            
            z = z_new
            
            r = (1 - dv) * r + dv * (W_out @ z)
            
            if t == T_out:
                y = softmax(r)
                target = np.zeros(n_out)
                target[target_class] = 1.0
                error = y - target
                loss = -np.log(y[target_class] + 1e-8)
                pred = int(y.argmax())
                
                L = W_out.T @ error
                
                dW_in  += L[:, None] * eps_in
                dW_rec += L[:, None] * eps_rec
                dW_out += np.outer(error, z)
        
        return pred, loss, dW_in, dW_rec, dW_out
    
    # Test both signs
    bit_A, bit_B = 1.0, 0.0
    target = int(bit_A) ^ int(bit_B)
    
    print(f"\nTarget: {target} (bit_A={bit_A}, bit_B={bit_B})")
    
    for sign_name, sign in [("Current (+)", +1), ("Inverted (-)", -1)]:
        print(f"\n{'='*50}")
        print(f"Testing sign: {sign_name}")
        print(f"{'='*50}")
        
        # Reset weights
        np.random.seed(42)
        W_in  = np.random.randn(n_h,  n_in)  * 0.1
        W_rec = np.random.randn(n_h,  n_h)   * 0.1 / np.sqrt(n_h)
        W_out = np.random.randn(n_out, n_h)  * 0.1
        
        pred_before, loss_before, dW_in, dW_rec, dW_out = run_trial(
            W_in, W_rec, W_out, bit_A, bit_B, sign=sign
        )
        
        print(f"Before: pred={pred_before}, loss={loss_before:.4f}")
        print(f"  |dW_in| = {np.abs(dW_in).max():.6f}")
        print(f"  |dW_out| = {np.abs(dW_out).max():.6f}")
        
        # Apply gradient step with specified sign
        W_in  -= sign * eta * dW_in
        W_rec -= sign * eta * dW_rec
        W_out -= sign * eta * dW_out
        
        pred_after, loss_after, _, _, _ = run_trial(
            W_in, W_rec, W_out, bit_A, bit_B, sign=sign
        )
        
        print(f"After:  pred={pred_after}, loss={loss_after:.4f}")
        print(f"  Loss change: {loss_after - loss_before:+.6f}")
        
        if loss_after < loss_before:
            print(f"  ✅ Loss decreased")
        else:
            print(f"  ❌ Loss increased")
    
    print(f"\n{'='*70}")
    print("Conclusion:")
    print(f"{'='*70}")
    print("If 'Inverted (-)' decreases loss but 'Current (+)' increases:")
    print("  → Sign error in gradient")
    print("  → Use ΔW = -η × L × ε (not +η × L × ε)")

if __name__ == '__main__':
    sign_test()