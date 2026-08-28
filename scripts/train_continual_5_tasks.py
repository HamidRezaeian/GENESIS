"""
Deep-Time Continual Multi-Task Training Driver for GENESIS.
Trains the unified cortical brain across all 5 Task Families using Substrate 22:
Task-Conditioned FiLM World Model + Adaptive MCTS Policy Distillation + Adaptive Curriculum Scheduler.

Invariants:
- Rule 21: Measured host work accounting
- Rule 23: Pure PyTorch FP16 Tensor Core execution
- Rule 24: 5 Task Families Benchmark Suite
- Rule 25: Zero hardcoding, pure neural matrix forward passes
- Rule 26: Unified model architecture alignment
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
from genesis.server.substrate22_engine import Substrate22Engine


def train_dmts_episode(brain: GenesisPyTorchBrain, rng: np.random.RandomState) -> float:
    """Train 1 episode on Task 1: Delayed Match-to-Sample (DMTS)."""
    task_id = 0
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
    
    # Substrate 22 MCTS with Task-Conditioned Dynamics & Policy Distillation
    mcts_info = brain.run_mcts(state, policy_mode="DIRECTED", task_id=task_id)
    mcts_probs = np.array(mcts_info["probs"], dtype=np.float64)
    
    if rng.rand() < 0.15:
        action = rng.randint(0, N_ACTIONS)
    else:
        action = int(np.argmax(mcts_probs))

    chosen_match = action % 4
    is_correct = (chosen_match == sample_id)
    reward = 1.0 if is_correct else -0.5

    next_state = state + np.random.randn(32).astype(np.float32) * 0.01
    brain.update_neural_weights(state, action, reward, next_state, mcts_target_probs=mcts_probs, task_id=task_id)
    return 1.0 if is_correct else 0.0


def train_bit_parity_episode(brain: GenesisPyTorchBrain, rng: np.random.RandomState) -> float:
    """Train 1 episode on Task 2: Delayed Bit Parity."""
    task_id = 1
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

    mcts_info = brain.run_mcts(state, policy_mode="DIRECTED", task_id=task_id)
    mcts_probs = np.array(mcts_info["probs"], dtype=np.float64)

    if rng.rand() < 0.15:
        action = rng.randint(0, N_ACTIONS)
    else:
        action = int(np.argmax(mcts_probs))

    predicted_parity = action % 2
    is_correct = (predicted_parity == true_parity)
    reward = 1.0 if is_correct else -0.5

    next_state = state + np.random.randn(32).astype(np.float32) * 0.01
    brain.update_neural_weights(state, action, reward, next_state, mcts_target_probs=mcts_probs, task_id=task_id)
    return 1.0 if is_correct else 0.0


def train_arithmetic_episode(brain: GenesisPyTorchBrain, rng: np.random.RandomState) -> float:
    """Train 1 episode on Task 3: Compositional Arithmetic."""
    task_id = 2
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

    mcts_info = brain.run_mcts(state, policy_mode="DIRECTED", task_id=task_id)
    mcts_probs = np.array(mcts_info["probs"], dtype=np.float64)

    if rng.rand() < 0.15:
        action = rng.randint(0, N_ACTIONS)
    else:
        action = int(np.argmax(mcts_probs))

    pred_sum = action % 4
    is_correct = (pred_sum == (true_sum % 4))
    reward = 1.0 if is_correct else -0.5

    next_state = state + np.random.randn(32).astype(np.float32) * 0.01
    brain.update_neural_weights(state, action, reward, next_state, mcts_target_probs=mcts_probs, task_id=task_id)
    return 1.0 if is_correct else 0.0


def train_navigation_episode(brain: GenesisPyTorchBrain, rng: np.random.RandomState) -> float:
    """Train 1 episode on Task 4: Spatial Navigation."""
    task_id = 3
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
        mcts_info = brain.run_mcts(state, policy_mode="DIRECTED", task_id=task_id)
        mcts_probs = np.array(mcts_info["probs"], dtype=np.float64)

        if rng.rand() < 0.2:
            action = rng.randint(0, N_ACTIONS)
        else:
            action = int(np.argmax(mcts_probs))

        if action == 0 and agent_pos[0] > 0:
            agent_pos[0] -= 1
        elif action == 1 and agent_pos[1] < 5:
            agent_pos[1] += 1
        elif action == 2 and agent_pos[0] < 5:
            agent_pos[0] += 1
        elif action == 3 and agent_pos[1] > 0:
            agent_pos[1] -= 1

        is_goal = np.array_equal(agent_pos, goal_pos)
        
        # Grounded Intrinsic Curiosity Reward
        sa_check = torch.zeros(36, dtype=brain.dtype, device=brain.device)
        sa_check[:32] = torch.tensor(state, dtype=brain.dtype, device=brain.device)
        sa_check[32 + action] = 1.0
        pred_next = brain.substrate22.world_model(sa_check, task_id)
        
        next_obs = np.zeros((7, 7, 7), dtype=np.float32)
        next_obs[3, 3, 0] = float(agent_pos[0]) / 5.0
        next_obs[3, 3, 1] = float(agent_pos[1]) / 5.0
        next_state = brain.forward_transformer(next_obs, "NAV_STEP")
        next_state_t = torch.tensor(next_state, dtype=brain.dtype, device=brain.device)
        pred_err = torch.mean((next_state_t - pred_next) ** 2).item()
        r_intrinsic = 0.5 * math.exp(-pred_err)

        reward = (2.0 if is_goal else -0.05) + r_intrinsic
        brain.update_neural_weights(state, action, reward, next_state, mcts_target_probs=mcts_probs, task_id=task_id)

        if is_goal:
            reached = True
            break

    return 1.0 if reached else 0.0


def train_causal_episode(brain: GenesisPyTorchBrain, rng: np.random.RandomState) -> float:
    """Train 1 episode on Task 5: Causal Intervention & Do-Calculus."""
    task_id = 4
    X_val = rng.randint(0, 2)
    Z_val = X_val if rng.rand() > 0.1 else 1 - X_val
    intervene_Y = rng.randint(0, 2)
    true_W = intervene_Y ^ Z_val

    # Stage 1: Passive context
    obs_context = np.zeros((7, 7, 7), dtype=np.float32)
    obs_context[:, :, 0] = float(X_val)
    obs_context[:, :, 1] = float(Z_val)
    brain.forward_transformer(obs_context, "PASSIVE_DAG")

    # Stage 2: Active intervention do(Y)
    obs_intervene = np.zeros((7, 7, 7), dtype=np.float32)
    obs_intervene[:, :, 2] = float(intervene_Y)
    obs_intervene[:, :, 6] = 1.0
    state = brain.forward_transformer(obs_intervene, f"DO_Y_{intervene_Y}")

    mcts_info = brain.run_mcts(state, policy_mode="DIRECTED", task_id=task_id)
    mcts_probs = np.array(mcts_info["probs"], dtype=np.float64)

    if rng.rand() < 0.15:
        action = rng.randint(0, N_ACTIONS)
    else:
        action = int(np.argmax(mcts_probs))

    pred_W = action % 2
    is_correct = (pred_W == true_W)
    reward = 1.0 if is_correct else -0.5

    next_state = state + np.random.randn(32).astype(np.float32) * 0.01
    brain.update_neural_weights(state, action, reward, next_state, mcts_target_probs=mcts_probs, task_id=task_id)
    return 1.0 if is_correct else 0.0


def main():
    print("=" * 70, flush=True)
    print("🚀 GENESIS Deep-Time Continual Multi-Task Training Engine (Substrate 22)", flush=True)
    print("=" * 70, flush=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🖥️ Hardware Device: {device.upper()}", flush=True)

    # Initialize brain with seed 42
    brain = GenesisPyTorchBrain(device=device, seed=42)
    brain_dir = REPO_ROOT / "Brain"
    brain_dir.mkdir(exist_ok=True, parents=True)

    # Training Hyperparameters (GLM 5.3 Optimal Guidance)
    N_EPOCHS = 60
    TOTAL_EPISODES_PER_EPOCH = 125
    rng = np.random.RandomState(42)

    task_names = ["DMTS", "Bit Parity", "Arithmetic", "Navigation", "Causal Intervention"]
    task_runners = [
        train_dmts_episode,
        train_bit_parity_episode,
        train_arithmetic_episode,
        train_navigation_episode,
        train_causal_episode
    ]

    scheduler = brain.substrate22.curriculum
    total_ticks = 0
    t0 = time.time()

    print(f"\nStarting Substrate 22 adaptive continual training ({N_EPOCHS} epochs, {TOTAL_EPISODES_PER_EPOCH} trials/epoch)...", flush=True)

    for epoch in range(1, N_EPOCHS + 1):
        brain.substrate22.current_epoch = epoch
        task_scores: Dict[int, List[float]] = {i: [] for i in range(5)}

        for _ in range(TOTAL_EPISODES_PER_EPOCH):
            task_id = scheduler.select_next_task()
            runner = task_runners[task_id]
            score = runner(brain, rng)
            task_scores[task_id].append(score)
            scheduler.update(task_id, score)
            total_ticks += 1

            # Periodic sleep consolidation every 100 ticks
            if total_ticks % 100 == 0 and brain.hippocampus.size >= 10:
                brain.sleep_consolidation()

        # Step temperature scheduler
        brain.substrate22.distill_temp_scheduler.step()

        # Circadian Sleep Consolidation every 5 epochs (3 cycles as recommended by GLM 5.3)
        if epoch % 5 == 0:
            for _ in range(3):
                brain.sleep_consolidation()

        elapsed = time.time() - t0
        epoch_means = [float(np.mean(task_scores[i])) if task_scores[i] else 0.0 for i in range(5)]
        scores_str = " | ".join([f"{name[:4]}: {m*100:.1f}%" for name, m in zip(task_names, epoch_means)])
        tau_val = brain.substrate22.distill_temp_scheduler.get_temperature()
        print(f"Epoch {epoch:2d}/{N_EPOCHS:2d} ({elapsed:.1f}s) | tau: {tau_val:.2f} | Hippo: {brain.hippocampus.size:5d} | {scores_str}", flush=True)

    # Final Deep-Time Sleep Consolidation (10 cycles)
    print("\nTriggering final circadian sleep consolidation...", flush=True)
    for _ in range(10):
        brain.sleep_consolidation()

    # Save trained checkpoint to canonical brain
    save_path = brain_dir / "canonical_brain.npz"
    brain.save_checkpoint(save_path)
    print(f"\n✅ Consolidated Substrate 22 checkpoint saved to: {save_path}", flush=True)

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
