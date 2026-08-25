import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"C:\Users\Hamid\source\repos\GENESIS\src\genesis\server")))

from genesis_pytorch_brain import GenesisPyTorchBrain
import numpy as np

print("Testing GenesisPyTorchBrain instantiation...")
brain = GenesisPyTorchBrain()
print(f"Device: {brain.device}, dtype: {brain.dtype}")

obs = np.random.randn(343).astype(np.float32)
s = brain.forward_transformer(obs, "EXPLORE")
print(f"Forward transformer output shape: {s.shape}, mean: {s.mean():.4f}")

mcts = brain.run_hierarchical_mcts(s, "DIRECTED")
print(f"Hierarchical MCTS result keys: {list(mcts.keys())}")
print(f"Selected option: {mcts['selected_option']}, Emitted symbol: {mcts['emitted_symbol']}")

s_next = brain.forward_transformer(obs, "EXPLORE")
brain.update_hierarchical_experience(s, mcts['selected_option'], mcts['emitted_symbol'], mcts['selected_action'], 1.0, s_next, False)
print(f"Hippocampus count: {len(brain.hippocampus)}, Option hippocampus count: {len(brain.option_hippocampus)}")

print("Baseline Brain test PASSED!")
