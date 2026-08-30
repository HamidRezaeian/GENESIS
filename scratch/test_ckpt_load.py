import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import torch
import pickle
from genesis.server.phase_e_substrate import BatchedPopulation
from genesis.server.phase_e_ecology import EcologyField

BRAIN_DIR = REPO_ROOT / "Brain"
phase_e_ckpt = BRAIN_DIR / "phase_e_state.pt"

pop = BatchedPopulation(n_worlds=32, pop_per_world=128, device="cuda")
eco = EcologyField(n_worlds=32, grid_size=32, device="cuda")

if phase_e_ckpt.exists():
    with open(phase_e_ckpt, "rb") as f:
        state = torch.load(f, pickle_module=pickle, weights_only=False)
    
    print("Keys in checkpoint pop_state:")
    print(list(state['pop_state'].keys())[:10])
    
    # Try strict load vs non-strict load
    try:
        pop.load_state_dict(state['pop_state'], strict=False)
        print("✅ pop.load_state_dict(strict=False) succeeded!")
    except Exception as e:
        print(f"❌ pop.load_state_dict failed: {e}")
