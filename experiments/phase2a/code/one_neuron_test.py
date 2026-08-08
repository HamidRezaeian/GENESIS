#!/usr/bin/env python
"""
1-Neuron Test (from Opus)
==========================
ساده‌ترین e-prop ممکن:
- 1 input → 1 hidden LIF → 1 output (linear)
- Task: input fires at t=1, target=1.0 at t=2
- اگر این کار نکند: implementation در ابتدایی‌ترین سطح broken است
"""

import numpy as np

def one_neuron_test():
    """Simplest possible e-prop test."""
    
    print("=" * 70)
    print("1-Neuron Test (from Opus)")
    print("=" * 70)
    print("Network: 1 input → 1 hidden LIF → 1 output (linear)")
    print("Task: input fires at t=1, target=1.0 at t=2")
    print("Goal: W_in should increase until hidden fires and y→1")
    print("=" * 70)
    
    n_h = 1
    W_in  = np.array([[0.5]])
    W_out = np.array([[1.0]])   # fixed — فقط W_in را train کنید
    eta = 0.1
    theta = 0.3
    
    print(f"\nInitial: W_in={W_in[0,0]:.3f}, W_out={W_out[0,0]:.3f}")
    print(f"eta={eta}, theta={theta}")
    print()
    
    print(f"{'Trial':>6} | {'y':>8} | {'Loss':>8} | {'W_in':>8} | {'z':>4}")
    print("-" * 50)
    
    for trial in range(200):
        v, z, eps = 0.0, 0.0, 0.0
        
        # t=1: input spike
        v = v * 0.95 + W_in[0, 0] * 1.0  # W_in × input=1
        z = float(v >= theta)
        if z:
            v -= theta
        
        # Surrogate derivative
        fp = 1.0 / (1 + 5 * abs(v))**2
        
        # Eligibility trace (pre=1)
        eps = 0.95 * eps + fp * 1.0
        
        # t=2: output
        y = W_out[0, 0] * z
        error = y - 1.0  # target=1
        L = W_out[0, 0] * error
        dW = L * eps
        
        # Gradient descent
        W_in[0, 0] -= eta * dW
        
        if trial % 50 == 0:
            print(f"{trial:>6} | {y:>8.3f} | {error**2:>8.4f} | "
                  f"{W_in[0,0]:>8.3f} | {z:>4.0f}")
    
    # Final result
    print()
    print("=" * 70)
    print("Result:")
    print("=" * 70)
    
    final_y = W_out[0, 0] * float(W_in[0, 0] >= theta)
    final_loss = (final_y - 1.0)**2
    
    print(f"Final W_in: {W_in[0,0]:.3f}")
    print(f"Final y: {final_y:.3f}")
    print(f"Final loss: {final_loss:.4f}")
    
    if final_y > 0.9:
        print(f"\n✅ SUCCESS: 1-neuron e-prop works!")
        print(f"   W_in increased until hidden fires")
        print(f"   → Implementation is correct at basic level")
        print(f"   → Problem is in XOR-specific complexity")
    elif W_in[0, 0] > 0.5:
        print(f"\n⚠️  PARTIAL: W_in increased but not enough")
        print(f"   → Learning is happening but slow")
        print(f"   → May need more trials or higher eta")
    else:
        print(f"\n❌ FAILURE: W_in did not increase")
        print(f"   → Implementation broken at basic level")
        print(f"   → Problem in dW formula: L × eps or sign")
        print(f"   → Need to debug eligibility trace or gradient")
    
    print("=" * 70)

if __name__ == '__main__':
    one_neuron_test()