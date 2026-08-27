"""
Deep-Time Continual Multi-Task Training Driver for GENESIS.
Trains the unified cortical brain across all 5 Task Families using Substrate 21.

Invariants:
- Rule 21: Measured host work accounting
- Rule 23: Pure PyTorch FP16 Tensor Core execution
- Rule 24: 5 Task Families Benchmark Suite
- Rule 25: Zero hardcoding, pure neural matrix forward passes
"""

import sys
import os
import math
import time
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from genesis.server.genesis_pytorch_brain import GenesisPyTorchBrain, D_MODEL, N_ACTIONS
from genesis.server.substrate21_engine import Substrate21Engine


def train_dmts_episode(brain: GenesisPyTorchBrain, rng: np.random.RandomState) -> float:
    """Train 1 episode on Task 1: Delayed Match-to-Sample (DMTS)."""
    sample_id = rng.randint(0, 4)
    sample_obs = np.zeros((7, 7, 7), dtype=np.float32)
    sample_obs[:, :, sample_id] = 1.0
    brain.forward_transformer(sample_obs, "SAMPLE")

    delay = rng.randint(3, 6)
    blank_obs = np.zeros((7, 7, 7), dtype=np.float32)
    for _ in range(delay):
        brain.forward_transformer(blank_obs, "DELAY")

    distractor_id = (sample_id + rng.randint(1, 4)) % 4
    test_obs = np.zeros((7, 7, 7), dtype=np.float32)
    test_obs[:, :, 0] = 0.5
    test_obs[:, :, sample_id] = 1.0
    test_obs[:, :, distractor_id] = 0.8

    state = brain.forward_transformer(test_obs, "MATCH")
    state_t = torch.tensor(state, dtype=brain.dtype, device=brain.device)
    logits = torch.matmul(state_t, brain.W_policy)
    probs = torch.softmax(logits, dim=-1)
    
    # Epsilon-greedy exploration for training
    if rng.rand() < 0.15:
        action = rng.randint(0, N_ACTIONS)
    else:
        action = int(torch.argmax(logits).item())

    chosen_match = action % 4
    is_correct = (chosen_match == sample_id)
    reward = 1.0 if is_correct else -0.5

    next_state = state + np.random.randn(32).astype(np.float32) * 0.01
    brain.update_neural_weights(state, action, reward, next_state)
    return 1.0 if is_correct else 0.0


def train_bit_parity_episode(brain: GenesisPyTorchBrain, rng: np.random.RandomState) -> float:
    """Train 1 episode on Task 2: Delayed Bit Parity."""
    seq_len = rng.randint(3, 6)
    bits = rng.randint(0, 2, size=seq_len)
    true_parity = int(np.sum(bits) % 2)

    for b in bits:
        obs = np.zeros((7, 7, 7), dtype=np.float32)
        obs[:, :, b] = 1.0
        brain.forward_transformer(obs, f"BIT_{b}")

    query_obs = np.zeros((7, 7, 7), dtype=np.float32)
    query_obs[:, :, 4] = 1.0
    state = brain.forward_transformer(query_obs, "PARITY?")
    state_t = torch.tensor(state, dtype=brain.dtype, device=brain.device)
    logits = torch.matmul(state_t, brain.W_policy)

    if rng.rand() < 0.15:
        action = rng.randint(0, N_ACTIONS)
    else:
        action = int(torch.argmax(logits).item())

    predicted_parity = action % 2
    is_correct = (predicted_parity == true_parity)
    reward = 1.0 if is_correct else -0.5

    next_state = state + np.random.randn(32).astype(np.float32) * 0.01
    brain.update_neural_weights(state, action, reward, next_state)
    return 1.0 if is_correct else 0.0


def train_arithmetic_episode(brain: GenesisPyTorchBrain, rng: np.random.RandomState) -> float:
    """Train 1 episode on Task 3: Compositional Arithmetic."""
    a = rng.randint(1, 9)
    b = rng.randint(1, 9)
    true_sum = (a + b) % 10

    obs_a = np.zeros((7, 7, 7), dtype=np.float32)
    obs_a[:, :, a % 7] = float(a) / 10.0
    brain.forward_transformer(obs_a, f"A_{a}")

    obs_b = np.zeros((7, 7, 7), dtype=np.float32)
    obs_b[:, :, b % 7] = float(b) / 10.0
    brain.forward_transformer(obs_b, f"B_{b}")

    query_obs = np.zeros((7, 7, 7), dtype=np.float32)
    query_obs[:, :, 5] = 1.0
    state = brain.forward_transformer(query_obs, "ADD")
    state_t = torch.tensor(state, dtype=brain.dtype, device=brain.device)
    logits = torch.matmul(state_t, brain.W_policy)

    if rng.rand() < 0.15:
        action = rng.randint(0, N_ACTIONS)
    else:
        action = int(torch.argmax(logits).item())

    pred_sum = action % 4
    is_correct = (pred_sum == (true_sum % 4))
    reward = 1.0 if is_correct else -0.5

    next_state = state + np.random.randn(32).astype(np.float32) * 0.01
    brain.update_neural_weights(state, action, reward, next_state)
    return 1.0 if is_correct else 0.0


def train_navigation_episode(brain: GenesisPyTorchBrain, rng: np.random.RandomState) -> float:
    """Train 1 episode on Task 4: Spatial Navigation."""
    agent_pos = np.array([1, 1])
    goal_pos = np.array([4, 4])
    max_steps = 15
    reached = False

    for _ in range(max_steps):
        obs = np.zeros((7, 7, 7), dtype=np.float32)
        dx = goal_pos[0] - agent_pos[0]
        dy = goal_pos[1] - agent_pos[1]
        obs[3, 3, 0] = float(agent_pos[0]) / 5.0
        obs[3, 3, 1] = float(agent_pos[1]) / 5.0
        obs[3, 3, 2] = math.tanh(dx)
        obs[3, 3, 3] = math.tanh(dy)

        state = brain.forward_transformer(obs, "NAV_GOAL")
        state_t = torch.tensor(state, dtype=brain.dtype, device=brain.device)
        logits = torch.matmul(state_t, brain.W_policy)

        if rng.rand() < 0.2:
            action = rng.randint(0, N_ACTIONS)
        else:
            action = int(torch.argmax(logits).item())

        if action == 0 and agent_pos[0] > 0:
            agent_pos[0] -= 1
        elif action == 1 and agent_pos[1] < 5:
            agent_pos[1] += 1
        elif action == 2 and agent_pos[0] < 5:
            agent_pos[0] += 1
        elif action == 3 and agent_pos[1] > 0:
            agent_pos[1] -= 1

        is_goal = np.array_equal(agent_pos, goal_pos)
        reward = 2.0 if is_goal else -0.05

        next_obs = np.zeros((7, 7, 7), dtype=np.float32)
        next_obs[3, 3, 0] = float(agent_pos[0]) / 5.0
        next_obs[3, 3, 1] = float(agent_pos[1]) / 5.0
        next_state = brain.forward_transformer(next_obs, "NAV_STEP")
        brain.update_neural_weights(state, action, reward, next_state)

        if is_goal:
            reached = True
            break

    return 1.0 if reached else 0.0


def train_causal_episode(brain: GenesisPyTorchBrain, rng: np.random.RandomState) -> float:
    """Train 1 episode on Task 5: Causal Intervention & Do-Calculus."""
    z_confounder = rng.randint(0, 2)
    p_x = 0.8 if z_confounder == 1 else 0.2
    is_intervention = (rng.rand() < 0.5)

    if is_intervention:
        x_val = rng.randint(0, 2)
    else:
        x_val = 1 if (rng.rand() < p_x) else 0

    p_y = 0.75 if x_val == 1 else 0.25
    y_val = 1 if (rng.rand() < p_y) else 0

    obs_context = np.zeros((7, 7, 7), dtype=np.float32)
    obs_context[:, :, 0] = float(z_confounder)
    obs_context[:, :, 1] = float(x_val)
    mode_text = f"DO_X_{x_val}" if is_intervention else f"OBS_X_{x_val}"
    state_ctx = brain.forward_transformer(obs_context, mode_text)

    query_obs = np.zeros((7, 7, 7), dtype=np.float32)
    query_obs[:, :, 6] = 1.0
    state = brain.forward_transformer(query_obs, "PRED_Y?")
    state_t = torch.tensor(state, dtype=brain.dtype, device=brain.device)
    logits = torch.matmul(state_t, brain.W_policy)

    if rng.rand() < 0.15:
        action = rng.randint(0, N_ACTIONS)
    else:
        action = int(torch.argmax(logits).item())

    pred_y = action % 2
    is_correct = (pred_y == y_val)
    reward = 1.0 if is_correct else -0.5

    next_state = state + np.random.randn(32).astype(np.float32) * 0.01
    brain.update_neural_weights(state, action, reward, next_state)
    return 1.0 if is_correct else 0.0


def main():
    print("=" * 70, flush=True)
    print("🚀 GENESIS Deep-Time Continual Multi-Task Training Engine (Substrate 21)", flush=True)
    print("=" * 70, flush=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🖥️ Hardware Device: {device.upper()}", flush=True)

    # Initialize brain with seed 42
    brain = GenesisPyTorchBrain(device=device, seed=42)
    brain_dir = REPO_ROOT / "Brain"
    brain_dir.mkdir(exist_ok=True, parents=True)

    # Training Hyperparameters
    N_EPOCHS = 20
    EPISODES_PER_TASK_PER_EPOCH = 10
    rng = np.random.RandomState(42)

    task_names = ["DMTS", "Bit Parity", "Arithmetic", "Navigation", "Causal Intervention"]
    task_runners = [
        train_dmts_episode,
        train_bit_parity_episode,
        train_arithmetic_episode,
        train_navigation_episode,
        train_causal_episode
    ]

    total_ticks = 0
    t0 = time.time()

    print(f"\nStarting continual multi-task training ({N_EPOCHS} epochs, {EPISODES_PER_TASK_PER_EPOCH * 5} trials/epoch)...", flush=True)

    for epoch in range(1, N_EPOCHS + 1):
        epoch_scores = [0.0] * 5

        for task_idx, runner in enumerate(task_runners):
            scores = []
            for _ in range(EPISODES_PER_TASK_PER_EPOCH):
                score = runner(brain, rng)
                scores.append(score)
                total_ticks += 1

                # Periodic sleep consolidation every 200 ticks
                if total_ticks % 200 == 0 and brain.hippocampus.size >= 10:
                    brain.sleep_consolidation()

            epoch_scores[task_idx] = float(np.mean(scores))

        elapsed = time.time() - t0
        scores_str = " | ".join([f"{name[:4]}: {score*100:.1f}%" for name, score in zip(task_names, epoch_scores)])
        print(f"Epoch {epoch:2d}/{N_EPOCHS:2d} ({elapsed:.1f}s) | Hippo: {brain.hippocampus.size:4d} | {scores_str}", flush=True)

    # Final Sleep Consolidation
    print("\nTriggering final circadian sleep consolidation...", flush=True)
    for _ in range(5):
        brain.sleep_consolidation()

    # Save trained checkpoint to canonical brain
    save_path = brain_dir / "canonical_brain.npz"
    brain.save_checkpoint(save_path)
    print(f"\n✅ Consolidated neural checkpoint saved to: {save_path}", flush=True)

    # Re-evaluate on 5 Task Families Benchmark Suite
    print("\n" + "=" * 70, flush=True)
    print("📊 Evaluating Post-Training 5 Task Families Benchmark Suite (Rule 24)...", flush=True)
    print("=" * 70, flush=True)

    import subprocess
    cmd = [sys.executable, str(REPO_ROOT / "tests" / "benchmark_5_task_families.py")]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout, flush=True)
    if res.stderr:
        print(res.stderr, flush=True)


if __name__ == "__main__":
    main()
