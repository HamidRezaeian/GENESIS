#!/usr/bin/env python
"""
Minimal Test Case from Opus: Credit Assignment Verification
============================================================
این test بررسی می‌کند که آیا L_j × ε_ij در جهت درست کار می‌کند.
"""

import numpy as np

def minimal_credit_test():
    """Minimal test: 1 input → 1 hidden (LIF) → 1 output (linear)."""
    
    print("=" * 70)
    print("Minimal Credit Assignment Test (from Opus)")
    print("=" * 70)
    
    np.random.seed(42)
    
    # Network parameters
    W_in  = np.array([[15.0]])   # input → hidden (large enough to spike)
    W_out = np.array([[1.0]])    # hidden → output (fixed)
    
    tau_m = 20.0   # membrane time constant
    tau_e = 20.0   # eligibility trace time constant
    eta   = 0.001
    theta = 0.6    # spike threshold
    beta  = 10.0   # surrogate parameter
    
    print(f"\nNetwork: 1 input → 1 hidden (LIF) → 1 output (linear)")
    print(f"W_in = {W_in[0,0]}, W_out = {W_out[0,0]}")
    print(f"tau_m = {tau_m}, tau_e = {tau_e}, eta = {eta}")
    print(f"theta = {theta}, beta = {beta}")
    
    # Step 1: input spike at t=0
    z_in = np.array([1.0])
    print(f"\nStep 1: Input spike z_in = {z_in[0]}")
    
    # Step 2: hidden membrane update
    v = 0.0 + (1/tau_m) * (W_in[0,0] * z_in[0])
    print(f"\nStep 2: Hidden membrane potential")
    print(f"  v = {v:.4f} (threshold = {theta})")
    
    z_hidden = 1.0 if v > theta else 0.0
    v_after_spike = v - theta if z_hidden else v
    
    print(f"  z_hidden = {z_hidden}")
    print(f"  v_after_spike = {v_after_spike:.4f}")
    
    # Step 3: eligibility trace with CORRECT surrogate
    # f'(v) = 1 / (1 + beta * |v - theta|)^2
    f_prime = 1.0 / (1.0 + beta * abs(v_after_spike - theta))**2
    
    # Wait, v_after_spike = v - theta, so v_after_spike - theta = v - 2*theta
    # Let me use v (before reset) for surrogate
    f_prime_correct = 1.0 / (1.0 + beta * abs(v - theta))**2
    
    print(f"\nStep 3: Surrogate derivative")
    print(f"  Using v_after_spike: f_prime = {f_prime:.4f}")
    print(f"  Using v (pre-reset): f_prime = {f_prime_correct:.4f}")
    print(f"  Expected: 0.1-0.3 (not 0.97!)")
    
    epsilon = f_prime_correct * z_in[0]
    print(f"\n  epsilon = f_prime * z_in = {epsilon:.4f}")
    
    # Step 4: output and error
    y_out = W_out[0,0] * z_hidden
    target = 0.0  # we want output OFF
    error = y_out - target
    
    print(f"\nStep 4: Output and error")
    print(f"  y_out = {y_out:.4f}, target = {target}")
    print(f"  error = y_out - target = {error:.4f}")
    
    # Step 5: learning signal for hidden
    # L_hidden = W_out^T @ error
    L_hidden = W_out[0,0] * error
    
    print(f"\nStep 5: Learning signal")
    print(f"  L_hidden = W_out * error = {L_hidden:.4f}")
    
    # Step 6: weight update
    # ΔW = -η × L × ε (negative because we want to decrease output)
    delta_W = -eta * L_hidden * epsilon
    
    print(f"\nStep 6: Weight update")
    print(f"  ΔW_in = -η × L × ε = {delta_W:.6f}")
    
    # Verification
    print(f"\n{'='*70}")
    print("Verification:")
    print(f"{'='*70}")
    
    if delta_W < 0:
        print(f"  ✅ ΔW_in < 0: W_in should DECREASE")
        print(f"     → Hidden will fire LESS → Output will be OFF")
        print(f"     → Credit assignment direction is CORRECT")
    else:
        print(f"  ❌ ΔW_in > 0: W_in would INCREASE")
        print(f"     → Hidden would fire MORE → Output would be ON")
        print(f"     → BUG: gradient direction is WRONG")
    
    if f_prime_correct < 0.5:
        print(f"  ✅ f_prime = {f_prime_correct:.4f} < 0.5: Surrogate is reasonable")
    else:
        print(f"  ⚠️  f_prime = {f_prime_correct:.4f} >= 0.5: Neuron saturated")
    
    print(f"\n{'='*70}")
    print("Key Insight from Opus:")
    print(f"{'='*70}")
    print(f"  In e-prop, credit assignment from output to hidden is:")
    print(f"    L_j(t) = W_out^T @ error(t)")
    print(f"  NOT by propagating eligibility traces backward.")
    print(f"  Eligibility traces live in the FORWARD direction only.")
    print(f"{'='*70}")

if __name__ == '__main__':
    minimal_credit_test()