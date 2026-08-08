#!/usr/bin/env python
"""
Diagnostic: بررسی دقیق چرا learning اتفاق نمی‌افتد
"""

import numpy as np

# Minimal test: 1 input -> 2 output neurons
def test_simple_case():
    """Test: 1 input bit -> 2 output neurons (one for each class)."""
    
    print("=" * 70)
    print("Diagnostic: Simple 1-bit classification")
    print("=" * 70)
    
    # Configuration
    n_input = 2  # [bit=0, bit=1]
    n_hidden = 5  # small for debugging
    n_output = 2  # [class=0, class=1]
    eta = 0.1  # large learning rate
    tau_e = 10
    vth = 5  # low threshold for more spikes
    
    # Task: input bit -> output class (identity mapping)
    sequence = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    
    # Initialize
    rng = np.random.RandomState(42)
    
    # Network
    v_hidden = np.zeros(n_hidden)
    v_out = np.zeros(n_output)
    
    # Weights
    w_in_hid = rng.randn(n_hidden, n_input) * 0.5
    w_hid_out = rng.randn(n_output, n_hidden) * 0.5
    
    # Eligibility
    e_in_hid = np.zeros((n_hidden, n_input))
    e_hid_out = np.zeros((n_output, n_hidden))
    
    print(f"\nInitial weights:")
    print(f"w_in_hid:\n{w_in_hid}")
    print(f"w_hid_out:\n{w_hid_out}")
    
    correct = 0
    total = 0
    
    for t in range(len(sequence) - 1):
        input_bit = sequence[t]
        target_bit = sequence[t+1]
        
        # Encode input
        x = np.array([1-input_bit, input_bit], dtype=float)
        
        # Forward: input -> hidden
        u_hidden = w_in_hid @ x
        v_hidden = v_hidden * 0.7 + u_hidden  # decay
        s_hidden = (v_hidden >= vth).astype(float)
        v_hidden[s_hidden > 0] = 0  # reset
        
        # Forward: hidden -> output
        u_out = w_hid_out @ s_hidden
        v_out = v_out * 0.7 + u_out
        s_out = (v_out >= vth).astype(float)
        v_out[s_out > 0] = 0
        
        # Prediction
        pred = int(s_out[1] > s_out[0])  # more spikes in neuron 1 = predict 1
        is_correct = (pred == target_bit)
        if is_correct:
            correct += 1
        total += 1
        
        # Eligibility traces
        e_in_hid = e_in_hid * np.exp(-1/tau_e) + np.outer(s_hidden, x)
        e_hid_out = e_hid_out * np.exp(-1/tau_e) + np.outer(s_out, s_hidden)
        
        # Learning (only from errors)
        if not is_correct:
            M = 1.0  # neuromodulator
            dw_in_hid = eta * M * e_in_hid
            dw_hid_out = eta * M * e_hid_out
            
            w_in_hid += dw_in_hid
            w_hid_out += dw_hid_out
            
            print(f"\nt={t}: input={input_bit}, target={target_bit}, pred={pred} ❌")
            print(f"  s_hidden={s_hidden}, s_out={s_out}")
            print(f"  dw_in_hid magnitude: {np.abs(dw_in_hid).sum():.4f}")
            print(f"  dw_hid_out magnitude: {np.abs(dw_hid_out).sum():.4f}")
        else:
            print(f"\nt={t}: input={input_bit}, target={target_bit}, pred={pred} ✓")
            print(f"  s_hidden={s_hidden}, s_out={s_out}")
    
    accuracy = correct / total
    print(f"\n{'='*70}")
    print(f"Final accuracy: {accuracy:.3f} ({correct}/{total})")
    print(f"\nFinal weights:")
    print(f"w_in_hid:\n{w_in_hid}")
    print(f"w_hid_out:\n{w_hid_out}")
    
    if accuracy > 0.7:
        print(f"\n✅ Learning WORKS in simple case!")
    else:
        print(f"\n❌ Learning BROKEN even in simple case")
        print(f"   → Problem is in core e-prop logic")
    
    print("=" * 70)

if __name__ == '__main__':
    test_simple_case()