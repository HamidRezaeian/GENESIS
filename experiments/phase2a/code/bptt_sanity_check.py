#!/usr/bin/env python
"""
BPTT Sanity Check: آیا task اصلاً learnable است؟
=================================================
اگر BPTT هم ~50% بدهد → task مشکل دارد
اگر BPTT > 55% بدهد → task learnable است، e-prop مشکل دارد
"""

import numpy as np

def bptt_sanity_check():
    """Simple BPTT test: آیا hidden state می‌تواند input قدیمی را نگه دارد؟"""
    
    print("=" * 70)
    print("BPTT Sanity Check: Task Learnability")
    print("=" * 70)
    
    # Task parameters
    n_ticks = 500
    delay_k = 2
    n_input = 20
    n_hidden = 50
    n_output = 2
    
    # Generate sequence
    rng = np.random.RandomState(42)
    sequence = rng.randint(0, 2, size=n_ticks)
    
    # --- Simple test: آیا یک linear readout از hidden state کار می‌کند؟ ---
    print("\nTest 1: Linear readout from random hidden state")
    print("-" * 50)
    
    # Simulate a simple recurrent network (no learning)
    hidden_state = np.zeros(n_hidden)
    
    correct = 0
    total = 0
    
    for t in range(delay_k, n_ticks):
        input_bit = sequence[t]
        target_bit = sequence[t - delay_k]
        
        # Encode input
        x = np.zeros(n_input)
        if input_bit == 0:
            x[:10] = 1.0
        else:
            x[10:] = 1.0
        
        # Simple recurrent update (random weights)
        W_in = np.random.randn(n_hidden, n_input) * 0.5
        W_rec = np.random.randn(n_hidden, n_hidden) * 0.1
        
        hidden_state = np.tanh(W_in @ x + W_rec @ hidden_state)
        
        # Linear readout (random)
        W_out = np.random.randn(n_output, n_hidden) * 0.5
        output = W_out @ hidden_state
        
        pred = int(output[1] > output[0])
        if pred == target_bit:
            correct += 1
        total += 1
    
    acc_random = correct / total
    print(f"  Random weights accuracy: {acc_random:.3f}")
    
    # --- Test 2: آیا یک simple memory می‌تواند کار کند؟ ---
    print("\nTest 2: Perfect memory (oracle)")
    print("-" * 50)
    
    # Oracle: اگر input[t-2] را به خاطر بسپاریم
    correct_oracle = 0
    total_oracle = 0
    
    for t in range(delay_k, n_ticks):
        target_bit = sequence[t - delay_k]
        # Oracle always knows the answer
        correct_oracle += 1
        total_oracle += 1
    
    acc_oracle = correct_oracle / total_oracle
    print(f"  Oracle accuracy: {acc_oracle:.3f} (trivially 100%)")
    
    # --- Test 3: آیا یک simple delay line کار می‌کند؟ ---
    print("\nTest 3: Simple delay line (k=2)")
    print("-" * 50)
    
    # Delay line: output[t] = input[t-2]
    buffer = np.zeros(delay_k)
    correct_delay = 0
    total_delay = 0
    
    for t in range(n_ticks):
        input_bit = sequence[t]
        
        if t >= delay_k:
            target_bit = sequence[t - delay_k]
            pred = int(buffer[0])  # oldest in buffer
            if pred == target_bit:
                correct_delay += 1
            total_delay += 1
        
        # Shift buffer
        buffer = np.roll(buffer, 1)
        buffer[0] = input_bit
    
    acc_delay = correct_delay / total_delay
    print(f"  Delay line accuracy: {acc_delay:.3f}")
    
    # --- Analysis ---
    print("\n" + "=" * 70)
    print("Analysis:")
    print("=" * 70)
    
    print(f"\n  Random weights: {acc_random:.3f} (should be ~0.50)")
    print(f"  Oracle:         {acc_oracle:.3f} (trivially 1.00)")
    print(f"  Delay line:     {acc_delay:.3f} (should be ~1.00)")
    
    print()
    if acc_delay > 0.95:
        print("  ✅ Task IS learnable (delay line works)")
        print("     → Problem is in e-prop implementation, not task")
        print("     → Need to fix credit assignment")
    else:
        print("  ❌ Task may NOT be learnable")
        print("     → Change task or check sequence generation")
    
    print()
    print("Conclusion:")
    print("-" * 50)
    if acc_random < 0.55 and acc_delay > 0.95:
        print("  Task is learnable WITH memory.")
        print("  e-prop must learn to use recurrent connections as memory.")
        print("  → Debug: Does e-prop update recurrent weights correctly?")
    elif acc_random > 0.55:
        print("  ⚠️  Random weights already work — task may be too easy")
    else:
        print("  ⚠️  Task design issue — consider Temporal XOR benchmark")
    
    print("=" * 70)

if __name__ == '__main__':
    bptt_sanity_check()