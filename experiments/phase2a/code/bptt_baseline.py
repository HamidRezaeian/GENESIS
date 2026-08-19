#!/usr/bin/env python
"""
BPTT Baseline: آیا task اصلاً learnable است؟
=============================================
یک simple logistic regression روی input features.
اگر این هم ~50% بدهد، task مشکل دارد.
اگر این هم > 60% بدهد، e-prop implementation مشکل دارد.
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score

def bptt_baseline():
    """Simple logistic regression baseline."""
    
    print("=" * 70)
    print("BPTT Baseline: Task Learnability Check")
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
    
    # Features: input[t], input[t-1], ..., input[t-6]
    start_tick = max(T1, T2)
    n_features = T2 + 1  # 7 features
    
    X = np.zeros((n_ticks - start_tick, n_features))
    y = np.zeros(n_ticks - start_tick, dtype=int)
    
    for i, t in enumerate(range(start_tick, n_ticks)):
        for k in range(n_features):
            X[i, k] = input_pulses[t - k] if t - k >= 0 else 0
        y[i] = target[t]
    
    print(f"\nTask: output[t] = input[t-{T1}] XOR input[t-{T2}]")
    print(f"Features: input[t], input[t-1], ..., input[t-{T2}]")
    print(f"Samples: {len(X)}")
    print(f"Target distribution: P(0)={np.mean(y==0):.3f}, P(1)={np.mean(y==1):.3f}")
    
    # Train/test split
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    # Logistic regression
    print(f"\nTraining logistic regression...")
    clf = LogisticRegression(random_state=42, max_iter=1000)
    clf.fit(X_train, y_train)
    
    # Evaluate
    y_pred_train = clf.predict(X_train)
    y_pred_test = clf.predict(X_test)
    
    train_acc = balanced_accuracy_score(y_train, y_pred_train)
    test_acc = balanced_accuracy_score(y_test, y_pred_test)
    
    print(f"\nResults:")
    print(f"  Train balanced accuracy: {train_acc:.3f}")
    print(f"  Test balanced accuracy:  {test_acc:.3f}")
    
    # Feature importance
    print(f"\nFeature importance (coefficients):")
    for k in range(n_features):
        print(f"  input[t-{k}]: {clf.coef_[0, k]:.4f}")
    
    # Analysis
    print(f"\n{'='*70}")
    print("Analysis:")
    print(f"{'='*70}")
    
    if test_acc > 0.60:
        print(f"  ✅ Task IS learnable (test_acc = {test_acc:.3f} > 0.60)")
        print(f"     → Problem is in e-prop implementation, not task")
        print(f"     → Need to fix credit assignment or hyperparameters")
    elif test_acc > 0.55:
        print(f"  ⚠️  Task is WEAKLY learnable (test_acc = {test_acc:.3f})")
        print(f"     → Task has some structure but hard to learn")
        print(f"     → e-prop may need more tuning")
    else:
        print(f"  ❌ Task is NOT learnable (test_acc = {test_acc:.3f} ≈ 0.50)")
        print(f"     → Problem is in task design")
        print(f"     → Need to change task or add more structure")
    
    print(f"\n{'='*70}")
    print("Comparison with e-prop:")
    print(f"{'='*70}")
    print(f"  Logistic regression: {test_acc:.3f}")
    print(f"  e-prop v14:          0.502")
    print(f"  Difference:          {(test_acc - 0.502)*100:+.1f} pp")
    
    if test_acc > 0.55:
        print(f"\n  → e-prop is UNDERPERFORMING the baseline")
        print(f"  → Need to debug e-prop further")
    else:
        print(f"\n  → e-prop is at baseline level")
        print(f"  → Task may not be learnable by any method")
    
    print(f"{'='*70}")

if __name__ == '__main__':
    bptt_baseline()