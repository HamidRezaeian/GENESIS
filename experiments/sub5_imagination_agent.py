r"""Substrate 5-I — World Model Imagination & Multi-Step Latent Planning Agent.

Phase 2 / 3 Advanced Implementation:
  - 2D Dynamic GridWorld with spatial obstacles, food pellets (+10 energy), and hazard traps (-5 energy).
  - Multi-Step Mental Simulation / Imagination Planning Loop (Horizon H=3).
  - Dual Architecture:
      1. Latent Causal Transformer: h_t = Transformer(o_{1:t})
      2. World Dynamics Model: \hat{o}_{t+1} = W_dyn([h_t, a_t])
      3. Latent Reward Predictor: \hat{r}_{t+1} = W_rew([h_t, a_t])
      4. Value Critic: \hat{V}(h_t) = W_val(h_t)
  - Before taking a physical step, the agent simulates 3 steps into the future for all 4 candidate actions,
    evaluating Q_imagined(a) = \sum_{k=1}^H \gamma^{k-1} \hat{r}_{t+k} + \gamma^H \hat{V}(\hat{h}_{t+H}).
  - Biological Synaptic Homeostasis active on all projection matrices.
"""

import os
import sys
import json
import time
import math
import numpy as np

GRID_SIZE = 16
MAX_TICKS = 50000
SEEDS = [100, 101, 102, 103]
IMAGINATION_HORIZON = 3
GAMMA = 0.95

ACTIONS = ["FORWARD", "TURN_LEFT", "TURN_RIGHT", "EAT"]
N_ACTIONS = 4
SENSORY_DIM = 24  # 8 raycast directions x 3 channels
D_MODEL = 32
CONTEXT_LEN = 16
LR_MODEL = 0.005
LAMBDA_HOMEO = 1e-4

class EmbodiedGridEnvironment:
    """2D Dynamic Physical GridWorld Environment."""
    def __init__(self, size=GRID_SIZE, n_food=12, n_hazards=6, seed=42):
        self.size = size
        self.n_food = n_food
        self.n_hazards = n_hazards
        self.rng = np.random.RandomState(seed)
        self.reset()

    def reset(self):
        self.grid = np.zeros((self.size, self.size), dtype=np.int32)
        # 0: empty, 1: wall, 2: food, 3: hazard
        self.grid[0, :] = 1
        self.grid[-1, :] = 1
        self.grid[:, 0] = 1
        self.grid[:, -1] = 1

        for _ in range(self.size // 2):
            rx, ry = self.rng.randint(2, self.size - 2, 2)
            self.grid[rx, ry] = 1

        self.food_positions = set()
        while len(self.food_positions) < self.n_food:
            fx, fy = self.rng.randint(1, self.size - 1, 2)
            if self.grid[fx, fy] == 0:
                self.grid[fx, fy] = 2
                self.food_positions.add((fx, fy))

        self.hazard_positions = set()
        while len(self.hazard_positions) < self.n_hazards:
            hx, hy = self.rng.randint(1, self.size - 1, 2)
            if self.grid[hx, hy] == 0:
                self.grid[hx, hy] = 3
                self.hazard_positions.add((hx, hy))

    def get_raycast_sensor(self, pos, direction):
        directions = [
            (0, 1), (1, 1), (1, 0), (1, -1),
            (0, -1), (-1, -1), (-1, 0), (-1, 1)
        ]
        dir_idx = direction % 8
        rot_dirs = directions[dir_idx:] + directions[:dir_idx]

        sensor = np.zeros((8, 3), dtype=np.float32)
        px, py = pos

        for i, (dx, dy) in enumerate(rot_dirs):
            dist_wall = self.size
            dist_food = self.size
            dist_hazard = self.size

            for step in range(1, self.size):
                cx, cy = px + dx * step, py + dy * step
                if cx < 0 or cx >= self.size or cy < 0 or cy >= self.size:
                    dist_wall = min(dist_wall, step)
                    break
                cell = self.grid[cx, cy]
                if cell == 1 and dist_wall == self.size:
                    dist_wall = step
                    break
                elif cell == 2 and dist_food == self.size:
                    dist_food = step
                elif cell == 3 and dist_hazard == self.size:
                    dist_hazard = step

            sensor[i, 0] = 1.0 / float(dist_wall)
            sensor[i, 1] = 1.0 / float(dist_food)
            sensor[i, 2] = 1.0 / float(dist_hazard)

        return sensor.flatten()

    def step(self, pos, direction, action):
        dxs = [0, 1, 0, -1]
        dys = [1, 0, -1, 0]
        curr_dir = direction % 4
        px, py = pos

        reward = -0.05  # Base metabolic cost
        food_eaten = False

        if action == 0:  # FORWARD
            nx, ny = px + dxs[curr_dir], py + dys[curr_dir]
            if 0 <= nx < self.size and 0 <= ny < self.size and self.grid[nx, ny] != 1:
                pos = (nx, ny)
                if self.grid[nx, ny] == 3:  # Hazard
                    reward -= 5.0
            else:
                reward -= 0.5  # Bump into wall
        elif action == 1:  # TURN_LEFT
            direction = (direction - 1) % 4
        elif action == 2:  # TURN_RIGHT
            direction = (direction + 1) % 4
        elif action == 3:  # EAT
            if pos in self.food_positions:
                self.food_positions.remove(pos)
                self.grid[pos[0], pos[1]] = 0
                reward += 10.0
                food_eaten = True
                while len(self.food_positions) < self.n_food:
                    fx, fy = self.rng.randint(1, self.size - 1, 2)
                    if self.grid[fx, fy] == 0:
                        self.grid[fx, fy] = 2
                        self.food_positions.add((fx, fy))

        return pos, direction, reward, food_eaten

class Substrate5ImaginationAgent:
    """Embodied Causal Transformer with Multi-Step Latent Mental Simulation."""
    def __init__(self, seed=42):
        self.rng = np.random.RandomState(seed)
        self.W_in = self.rng.randn(SENSORY_DIM, D_MODEL) * 0.1
        self.W_pos = self.rng.randn(CONTEXT_LEN, D_MODEL) * 0.05

        # Causal Attention weights
        self.W_q = self.rng.randn(D_MODEL, D_MODEL) * 0.1
        self.W_k = self.rng.randn(D_MODEL, D_MODEL) * 0.1
        self.W_v = self.rng.randn(D_MODEL, D_MODEL) * 0.1
        self.W_out = self.rng.randn(D_MODEL, D_MODEL) * 0.1

        # MLP
        self.W_ff1 = self.rng.randn(D_MODEL, D_MODEL * 2) * 0.1
        self.W_ff2 = self.rng.randn(D_MODEL * 2, D_MODEL) * 0.1

        # Model Heads:
        # 1. Dynamics: (D_MODEL + N_ACTIONS) -> SENSORY_DIM
        self.W_dyn = self.rng.randn(D_MODEL + N_ACTIONS, SENSORY_DIM) * 0.1
        # 2. Reward Predictor: (D_MODEL + N_ACTIONS) -> 1
        self.W_rew = self.rng.randn(D_MODEL + N_ACTIONS, 1) * 0.1
        # 3. Value Critic: D_MODEL -> 1
        self.W_val = self.rng.randn(D_MODEL, 1) * 0.1
        # 4. Default Policy: D_MODEL -> N_ACTIONS
        self.W_actor = self.rng.randn(D_MODEL, N_ACTIONS) * 0.1

        self.context_buf = np.zeros((CONTEXT_LEN, SENSORY_DIM), dtype=np.float32)
        self.scale = 1.0 / math.sqrt(D_MODEL)

    def encode(self, obs, context_history=None):
        if context_history is None:
            buf = np.copy(self.context_buf)
            buf[:-1] = buf[1:]
            buf[-1] = obs
        else:
            buf = np.copy(context_history)
            buf[:-1] = buf[1:]
            buf[-1] = obs

        x = buf @ self.W_in + self.W_pos
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
        return x[-1], buf

    def evaluate_imagination(self, obs, horizon=IMAGINATION_HORIZON):
        """Simulates candidate action trajectories H steps ahead in imagination."""
        h_0, buf_0 = self.encode(obs)
        q_values = np.zeros(N_ACTIONS, dtype=np.float32)

        for candidate_a in range(N_ACTIONS):
            total_imagined_val = 0.0
            curr_h = np.copy(h_0)
            curr_buf = np.copy(buf_0)
            curr_a = candidate_a

            for step_k in range(horizon):
                a_vec = np.zeros(N_ACTIONS)
                a_vec[curr_a] = 1.0
                state_action = np.concatenate([curr_h, a_vec])

                pred_obs = np.tanh(state_action @ self.W_dyn)
                pred_rew = float((state_action @ self.W_rew)[0])
                total_imagined_val += (GAMMA ** step_k) * pred_rew

                if step_k < horizon - 1:
                    curr_h, curr_buf = self.encode(pred_obs, curr_buf)
                    curr_a = int(np.argmax(curr_h @ self.W_actor))
                else:
                    pred_v = float((curr_h @ self.W_val)[0])
                    total_imagined_val += (GAMMA ** horizon) * pred_v

            q_values[candidate_a] = total_imagined_val

        # Softmax choice over imagined Q-values
        exps = np.exp((q_values - np.max(q_values)) * 2.0)
        probs = exps / (np.sum(exps) + 1e-9)
        return h_0, q_values, probs

    def update_models(self, h_t, action, actual_next_obs, actual_reward, next_h):
        a_vec = np.zeros(N_ACTIONS)
        a_vec[action] = 1.0
        state_action = np.concatenate([h_t, a_vec])

        # 1. World Dynamics Update (MSE)
        pred_obs = np.tanh(state_action @ self.W_dyn)
        err_obs = actual_next_obs - pred_obs
        grad_dyn = np.outer(state_action, err_obs * (1.0 - pred_obs**2))
        self.W_dyn += LR_MODEL * grad_dyn - LAMBDA_HOMEO * self.W_dyn

        # 2. Reward Predictor Update
        pred_rew = float((state_action @ self.W_rew)[0])
        err_rew = actual_reward - pred_rew
        grad_rew = state_action[:, None] * err_rew
        self.W_rew += LR_MODEL * grad_rew - LAMBDA_HOMEO * self.W_rew

        # 3. Value Critic Update (TD Error)
        v_curr = float((h_t @ self.W_val)[0])
        v_next = float((next_h @ self.W_val)[0])
        td_err = actual_reward + GAMMA * v_next - v_curr
        grad_val = h_t[:, None] * td_err
        self.W_val += LR_MODEL * grad_val - LAMBDA_HOMEO * self.W_val

        # 4. Policy Update
        logits = h_t @ self.W_actor
        probs = np.exp(logits - np.max(logits))
        probs = probs / np.sum(probs)
        grad_act = np.outer(h_t, -probs)
        grad_act[:, action] += h_t
        self.W_actor += LR_MODEL * td_err * grad_act - LAMBDA_HOMEO * self.W_actor

def run_imagination_benchmark(ticks=MAX_TICKS, mode="IMAGINATION", seed=42):
    env = EmbodiedGridEnvironment(seed=seed)
    agent = Substrate5ImaginationAgent(seed=seed)

    pos = (GRID_SIZE // 2, GRID_SIZE // 2)
    direction = 0

    total_reward = 0.0
    total_food = 0
    total_hazard_hits = 0
    total_imagined_err = 0.0

    obs = env.get_raycast_sensor(pos, direction)

    for tick in range(ticks):
        if mode == "IMAGINATION":
            h_t, q_vals, action_probs = agent.evaluate_imagination(obs, horizon=IMAGINATION_HORIZON)
            action = agent.rng.choice(N_ACTIONS, p=action_probs)
        elif mode == "REACTIVE":
            h_t, _ = agent.encode(obs)
            logits = h_t @ agent.W_actor
            probs = np.exp(logits - np.max(logits))
            probs = probs / np.sum(probs)
            action = agent.rng.choice(N_ACTIONS, p=probs)
        else:  # RANDOM
            h_t, _ = agent.encode(obs)
            action = agent.rng.choice(N_ACTIONS)

        # Execute in real environment
        next_pos, next_direction, reward, food_eaten = env.step(pos, direction, action)
        next_obs = env.get_raycast_sensor(next_pos, next_direction)

        # Encode next state
        next_h, _ = agent.encode(next_obs)

        # Update models if active learner
        if mode in ["IMAGINATION", "REACTIVE"]:
            agent.update_models(h_t, action, next_obs, reward, next_h)

        # Commit context buffer
        agent.context_buf[:-1] = agent.context_buf[1:]
        agent.context_buf[-1] = obs

        total_reward += reward
        if food_eaten:
            total_food += 1
        if reward <= -5.0:
            total_hazard_hits += 1

        pos = next_pos
        direction = next_direction
        obs = next_obs

    dyn_norm = float(np.linalg.norm(agent.W_dyn))
    val_norm = float(np.linalg.norm(agent.W_val))

    return {
        "seed": seed,
        "mode": mode,
        "ticks": ticks,
        "total_reward": round(total_reward, 2),
        "food_collected": total_food,
        "hazard_hits": total_hazard_hits,
        "dyn_norm": round(dyn_norm, 3),
        "val_norm": round(val_norm, 3)
    }

def main():
    print("=" * 80)
    print("GENESIS SUBSTRATE 5-I — WORLD MODEL IMAGINATION & MENTAL SIMULATION BENCHMARK")
    print(f"Seeds: {SEEDS} | Ticks: {MAX_TICKS:,} | Horizon: H={IMAGINATION_HORIZON} steps ahead")
    print("=" * 80)

    imag_results = []
    react_results = []
    ctrl_results = []

    for s in SEEDS:
        print(f"Evaluating Seed {s} across 3 Arms...", flush=True)
        r_imag = run_imagination_benchmark(ticks=MAX_TICKS, mode="IMAGINATION", seed=s)
        r_react = run_imagination_benchmark(ticks=MAX_TICKS, mode="REACTIVE", seed=s)
        r_ctrl = run_imagination_benchmark(ticks=MAX_TICKS, mode="RANDOM", seed=s)
        imag_results.append(r_imag)
        react_results.append(r_react)
        ctrl_results.append(r_ctrl)

    mean_imag_food = np.mean([r["food_collected"] for r in imag_results])
    mean_react_food = np.mean([r["food_collected"] for r in react_results])
    mean_ctrl_food = np.mean([r["food_collected"] for r in ctrl_results])

    mean_imag_rew = np.mean([r["total_reward"] for r in imag_results])
    mean_react_rew = np.mean([r["total_reward"] for r in react_results])
    mean_ctrl_rew = np.mean([r["total_reward"] for r in ctrl_results])

    mean_imag_haz = np.mean([r["hazard_hits"] for r in imag_results])
    mean_react_haz = np.mean([r["hazard_hits"] for r in react_results])
    mean_ctrl_haz = np.mean([r["hazard_hits"] for r in ctrl_results])

    print("\n" + "=" * 80)
    print("IMAGINATION & MENTAL SIMULATION COMPARATIVE SCORECARD")
    print("=" * 80)
    print(f"  Food Harvested:  Imagination={mean_imag_food:.1f} | Reactive={mean_react_food:.1f} | Control={mean_ctrl_food:.1f}")
    print(f"  Hazard Traps:    Imagination={mean_imag_haz:.1f} | Reactive={mean_react_haz:.1f} | Control={mean_ctrl_haz:.1f} (Lower is better)")
    print(f"  Net Reward:      Imagination={mean_imag_rew:+.1f} | Reactive={mean_react_rew:+.1f} | Control={mean_ctrl_rew:+.1f}")
    print(f"  Planning Delta:  Imagination vs Reactive: {mean_imag_rew - mean_react_rew:+.1f} Reward Delta")
    print(f"  Synaptic Norm:   ||W_dyn||={np.mean([r['dyn_norm'] for r in imag_results]):.2f} (Homeostatic Clamped)")
    print("=" * 80)

    summary = {
        "protocol": "SUBSTRATE_5I_IMAGINATION_PLANNING_v1",
        "horizon": IMAGINATION_HORIZON,
        "mean_imagination_food": round(float(mean_imag_food), 2),
        "mean_reactive_food": round(float(mean_react_food), 2),
        "mean_control_food": round(float(mean_ctrl_food), 2),
        "mean_imagination_reward": round(float(mean_imag_rew), 2),
        "mean_reactive_reward": round(float(mean_react_rew), 2),
        "mean_control_reward": round(float(mean_ctrl_rew), 2),
        "mean_imagination_hazard_hits": round(float(mean_imag_haz), 2),
        "mean_reactive_hazard_hits": round(float(mean_react_haz), 2),
        "mean_control_hazard_hits": round(float(mean_ctrl_haz), 2),
        "imagination_runs": imag_results,
        "reactive_runs": react_results,
        "control_runs": ctrl_results
    }

    out_file = os.path.join(os.path.dirname(__file__), "sub4_results", "sub5_imagination_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Synthesis saved -> {out_file}")

if __name__ == "__main__":
    main()
