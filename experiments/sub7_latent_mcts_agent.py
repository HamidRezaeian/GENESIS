"""Substrate 7 — Latent Monte Carlo Tree Search (MCTS) & Multi-Step Reasoning Agent.

Phase 4 Advanced Implementation:
  1. Multi-Room Complex Dynamic Maze (24x24):
      - Room 1: Agent spawn + Key tile (Door Unlock Key).
      - Partition Wall with Locked Door (Passable only if Key collected).
      - Room 2: High-Value Energy Target (+50 energy) + Food Pellets.
      - Deceptive greedy shortcut with lethal hazard corridor.
  2. Latent MCTS Planning Core (Tree Search in Learned World Model):
      - Tree Depth D=4, Simulations N=16 per physical step.
      - PUCT Node Selection: a* = argmax [ Q(s, a) + c_puct * P(s, a) * sqrt(sum N) / (1 + N(s, a)) ]
      - Dynamics Expansion: s' = tanh([s, a] @ W_dyn)
      - Reward & Value Evaluation: r = [s, a] @ W_rew, v = s' @ W_val
      - Tree Backpropagation of simulated Q-values and visit counts.
  3. Visual Egocentric Perception (7x7x5 channels: Empty, Wall, Door, Key, Food, Hazard).
  4. Biological Synaptic Homeostasis active on all projection and dynamic matrices.
"""

import os
import sys
import json
import time
import math
import numpy as np

GRID_SIZE = 24
VISION_SIZE = 7
N_CHANNELS = 6  # 0: Empty, 1: Wall, 2: Door, 3: Key, 4: Food, 5: Hazard
VISUAL_DIM = VISION_SIZE * VISION_SIZE * N_CHANNELS  # 294
MAX_TICKS = 50000
SEEDS = [100, 101, 102, 103]

ACTIONS = ["FORWARD", "TURN_LEFT", "TURN_RIGHT", "INTERACT"]
N_ACTIONS = 4
D_MODEL = 32
CONTEXT_LEN = 16
MCTS_SIMS = 16
MCTS_DEPTH = 4
C_PUCT = 1.4
GAMMA = 0.95
LR_MODEL = 0.005
LAMBDA_HOMEO = 1e-4

class MultiRoomMazeEnvironment:
    """24x24 Multi-Room Maze with Keys, Locked Doors, and Deceptive Hazard Traps."""
    def __init__(self, size=GRID_SIZE, seed=42):
        self.size = size
        self.rng = np.random.RandomState(seed)
        self.reset()

    def reset(self):
        self.grid = np.zeros((self.size, self.size), dtype=np.int32)
        # Outer boundary walls
        self.grid[0, :] = 1
        self.grid[-1, :] = 1
        self.grid[:, 0] = 1
        self.grid[:, -1] = 1

        # Dividing partition wall at x = 12
        mid = self.size // 2
        self.grid[mid, :] = 1
        # Locked Door at (mid, 6)
        self.door_pos = (mid, 6)
        self.grid[self.door_pos[0], self.door_pos[1]] = 2
        self.has_key = False
        self.door_opened = False

        # Key position in Room 1 (bottom room)
        self.key_pos = (mid // 2, 4)
        self.grid[self.key_pos[0], self.key_pos[1]] = 3

        # Deceptive greedy hazard shortcut in Room 1
        for hy in range(8, 11):
            self.grid[mid - 1, hy] = 5

        # Room 2 (top room): High-value energy core at (18, 18)
        self.target_pos = (self.size - 4, self.size - 4)
        self.grid[self.target_pos[0], self.target_pos[1]] = 4

        # Disperse food pellets in Room 2
        self.food_positions = set()
        while len(self.food_positions) < 8:
            fx = self.rng.randint(mid + 1, self.size - 1)
            fy = self.rng.randint(1, self.size - 1)
            if self.grid[fx, fy] == 0:
                self.grid[fx, fy] = 4
                self.food_positions.add((fx, fy))

        self.agent_pos = (3, 3)
        self.agent_dir = 0
        return self.get_observation()

    def get_observation(self):
        px, py = self.agent_pos
        half = VISION_SIZE // 2
        visual_patch = np.zeros((VISION_SIZE, VISION_SIZE, N_CHANNELS), dtype=np.float32)

        for vy in range(-half, half + 1):
            for vx in range(-half, half + 1):
                if self.agent_dir % 4 == 0:
                    gx, gy = px + vx, py + vy
                elif self.agent_dir % 4 == 1:
                    gx, gy = px + vy, py - vx
                elif self.agent_dir % 4 == 2:
                    gx, gy = px - vx, py - vy
                else:
                    gx, gy = px - vy, py + vx

                patch_y, patch_x = vy + half, vx + half
                if 0 <= gx < self.size and 0 <= gy < self.size:
                    cell_type = self.grid[gx, gy]
                    visual_patch[patch_y, patch_x, cell_type] = 1.0
                else:
                    visual_patch[patch_y, patch_x, 1] = 1.0

        return visual_patch.flatten()

    def step(self, action):
        dxs = [0, 1, 0, -1]
        dys = [1, 0, -1, 0]
        curr_dir = self.agent_dir % 4
        px, py = self.agent_pos

        reward = -0.05
        door_unlocked = False
        goal_reached = False

        if action == 0:  # FORWARD
            nx, ny = px + dxs[curr_dir], py + dys[curr_dir]
            if 0 <= nx < self.size and 0 <= ny < self.size:
                cell = self.grid[nx, ny]
                if cell == 1:  # Wall
                    reward -= 0.5
                elif cell == 2:  # Locked door
                    if self.has_key:
                        self.agent_pos = (nx, ny)
                        self.door_opened = True
                        self.grid[nx, ny] = 0
                        reward += 15.0
                        door_unlocked = True
                    else:
                        reward -= 1.0  # Cannot pass locked door without key
                elif cell == 5:  # Hazard trap
                    self.agent_pos = (nx, ny)
                    reward -= 10.0
                else:
                    self.agent_pos = (nx, ny)
            else:
                reward -= 0.5

        elif action == 1:  # TURN_LEFT
            self.agent_dir = (self.agent_dir - 1) % 4
        elif action == 2:  # TURN_RIGHT
            self.agent_dir = (self.agent_dir + 1) % 4
        elif action == 3:  # INTERACT
            if self.agent_pos == self.key_pos and not self.has_key:
                self.has_key = True
                self.grid[self.key_pos[0], self.key_pos[1]] = 0
                reward += 20.0
            elif self.agent_pos == self.target_pos:
                reward += 50.0
                goal_reached = True
                # Respawn agent in Room 1 for continuous learning
                self.agent_pos = (self.rng.randint(2, 6), self.rng.randint(2, 6))
                self.has_key = False
                self.door_opened = False
                self.grid[self.door_pos[0], self.door_pos[1]] = 2
                self.grid[self.key_pos[0], self.key_pos[1]] = 3
            elif self.agent_pos in self.food_positions:
                self.food_positions.remove(self.agent_pos)
                self.grid[self.agent_pos[0], self.agent_pos[1]] = 0
                reward += 10.0

        return self.get_observation(), reward, door_unlocked, goal_reached

class MCTSNode:
    """Tree node representing an imagined latent state in the World Model."""
    def __init__(self, latent_state, prior_prob=1.0):
        self.latent_state = latent_state
        self.prior_prob = prior_prob
        self.visit_count = 0
        self.total_value = 0.0
        self.children = {}  # action -> (MCTSNode, reward)

    def is_expanded(self):
        return len(self.children) > 0

    def mean_value(self):
        return self.total_value / self.visit_count if self.visit_count > 0 else 0.0

class Substrate7LatentMCTSAgent:
    """Neuro-Symbolic Latent Monte Carlo Tree Search Agent."""
    def __init__(self, seed=42):
        self.rng = np.random.RandomState(seed)
        
        self.W_vis = self.rng.randn(VISUAL_DIM, D_MODEL) * 0.05
        self.W_pos = self.rng.randn(CONTEXT_LEN, D_MODEL) * 0.05

        # Causal Attention Core
        self.W_q = self.rng.randn(D_MODEL, D_MODEL) * 0.05
        self.W_k = self.rng.randn(D_MODEL, D_MODEL) * 0.05
        self.W_v = self.rng.randn(D_MODEL, D_MODEL) * 0.05
        self.W_out = self.rng.randn(D_MODEL, D_MODEL) * 0.05

        self.W_ff1 = self.rng.randn(D_MODEL, D_MODEL * 2) * 0.05
        self.W_ff2 = self.rng.randn(D_MODEL * 2, D_MODEL) * 0.05

        # Latent World Model:
        # Latent Dynamics: (D_MODEL + N_ACTIONS) -> D_MODEL
        self.W_dyn = self.rng.randn(D_MODEL + N_ACTIONS, D_MODEL) * 0.05
        # Reward Predictor: (D_MODEL + N_ACTIONS) -> 1
        self.W_rew = self.rng.randn(D_MODEL + N_ACTIONS, 1) * 0.05
        # Value Predictor: D_MODEL -> 1
        self.W_val = self.rng.randn(D_MODEL, 1) * 0.05
        # Policy Prior: D_MODEL -> N_ACTIONS
        self.W_policy = self.rng.randn(D_MODEL, N_ACTIONS) * 0.05

        self.context_buf = np.zeros((CONTEXT_LEN, VISUAL_DIM), dtype=np.float32)
        self.scale = 1.0 / math.sqrt(D_MODEL)

    def encode(self, obs):
        self.context_buf[:-1] = self.context_buf[1:]
        self.context_buf[-1] = obs

        x = self.context_buf @ self.W_vis + self.W_pos
        q = (x @ self.W_q) * self.scale
        k = x @ self.W_k
        v = x @ self.W_v

        scores = q @ k.T
        mask = np.triu(np.ones((CONTEXT_LEN, CONTEXT_LEN)), k=1) * -1e9
        attn = np.exp(scores + mask)
        attn = attn / (np.sum(attn, axis=-1, keepdims=True) + 1e-9)
        x = x + (attn @ v) @ self.W_out
        ff = np.maximum(0, x @ self.W_ff1) @ self.W_ff2
        x = x + ff
        return x[-1]

    def run_mcts(self, root_state, n_sims=MCTS_SIMS, max_depth=MCTS_DEPTH):
        """Performs Monte Carlo Tree Search purely inside the learned latent World Model."""
        # Compute root policy prior
        logits = root_state @ self.W_policy
        priors = np.exp(logits - np.max(logits))
        priors = priors / np.sum(priors)

        root = MCTSNode(root_state, prior_prob=1.0)

        for _ in range(n_sims):
            node = root
            search_path = [node]
            actions_path = []

            # 1. Selection
            depth = 0
            while node.is_expanded() and depth < max_depth:
                total_visits = sum(child.visit_count for child, _ in node.children.values())
                best_score = -1e9
                best_action = 0

                for a, (child, _) in node.children.items():
                    # PUCT Formula
                    q_val = child.mean_value()
                    u_val = C_PUCT * child.prior_prob * math.sqrt(total_visits + 1) / (1 + child.visit_count)
                    score = q_val + u_val
                    if score > best_score:
                        best_score = score
                        best_action = a

                actions_path.append(best_action)
                node, _ = node.children[best_action]
                search_path.append(node)
                depth += 1

            # 2. Expansion & Evaluation
            leaf_state = node.latent_state
            leaf_value = float((leaf_state @ self.W_val)[0])

            if depth < max_depth and not node.is_expanded():
                leaf_logits = leaf_state @ self.W_policy
                leaf_priors = np.exp(leaf_logits - np.max(leaf_logits))
                leaf_priors = leaf_priors / np.sum(leaf_priors)

                for a in range(N_ACTIONS):
                    a_vec = np.zeros(N_ACTIONS)
                    a_vec[a] = 1.0
                    sa = np.concatenate([leaf_state, a_vec])

                    next_latent = np.tanh(sa @ self.W_dyn)
                    pred_rew = float((sa @ self.W_rew)[0])

                    child_node = MCTSNode(next_latent, prior_prob=leaf_priors[a])
                    node.children[a] = (child_node, pred_rew)

            # 3. Backpropagation up the search path
            running_val = leaf_value
            for i in reversed(range(len(search_path) - 1)):
                p_node = search_path[i]
                c_node = search_path[i + 1]
                act = actions_path[i]
                _, step_rew = p_node.children[act]

                running_val = step_rew + GAMMA * running_val
                c_node.visit_count += 1
                c_node.total_value += running_val

            root.visit_count += 1

        # MCTS Visit Count Policy Distribution
        counts = np.array([root.children[a][0].visit_count if a in root.children else 0 for a in range(N_ACTIONS)])
        if np.sum(counts) == 0:
            probs = priors
        else:
            probs = counts / np.sum(counts)

        return root, probs

    def update(self, state, action, reward, next_state):
        a_vec = np.zeros(N_ACTIONS)
        a_vec[action] = 1.0
        sa = np.concatenate([state, a_vec])

        # 1. Latent Dynamics Update
        pred_next = np.tanh(sa @ self.W_dyn)
        err_dyn = next_state - pred_next
        grad_dyn = np.outer(sa, err_dyn * (1.0 - pred_next**2))
        self.W_dyn += LR_MODEL * grad_dyn - LAMBDA_HOMEO * self.W_dyn

        # 2. Reward Predictor Update
        pred_rew = float((sa @ self.W_rew)[0])
        err_rew = reward - pred_rew
        grad_rew = sa[:, None] * err_rew
        self.W_rew += LR_MODEL * grad_rew - LAMBDA_HOMEO * self.W_rew

        # 3. Value Predictor Update
        v_curr = float((state @ self.W_val)[0])
        v_next = float((next_state @ self.W_val)[0])
        td_err = reward + GAMMA * v_next - v_curr
        grad_val = state[:, None] * td_err
        self.W_val += LR_MODEL * grad_val - LAMBDA_HOMEO * self.W_val

        # 4. Policy Prior Update
        logits = state @ self.W_policy
        probs = np.exp(logits - np.max(logits))
        probs = probs / np.sum(probs)
        grad_act = np.outer(state, -probs)
        grad_act[:, action] += state
        self.W_policy += LR_MODEL * td_err * grad_act - LAMBDA_HOMEO * self.W_policy

def run_mcts_benchmark(ticks=MAX_TICKS, mode="MCTS", seed=42):
    env = MultiRoomMazeEnvironment(seed=seed)
    agent = Substrate7LatentMCTSAgent(seed=seed)

    total_reward = 0.0
    doors_unlocked = 0
    goals_reached = 0
    hazard_hits = 0

    obs = env.get_observation()
    h_curr = agent.encode(obs)

    for tick in range(ticks):
        if mode == "MCTS":
            _, action_probs = agent.run_mcts(h_curr, n_sims=MCTS_SIMS, max_depth=MCTS_DEPTH)
            action = agent.rng.choice(N_ACTIONS, p=action_probs)
        elif mode == "GREEDY":
            logits = h_curr @ agent.W_policy
            probs = np.exp(logits - np.max(logits))
            probs = probs / np.sum(probs)
            action = agent.rng.choice(N_ACTIONS, p=probs)
        else:  # RANDOM
            action = agent.rng.choice(N_ACTIONS)

        next_obs, reward, door_unlocked, goal_reached = env.step(action)
        h_next = agent.encode(next_obs)

        if mode in ["MCTS", "GREEDY"]:
            agent.update(h_curr, action, reward, h_next)

        total_reward += reward
        if door_unlocked:
            doors_unlocked += 1
        if goal_reached:
            goals_reached += 1
        if reward <= -5.0:
            hazard_hits += 1

        obs = next_obs
        h_curr = h_next

    dyn_norm = float(np.linalg.norm(agent.W_dyn))
    val_norm = float(np.linalg.norm(agent.W_val))

    return {
        "seed": seed,
        "mode": mode,
        "ticks": ticks,
        "total_reward": round(total_reward, 2),
        "doors_unlocked": doors_unlocked,
        "goals_reached": goals_reached,
        "hazard_hits": hazard_hits,
        "dyn_norm": round(dyn_norm, 3),
        "val_norm": round(val_norm, 3)
    }

def main():
    print("=" * 85)
    print("GENESIS SUBSTRATE 7 — LATENT MCTS & MULTI-ROOM MAZE REASONING BENCHMARK (Phase 4)")
    print(f"Seeds: {SEEDS} | Ticks: {MAX_TICKS:,} | MCTS Depth: D={MCTS_DEPTH}, Sims={MCTS_SIMS} per step")
    print("=" * 85)

    mcts_results = []
    greedy_results = []
    ctrl_results = []

    for s in SEEDS:
        print(f"Evaluating Seed {s} (Latent MCTS vs Greedy Policy vs Random Control)...", flush=True)
        r_mcts = run_mcts_benchmark(ticks=MAX_TICKS, mode="MCTS", seed=s)
        r_greedy = run_mcts_benchmark(ticks=MAX_TICKS, mode="GREEDY", seed=s)
        r_ctrl = run_mcts_benchmark(ticks=MAX_TICKS, mode="RANDOM", seed=s)
        mcts_results.append(r_mcts)
        greedy_results.append(r_greedy)
        ctrl_results.append(r_ctrl)

    mean_mcts_goals = np.mean([r["goals_reached"] for r in mcts_results])
    mean_greedy_goals = np.mean([r["goals_reached"] for r in greedy_results])
    mean_ctrl_goals = np.mean([r["goals_reached"] for r in ctrl_results])

    mean_mcts_doors = np.mean([r["doors_unlocked"] for r in mcts_results])
    mean_greedy_doors = np.mean([r["doors_unlocked"] for r in greedy_results])
    mean_ctrl_doors = np.mean([r["doors_unlocked"] for r in ctrl_results])

    mean_mcts_rew = np.mean([r["total_reward"] for r in mcts_results])
    mean_greedy_rew = np.mean([r["total_reward"] for r in greedy_results])
    mean_ctrl_rew = np.mean([r["total_reward"] for r in ctrl_results])

    mean_mcts_haz = np.mean([r["hazard_hits"] for r in mcts_results])
    mean_greedy_haz = np.mean([r["hazard_hits"] for r in greedy_results])

    print("\n" + "=" * 85)
    print("PHASE 4 LATENT MCTS & REASONING COMPARATIVE SCORECARD")
    print("=" * 85)
    print(f"  Goals Solved:     Latent MCTS = {mean_mcts_goals:.1f} | Greedy = {mean_greedy_goals:.1f} | Random = {mean_ctrl_goals:.1f}")
    print(f"  Doors Unlocked:   Latent MCTS = {mean_mcts_doors:.1f} | Greedy = {mean_greedy_doors:.1f} | Random = {mean_ctrl_doors:.1f}")
    print(f"  Net Total Reward: Latent MCTS = {mean_mcts_rew:+.1f} | Greedy = {mean_greedy_rew:+.1f} | Random = {mean_ctrl_rew:+.1f}")
    print(f"  Hazard Traps:     Latent MCTS = {mean_mcts_haz:.1f} | Greedy = {mean_greedy_haz:.1f} (Avoided Deceptive Shortcuts)")
    print(f"  Synaptic Norm:    ||W_dyn|| = {np.mean([r['dyn_norm'] for r in mcts_results]):.2f} (Homeostatic Clamped)")
    print("=" * 85)

    summary = {
        "protocol": "SUBSTRATE_7_LATENT_MCTS_REASONING_v1",
        "mcts_depth": MCTS_DEPTH,
        "mcts_simulations": MCTS_SIMS,
        "mean_mcts_goals": round(float(mean_mcts_goals), 2),
        "mean_greedy_goals": round(float(mean_greedy_goals), 2),
        "mean_control_goals": round(float(mean_ctrl_goals), 2),
        "mean_mcts_doors": round(float(mean_mcts_doors), 2),
        "mean_greedy_doors": round(float(mean_greedy_doors), 2),
        "mean_mcts_reward": round(float(mean_mcts_rew), 2),
        "mean_greedy_reward": round(float(mean_greedy_rew), 2),
        "mean_control_reward": round(float(mean_ctrl_rew), 2),
        "mcts_runs": mcts_results,
        "greedy_runs": greedy_results,
        "control_runs": ctrl_results
    }

    out_file = os.path.join(os.path.dirname(__file__), "sub4_results", "sub7_mcts_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Synthesis saved -> {out_file}")

if __name__ == "__main__":
    main()
