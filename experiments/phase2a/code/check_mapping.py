#!/usr/bin/env python
"""
Diagnostic: آیا prediction logic درست است؟
"""

import numpy as np

def check_mapping():
    """بررسی کنیم آیا mapping بین target و prediction درست است."""
    
    print("=" * 70)
    print("Mapping Diagnostic: Target vs Prediction")
    print("=" * 70)
    
    # Setup
    n_ticks = 1000
    T1, T2 = 3, 6
    pulse_prob = 0.3
    
    rng = np.random.RandomState(42)
    input_pulses = (rng.rand(n_ticks) < pulse_prob).astype(int)
    
    # Target: XOR
    target = np.zeros(n_ticks, dtype=int)
    for t in range(max(T1, T2), n_ticks):
        target[t] = input_pulses[t - T1] ^ input_pulses[t - T2]
    
    # Check target distribution
    targets_after = target[max(T1, T2):]
    print(f"\nTarget distribution:")
    print(f"  P(target=0): {np.mean(targets_after == 0):.3f}")
    print(f"  P(target=1): {np.mean(targets_after == 1):.3f}")
    
    # If we always predict 0
    acc_predict_0 = np.mean(targets_after == 0)
    print(f"\nBaseline accuracies:")
    print(f"  Always predict 0: {acc_predict_0:.3f}")
    print(f"  Always predict 1: {1 - acc_predict_0:.3f}")
    
    # Check if target has structure
    print(f"\nTarget autocorrelation:")
    for lag in [1, 2, 3, 5]:
        if len(targets_after) > lag:
            autocorr = np.corrcoef(targets_after[:-lag], targets_after[lag:])[0, 1]
            print(f"  lag={lag}: {autocorr:.4f}")
    
    # Check XOR pattern
    print(f"\nXOR pattern analysis:")
    print(f"  input[t-3]=0, input[t-6]=0 → target=0")
    print(f"  input[t-3]=0, input[t-6]=1 → target=1")
    print(f"  input[t-3]=1, input[t-6]=0 → target=1")
    print(f"  input[t-3]=1, input[t-6]=1 → target=0")
    
    # Count each case
    counts = {(0,0): 0, (0,1): 0, (1,0): 0, (1,1): 0}
    for t in range(max(T1, T2), n_ticks):
        key = (input_pulses[t-T1], input_pulses[t-T2])
        counts[key] += 1
    
    print(f"\nCase counts:")
    for key, count in counts.items():
        expected_xor = key[0] ^ key[1]
        print(f"  {key} → XOR={expected_xor}, count={count}")
    
    print("\n" + "=" * 70)
    print("Conclusion:")
    print("-" * 50)
    
    if acc_predict_0 > 0.6:
        print(f"  ⚠️  Target is IMBALANCED (P(0)={acc_predict_0:.2f})")
        print(f"     → A model that always predicts 0 gets {acc_predict_0:.2f}")
        print(f"     → Need balanced accuracy metric")
    else:
        print(f"  ✅ Target is roughly balanced")
    
    if abs(np.corrcoef(targets_after[:-1], targets_after[1:])[0, 1]) < 0.05:
        print(f"  ⚠️  Target has NO autocorrelation (hard to predict)")
    else:
        print(f"  ✅ Target has some structure")
    
    print("=" * 70)

if __name__ == '__main__':
    check_mapping()