#!/usr/bin/env python
"""
Task Validity Check (from Opus)
================================
آیا task واقعاً temporal است؟

اگر logistic regression با single-timestep input > 60% بگیرد:
  → Task temporal نیست
  → XOR به حافظه نیاز ندارد
  → e-prop wrong tool است
  → همه 20 iteration اشتباه بوده

اگر logistic regression با single-timestep input ≈ 50% بگیرد:
  → Task temporal است
  → XOR نیاز به حافظه دارد
  → e-prop appropriate است
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score

def task_validity_check():
    """Test if task is truly temporal."""
    
    print("=" * 70)
    print("Task Validity Check (from Opus)")
    print("=" * 70)
    
    # Task parameters
    n_ticks = 2000
    T1, T2 = 3, 6
    pulse_prob = 0.3
    
    # Generate data
    rng = np.random.RandomState(42)
    input_pulses = (rng.rand(n_ticks) < pulse_prob).astype(int)
    
    # Target: XOR
    target = np.zeros(n_ticks, dtype=int)
    for t in range(max(T1, T2), n_ticks):
        target[t] = input_pulses[t - T1] ^ input_pulses[t - T2]
    
    print(f"\nTask: output[t] = input[t-{T1}] XOR input[t-{T2}]")
    print(f"Samples: {n_ticks - max(T1, T2)}")
    print(f"Target distribution: P(0)={np.mean(target[max(T1,T2):]==0):.3f}")
    
    # ========================================================================
    # Test 1: Logistic Regression with ROLLING HISTORY (قبلی)
    # ========================================================================
    print(f"\n{'='*70}")
    print("Test 1: Logistic Regression with Rolling History (Previous)")
    print(f"{'='*70}")
    
    start_tick = max(T1, T2)
    n_features_history = T2 + 1  # 7 features: input[t], ..., input[t-6]
    
    X_history = np.zeros((n_ticks - start_tick, n_features_history))
    y_history = np.zeros(n_ticks - start_tick, dtype=int)
    
    for i, t in enumerate(range(start_tick, n_ticks)):
        for k in range(n_features_history):
            X_history[i, k] = input_pulses[t - k] if t - k >= 0 else 0
        y_history[i] = target[t]
    
    # Train/test split
    split = int(len(X_history) * 0.8)
    X_train_h, X_test_h = X_history[:split], X_history[split:]
    y_train_h, y_test_h = y_history[:split], y_history[split:]
    
    clf_history = LogisticRegression(random_state=42, max_iter=1000)
    clf_history.fit(X_train_h, y_train_h)
    
    y_pred_h = clf_history.predict(X_test_h)
    acc_history = balanced_accuracy_score(y_test_h, y_pred_h)
    
    print(f"Features: input[t], input[t-1], ..., input[t-{T2}]")
    print(f"Test balanced accuracy: {acc_history:.3f}")
    
    # ========================================================================
    # Test 2: Logistic Regression with SINGLE TIMESTEP (Opus check)
    # ========================================================================
    print(f"\n{'='*70}")
    print("Test 2: Logistic Regression with Single Timestep (Opus Check)")
    print(f"{'='*70}")
    
    # فقط input[t_out] را استفاده می‌کنیم - هیچ history
    X_single = np.zeros((n_ticks - start_tick, 1))
    y_single = np.zeros(n_ticks - start_tick, dtype=int)
    
    for i, t in enumerate(range(start_tick, n_ticks)):
        X_single[i, 0] = input_pulses[t]  # فقط current timestep
        y_single[i] = target[t]
    
    X_train_s, X_test_s = X_single[:split], X_single[split:]
    y_train_s, y_test_s = y_single[:split], y_single[split:]
    
    clf_single = LogisticRegression(random_state=42, max_iter=1000)
    clf_single.fit(X_train_s, y_train_s)
    
    y_pred_s = clf_single.predict(X_test_s)
    acc_single = balanced_accuracy_score(y_test_s, y_pred_s)
    
    print(f"Features: فقط input[t] (single timestep, no history)")
    print(f"Test balanced accuracy: {acc_single:.3f}")
    
    # ========================================================================
    # Test 3: Random Baseline
    # ========================================================================
    print(f"\n{'='*70}")
    print("Test 3: Random Baseline")
    print(f"{'='*70}")
    
    y_pred_random = rng.randint(0, 2, size=len(y_test_s))
    acc_random = balanced_accuracy_score(y_test_s, y_pred_random)
    
    print(f"Random prediction: {acc_random:.3f}")
    
    # ========================================================================
    # Analysis
    # ========================================================================
    print(f"\n{'='*70}")
    print("Analysis:")
    print(f"{'='*70}")
    
    print(f"\nComparison:")
    print(f"  Rolling history: {acc_history:.3f}")
    print(f"  Single timestep: {acc_single:.3f}")
    print(f"  Random:          {acc_random:.3f}")
    
    print(f"\n{'='*70}")
    print("Diagnosis:")
    print(f"{'='*70}")
    
    if acc_single > 0.60:
        print(f"\n❌ TASK IS NOT TEMPORAL!")
        print(f"   Single timestep accuracy: {acc_single:.3f} > 0.60")
        print(f"   → Task does NOT require memory")
        print(f"   → XOR can be solved without temporal dependency")
        print(f"   → e-prop is the WRONG TOOL for this task")
        print(f"   → All 20 iterations were wasted on wrong problem")
        print(f"\n   Root cause:")
        print(f"   - Input encoding includes input[t-T1] directly")
        print(f"   - This makes both bits available at same timestep")
        print(f"   - No temporal credit assignment needed")
        print(f"\n   Next steps:")
        print(f"   - Redesign task to be truly temporal")
        print(f"   - Remove direct encoding of input[t-T1]")
        print(f"   - Force network to use recurrent connections for memory")
        
    elif acc_single > 0.55:
        print(f"\n⚠️  TASK IS WEAKLY TEMPORAL")
        print(f"   Single timestep accuracy: {acc_single:.3f} (55-60%)")
        print(f"   → Task has some structure but not fully temporal")
        print(f"   → May need task redesign")
        
    else:
        print(f"\n✅ TASK IS TRULY TEMPORAL")
        print(f"   Single timestep accuracy: {acc_single:.3f} ≈ 0.50 (random)")
        print(f"   → Task requires memory to solve")
        print(f"   → e-prop is appropriate tool")
        print(f"   → Continue with identity mapping test")
        print(f"\n   Next steps:")
        print(f"   1. Identity mapping test (verify e-prop works)")
        print(f"   2. XOR without constraint (positive control)")
        print(f"   3. XOR with constraint (real experiment)")
    
    print(f"\n{'='*70}")
    print("Recommendation:")
    print(f"{'='*70}")
    
    if acc_single > 0.60:
        print(f"\n  🚨 STOP: Task design is fundamentally flawed")
        print(f"     - Remove direct encoding of input[t-T1]")
        print(f"     - Redesign task to force temporal dependency")
        print(f"     - Then restart from scratch")
    elif acc_single > 0.55:
        print(f"\n  ⚠️  CAUTION: Task may not be fully temporal")
        print(f"     - Consider task redesign")
        print(f"     - Or proceed with caution")
    else:
        print(f"\n  ✅ CONTINUE: Task is valid")
        print(f"     - Run identity mapping test")
        print(f"     - Build positive control")
        print(f"     - Then run Exp-P2A-01 properly")
    
    print(f"{'='*70}")

if __name__ == '__main__':
    task_validity_check()