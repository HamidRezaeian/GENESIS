# experiments/phase2a/code/check_task_learnability.py
import numpy as np

def check_learnability():
    """بررسی کنیم آیا bitstream ما learnable است یا نه."""
    
    print("=" * 70)
    print("Task Learnability Check")
    print("=" * 70)
    
    # Generate sequence (مثل eprop_v5.py)
    rng = np.random.RandomState(42)
    n_ticks = 1000
    sequence = rng.randint(0, 2, size=n_ticks)
    
    # Check: آیا sequence random IID است؟
    # Autocorrelation برای lag=1 (predict next from current)
    autocorr_lag1 = np.corrcoef(sequence[:-1], sequence[1:])[0, 1]
    
    print(f"\nSequence statistics:")
    print(f"  Length: {n_ticks}")
    print(f"  Mean (P(bit=1)): {np.mean(sequence):.3f}")
    print(f"  Autocorrelation lag=1: {autocorr_lag1:.4f}")
    
    if abs(autocorr_lag1) < 0.05:
        print(f"\n❌ Sequence is IID RANDOM (autocorr ≈ 0)")
        print(f"   → accuracy=50% is THE BEST POSSIBLE for any model")
        print(f"   → Task is NOT learnable")
        print(f"   → Need to change task (delayed copy or temporal XOR)")
    else:
        print(f"\n✅ Sequence has STRUCTURE (autocorr = {autocorr_lag1:.4f})")
        print(f"   → Task may be learnable")
    
    print("=" * 70)

if __name__ == '__main__':
    check_learnability()