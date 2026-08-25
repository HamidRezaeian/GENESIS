"""
GENESIS Authoritative Python Brain Server (Substrate 8)
100% Pure Neural Core — Zero Heuristics / Zero Hardcoded Rules
Rule 21 & Rule 25 Compliant.
"""

import os
import sys
import json
import time
import math
import asyncio
import numpy as np
from pathlib import Path
from aiohttp import web, WSMsgType

# Repository Root & Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BRAIN_DIR = REPO_ROOT / "Brain"
PUBLIC_DIR = REPO_ROOT / "public"
BRAIN_DIR.mkdir(exist_ok=True, parents=True)

from numba import njit
from genesis_pytorch_brain import GenesisPyTorchBrain


# Architectural Hyperparameters
GRID_SIZE = 24
VISION_SIZE = 7
N_CHANNELS = 6
VISUAL_DIM = VISION_SIZE * VISION_SIZE * N_CHANNELS # 294
VOCAB_SIZE = 64
MAX_TEXT_LEN = 16
D_MODEL = 32
N_ACTIONS = 4
LR_MODEL = np.float32(0.005)
LAMBDA_HOMEO = np.float32(1e-6)
LAMBDA_EWC = np.float32(0.5)
GAMMA = np.float32(0.95)
MCTS_SIMS_DIRECTED = 32
MCTS_SIMS_EXPLORE = 16
MCTS_DEPTH = 6

# ==============================================================================
# NUMBA LLVM JIT ACCELERATED COMPUTATIONAL KERNELS (Rule 21 & Rule 23 Grounded)
# ==============================================================================

@njit(fastmath=True, nogil=True)
def numba_get_visual_observation(grid: np.ndarray, agent_x: int, agent_y: int, agent_dir: int, vision_size: int, n_channels: int) -> np.ndarray:
    half = vision_size // 2
    obs = np.zeros(vision_size * vision_size * n_channels, dtype=np.float32)
    idx = 0
    for vy in range(-half, half + 1):
        for vx in range(-half, half + 1):
            gx = agent_x
            gy = agent_y
            if agent_dir == 0:
                gx += vx; gy += vy
            elif agent_dir == 1:
                gx -= vy; gy += vx
            elif agent_dir == 2:
                gx -= vx; gy -= vy
            elif agent_dir == 3:
                gx += vy; gy -= vx
            
            if 0 <= gx < 24 and 0 <= gy < 24:
                cell = grid[gx, gy]
                if 0 <= cell < n_channels:
                    obs[idx * n_channels + cell] = np.float32(1.0)
            else:
                obs[idx * n_channels + 1] = np.float32(1.0)
            idx += 1
    return obs

@njit(fastmath=True, nogil=True)
def numba_forward_transformer(obs_vis: np.ndarray, text_emb: np.ndarray, 
                              W_vis: np.ndarray, W_fuse_vis: np.ndarray, W_fuse_lang: np.ndarray, 
                              W_q: np.ndarray, W_k: np.ndarray, W_v: np.ndarray, 
                              W_out: np.ndarray, W_ff1: np.ndarray, W_ff2: np.ndarray) -> np.ndarray:
    z_vis = np.dot(obs_vis, W_vis)
    fused_v = np.dot(z_vis, W_fuse_vis)
    fused_l = np.dot(text_emb, W_fuse_lang)
    fused = np.tanh(fused_v + fused_l)
    
    Q = np.dot(fused, W_q)
    K = np.dot(fused, W_k)
    V = np.dot(fused, W_v)
    
    score = np.dot(Q, K) / np.float32(5.656854)
    attn = np.float32(1.0) / (np.float32(1.0) + np.exp(-score))
    attn_out = np.dot(fused, W_out)
    mixed = fused + attn * V
    
    ff1 = np.maximum(np.float32(0.0), np.dot(mixed, W_ff1))
    ff2 = np.dot(ff1, W_ff2)
    return mixed + ff2

@njit(fastmath=True, nogil=True)
def numba_mcts_eval(root_state: np.ndarray, W_dyn: np.ndarray, W_rew: np.ndarray, 
                    W_val: np.ndarray, W_policy: np.ndarray, noisy_priors: np.ndarray, 
                    effective_cpuct: float, effective_sims: int):
    MAX_NODES = effective_sims + 1
    tree_state = np.zeros((MAX_NODES, 32), dtype=np.float32)
    tree_visit = np.zeros(MAX_NODES, dtype=np.int32)
    tree_val_sum = np.zeros(MAX_NODES, dtype=np.float32)
    tree_reward = np.zeros(MAX_NODES, dtype=np.float32)
    tree_children = np.zeros((MAX_NODES, 4), dtype=np.int32)
    tree_policy = np.zeros((MAX_NODES, 4), dtype=np.float32)
    tree_q_prior = np.zeros((MAX_NODES, 4), dtype=np.float32)
    
    tree_state[0] = root_state
    tree_policy[0] = noisy_priors
    node_count = 1
    
    # Calculate root Q-priors in batch
    sa_root_batch = np.zeros((4, 36), dtype=np.float32)
    sa_root_batch[:, :32] = root_state
    for a in range(4):
        sa_root_batch[a, 32 + a] = np.float32(1.0)
    root_next_s = np.tanh(np.dot(sa_root_batch, W_dyn))
    root_r = np.dot(sa_root_batch, W_rew)
    root_v = np.dot(root_next_s, W_val)
    tree_q_prior[0] = root_r + np.float32(0.95) * root_v
    
    for sim in range(effective_sims):
        curr_node = 0
        search_path = np.zeros(10, dtype=np.int32)
        search_path[0] = 0
        path_len = 1
        
        depth = 0
        while depth < 4:
            best_action = -1
            best_ucb = np.float32(-999999.0)
            
            for a in range(4):
                child_idx = tree_children[curr_node, a]
                if child_idx == 0:
                    q = tree_q_prior[curr_node, a]
                    n = 0
                else:
                    q = tree_val_sum[child_idx] / np.float32(max(1, tree_visit[child_idx]))
                    n = tree_visit[child_idx]
                
                u = effective_cpuct * tree_policy[curr_node, a] * np.sqrt(np.float32(tree_visit[curr_node] + 1)) / (np.float32(1.0) + n)
                score = q + u
                if score > best_ucb:
                    best_ucb = score
                    best_action = a
                    
            child_idx = tree_children[curr_node, best_action]
            
            if child_idx == 0:
                if node_count < MAX_NODES:
                    new_node = node_count
                    node_count += 1
                    
                    sa = np.zeros(36, dtype=np.float32)
                    sa[:32] = tree_state[curr_node]
                    sa[32 + best_action] = np.float32(1.0)
                    
                    next_s = np.tanh(np.dot(sa, W_dyn))
                    rew = np.dot(sa, W_rew)
                    
                    tree_state[new_node] = next_s
                    tree_reward[new_node] = rew
                    
                    logits = np.dot(next_s, W_policy)
                    max_l = np.max(logits)
                    exp_l = np.exp(logits - max_l)
                    p_probs = exp_l / (np.sum(exp_l) + np.float32(1e-9))
                    tree_policy[new_node] = p_probs
                    
                    # Compute Q-priors for the new node in batch
                    sa_new_batch = np.zeros((4, 36), dtype=np.float32)
                    sa_new_batch[:, :32] = next_s
                    for a_new in range(4):
                        sa_new_batch[a_new, 32 + a_new] = np.float32(1.0)
                    nn_s = np.tanh(np.dot(sa_new_batch, W_dyn))
                    nn_r = np.dot(sa_new_batch, W_rew)
                    nn_v = np.dot(nn_s, W_val)
                    tree_q_prior[new_node] = nn_r + np.float32(0.95) * nn_v
                    
                    tree_children[curr_node, best_action] = new_node
                    curr_node = new_node
                    search_path[path_len] = new_node
                    path_len += 1
                break
            else:
                curr_node = child_idx
                search_path[path_len] = curr_node
                path_len += 1
                depth += 1
                
        leaf_val = np.dot(tree_state[curr_node], W_val)
        
        G = leaf_val
        for i in range(path_len - 1, -1, -1):
            node = search_path[i]
            tree_visit[node] += 1
            tree_val_sum[node] += G
            G = tree_reward[node] + np.float32(0.95) * G

    visit_counts = np.zeros(4, dtype=np.int32)
    q_values = np.zeros(4, dtype=np.float32)
    
    for a in range(4):
        child_idx = tree_children[0, a]
        if child_idx != 0:
            visit_counts[a] = tree_visit[child_idx]
            q_values[a] = tree_reward[child_idx] + np.float32(0.95) * (tree_val_sum[child_idx] / np.float32(max(1, tree_visit[child_idx])))
        else:
            q_values[a] = tree_q_prior[0, a]
            
    total_v = np.sum(visit_counts)
    mcts_probs = visit_counts.astype(np.float32) / np.float32(max(1, total_v))
    return mcts_probs, q_values, visit_counts

@njit(fastmath=True, nogil=True)
def numba_update_neural_weights(s_curr: np.ndarray, action: int, reward: float, s_next: np.ndarray,
                                W_dyn: np.ndarray, W_rew: np.ndarray, W_val: np.ndarray, W_policy: np.ndarray,
                                fisher_dyn: np.ndarray, anchor_dyn: np.ndarray):
    sa = np.zeros(36, dtype=np.float32)
    sa[:32] = s_curr
    sa[32 + action] = np.float32(1.0)
    
    pred_next = np.tanh(np.dot(sa, W_dyn))
    err_dyn = s_next - pred_next
    loss_dyn = np.sum(err_dyn ** 2)
    
    grad_d = err_dyn * (np.float32(1.0) - pred_next ** 2)
    G = np.outer(sa, grad_d)
    fisher_dyn += (G ** 2) * np.float32(0.01)
    ewc_pen = np.float32(0.5) * fisher_dyn * (W_dyn - anchor_dyn)
    W_dyn += np.float32(0.005) * G - np.float32(1e-6) * W_dyn - np.float32(0.005) * ewc_pen
    
    pred_rew = np.dot(sa, W_rew)
    err_rew = reward - pred_rew
    W_rew += np.float32(0.005) * sa * err_rew - np.float32(1e-6) * W_rew
    
    v_curr = np.dot(s_curr, W_val)
    v_next = np.dot(s_next, W_val)
    td_err = reward + np.float32(0.95) * v_next - v_curr
    W_val += np.float32(0.005) * s_curr * td_err - np.float32(1e-6) * W_val
    
    logits = np.dot(s_curr, W_policy)
    exp_l = np.exp(logits - np.max(logits))
    probs = exp_l / (np.sum(exp_l) + np.float32(1e-9))
    grad_p = -probs
    grad_p[action] += np.float32(1.0)
    W_policy += np.float32(0.005) * np.outer(s_curr, grad_p * td_err) - np.float32(1e-6) * W_policy
    
    return loss_dyn / np.float32(32.0), v_curr

class GenesisNumbaBrain:
    def __init__(self):
        self.rng = np.random.RandomState(42)
        self.init_weights()
        self.hippocampus = []
        self.fisher_diag = {"W_dyn": np.zeros((D_MODEL + N_ACTIONS, D_MODEL), dtype=np.float32)}
        self.anchor_weights = {"W_dyn": self.W_dyn.copy()}
        self._warmup_numba()

    def _warmup_numba(self):
        d_obs = np.zeros(VISUAL_DIM, dtype=np.float32)
        d_text = np.zeros(D_MODEL, dtype=np.float32)
        d_priors = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float32)
        d_grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        
        numba_get_visual_observation(d_grid, 3, 3, 0, VISION_SIZE, N_CHANNELS)
        s = numba_forward_transformer(
            d_obs, d_text, self.W_vis, self.W_fuse_vis, self.W_fuse_lang,
            self.W_q, self.W_k, self.W_v, self.W_out, self.W_ff1, self.W_ff2
        )
        numba_mcts_eval(s, self.W_dyn, self.W_rew, self.W_val, self.W_policy, d_priors, 0.8, 4)
        numba_update_neural_weights(
            s, 0, np.float32(0.0), s, self.W_dyn, self.W_rew, self.W_val, self.W_policy,
            self.fisher_diag["W_dyn"], self.anchor_weights["W_dyn"]
        )

    def _rand_mat(self, rows, cols, std=0.05):
        return (self.rng.uniform(-1.0, 1.0, (rows, cols)) * math.sqrt(3) * std).astype(np.float32)

    def init_weights(self):
        self.W_vis = self._rand_mat(VISUAL_DIM, D_MODEL, 0.05)
        self.W_lang = self._rand_mat(VOCAB_SIZE, D_MODEL, 0.05)
        self.W_fuse_vis = self._rand_mat(D_MODEL, D_MODEL, 0.05)
        self.W_fuse_lang = self._rand_mat(D_MODEL, D_MODEL, 0.05)

        self.W_q = self._rand_mat(D_MODEL, D_MODEL, 0.05)
        self.W_k = self._rand_mat(D_MODEL, D_MODEL, 0.05)
        self.W_v = self._rand_mat(D_MODEL, D_MODEL, 0.05)
        self.W_out = self._rand_mat(D_MODEL, D_MODEL, 0.05)
        self.W_ff1 = self._rand_mat(D_MODEL, D_MODEL * 2, 0.05)
        self.W_ff2 = self._rand_mat(D_MODEL * 2, D_MODEL, 0.05)

        self.W_dyn = self._rand_mat(D_MODEL + N_ACTIONS, D_MODEL, 0.05)
        self.W_rew = self._rand_mat(D_MODEL + N_ACTIONS, 1, 0.05)[:, 0].copy()
        self.W_val = self._rand_mat(D_MODEL, 1, 0.05)[:, 0].copy()
        self.W_policy = self._rand_mat(D_MODEL, N_ACTIONS, 0.05)

    def encode_text(self, text_str: str) -> np.ndarray:
        clean = (text_str or "").upper()[:MAX_TEXT_LEN]
        tokens = [ord(c) % VOCAB_SIZE for c in clean]
        if not tokens:
            tokens = [0]
        emb = np.mean([self.W_lang[t] for t in tokens], axis=0).astype(np.float32)
        return emb

    def forward_transformer(self, obs_vis: np.ndarray, text_str: str) -> np.ndarray:
        z_lang = self.encode_text(text_str)
        return numba_forward_transformer(
            obs_vis, z_lang,
            self.W_vis, self.W_fuse_vis, self.W_fuse_lang,
            self.W_q, self.W_k, self.W_v,
            self.W_out, self.W_ff1, self.W_ff2
        )

    def run_mcts(self, root_state: np.ndarray, policy_mode: str = "DIRECTED") -> dict:
        logits = np.dot(root_state, self.W_policy)
        max_l = np.max(logits)
        exp_l = np.exp(logits - max_l)
        priors = exp_l / (np.sum(exp_l) + 1e-9)

        noise = -np.log(np.maximum(1e-6, self.rng.uniform(0.0, 1.0, N_ACTIONS)))
        noise /= (np.sum(noise) + 1e-9)
        eps_noise = 0.20 if policy_mode == "DIRECTED" else 0.40
        noisy_priors = ((1.0 - eps_noise) * priors + eps_noise * noise).astype(np.float32)

        effective_sims = MCTS_SIMS_DIRECTED if policy_mode == "DIRECTED" else MCTS_SIMS_EXPLORE
        effective_cpuct = 0.8 if policy_mode == "DIRECTED" else 1.4

        mcts_probs, q_values, visit_counts = numba_mcts_eval(
            root_state, self.W_dyn, self.W_rew, self.W_val, self.W_policy,
            noisy_priors, effective_cpuct, effective_sims
        )

        return {
            "probs": mcts_probs.tolist(),
            "qValues": q_values.tolist(),
            "visitCounts": visit_counts.tolist()
        }

    def update_neural_weights(self, s_curr: np.ndarray, action: int, reward: float, s_next: np.ndarray) -> dict:
        loss, v_curr = numba_update_neural_weights(
            s_curr, action, np.float32(reward), s_next,
            self.W_dyn, self.W_rew, self.W_val, self.W_policy,
            self.fisher_diag["W_dyn"], self.anchor_weights["W_dyn"]
        )

        # Record to Hippocampal Episodic Buffer
        self.hippocampus.append({
            "s_curr": s_curr.copy(),
            "action": action,
            "reward": reward,
            "s_next": s_next.copy(),
            "surprise": float(loss) + abs(reward)
        })
        if len(self.hippocampus) > 5000:
            self.hippocampus.pop(0)

        return {"loss": float(loss), "vCurr": float(v_curr)}

    def sleep_consolidation(self) -> int:
        if len(self.hippocampus) < 10: return 0
        replays = min(50, len(self.hippocampus))
        for _ in range(replays):
            idx = self.rng.randint(0, len(self.hippocampus))
            mem = self.hippocampus[idx]
            numba_update_neural_weights(
                mem["s_curr"], mem["action"], np.float32(mem["reward"]), mem["s_next"],
                self.W_dyn, self.W_rew, self.W_val, self.W_policy,
                self.fisher_diag["W_dyn"], self.anchor_weights["W_dyn"]
            )
        self.anchor_weights["W_dyn"] = self.W_dyn.copy()
        return replays

    def decode_neural_language(self, s_curr: np.ndarray, user_prompt: str) -> dict:
        vocab_logits = np.dot(s_curr, self.W_lang.T)
        exp_v = np.exp(vocab_logits - np.max(vocab_logits))
        probs = exp_v / (np.sum(exp_v) + 1e-9)
        top_ids = np.argsort(probs)[-8:][::-1]
        
        emitted = "".join(chr(65 + (tid % 26)) for tid in top_ids)
        v_val = np.dot(s_curr, self.W_val)
        return {
            "top_tokens": emitted,
            "state_sample": [round(float(x), 3) for x in s_curr[:4]],
            "v_val": float(v_val)
        }

GenesisNeuralBrain = GenesisPyTorchBrain


class GenesisEnvironment:
    def __init__(self):
        self.grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        self.agent_pos = [3, 2]
        self.agent_dir = 2 # 0: North, 1: East, 2: South, 3: West
        self.has_key = False
        self.door_opened = False
        self.current_level = 1
        self.level_consecutive_solves = 0
        self.init_level(1)

    def reset_agent_position(self):
        if self.current_level == 1:
            self.agent_pos = [3, 2]
            self.agent_dir = 2
        elif self.current_level == 2:
            self.agent_pos = [2, 2]
            self.agent_dir = 1
        elif self.current_level == 3:
            self.agent_pos = [3, 3]
            self.agent_dir = 1
        else:
            self.agent_pos = [3, 3]
            self.agent_dir = 0

    def init_level(self, lvl: int):
        self.current_level = lvl
        self.grid.fill(0)
        self.has_key = False
        self.door_opened = False

        if lvl == 1: # 🍼 Infant (8x8 boundary, food at (3, 5))
            S = 8
            for i in range(GRID_SIZE):
                for j in range(GRID_SIZE):
                    if i >= S or j >= S:
                        self.grid[i, j] = 1
            for i in range(S):
                self.grid[0, i] = 1; self.grid[S - 1, i] = 1
                self.grid[i, 0] = 1; self.grid[i, S - 1] = 1
            self.agent_pos = [3, 2]
            self.agent_dir = 2
            self.grid[3, 5] = 4 # Food directly in front
        elif lvl == 2: # 🚶 Toddler (10x10 with corner barrier)
            S = 10
            for i in range(GRID_SIZE):
                for j in range(GRID_SIZE):
                    if i >= S or j >= S:
                        self.grid[i, j] = 1
            for i in range(S):
                self.grid[0, i] = 1; self.grid[S - 1, i] = 1
                self.grid[i, 0] = 1; self.grid[i, S - 1] = 1
            self.grid[4, 4] = 1; self.grid[5, 4] = 1
            self.agent_pos = [2, 2]
            self.agent_dir = 1
            self.grid[7, 7] = 4
        elif lvl == 3: # 🏃 Chambers (14x14 with open doorway)
            S = 14
            for i in range(GRID_SIZE):
                for j in range(GRID_SIZE):
                    if i >= S or j >= S:
                        self.grid[i, j] = 1
            for i in range(S):
                self.grid[0, i] = 1; self.grid[S - 1, i] = 1
                self.grid[i, 0] = 1; self.grid[i, S - 1] = 1
            mid = 7
            for i in range(S):
                self.grid[mid, i] = 1
            self.grid[mid, 4] = 0 # Open doorway
            self.agent_pos = [3, 3]
            self.agent_dir = 0
            self.grid[S - 3, S - 3] = 6 # Goal
            self.grid[mid + 2, 4] = 4
        elif lvl == 4: # 🔑 Key & Lock (18x18)
            S = 18
            for i in range(GRID_SIZE):
                for j in range(GRID_SIZE):
                    if i >= S or j >= S:
                        self.grid[i, j] = 1
            for i in range(S):
                self.grid[0, i] = 1; self.grid[S - 1, i] = 1
                self.grid[i, 0] = 1; self.grid[i, S - 1] = 1
            mid = 9
            for i in range(S):
                self.grid[mid, i] = 1
            self.grid[mid, 5] = 2 # Locked Door
            self.grid[4, 4] = 3 # Key
            self.grid[S - 3, S - 3] = 6 # Goal
            self.grid[mid + 2, 4] = 4
            self.agent_pos = [3, 3]
            self.agent_dir = 0
        else: # 🏆 Master (24x24 Full Labyrinth)
            for i in range(GRID_SIZE):
                self.grid[0, i] = 1; self.grid[GRID_SIZE - 1, i] = 1
                self.grid[i, 0] = 1; self.grid[i, GRID_SIZE - 1] = 1
            mid = GRID_SIZE // 2
            for i in range(GRID_SIZE):
                self.grid[mid, i] = 1
            self.grid[mid, 6] = 2
            self.grid[mid // 2, 4] = 3
            self.grid[GRID_SIZE - 4, GRID_SIZE - 4] = 6
            for y in range(8, 12):
                self.grid[mid - 1, y] = 5
            for i in range(6):
                self.grid[mid + 2 + (i % 3) * 3, 4 + i * 2] = 4
            self.agent_pos = [3, 3]
            self.agent_dir = 0

    def get_visual_observation(self) -> np.ndarray:
        return numba_get_visual_observation(
            self.grid, self.agent_pos[0], self.agent_pos[1], self.agent_dir,
            VISION_SIZE, N_CHANNELS
        )

    def step(self, action: int) -> tuple:
        dirs = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        # Metabolic baseline: MCTS invalidation cost
        reward = -0.5
        event = None

        if action == 0: # FORWARD
            dx, dy = dirs[self.agent_dir % 4]
            nx, ny = self.agent_pos[0] + dx, self.agent_pos[1] + dy

            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                cell = self.grid[nx, ny]
                if cell == 1: # Wall
                    reward = -2.0
                elif cell == 2: # Door
                    if self.has_key:
                        self.grid[nx, ny] = 0
                        self.door_opened = True
                        self.agent_pos = [nx, ny]
                        reward = 64.0 # Freed 2 cells (door + key memory)
                        event = "DOOR_UNLOCKED"
                    else:
                        reward = -5.0
                elif cell == 5: # Hazard
                    self.agent_pos = [nx, ny]
                    reward = -50.0
                    event = "HAZARD_HIT"
                else:
                    self.agent_pos = [nx, ny]
                    if cell == 4: # Food
                        self.grid[nx, ny] = 0
                        reward = 32.0 # 256 bits / 8
                        event = "FOOD_HARVESTED"
        elif action == 1:
            self.agent_dir = (self.agent_dir - 1 + 4) % 4
        elif action == 2:
            self.agent_dir = (self.agent_dir + 1) % 4
        elif action == 3: # INTERACT
            cell = self.grid[self.agent_pos[0], self.agent_pos[1]]
            if cell == 3 and not self.has_key:
                self.has_key = True
                self.grid[self.agent_pos[0], self.agent_pos[1]] = 0
                reward = 32.0
                event = "KEY_PICKED"
            elif cell == 6: # Goal
                reward = 196.0 # Freed entire 14x14 grid
                event = "GOAL_SOLVED"

        return reward, event


class GenesisEngineRunner:
    def __init__(self):
        self.brain = GenesisPyTorchBrain()
        self.env = GenesisEnvironment()
        self.is_running = True
        self.speed = 1
        self.tick_count = 0
        
        # Grounded Initial Energy (Rule 21.3)
        # FOOTPRINT_QUANTUM = 898.0 energy/byte (Exp 91 Baseline)
        footprint_bytes = self.brain.get_footprint_bytes()
        self.max_energy = footprint_bytes / 898.0
        self.energy = self.max_energy
        
        # Grounded Metabolic Cost
        # Forward pass FLOPs estimate ~ footprint / 100
        self.metabolic_cost = footprint_bytes / (898.0 * 2000.0) # ~ 0.06 per tick
        
        self.goals_solved = 0
        self.food_harvested = 0
        self.doors_unlocked = 0
        self.hazard_collisions = 0
        self.policy_mode = "DIRECTED"
        self.active_task_text = "EXPLORE & SURVIVE"
        self.connected_websockets = set()

        # Load existing brain if available
        ckpt_path = BRAIN_DIR / "canonical_brain.npz"
        if ckpt_path.exists():
            try:
                self.brain.load_checkpoint(ckpt_path)
                print(f"[GENESIS CORE] Successfully loaded canonical brain from {ckpt_path}")
            except Exception as e:
                print(f"[GENESIS CORE] Checkpoint load note: {e}")

    def step_once(self) -> dict:
        self.tick_count += 1
        self.energy -= self.metabolic_cost

        obs = self.env.get_visual_observation()
        s_curr = self.brain.forward_transformer(obs, self.active_task_text)
        mcts_info = self.brain.run_mcts(s_curr, self.policy_mode)

        probs = np.array(mcts_info["probs"], dtype=np.float64)
        probs /= (np.sum(probs) + 1e-9) # ensure sum is exactly 1.0 for np.random.choice
        action = int(self.brain.rng.choice(N_ACTIONS, p=probs))

        reward, event = self.env.step(action)
        self.energy += reward

        if event == "FOOD_HARVESTED":
            self.food_harvested += 1
            if self.env.current_level <= 2:
                self.env.level_consecutive_solves += 1
                if self.env.level_consecutive_solves >= 3 and self.env.current_level < 5:
                    self.env.init_level(self.env.current_level + 1)
                else:
                    self.env.init_level(self.env.current_level)
        elif event == "DOOR_UNLOCKED":
            self.doors_unlocked += 1
        elif event == "HAZARD_HIT":
            self.hazard_collisions += 1
        elif event == "GOAL_SOLVED":
            self.goals_solved += 1
            if self.env.current_level >= 3:
                self.env.level_consecutive_solves += 1
                if self.env.level_consecutive_solves >= 2 and self.env.current_level < 5:
                    self.env.init_level(self.env.current_level + 1)
                else:
                    self.env.init_level(self.env.current_level)
            else:
                self.env.init_level(self.env.current_level)

        next_obs = self.env.get_visual_observation()
        s_next = self.brain.forward_transformer(next_obs, self.active_task_text)
        metrics = self.brain.update_neural_weights(s_curr, action, reward, s_next)

        # Prioritized Mini-batch replay
        if len(self.brain.hippocampus) >= 32:
            surprises = np.array([m["surprise"] for m in self.brain.hippocampus], dtype=np.float32)
            np.maximum(surprises, 1e-6, out=surprises)
            probs = surprises / np.sum(surprises)
            indices = self.brain.rng.choice(len(self.brain.hippocampus), size=32, p=probs)
            for idx in indices:
                m = self.brain.hippocampus[idx]
                self.brain.update_neural_weights(m["s_curr"], m["action"], m["reward"], m["s_next"])

        if self.energy <= 0.0:
            self.energy = self.max_energy
            self.env.level_consecutive_solves = 0
            self.env.init_level(self.env.current_level)

        is_sleeping = False
        if self.tick_count > 0 and self.tick_count % 2000 == 0 and len(self.brain.hippocampus) > 100:
            print(f"[GENESIS CORE] Circadian Rhythm Triggered: Sleep Consolidation (Tick {self.tick_count})")
            self.brain.sleep_consolidation()
            is_sleeping = True

        if self.tick_count % 1000 == 0:
            save_path = BRAIN_DIR / "canonical_brain.npz"
            self.brain.save_checkpoint(save_path)

        state_payload = {
            "type": "STATE_UPDATE",
            "tick": self.tick_count,
            "energy": max(0.0, self.energy),
            "level": self.env.current_level,
            "goals": self.goals_solved,
            "food": self.food_harvested,
            "doors": self.doors_unlocked,
            "hazards": self.hazard_collisions,
            "hasKey": self.env.has_key,
            "agentPos": self.env.agent_pos,
            "agentDir": self.env.agent_dir,
            "grid": self.env.grid.tolist(),
            "obs": obs.tolist(),
            "mcts": mcts_info,
            "vVal": metrics["vCurr"],
            "loss": metrics["loss"],
            "hippoCount": len(self.brain.hippocampus),
            "policyMode": self.policy_mode,
            "activeTask": self.active_task_text,
            "isSleeping": is_sleeping
        }
        return state_payload

    async def broadcast_state(self, payload: dict):
        if not self.connected_websockets:
            return
        msg = json.dumps(payload)
        dead_ws = set()
        for ws in self.connected_websockets:
            try:
                await ws.send_str(msg)
            except Exception:
                dead_ws.add(ws)
        self.connected_websockets -= dead_ws

    def handle_user_dialogue(self, user_msg: str) -> dict:
        self.active_task_text = user_msg.upper()[:MAX_TEXT_LEN]
        obs = self.env.get_visual_observation()
        s_curr = self.brain.forward_transformer(obs, self.active_task_text)
        dec = self.brain.decode_neural_language(s_curr, user_msg)
        mcts_info = self.brain.run_mcts(s_curr, self.policy_mode)

        action_names = ["FWD", "LEFT", "RIGHT", "ACT"]
        best_a = action_names[int(np.argmax(mcts_info["visitCounts"]))]
        best_q = mcts_info["qValues"][action_names.index(best_a)]

        reply_str = (
            f"🧠 [Python PyTorch Latent]: {dec['state_sample']} | V(s)={dec['v_val']:.2f} | "
            f"Energy={self.energy:.1f} | MCTS Plan: {best_a} (Q={best_q:.2f}) | "
            f"Conditioned: \"{self.active_task_text}\" | Emitted Tokens: \"{dec['top_tokens']}\""
        )
        return {
            "type": "CHAT_RESPONSE",
            "reply": reply_str,
            "activeTask": self.active_task_text
        }


runner = GenesisEngineRunner()

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    runner.connected_websockets.add(ws)
    print(f"[GENESIS SERVER] Client connected via WebSocket. Active clients: {len(runner.connected_websockets)}")

    # Send initial full state immediately
    init_state = runner.step_once()
    await ws.send_str(json.dumps(init_state))

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                cmd = data.get("action")
                if cmd == "SET_SPEED":
                    runner.speed = int(data.get("value", 1))
                elif cmd == "SET_LEVEL":
                    runner.env.init_level(int(data.get("value", 1)))
                elif cmd == "SET_POLICY_MODE":
                    runner.policy_mode = str(data.get("value", "DIRECTED"))
                elif cmd == "TRIGGER_SLEEP":
                    replays = runner.brain.sleep_consolidation()
                    resp = {
                        "type": "CHAT_RESPONSE",
                        "reply": f"🌙 [Python Core]: Sleep consolidation completed across {replays} salient hippocampal transitions. Synaptic weights anchored with Fisher matrix.",
                        "activeTask": runner.active_task_text
                    }
                    await ws.send_str(json.dumps(resp))
                elif cmd == "USER_CHAT":
                    resp = runner.handle_user_dialogue(data.get("text", ""))
                    await ws.send_str(json.dumps(resp))
                elif cmd == "TOGGLE_PLAY":
                    runner.is_running = not runner.is_running
                elif cmd == "STEP_ONCE":
                    st = runner.step_once()
                    await ws.send_str(json.dumps(st))
                elif cmd == "WIPE_BRAIN":
                    runner.brain.init_weights()
                    runner.tick_count = 0
                    runner.energy = runner.max_energy
                    runner.goals_solved = 0
                    runner.food_harvested = 0
                    runner.doors_unlocked = 0
                    runner.hazard_collisions = 0
                    runner.env.init_level(1)
                    resp = {
                        "type": "CHAT_RESPONSE",
                        "reply": "🧹 [Python Core]: Neural brain wiped to Tabula Rasa (Random Gaussian Noise).",
                        "activeTask": runner.active_task_text
                    }
                    await ws.send_str(json.dumps(resp))
            elif msg.type == WSMsgType.ERROR:
                print(f"[GENESIS SERVER] WS exception: {ws.exception()}")
    finally:
        runner.connected_websockets.discard(ws)
        print(f"[GENESIS SERVER] Client disconnected. Active clients: {len(runner.connected_websockets)}", flush=True)
    return ws

async def simulation_loop():
    last_broadcast = time.perf_counter()
    st = None
    while True:
        if runner.is_running:
            target_speed = runner.speed
            if target_speed <= 5:
                st = runner.step_once()
                await runner.broadcast_state(st)
                delay = 0.08 / max(1, target_speed)
                await asyncio.sleep(delay)
            elif target_speed <= 25:
                for _ in range(5):
                    st = runner.step_once()
                await runner.broadcast_state(st)
                await asyncio.sleep(0.015)
            else:
                # Ultra-High-Speed Numba JIT Batching (100x, 250x, 500x, 1000x)
                batch_size = max(20, target_speed)
                for _ in range(batch_size):
                    st = runner.step_once()
                
                # Decoupled Observer Broadcast: 50 Hz streaming for smooth 60 FPS display
                now = time.perf_counter()
                if now - last_broadcast >= 0.02:
                    if st is not None:
                        await runner.broadcast_state(st)
                    last_broadcast = now
                await asyncio.sleep(0)
        else:
            await asyncio.sleep(0.1)

async def start_background_tasks(app):
    print("[GENESIS SERVER] Starting background simulation loop...", flush=True)
    sim_task = asyncio.create_task(simulation_loop())
    yield
    sim_task.cancel()
    try:
        await sim_task
    except asyncio.CancelledError:
        pass

async def index_handler(request):
    return web.FileResponse(PUBLIC_DIR / "embodied_deck.html")

async def static_file_handler(request):
    filename = request.match_info.get("filename", "")
    target = PUBLIC_DIR / filename
    if filename and target.exists() and target.is_file():
        return web.FileResponse(target)
    return web.FileResponse(PUBLIC_DIR / "embodied_deck.html")

def init_app():
    app = web.Application()
    app.cleanup_ctx.append(start_background_tasks)
    app.router.add_get("/ws", ws_handler)
    app.router.add_get("/", index_handler)
    app.router.add_get("/embodied_deck.html", index_handler)
    app.router.add_get("/{filename:.*}", static_file_handler)
    return app

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test-headless":
        print("[TEST] Running 100 headless ticks on Python Core Engine...", flush=True)
        for _ in range(100):
            runner.step_once()
        print(f"[TEST SUCCESS] 100 ticks completed. Energy: {runner.energy:.1f}, Goals: {runner.goals_solved}", flush=True)
        sys.exit(0)

    app = init_app()
    port = int(os.environ.get("PORT", 8088))
    print("=" * 70, flush=True)
    print(f"🚀 GENESIS Python Brain Server (Substrate 8) Online on Port {port}", flush=True)
    print(f"📡 WebSocket & HTTP UI serving at: http://localhost:{port}/embodied_deck.html", flush=True)
    print("=" * 70, flush=True)
    web.run_app(app, host="0.0.0.0", port=port)
