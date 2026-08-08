#!/usr/bin/env python
"""
1-Neuron Test v2 (FIXED)
=========================
W_in کوچک‌تر شروع می‌شود تا از ابتدا y=0 باشد.
سپس learning باید W_in را افزایش دهد تا y→1 برود.
"""

import numpy as np

def one_neuron_test_v2():
    """1-neuron test with proper initialization."""
    
    print("=" * 70)
    print("1-Neuron Test v2 (FIXED - Proper Initialization)")
    print("=" * 70)
    print("Network: 1 input → 1 hidden LIF → 1 output (linear)")
    print("Task: input fires at t=1, target=1.0 at t=2")
    print("Fix: W_in starts below threshold, learning must increase it")
    print("=" * 70)
    
    n_h = 1
    W_in  = np.array([[0.2]])    # ← شروع زیر threshold (0.3)
    W_out = np.array([[1.0]])    # fixed
    eta = 0.05                   # learning rate
    theta = 0.3
    
    print(f"\nInitial: W_in={W_in[0,0]:.3f}, W_out={W_out[0,0]:.3f}")
    print(f"eta={eta}, theta={theta}")
    print(f"Initial state: W_in < theta, so hidden should NOT fire")
    print()
    
    print(f"{'Trial':>6} | {'y':>8} | {'Loss':>8} | {'W_in':>8} | {'z':>4}")
    print("-" * 50)
    
    for trial in range(500):
        v, z, eps = 0.0, 0.0, 0.0
        
        # t=1: input spike
        v = v * 0.95 + W_in[0, 0] * 1.0
        z = float(v >= theta)
        
        # Surrogate derivative (قبل از reset)
        fp = 1.0 / (1 + 5 * abs(v - theta))**2
        
        # Reset
        if z:
            v -= theta
        
        # Eligibility trace
        eps = 0.95 * eps + fp * 1.0
        
        # t=2: output
        y = W_out[0, 0] * z
        error = y - 1.0  # target=1
        L = W_out[0, 0] * error
        dW = L * eps
        
        # Gradient descent: W_in -= eta * dW
        # چون target=1 و y=0، error=-1، L=-1، dW=-eps < 0
        # پس W_in -= eta * (-eps) = W_in += eta * eps  (increase!)
        W_in[0, 0] -= eta * dW
        
        if trial % 50 == 0 or trial < 5:
            print(f"{trial:>6} | {y:>8.3f} | {error**2:>8.4f} | "
                  f"{W_in[0,0]:>8.3f} | {z:>4.0f}")
    
    # Final result
    print()
    print("=" * 70)
    print("Result:")
    print("=" * 70)
    
    # Final forward pass
    v_final = W_in[0, 0] * 1.0
    z_final = float(v_final >= theta)
    y_final = W_out[0, 0] * z_final
    loss_final = (y_final - 1.0)**2
    
    print(f"Final W_in: {W_in[0,0]:.3f}")
    print(f"Final y: {y_final:.3f}")
    print(f"Final loss: {loss_final:.4f}")
    print(f"Final z: {z_final:.0f}")
    
    if y_final > 0.9:
        print(f"\n✅ SUCCESS: e-prop learned to make hidden fire!")
        print(f"   W_in increased from 0.200 to {W_in[0,0]:.3f}")
        print(f"   → Implementation is CORRECT at basic level")
        print(f"   → Problem is in XOR-specific complexity")
    elif W_in[0, 0] > 0.2:
        print(f"\n⚠️  PARTIAL: W_in increased but not enough")
        print(f"   W_in went from 0.200 to {W_in[0,0]:.3f}")
        print(f"   → Learning happening but slow")
    else:
        print(f"\n❌ FAILURE: W_in did not increase")
        print(f"   → Implementation broken")
        print(f"   → dW formula or sign error")
    
    print("=" * 70)

if __name__ == '__main__':
    one_neuron_test_v2()