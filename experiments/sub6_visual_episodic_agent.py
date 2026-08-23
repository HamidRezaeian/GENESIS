"""Substrate 6 — Visual Embodied Agent with Episodic Memory Consolidation.

Phases 2 & 3 Unified Advanced Implementation:
  1. 2D Visual Perception Grid (7x7 local field with 4 categorical channels: Empty, Wall, Food, Hazard).
  2. 2D Spatial Patch Convolutional / Linear Projection into d_model=32.
  3. Causal Transformer Core with Multi-Step Latent World Model.
  4. Surprise-Driven Episodic Memory Buffer (Capacity N=256):
      - Stores high-surprise transition experiences: (obs_t, action_t, reward_t, obs_{t+1}, surprise).
      - Periodically triggers Sleep / Memory Consolidation Replay (every 500 ticks) to replay salient events.
  5. Biological Synaptic Homeostasis active on all projection and dynamic matrices.
"""

import os
import sys
import json
import time
import math
import numpy as np

GRID_SIZE = 16
VISION_SIZE = 7       # 7x7 local visual field
N_CHANNELS = 4        # 0: Empty, 1: Wall, 2: Food, 3: Hazard
VISUAL_DIM = VISION_SIZE * VISION_SIZE * N_CHANNELS  # 196
MAX_TICKS = 50000
SEEDS = [100, 101, 102, 103]
IMAGINATION_HORIZON = 3
EPISODIC_CAPACITY = 256
SLEEP_INTERVAL = 500
SLEEP_BATCH_SIZE = 16
GAMMA = 0.95

ACTIONS = ["FORWARD", "TURN_LEFT", "TURN_RIGHT", "EAT"]
N_ACTIONS = 4
D_MODEL = 32
CONTEXT_LEN = 16
LR_MODEL = 0.005
LAMBDA_HOMEO = 1e-4

class VisualGridEnvironment:
    """2D Physical GridWorld with 7x7 Local Multi-Channel Visual Observation."""
    def __init__(self, size=GRID_SIZE, n_food=12, n_hazards=6, seed=42):
        self.size = size
        self.n_food = n_food
        self.n_hazards = n_hazards
        self.rng = np.random.RandomState(seed)
        self.reset()

    def reset(self):
        self.grid = np.zeros((self.size, self.size), dtype=np.int32)
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

    def get_visual_observation(self, pos, direction):
        """Extracts a 7x7x4 local egocentric visual patch centered on agent."""
        px, py = pos
        half = VISION_SIZE // 2
        visual_patch = np.zeros((VISION_SIZE, VISION_SIZE, N_CHANNELS), dtype=np.float32)

        for vy in range(-half, half + 1):
            for vx in range(-half, half + 1):
                # Rotate based on facing direction
                if direction % 4 == 0:     # NORTH
                    gx, gy = px + vx, py + vy
                elif direction % 4 == 1:   # EAST
                    gx, gy = px + vy, py - vx
                elif direction % 4 == 2:   # SOUTH
                    gx, gy = px - vx, py - vy
                else:                      # WEST
                    gx, gy = px - vy, py + vx

                patch_y, patch_x = vy + half, vx + half
                if 0 <= gx < self.size and 0 <= gy < self.size:
                    cell_type = self.grid[gx, gy]
                    visual_patch[patch_y, patch_x, cell_type] = 1.0
                else:
                    visual_patch[patch_y, patch_x, 1] = 1.0  # Out of bounds treated as wall

        return visual_patch.flatten()

    def step(self, pos, direction, action):
        dxs = [0, 1, 0, -1]
        dys = [1, 0, -1, 0]
        curr_dir = direction % 4
        px, py = pos

        reward = -0.05
        food_eaten = False

        if action == 0:  # FORWARD
            nx, ny = px + dxs[curr_dir], py + dys[curr_dir]
            if 0 <= nx < self.size and 0 <= ny < self.size and self.grid[nx, ny] != 1:
                pos = (nx, ny)
                if self.grid[nx, ny] == 3:
                    reward -= 5.0
            else:
                reward -= 0.5
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

class EpisodicMemoryBuffer:
    """Surprise-Weighted Salient Episodic Replay Memory."""
    def __init__(self, capacity=EPISODIC_CAPACITY):
        self.capacity = capacity
        self.buffer = []

    def push(self, obs, action, reward, next_obs, surprise):
        event = {
            "obs": np.copy(obs),
            "action": action,
            "reward": reward,
            "next_obs": np.copy(next_obs),
            "surprise": float(surprise)
        }
        if len(self.buffer) < self.capacity:
            self.buffer.append(event)
        else:
            # Replace lowest surprise item with probability proportional to surprise delta
            min_idx = int(np.argmin([e["surprise"] for e in self.buffer]))
            if surprise > self.buffer[min_idx]["surprise"]:
                self.buffer[min_idx] = event

    def sample_batch(self, batch_size=SLEEP_BATCH_SIZE, rng=None):
        if not self.buffer:
            return []
        if rng is None:
            rng = np.random
        n = min(len(self.buffer), batch_size)
        # Prioritized sampling by surprise
        surprises = np.array([max(1e-4, e["surprise"]) for e in self.buffer])
        probs = surprises / np.sum(surprises)
        indices = rng.choice(len(self.buffer), size=n, p=probs, replace=False)
        return [self.buffer[i] for i in indices]

class Substrate6VisualEpisodicAgent:
    """Visual Embodied Causal Transformer with World Model & Episodic Consolidation."""
    def __init__(self, seed=42):
        self.rng = np.random.RandomState(seed)
        
        # 2D Visual Linear Embedding: VISUAL_DIM (196) -> D_MODEL (32)
        self.W_vis = self.rng.randn(VISUAL_DIM, D_MODEL) * 0.05
        self.W_pos = self.rng.randn(CONTEXT_LEN, D_MODEL) * 0.05

        # Causal Attention weights
        self.W_q = self.rng.randn(D_MODEL, D_MODEL) * 0.05
        self.W_k = self.rng.randn(D_MODEL, D_MODEL) * 0.05
        self.W_v = self.rng.randn(D_MODEL, D_MODEL) * 0.05
        self.W_out = self.rng.randn(D_MODEL, D_MODEL) * 0.05

        # MLP
        self.W_ff1 = self.rng.randn(D_MODEL, D_MODEL * 2) * 0.05
        self.W_ff2 = self.rng.randn(D_MODEL * 2, D_MODEL) * 0.05

        # World Model & Decision Heads
        self.W_dyn = self.rng.randn(D_MODEL + N_ACTIONS, VISUAL_DIM) * 0.05
        self.W_rew = self.rng.randn(D_MODEL + N_ACTIONS, 1) * 0.05
        self.W_val = self.rng.randn(D_MODEL, 1) * 0.05
        self.W_actor = self.rng.randn(D_MODEL, N_ACTIONS) * 0.05

        self.context_buf = np.zeros((CONTEXT_LEN, VISUAL_DIM), dtype=np.float32)
        self.scale = 1.0 / math.sqrt(D_MODEL)
        self.episodic_memory = EpisodicMemoryBuffer(capacity=EPISODIC_CAPACITY)

    def encode(self, obs, context_history=None):
        if context_history is None:
            buf = np.copy(self.context_buf)
            buf[:-1] = buf[1:]
            buf[-1] = obs
        else:
            buf = np.copy(context_history)
            buf[:-1] = buf[1:]
            buf[-1] = obs

        x = buf @ self.W_vis + self.W_pos
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

    def sleep_and_consolidate(self):
        """Replays surprise-salient episodic transitions to consolidate synaptic memory."""
        batch = self.episodic_memory.sample_batch(batch_size=SLEEP_BATCH_SIZE, rng=self.rng)
        for event in batch:
            h_t, _ = self.encode(event["obs"])
            next_h, _ = self.encode(event["next_obs"])
            self.update_models(h_t, event["action"], event["next_obs"], event["reward"], next_h)

def run_visual_episodic_benchmark(ticks=MAX_TICKS, use_episodic=True, seed=42):
    env = VisualGridEnvironment(seed=seed)
    agent = Substrate6VisualEpisodicAgent(seed=seed)

    pos = (GRID_SIZE // 2, GRID_SIZE // 2)
    direction = 0

    total_reward = 0.0
    total_food = 0
    total_hazards = 0
    sleep_cycles = 0

    obs = env.get_visual_observation(pos, direction)

    for tick in range(ticks):
        h_t, q_vals, action_probs = agent.evaluate_imagination(obs, horizon=IMAGINATION_HORIZON)
        action = agent.rng.choice(N_ACTIONS, p=action_probs)

        # Real Environment Step
        next_pos, next_direction, reward, food_eaten = env.step(pos, direction, action)
        next_obs = env.get_visual_observation(next_pos, next_direction)
        next_h, _ = agent.encode(next_obs)

        # Compute Sensory Surprise
        a_vec = np.zeros(N_ACTIONS)
        a_vec[action] = 1.0
        pred_next_obs = np.tanh(np.concatenate([h_t, a_vec]) @ agent.W_dyn)
        surprise = float(np.mean((next_obs - pred_next_obs)**2)) + abs(reward) * 0.1

        # Online update
        agent.update_models(h_t, action, next_obs, reward, next_h)

        # Store in Episodic Memory
        if use_episodic:
            agent.episodic_memory.push(obs, action, reward, next_obs, surprise)

            # Trigger Sleep Consolidation periodically
            if (tick + 1) % SLEEP_INTERVAL == 0:
                agent.sleep_and_consolidate()
                sleep_cycles += 1

        agent.context_buf[:-1] = agent.context_buf[1:]
        agent.context_buf[-1] = obs

        total_reward += reward
        if food_eaten:
            total_food += 1
        if reward <= -5.0:
            total_hazards += 1

        pos = next_pos
        direction = next_direction
        obs = next_obs

    dyn_norm = float(np.linalg.norm(agent.W_dyn))
    val_norm = float(np.linalg.norm(agent.W_val))

    return {
        "seed": seed,
        "use_episodic": use_episodic,
        "ticks": ticks,
        "total_reward": round(total_reward, 2),
        "food_collected": total_food,
        "hazard_hits": total_hazards,
        "sleep_cycles": sleep_cycles,
        "dyn_norm": round(dyn_norm, 3),
        "val_norm": round(val_norm, 3)
    }

def main():
    print("=" * 80)
    print("GENESIS SUBSTRATE 6 — VISUAL EMBODIED & EPISODIC CONSOLIDATION BENCHMARK")
    print(f"Seeds: {SEEDS} | Ticks: {MAX_TICKS:,} | Vision: {VISION_SIZE}x{VISION_SIZE} (196-dim) | Episodic: N={EPISODIC_CAPACITY}")
    print("=" * 80)

    episodic_results = []
    baseline_results = []

    for s in SEEDS:
        print(f"Evaluating Seed {s} (Episodic Sleep Consolidation vs Online-Only Baseline)...", flush=True)
        r_epi = run_visual_episodic_benchmark(ticks=MAX_TICKS, use_episodic=True, seed=s)
        r_base = run_visual_episodic_benchmark(ticks=MAX_TICKS, use_episodic=False, seed=s)
        episodic_results.append(r_epi)
        baseline_results.append(r_base)

    mean_epi_food = np.mean([r["food_collected"] for r in episodic_results])
    mean_base_food = np.mean([r["food_collected"] for r in baseline_results])

    mean_epi_rew = np.mean([r["total_reward"] for r in episodic_results])
    mean_base_rew = np.mean([r["total_reward"] for r in baseline_results])

    mean_epi_haz = np.mean([r["hazard_hits"] for r in episodic_results])
    mean_base_haz = np.mean([r["hazard_hits"] for r in baseline_results])

    print("\n" + "=" * 80)
    print("SUBSTRATE 6 VISUAL & EPISODIC CONSOLIDATION COMPARATIVE SCORECARD")
    print("=" * 80)
    print(f"  Food Collected:    Episodic+Vision = {mean_epi_food:.1f} | Online-Only = {mean_base_food:.1f} (Delta: {mean_epi_food - mean_base_food:+.1f})")
    print(f"  Hazard Collisions: Episodic+Vision = {mean_epi_haz:.1f} | Online-Only = {mean_base_haz:.1f} (Delta: {mean_epi_haz - mean_base_haz:+.1f})")
    print(f"  Net Total Reward:  Episodic+Vision = {mean_epi_rew:+.1f} | Online-Only = {mean_base_rew:+.1f} (Delta: {mean_epi_rew - mean_base_rew:+.1f})")
    print(f"  Sleep Cycles:      {np.mean([r['sleep_cycles'] for r in episodic_results]):.0f} Consolidation Replay Phases")
    print(f"  Synaptic Norms:    ||W_dyn|| = {np.mean([r['dyn_norm'] for r in episodic_results]):.2f} (Homeostatic Clamped)")
    print("=" * 80)

    summary = {
        "protocol": "SUBSTRATE_6_VISUAL_EPISODIC_CONSOLIDATION_v1",
        "vision_field": f"{VISION_SIZE}x{VISION_SIZE}x{N_CHANNELS}",
        "episodic_capacity": EPISODIC_CAPACITY,
        "mean_episodic_food": round(float(mean_epi_food), 2),
        "mean_baseline_food": round(float(mean_base_food), 2),
        "mean_episodic_reward": round(float(mean_epi_rew), 2),
        "mean_baseline_reward": round(float(mean_base_rew), 2),
        "mean_episodic_hazard_hits": round(float(mean_epi_haz), 2),
        "mean_baseline_hazard_hits": round(float(mean_base_haz), 2),
        "episodic_runs": episodic_results,
        "baseline_runs": baseline_results
    }

    out_file = os.path.join(os.path.dirname(__file__), "sub4_results", "sub6_visual_episodic_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Synthesis saved -> {out_file}")

if __name__ == "__main__":
    main()
