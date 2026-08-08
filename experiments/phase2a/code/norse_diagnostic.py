#!/usr/bin/env python
"""
Norse Diagnostic: Reference e-prop Implementation
====================================================
از Norse library استفاده می‌کنیم تا ببینیم:
1. آیا task واقعاً learnable است؟
2. آیا implementation ما باگ دارد؟

اگر Norse کار کند → bug در implementation ما
اگر Norse هم کار نکند → problem در task یا hyperparameters
"""

import numpy as np
import sys

def check_norse_installed():
    """Check if norse is installed."""
    try:
        import norse
        import torch
        print(f"✅ Norse installed: {norse.__version__}")
        print(f"✅ PyTorch installed: {torch.__version__}")
        return True
    except ImportError:
        print("❌ Norse or PyTorch not installed")
        print("\nInstall with:")
        print("  pip install torch norse-torch")
        return False


def norse_diagnostic():
    """Run Temporal XOR with Norse e-prop."""
    
    print("=" * 70)
    print("Norse Diagnostic: Reference e-prop Implementation")
    print("=" * 70)
    
    if not check_norse_installed():
        return False
    
    import torch
    import norse.torch as snn
    
    print("\n" + "=" * 70)
    print("Running Temporal XOR with Norse e-prop...")
    print("=" * 70)
    
    # Task parameters
    T1, T2, T_out = 3, 6, 9
    n_ticks = 500
    n_trials = 200
    pulse_prob = 0.3
    
    # Network parameters
    n_input = 2
    n_hidden = 50
    n_output = 2
    
    # LIF parameters
    lif_params = snn.LIFParameters(
        tau_syn_inv=1/20.0,  # synaptic time constant
        tau_mem_inv=1/20.0,  # membrane time constant
        v_th=torch.tensor(0.3),
        v_reset=torch.tensor(0.0),
        method='super',
        alpha=100.0,  # surrogate gradient width
    )
    
    # Initialize network
    input_weights = torch.randn(n_hidden, n_input) * 0.3
    recurrent_weights = torch.randn(n_hidden, n_hidden) * 0.1
    output_weights = torch.randn(n_output, n_hidden) * 0.3
    
    input_weights.requires_grad = True
    recurrent_weights.requires_grad = True
    output_weights.requires_grad = True
    
    optimizer = torch.optim.Adam([input_weights, recurrent_weights, output_weights], lr=0.01)
    
    def generate_xor_trial():
        """Generate one XOR trial."""
        rng = np.random.RandomState()
        
        # Input sequence
        pulses = (rng.rand(n_ticks) < pulse_prob).astype(int)
        
        # Encode as one-hot at T1 and T2
        x = torch.zeros(n_ticks, n_input)
        x[T1, 0] = pulses[T1] if T1 < n_ticks else 0
        x[T2, 1] = pulses[T2] if T2 < n_ticks else 0
        
        # Target at T_out
        if T_out < n_ticks:
            target = int(pulses[T1] ^ pulses[T2]) if T1 < n_ticks and T2 < n_ticks else 0
        else:
            target = 0
        
        return x, target
    
    # Training loop
    print(f"\nTraining for {n_trials} trials...")
    print(f"{'Trial':>6} | {'Loss':>8} | {'Acc':>6}")
    print("-" * 30)
    
    losses = []
    correct_total = 0
    
    for trial in range(n_trials):
        optimizer.zero_grad()
        
        # Generate trial
        x, target = generate_xor_trial()
        
        # Forward pass through LIF network
        v = torch.zeros(n_hidden)
        z_rec = torch.zeros(n_hidden)
        
        hidden_spikes = []
        
        for t in range(min(T_out + 1, n_ticks)):
            # Input current
            i_in = x[t] @ input_weights.T
            
            # Recurrent current
            i_rec = z_rec @ recurrent_weights.T
            
            # LIF step
            z, v = snn.lif_step(
                i_in + i_rec,
                v,
                z_rec,
                lif_params,
                input_weights,
                recurrent_weights,
            )
            
            z_rec = z
            hidden_spikes.append(z)
        
        # Output at T_out
        if T_out < len(hidden_spikes):
            output_spikes = hidden_spikes[T_out]
            logits = output_spikes @ output_weights.T
            
            # Loss
            target_tensor = torch.tensor([target], dtype=torch.long)
            loss = torch.nn.functional.cross_entropy(logits.unsqueeze(0), target_tensor)
            
            # Backward
            loss.backward()
            optimizer.step()
            
            # Track
            pred = logits.argmax().item()
            correct = int(pred == target)
            correct_total += correct
            losses.append(loss.item())
            
            if trial % 50 == 0 or trial < 5:
                acc = correct_total / (trial + 1)
                print(f"{trial:>6} | {loss.item():>8.4f} | {acc:>6.2%}")
    
    # Final result
    print()
    print("=" * 70)
    print("Norse Diagnostic Result:")
    print("=" * 70)
    
    final_loss = np.mean(losses[-50:]) if losses else 1.0
    final_acc = correct_total / n_trials
    
    print(f"Final loss (last 50 trials): {final_loss:.4f}")
    print(f"Final accuracy: {final_acc:.2%}")
    
    if final_acc > 0.8:
        print(f"\n✅ SUCCESS: Norse e-prop learned Temporal XOR!")
        print(f"   → Task IS learnable")
        print(f"   → Implementation our code has bugs")
        print(f"   → Next: compare line-by-line with Norse implementation")
        return True
    elif final_acc > 0.6:
        print(f"\n⚠️  PARTIAL: Norse shows some learning")
        print(f"   → Task is learnable but difficult")
        print(f"   → May need hyperparameter tuning")
        return True
    else:
        print(f"\n❌ FAILURE: Even Norse cannot learn this task")
        print(f"   → Problem is in task design or hyperparameters")
        print(f"   → Consider: simpler task or different architecture")
        return False
    
    print("=" * 70)


if __name__ == '__main__':
    try:
        success = norse_diagnostic()
        if success:
            print("\n🎉 Next step: Compare our implementation with Norse")
        else:
            print("\n⚠️  Consider: pivot to simpler task or null result paper")
    except Exception as e:
        print(f"\n❌ Error during Norse diagnostic: {e}")
        print("\nThis may indicate:")
        print("  - Norse installation issue")
        print("  - Incompatible versions")
        print("  - Code error")
        import traceback
        traceback.print_exc()