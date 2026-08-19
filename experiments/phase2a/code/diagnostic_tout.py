#!/usr/bin/env python
"""
Diagnostic: بررسی دقیق وضعیت در زمان T_out
"""

import numpy as np

def diagnostic_tout():
    """بررسی کنیم چرا z در زمان T_out صفر است."""
    
    print("=" * 70)
    print("Diagnostic: Status at T_out")
    print("=" * 70)
    
    np.random.seed(42)
    
    # Setup
    n_in, n_h, n_out = 2, 10, 2
    dv = 0.05
    theta = 0.5
    
    W_in  = np.random.randn(n_h,  n_in)  * 0.1
    W_rec = np.random.randn(n_h,  n_h)   * 0.1 / np.sqrt(n_h)
    W_out = np.random.randn(n_out, n_h)  * 0.1
    
    bit_A, bit_B = 1.0, 0.0
    T1, T2, T_out = 3, 6, 9
    
    v = np.zeros(n_h)
    z = np.zeros(n_h)
    r = np.zeros(n_out)
    
    print(f"\nTracking network state:")
    print(f"{'t':<3} {'Input':<10} {'z sum':<10} {'v mean':<10} {'r':<20}")
    print("-" * 60)
    
    for t in range(12):
        # Input
        x = np.zeros(n_in)
        if t == T1: x[0] = bit_A
        if t == T2: x[1] = bit_B
        
        # Forward
        I = W_in @ x + W_rec @ z
        v = (1 - dv) * v + dv * (I / dv)
        
        z_new = (v >= theta).astype(float)
        v[z_new == 1] -= theta
        z = z_new
        
        r = (1 - dv) * r + dv * (W_out @ z)
        
        print(f"{t:<3} {str(x):<10} {z.sum():<10.3f} {v.mean():<10.3f} {r}")
    
    print(f"\n{'='*70}")
    print(f"Analysis:")
    print(f"{'='*70}")
    
    print(f"\nAt T_out={T_out}:")
    print(f"  z sum = {z.sum():.3f}")
    print(f"  v mean = {v.mean():.3f}")
    print(f"  r = {r}")
    
    if z.sum() == 0:
        print(f"\n  ❌ z = 0 at T_out!")
        print(f"     → dW_out = outer(error, z) = 0")
        print(f"     → No gradient for output layer")
        
        print(f"\n  Root cause:")
        print(f"     Hidden neurons do not spike at exactly t={T_out}")
        print(f"     Need to use READOUT WINDOW (average over several ticks)")
    else:
        print(f"\n  ✅ z non-zero at T_out")
        print(f"     → Problem elsewhere")

if __name__ == '__main__':
    diagnostic_tout()