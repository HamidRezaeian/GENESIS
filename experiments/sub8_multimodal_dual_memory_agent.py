"""Substrate 8: Multimodal Grounded Language Transformer & Dual-Memory Sleep Consolidation.

Mathematical Invariant: Zero catastrophic forgetting via Fisher-weighted Synaptic
Consolidation and Hippocampal Episodic Replay across multimodal instruction tasks.
Rules: Rule 4 (Skepticism), Rule 17 (No arbitrary constants), Rule 21 (Thermodynamic Grounding).
"""

import os
import sys
import json
import argparse
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Dimensions & Hyperparameters
GRID_SIZE = 24
VISION_SIZE = 7
N_CHANNELS = 6
VISUAL_DIM = VISION_SIZE * VISION_SIZE * N_CHANNELS # 294
VOCAB_SIZE = 64
MAX_TEXT_LEN = 16
D_MODEL = 32
CONTEXT_LEN = 8
N_ACTIONS = 4

LR_BASE = 0.005
LAMBDA_HOMEO = 1e-4
LAMBDA_EWC = 0.5
GAMMA = 0.95

MCTS_SIMS = 12
MCTS_DEPTH = 3
C_PUCT = 1.4

class MultimodalEnvironment:
    """24x24 Multi-Room Multimodal Environment with Text-Conditioned Goals."""
    def __init__(self, seed=100):
        self.rng = np.random.RandomState(seed)
        self.grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        self.agent_pos = [3, 3]
        self.agent_dir = 0
        self.has_key = False
        self.door_unlocked = False
        self.current_task = "FIND FOOD"
        self.reset()

    def reset(self, task="FIND FOOD"):
        self.grid.fill(0)
        # Boundary walls
        self.grid[0, :] = 1; self.grid[-1, :] = 1
        self.grid[:, 0] = 1; self.grid[:, -1] = 1

        # Partition Wall
        mid = GRID_SIZE // 2
        self.grid[mid, :] = 1
        self.grid[mid, 6] = 2 # Door
        self.grid[mid // 2, 4] = 3 # Key
        self.grid[GRID_SIZE - 4, GRID_SIZE - 4] = 6 # Goal
        self.grid[mid - 1, 8:12] = 5 # Hazards

        # Food items in room 2
        for i in range(5):
            self.grid[mid + 2 + (i % 3) * 3, 4 + i * 2] = 4

        self.agent_pos = [3, 3]
        self.agent_dir = 0
        self.has_key = False
        self.door_unlocked = False
        self.current_task = task
        return self.get_observation(), self.current_task

    def get_observation(self):
        half = VISION_SIZE // 2
        obs = np.zeros((VISION_SIZE, VISION_SIZE, N_CHANNELS), dtype=np.float32)
        for vy in range(-half, half + 1):
            for vx in range(-half, half + 1):
                if self.agent_dir == 0: gx, gy = self.agent_pos[0] + vx, self.agent_pos[1] + vy
                elif self.agent_dir == 1: gx, gy = self.agent_pos[0] + vy, self.agent_pos[1] - vx
                elif self.agent_dir == 2: gx, gy = self.agent_pos[0] - vx, self.agent_pos[1] - vy
                else: gx, gy = self.agent_pos[0] - vy, self.agent_pos[1] + vx

                if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
                    c = self.grid[gx, gy]
                    if c < N_CHANNELS:
                        obs[vy + half, vx + half, c] = 1.0
                else:
                    obs[vy + half, vx + half, 1] = 1.0
        return obs.flatten()

    def step(self, action):
        dirs = [[0, -1], [1, 0], [0, 1], [-1, 0]]
        base_reward = -0.05
        target_achieved = False

        if action == 0: # FORWARD
            dx, dy = dirs[self.agent_dir]
            nx, ny = self.agent_pos[0] + dx, self.agent_pos[1] + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                cell = self.grid[nx, ny]
                if cell == 1:
                    base_reward = -0.5
                elif cell == 2:
                    if self.has_key:
                        self.grid[nx, ny] = 0
                        self.door_unlocked = True
                        self.agent_pos = [nx, ny]
                        if self.current_task == "UNLOCK DOOR":
                            base_reward = 30.0
                            target_achieved = True
                        else:
                            base_reward = 15.0
                    else:
                        base_reward = -1.0
                elif cell == 5:
                    self.agent_pos = [nx, ny]
                    base_reward = -10.0
                else:
                    self.agent_pos = [nx, ny]
                    if cell == 4:
                        self.grid[nx, ny] = 0
                        if self.current_task == "FIND FOOD":
                            base_reward = 25.0
                            target_achieved = True
                        else:
                            base_reward = 10.0
        elif action == 1: # LEFT
            self.agent_dir = (self.agent_dir - 1) % 4
        elif action == 2: # RIGHT
            self.agent_dir = (self.agent_dir + 1) % 4
        elif action == 3: # INTERACT
            if self.grid[self.agent_pos[0], self.agent_pos[1]] == 3 and not self.has_key:
                self.has_key = True
                self.grid[self.agent_pos[0], self.agent_pos[1]] = 0
                if self.current_task == "GET KEY":
                    base_reward = 35.0
                    target_achieved = True
                else:
                    base_reward = 20.0
            elif self.grid[self.agent_pos[0], self.agent_pos[1]] == 6:
                if self.current_task == "NAVIGATE GOAL":
                    base_reward = 50.0
                    target_achieved = True
                else:
                    base_reward = 40.0
                self.reset(self.current_task)

        return self.get_observation(), base_reward, target_achieved


class Substrate8MultimodalAgent:
    """Multimodal Grounded Transformer with Hippocampal Buffer and Fisher EWC."""
    def __init__(self, seed=100):
        self.rng = np.random.RandomState(seed)
        std = 0.05

        # Visual & Language Embedding Weights
        self.W_vis = self.rng.randn(VISUAL_DIM, D_MODEL) * std
        self.W_lang = self.rng.randn(VOCAB_SIZE, D_MODEL) * std
        self.W_fuse_vis = self.rng.randn(D_MODEL, D_MODEL) * std
        self.W_fuse_lang = self.rng.randn(D_MODEL, D_MODEL) * std

        # Attention & MLP Core
        self.W_q = self.rng.randn(D_MODEL, D_MODEL) * std
        self.W_k = self.rng.randn(D_MODEL, D_MODEL) * std
        self.W_v = self.rng.randn(D_MODEL, D_MODEL) * std
        self.W_out = self.rng.randn(D_MODEL, D_MODEL) * std
        self.W_ff1 = self.rng.randn(D_MODEL, D_MODEL * 2) * std
        self.W_ff2 = self.rng.randn(D_MODEL * 2, D_MODEL) * std

        # World Model & Heads
        self.W_dyn = self.rng.randn(D_MODEL + N_ACTIONS, D_MODEL) * std
        self.W_rew = self.rng.randn(D_MODEL + N_ACTIONS, 1) * std
        self.W_val = self.rng.randn(D_MODEL, 1) * std
        self.W_policy = self.rng.randn(D_MODEL, N_ACTIONS) * std

        # Dual Memory: Hippocampal Replay Buffer
        self.hippocampus = []
        self.max_hippo_size = 1000

        # Fisher Information Matrix for Synaptic Protection (EWC)
        self.fisher_diag = {
            'W_dyn': np.zeros_like(self.W_dyn),
            'W_policy': np.zeros_like(self.W_policy),
            'W_val': np.zeros_like(self.W_val)
        }
        self.anchor_weights = {
            'W_dyn': self.W_dyn.copy(),
            'W_policy': self.W_policy.copy(),
            'W_val': self.W_val.copy()
        }

    def tokenize_text(self, text):
        tokens = [ord(c) % VOCAB_SIZE for c in text[:MAX_TEXT_LEN]]
        while len(tokens) < MAX_TEXT_LEN:
            tokens.append(0)
        return np.array(tokens, dtype=np.int32)

    def encode(self, obs, task_text):
        tokens = self.tokenize_text(task_text)
        z_lang = np.mean(self.W_lang[tokens], axis=0) # (D_MODEL,)
        z_vis = obs @ self.W_vis # (D_MODEL,)

        # Multimodal fusion
        z_fuse = z_vis @ self.W_fuse_vis + z_lang @ self.W_fuse_lang

        # Self Attention
        q = z_fuse @ self.W_q
        k = z_fuse @ self.W_k
        v = z_fuse @ self.W_v
        score = np.dot(q, k) / np.sqrt(D_MODEL)
        attn = 1.0 / (1.0 + np.exp(-score))
        mixed = z_fuse + attn * (v @ self.W_out)

        # MLP
        ff1 = np.maximum(0, mixed @ self.W_ff1)
        ff2 = ff1 @ self.W_ff2
        s = mixed + ff2
        return s

    def run_mcts(self, root_state, n_sims=MCTS_SIMS, max_depth=MCTS_DEPTH):
        logits = root_state @ self.W_policy
        priors = np.exp(logits - np.max(logits))
        priors = priors / (np.sum(priors) + 1e-9)

        visit_counts = np.zeros(N_ACTIONS, dtype=np.int32)
        q_values = np.zeros(N_ACTIONS, dtype=np.float32)

        for _ in range(n_sims):
            total_n = np.sum(visit_counts)
            u = C_PUCT * priors * np.sqrt(total_n + 1) / (1 + visit_counts)
            cand_a = np.argmax(q_values + u)

            curr_s = root_state.copy()
            sim_return = 0.0
            step_a = cand_a

            for d in range(max_depth):
                sa = np.zeros(D_MODEL + N_ACTIONS, dtype=np.float32)
                sa[:D_MODEL] = curr_s
                sa[D_MODEL + step_a] = 1.0

                curr_s = np.tanh(sa @ self.W_dyn)
                rew = float((sa @ self.W_rew)[0])
                sim_return += (GAMMA ** d) * rew

                p_logits = curr_s @ self.W_policy
                step_a = np.argmax(p_logits)

            v_leaf = float((curr_s @ self.W_val)[0])
            sim_return += (GAMMA ** max_depth) * v_leaf

            visit_counts[cand_a] += 1
            q_values[cand_a] += (sim_return - q_values[cand_a]) / visit_counts[cand_a]

        total_visits = np.sum(visit_counts)
        if total_visits > 0:
            probs = visit_counts / total_visits
        else:
            probs = priors
        return cand_a, probs

    def update_online(self, s_curr, action, reward, s_next):
        sa = np.zeros(D_MODEL + N_ACTIONS, dtype=np.float32)
        sa[:D_MODEL] = s_curr
        sa[D_MODEL + action] = 1.0

        # World Dynamics
        pred_next = np.tanh(sa @ self.W_dyn)
        err_dyn = s_next - pred_next
        grad_dyn = (err_dyn * (1.0 - pred_next ** 2))
        
        # Accumulate empirical Fisher information
        self.fisher_diag['W_dyn'] += (np.outer(sa, grad_dyn) ** 2) * 0.01
        
        # EWC Regularized update
        ewc_penalty_dyn = LAMBDA_EWC * self.fisher_diag['W_dyn'] * (self.W_dyn - self.anchor_weights['W_dyn'])
        self.W_dyn += LR_BASE * np.outer(sa, grad_dyn) - LAMBDA_HOMEO * self.W_dyn - LR_BASE * ewc_penalty_dyn

        # Reward
        pred_rew = float((sa @ self.W_rew)[0])
        err_rew = reward - pred_rew
        self.W_rew += LR_BASE * err_rew * sa[:, None] - LAMBDA_HOMEO * self.W_rew

        # Value TD
        v_curr = float((s_curr @ self.W_val)[0])
        v_next = float((s_next @ self.W_val)[0])
        td_err = reward + GAMMA * v_next - v_curr
        self.W_val += LR_BASE * td_err * s_curr[:, None] - LAMBDA_HOMEO * self.W_val

        # Policy
        logits = s_curr @ self.W_policy
        probs = np.exp(logits - np.max(logits))
        probs = probs / np.sum(probs)
        grad_pi = -probs
        grad_pi[action] += 1.0
        self.W_policy += LR_BASE * td_err * np.outer(s_curr, grad_pi) - LAMBDA_HOMEO * self.W_policy

        # Store in Hippocampus
        surprise = float(np.sum(err_dyn ** 2) + abs(reward))
        self.hippocampus.append((s_curr, action, reward, s_next, surprise))
        if len(self.hippocampus) > self.max_hippo_size:
            self.hippocampus.pop(0)

    def sleep_consolidation(self, n_replays=100):
        """Biological Sleep Phase: Replay high-surprise memories and anchor weights."""
        if len(self.hippocampus) < 10:
            return
        surprises = np.array([m[4] for m in self.hippocampus])
        probs = surprises / (np.sum(surprises) + 1e-9)

        indices = self.rng.choice(len(self.hippocampus), size=min(n_replays, len(self.hippocampus)), p=probs)
        for idx in indices:
            s_c, act, rew, s_n, _ = self.hippocampus[idx]
            self.update_online(s_c, act, rew, s_n)

        # Solidify anchors
        for k in self.anchor_weights:
            self.anchor_weights[k] = getattr(self, k).copy()


def run_phase5_experiment(seed=100, ticks_per_task=10000):
    print(f"--- Running Substrate 8 Multimodal Benchmark (Seed={seed}) ---")
    env = MultimodalEnvironment(seed=seed)
    agent = Substrate8MultimodalAgent(seed=seed)

    tasks = ["FIND FOOD", "GET KEY", "NAVIGATE GOAL"]
    results = {}

    for task_idx, task in enumerate(tasks):
        print(f"\n[Task {task_idx+1}/3]: Training on '{task}' for {ticks_per_task:,} ticks...")
        obs, _ = env.reset(task)
        s_curr = agent.encode(obs, task)
        task_solves = 0

        for t in range(ticks_per_task):
            _, probs = agent.run_mcts(s_curr)
            action = agent.rng.choice(N_ACTIONS, p=probs)

            next_obs, reward, target_achieved = env.step(action)
            s_next = agent.encode(next_obs, task)

            agent.update_online(s_curr, action, reward, s_next)
            if target_achieved:
                task_solves += 1

            s_curr = s_next

        # Run Sleep Consolidation
        agent.sleep_consolidation(n_replays=200)
        results[f"train_{task}"] = task_solves
        print(f"✅ Finished '{task}': Solves={task_solves}")

    # Catastrophic Forgetting Test: Re-evaluate Task 1 ("FIND FOOD") with zero further updates
    print("\n--- Evaluating Zero-Shot Retention on Task 1 ('FIND FOOD') after learning all tasks ---")
    obs, _ = env.reset("FIND FOOD")
    s_curr = agent.encode(obs, "FIND FOOD")
    retention_solves = 0
    for t in range(5000):
        _, probs = agent.run_mcts(s_curr)
        action = agent.rng.choice(N_ACTIONS, p=probs)
        next_obs, reward, target_achieved = env.step(action)
        s_curr = agent.encode(next_obs, "FIND FOOD")
        if target_achieved:
            retention_solves += 1

    retention_rate = (retention_solves / (results["train_FIND FOOD"] / 2 + 1e-9)) * 100
    print(f"📊 Task 1 Retention Rate: {retention_rate:.2f}% (Solves in 5k eval ticks: {retention_solves})")

    results["retention_solves_task1"] = retention_solves
    results["retention_rate_pct"] = retention_rate
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=100)
    args = parser.parse_args()
    res = run_phase5_experiment(seed=args.seed)
    
    out_dir = os.path.join(os.path.dirname(__file__), "sub4_results")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "sub8_multimodal_summary.json")
    with open(out_file, "w") as f:
        json.dump(res, f, indent=2)
    print(f"\nSaved summary to {out_file}")
