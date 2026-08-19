#!/usr/bin/env python
"""
Diagnostic v3: بررسی output voltage و prediction
"""

import numpy as np

def test_output_separation():
    """Test: آیا output voltage ها برای دو کلاس متفاوت هستند؟"""
    
    print("=" * 70)
    print("Diagnostic v3: Output Voltage Separation")
    print("=" * 70)
    
    # Small network
    n_in, n_hid, n_out = 10, 20, 2
    vth = 0.5
    dv = 0.3
    du = 0.3
    
    # Initialize
    rng = np.random.RandomState(42)
    w_in_hid = rng.randn(n_hid, n_in) * 2.0
    w_hid_out = rng.randn(n_out, n_hid) * 2.0
    
    v_hid = np.zeros(n_hid)
    v_out = np.zeros(n_out)
    
    # Test with both input classes
    print("\nTesting input=0:")
    x0 = np.zeros(n_in)
    x0[:5] = 1.0  # 5 spikes for bit=0
    
    u_hid0 = w_in_hid @ x0
    v_hid0 = v_hid * (1-dv) + u_hid0
    s_hid0 = (v_hid0 >= vth).astype(float)
    
    u_out0 = w_hid_out @ s_hid0
    v_out0 = v_out * (1-dv) + u_out0
    
    print(f"  Hidden spikes: {s_hid0.sum():.0f}")
    print(f"  Output voltage: {v_out0}")
    print(f"  Prediction: {int(v_out0[1] > v_out0[0])}")
    
    print("\nTesting input=1:")
    x1 = np.zeros(n_in)
    x1[5:] = 1.0  # 5 spikes for bit=1
    
    u_hid1 = w_in_hid @ x1
    v_hid1 = v_hid * (1-dv) + u_hid1
    s_hid1 = (v_hid1 >= vth).astype(float)
    
    u_out1 = w_hid_out @ s_hid1
    v_out1 = v_out * (1-dv) + u_out1
    
    print(f"  Hidden spikes: {s_hid1.sum():.0f}")
    print(f"  Output voltage: {v_out1}")
    print(f"  Prediction: {int(v_out1[1] > v_out1[0])}")
    
    # Check separation
    print(f"\n{'='*70}")
    print("Separation analysis:")
    print(f"{'='*70}")
    
    diff0 = v_out0[1] - v_out0[0]
    diff1 = v_out1[1] - v_out1[0]
    
    print(f"  input=0: v_out[1] - v_out[0] = {diff0:.4f}")
    print(f"  input=1: v_out[1] - v_out[0] = {diff1:.4f}")
    
    if diff0 < 0 and diff1 > 0:
        print(f"\n✅ Output voltages ARE separated (learnable)")
    elif diff0 > 0 and diff1 < 0:
        print(f"\n✅ Output voltages ARE separated (inverted, learnable)")
    else:
        print(f"\n❌ Output voltages NOT separated (problem!)")
        print(f"   → Network cannot distinguish classes")
    
    # Check if prediction matches input
    pred0 = int(v_out0[1] > v_out0[0])
    pred1 = int(v_out1[1] > v_out1[0])
    
    print(f"\nPrediction check:")
    print(f"  input=0 → pred={pred0} (should be 0)")
    print(f"  input=1 → pred={pred1} (should be 1)")
    
    if pred0 == 0 and pred1 == 1:
        print(f"  ✅ Predictions correct")
    else:
        print(f"  ⚠️  Predictions may be inverted or random")
    
    print("=" * 70)

if __name__ == '__main__':
    test_output_separation()