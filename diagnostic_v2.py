#!/usr/bin/env python
"""
Diagnostic v2: بررسی دقیق weight changes
"""

import numpy as np

def test_weight_changes():
    """Test: آیا weights واقعاً تغییر می‌کنند؟"""
    
    print("=" * 70)
    print("Diagnostic v2: Weight Change Verification")
    print("=" * 70)
    
    # Small network برای debugging
    n_in, n_hid, n_out = 5, 10, 2
    eta = 0.1  # large learning rate
    tau_e = 10
    vth = 0.5
    
    # Initialize
    rng = np.random.RandomState(42)
    w_in_hid = rng.randn(n_hid, n_in) * 2.0
    w_hid_out = rng.randn(n_out, n_hid) * 2.0
    
    # Eligibility
    e_in_hid = np.zeros((n_hid, n_in))
    e_hid_out = np.zeros((n_out, n_hid))
    
    # Track weight changes
    initial_w1 = w_in_hid.copy()
    initial_w2 = w_hid_out.copy()
    
    print(f"\nInitial weights:")
    print(f"  w_in_hid magnitude: {np.abs(w_in_hid).mean():.4f}")
    print(f"  w_hid_out magnitude: {np.abs(w_hid_out).mean():.4f}")
    
    # Simple sequence
    sequence = [0, 1, 0, 1, 0, 1, 0, 1]
    
    v_hid = np.zeros(n_hid)
    v_out = np.zeros(n_out)
    
    for t in range(len(sequence) - 1):
        input_bit = sequence[t]
        target_bit = sequence[t+1]
        
        # Encode input
        x = np.zeros(n_in)
        if input_bit == 0:
            x[:3] = 1.0
        else:
            x[3:] = 1.0
        
        # Forward
        u_hid = w_in_hid @ x
        v_hid = v_hid * 0.7 + u_hid
        s_hid = (v_hid >= vth).astype(float)
        v_hid[s_hid > 0] = 0.0
        
        u_out = w_hid_out @ s_hid
        v_out = v_out * 0.7 + u_out
        s_out = (v_out >= vth).astype(float)
        v_out[s_out > 0] = 0.0
        
        # Eligibility
        e_in_hid = e_in_hid * np.exp(-1/tau_e) + np.outer(s_hid, x)
        e_hid_out = e_hid_out * np.exp(-1/tau_e) + np.outer(s_out, s_hid)
        
        # Prediction
        pred = int(s_out[1] > s_out[0])
        is_correct = (pred == target_bit)
        
        # Learning (on errors)
        if not is_correct:
            M = 1.0
            dw1 = eta * M * e_in_hid
            dw2 = eta * M * e_hid_out
            
            print(f"\nt={t}: input={input_bit}, target={target_bit}, pred={pred} ❌")
            print(f"  s_hid={s_hid.sum():.0f} spikes, s_out={s_out}")
            print(f"  e_in_hid magnitude: {np.abs(e_in_hid).mean():.4f}")
            print(f"  e_hid_out magnitude: {np.abs(e_hid_out).mean():.4f}")
            print(f"  dw1 magnitude: {np.abs(dw1).mean():.4f}")
            print(f"  dw2 magnitude: {np.abs(dw2).mean():.4f}")
            
            w_in_hid += dw1
            w_hid_out += dw2
    
    # Final check
    print(f"\n{'='*70}")
    print(f"Weight change analysis:")
    print(f"{'='*70}")
    
    delta_w1 = w_in_hid - initial_w1
    delta_w2 = w_hid_out - initial_w2
    
    print(f"  w_in_hid changed by: {np.abs(delta_w1).mean():.6f} (mean)")
    print(f"  w_hid_out changed by: {np.abs(delta_w2).mean():.6f} (mean)")
    print(f"  w_in_hid max change: {np.abs(delta_w1).max():.6f}")
    print(f"  w_hid_out max change: {np.abs(delta_w2).max():.6f}")
    
    if np.abs(delta_w1).max() > 1e-6:
        print(f"\n✅ Weights DO change")
    else:
        print(f"\n❌ Weights DO NOT change (updates are zero)")
    
    # Check final weights
    print(f"\nFinal weights:")
    print(f"  w_in_hid magnitude: {np.abs(w_in_hid).mean():.4f}")
    print(f"  w_hid_out magnitude: {np.abs(w_hid_out).mean():.4f}")
    print(f"{'='*70}")

if __name__ == '__main__':
    test_weight_changes()