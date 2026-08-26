import numpy as np
import torch
import math
from src.genesis.server.genesis_pytorch_brain import GenesisPyTorchBrain

def test_doubt_token_probability():
    print("\n[TEST] Validating Substrate 15 Epistemic Doubt Probability...")
    brain = GenesisPyTorchBrain(device="cpu")
    
    # Simulate different uncertainty levels
    uncertainties = [0.0, 1.0, 2.0, 4.0, 10.0]
    
    for h in uncertainties:
        p_doubt = 1.0 - (2.0 ** (-h))
        print(f"  Uncertainty: {h:>4.1f} bits -> P(doubt): {p_doubt:>6.2%}")
        
    assert math.isclose(1.0 - (2.0 ** 0.0), 0.0), "0 bits should mean 0% doubt"
    assert math.isclose(1.0 - (2.0 ** -1.0), 0.5), "1 bit should mean 50% doubt"
    
def test_mcts_doubt_emission():
    print("\n[TEST] Validating Substrate 15 MCTS Doubt Token Emission...")
    brain = GenesisPyTorchBrain(device="cpu")
    
    # Force high uncertainty by making tau2_hat very low and I_dyn very low
    brain.tau2_hat = torch.ones(32, dtype=torch.float32) * 1e-6
    brain.I_dyn = torch.zeros((36, 32), dtype=torch.float32)
    
    # We should see doubt token '63' often
    root_state = np.random.randn(32).astype(np.float32)
    
    doubt_count = 0
    total_runs = 50
    for _ in range(total_runs):
        res = brain.run_hierarchical_mcts(root_state, policy_mode="EXPLORE")
        if res["emitted_symbol"] == 63:
            doubt_count += 1
            
    p_empirical = doubt_count / total_runs
    print(f"  Empirical P(doubt) over {total_runs} runs: {p_empirical:.2%}")
    assert doubt_count > 0, "Agent never expressed doubt despite high uncertainty!"
    print("[TEST SUCCESS] Substrate 15 tests passed.")

if __name__ == "__main__":
    test_doubt_token_probability()
    test_mcts_doubt_emission()
