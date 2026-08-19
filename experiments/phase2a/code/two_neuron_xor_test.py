#!/usr/bin/env python
"""
2-Neuron XOR Test (Intermediate)
=================================
XOR ساده بدون temporal complexity:
- Input A در t=1, Input B در t=2, Output در t=3
- اگر این کار کند: مشکل در temporal aspect است
- اگر کار نکند: مشکل در XOR logic یا recurrent است
"""

import numpy as np

def two_neuron_xor_test():
    """Simple XOR without temporal complexity."""
    
    print("=" * 70)
    print("2-Neuron XOR Test (Intermediate)")
    print("=" * 70)
    print("Network: 2 input → 5 hidden LIF → 2 output (softmax)")
    print("Task: XOR of two bits presented at t=1 and t=2")
    print("Output at t=3")
    print("=" * 70)
    
    np.random.seed(42)
    
    n_in, n_h, n_out = 2, 5, 2
    dv = 0.05
    theta = 0.5
    eta = 0.1
    beta = 5.0
    
    W_in  = np.random.randn(n_h, n_in)  * 0.3
    W_out = np.random.randn(n_out, n_h) * 0.3
    
    def surrogate(v, thr=0.5, beta=5.0):
        return 1.0 / (1.0 + beta * np.abs(v - thr))**2
    
    def softmax(x):
        e = np.exp(x - x.max())
        return e / e.sum()
    
    # XOR training data
    xor_data = [
        ([1, 0], 1),  # 1 XOR 0 = 1
        ([0, 1], 1),  # 0 XOR 1 = 1
        ([0, 0], 0),  # 0 XOR 0 = 0
        ([1, 1], 0),  # 1 XOR 1 = 0
    ]
    
    print(f"\nTraining data:")
    for inp, target in xor_data:
        print(f"  Input {inp} → Target {target}")
    
    print(f"\n{'Epoch':>6} | {'Loss':>8} | {'Acc':>6}")
    print("-" * 30)
    
    losses, accs = [], []
    
    for epoch in range(200):
        epoch_loss, correct = 0, 0
        
        for inp, target_class in xor_data:
            # Reset state for each sample
            v = np.zeros(n_h)
            r = np.zeros(n_out)
            eps_in = np.zeros_like(W_in)
            
            dW_in = np.zeros_like(W_in)
            dW_out = np.zeros_like(W_out)
            loss = None
            
            # t=1: Input A
            x1 = np.zeros(n_in)
            x1[0] = inp[0]
            
            I1 = W_in @ x1
            v = (1 - dv) * v + dv * (I1 / dv)
            z1 = (v >= theta).astype(float)
            fp1 = surrogate(v)
            v[z1 == 1] -= theta
            eps_in = (1 - dv) * eps_in + fp1[:, None] * x1[None, :]
            
            # t=2: Input B
            x2 = np.zeros(n_in)
            x2[1] = inp[1]
            
            I2 = W_in @ x2
            v = (1 - dv) * v + dv * (I2 / dv)
            z2 = (v >= theta).astype(float)
            fp2 = surrogate(v)
            v[z2 == 1] -= theta
            eps_in = (1 - dv) * eps_in + fp2[:, None] * x2[None, :]
            
            # t=3: Output
            r = (1 - dv) * r + dv * (W_out @ z2)
            y = softmax(r)
            
            target = np.zeros(n_out)
            target[target_class] = 1.0
            error = y - target
            loss = -np.log(y[target_class] + 1e-9)
            
            L = W_out.T @ error
            dW_in  += L[:, None] * eps_in
            dW_out += np.outer(error, z2)
            
            pred = int(y.argmax())
            correct += int(pred == target_class)
        
        # Update weights
        W_in  -= eta * dW_in
        W_out -= eta * dW_out
        
        avg_loss = loss  # last sample loss
        acc = correct / 4
        losses.append(avg_loss)
        accs.append(acc)
        
        if epoch % 50 == 0:
            print(f"{epoch:>6} | {avg_loss:>8.4f} | {acc:>6.2%}")
    
    # Final result
    print()
    print("=" * 70)
    print("Result:")
    print("=" * 70)
    
    final_loss = losses[-1]
    final_acc = accs[-1]
    
    print(f"Final loss: {final_loss:.4f}")
    print(f"Final accuracy: {final_acc:.2%}")
    
    if final_acc > 0.8:
        print(f"\n✅ SUCCESS: e-prop learned XOR!")
        print(f"   → Problem is in temporal aspect of full task")
        print(f"   → Next: investigate recurrent connections and eligibility decay")
    elif final_acc > 0.5:
        print(f"\n⚠️  PARTIAL: Some learning but not complete")
        print(f"   → May need more epochs or higher eta")
    else:
        print(f"\n❌ FAILURE: e-prop cannot learn XOR")
        print(f"   → Problem in XOR logic implementation")
        print(f"   → Check eligibility trace for multiple inputs")
    
    print("=" * 70)

if __name__ == '__main__':
    two_neuron_xor_test()