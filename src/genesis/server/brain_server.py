from aiohttp import web, WSMsgType
import numpy as np
import asyncio
from collections import deque
import math
import time
import json
from numba import njit
from genesis_pytorch_brain import GenesisPyTorchBrain
import os
import sys
from pathlib import Path

# Ensure local server directory is discoverable on sys.path
SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))


# Repository Root & Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BRAIN_DIR = REPO_ROOT / "Brain"
PUBLIC_DIR = REPO_ROOT / "public"
BRAIN_DIR.mkdir(exist_ok=True, parents=True)


# Architectural Hyperparameters
GRID_SIZE = 24
VISION_SIZE = 7
N_CHANNELS = 7
VISUAL_DIM = VISION_SIZE * VISION_SIZE * N_CHANNELS  # 343
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
def numba_diffuse_chem(chem: np.ndarray, grid: np.ndarray, D: np.float32, decay: np.float32):
    rows, cols = chem.shape
    new_chem = np.empty_like(chem)
    for y in range(rows):
        for x in range(cols):
            if grid[y, x] == 1:
                new_chem[y, x] = np.float32(0.0)
                continue

            val = chem[y, x]
            sum_neighbors = np.float32(0.0)
            sum_neighbors += chem[y+1, x] if y < rows - \
                1 and grid[y+1, x] != 1 else val
            sum_neighbors += chem[y-1,
                                  x] if y > 0 and grid[y-1, x] != 1 else val
            sum_neighbors += chem[y, x+1] if x < cols - \
                1 and grid[y, x+1] != 1 else val
            sum_neighbors += chem[y, x -
                                  1] if x > 0 and grid[y, x-1] != 1 else val

            laplacian = sum_neighbors - np.float32(4.0) * val
            new_val = val + D * laplacian - decay * val
            new_chem[y, x] = max(np.float32(0.0), np.float32(new_val))

    for y in range(rows):
        for x in range(cols):
            chem[y, x] = new_chem[y, x]


@njit(fastmath=True, nogil=True)
def numba_get_visual_observation(grid: np.ndarray, chem: np.ndarray, agent_x: int, agent_y: int, agent_dir: int, vision_size: int, n_channels: int) -> np.ndarray:
    half = vision_size // 2
    obs = np.zeros(vision_size * vision_size * n_channels, dtype=np.float32)
    idx = 0
    for vy in range(-half, half + 1):
        for vx in range(-half, half + 1):
            gx = agent_x
            gy = agent_y
            if agent_dir == 0:
                gx += vy
                gy += vx
            elif agent_dir == 1:
                gx += vx
                gy -= vy
            elif agent_dir == 2:
                gx -= vy
                gy -= vx
            elif agent_dir == 3:
                gx -= vx
                gy += vy

            if 0 <= gx < 24 and 0 <= gy < 24:
                cell = grid[gx, gy]
                if 0 <= cell < 6:
                    obs[idx * n_channels + cell] = np.float32(1.0)
                obs[idx * n_channels + 6] = chem[gx, gy] / \
                    np.float32(100.0)  # scale down for observation
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
                    q = tree_val_sum[child_idx] / \
                        np.float32(max(1, tree_visit[child_idx]))
                    n = tree_visit[child_idx]

                u = effective_cpuct * tree_policy[curr_node, a] * np.sqrt(
                    np.float32(tree_visit[curr_node] + 1)) / (np.float32(1.0) + n)
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
            q_values[a] = tree_reward[child_idx] + np.float32(0.95) * (
                tree_val_sum[child_idx] / np.float32(max(1, tree_visit[child_idx])))
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
    W_dyn += np.float32(0.005) * G - np.float32(1e-6) * \
        W_dyn - np.float32(0.005) * ewc_pen

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
    W_policy += np.float32(0.005) * np.outer(s_curr,
                                             grad_p * td_err) - np.float32(1e-6) * W_policy

    return loss_dyn / np.float32(32.0), v_curr


class GenesisNumbaBrain:
    def __init__(self):
        self.rng = np.random.RandomState(42)
        self.init_weights()
        self.hippocampus = []
        self.fisher_diag = {"W_dyn": np.zeros(
            (D_MODEL + N_ACTIONS, D_MODEL), dtype=np.float32)}
        self.anchor_weights = {"W_dyn": self.W_dyn.copy()}
        self._warmup_numba()

    def _warmup_numba(self):
        d_obs = np.zeros(VISUAL_DIM, dtype=np.float32)
        d_text = np.zeros(D_MODEL, dtype=np.float32)
        d_priors = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float32)
        d_grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        d_chem = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.float32)

        numba_get_visual_observation(
            d_grid, d_chem, 3, 3, 0, VISION_SIZE, N_CHANNELS)
        numba_diffuse_chem(d_chem, d_grid, np.float32(0.5),
                           np.float32(1.0/8192.0))
        s = numba_forward_transformer(
            d_obs, d_text, self.W_vis, self.W_fuse_vis, self.W_fuse_lang,
            self.W_q, self.W_k, self.W_v, self.W_out, self.W_ff1, self.W_ff2
        )
        numba_mcts_eval(s, self.W_dyn, self.W_rew, self.W_val,
                        self.W_policy, d_priors, 0.8, 4)
        numba_update_neural_weights(
            s, 0, np.float32(
                0.0), s, self.W_dyn, self.W_rew, self.W_val, self.W_policy,
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
        emb = np.mean([self.W_lang[t]
                      for t in tokens], axis=0).astype(np.float32)
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

        noise = - \
            np.log(np.maximum(1e-6, self.rng.uniform(0.0, 1.0, N_ACTIONS)))
        noise /= (np.sum(noise) + 1e-9)
        eps_noise = 0.20 if policy_mode == "DIRECTED" else 0.40
        noisy_priors = ((1.0 - eps_noise) * priors +
                        eps_noise * noise).astype(np.float32)

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
        if len(self.hippocampus) < 10:
            return 0
        replays = min(50, len(self.hippocampus))
        for _ in range(replays):
            idx = self.rng.randint(0, len(self.hippocampus))
            mem = self.hippocampus[idx]
            numba_update_neural_weights(
                mem["s_curr"], mem["action"], np.float32(
                    mem["reward"]), mem["s_next"],
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


# ---- Phase A constants (Rule 17 provenance tags) ----
# [H] CELL_STATES(256)/BITS_PER_BYTE(8) — elementary info-income quantum
U_QUANTUM = 32.0
# [S] structural constant: rejection-sampling budget
GEN_MAX_ATTEMPTS = 64
# [E] documented exposure horizon (full tank drain while standing)
HAZARD_LETHAL_TICKS = 20
COLLISION_K = 1.0


class GenesisEnvironment:
    def __init__(self):
        self.grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        self.chem = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.float32)
        self.agent_pos = [3, 2]
        self.agent_dir = 2
        self.has_key = False
        self.door_opened = False
        self.episode_seed = 0
        self.size = 12
        self.difficulty = self.base_difficulty()
        # injected by runner (= its metabolic_cost)
        self.tick_cost = 0.0
        self.max_energy_hint = 0.0
        self.on_hazard = False
        self.reset_episode(seed=0)

    @staticmethod
    def base_difficulty():
        # All values [E]-class generator parameters (NOT reward knobs)
        return {"size": 12, "wall_density": 0.02, "gaps": 1,
                "lock": False, "hazard_density": 0.01, "food": 2}

    # -- reachability primitive (also measures door ΔReach for income) --
    def _bfs(self, sy: int, sx: int, treat_door_as_wall: bool):
        dist = -np.ones((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        blocked = (2,) if treat_door_as_wall else ()
        dq = deque([(sy, sx)])
        dist[sy, sx] = 0
        while dq:
            y, x = dq.popleft()
            for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                ny, nx_ = y+dy, x+dx
                if 0 <= ny < GRID_SIZE and 0 <= nx_ < GRID_SIZE \
                        and dist[ny, nx_] == -1 \
                        and self.grid[ny, nx_] not in (1,) + blocked:
                    dist[ny, nx_] = dist[y, x] + 1
                    dq.append((ny, nx_))
        return dist

    def _bfs_open_all(self):
        return self._bfs(self.agent_pos[0], self.agent_pos[1], treat_door_as_wall=False)

    def _reachable_count(self, sy, sx):
        d = self._bfs(sy, sx, treat_door_as_wall=False)
        return int((d >= 0).sum())

    def reset_episode(self, seed: int, difficulty: dict | None = None):
        self.episode_seed = int(seed)
        if difficulty is not None:
            self.difficulty.update(difficulty)
        d = self.difficulty
        S = int(np.clip(d["size"], 8, GRID_SIZE))
        self.size = S
        rng = np.random.default_rng(self.episode_seed)

        layout = self._generate(rng, S, d)
        if layout is None:                       # deterministic fallback: open arena
            layout = self._fallback(rng, S)
        self.grid[:] = layout["grid"]
        self.chem[:] = 0.0
        self.agent_pos = layout["spawn"]
        self.agent_dir = layout["dir"]
        self.has_key = False
        self.door_opened = False
        self.on_hazard = False

    def _generate(self, rng, S, d):
        for _ in range(GEN_MAX_ATTEMPTS):
            g = np.ones((GRID_SIZE, GRID_SIZE), dtype=np.int32)
            # playable island in fixed 24×24 buffer
            g[:S, :S] = 0

            # Border walls at active S x S boundaries
            g[0, :S] = 1
            g[S-1, :S] = 1
            g[:S, 0] = 1
            g[:S, S-1] = 1

            for _ in range(int(S * S * d.get("wall_density", 0.02))):  # scattered segments
                y, x = rng.integers(1, S - 1, 2)
                vert = rng.random() < 0.5
                for k in range(int(rng.integers(2, max(3, S // 4)))):
                    yy, xx = (y + k, x) if vert else (y, x + k)
                    if 0 < yy < S - 1 and 0 < xx < S - 1:
                        g[yy, xx] = 1

            # partition wall + openings (generalizes the Level-3/4 bottleneck)
            axis = int(rng.integers(2))
            cut = int(rng.integers(S // 3, max(S // 3 + 1, 2 * S // 3)))
            if axis == 0:
                g[cut, :S] = 1
            else:
                g[:S, cut] = 1
            gaps = rng.choice(np.arange(1, S - 1),
                              size=int(d.get("gaps", 1)), replace=False)
            for i, gc in enumerate(gaps):
                if axis == 0:
                    g[cut, int(gc)] = 0
                else:
                    g[int(gc), cut] = 0
            locked_gap = None
            # seal one opening with a keyed door
            if d.get("lock", False):
                li = int(rng.integers(len(gaps)))
                locked_gap = int(gaps[li])
                if axis == 0:
                    g[cut, locked_gap] = 5                   # 5 = Lock / Door
                else:
                    g[locked_gap, cut] = 5

            free = np.argwhere(g[:S, :S] == 0)
            if len(free) < 8:
                continue
            spawn = free[int(rng.integers(len(free)))]

            probe = GenesisEnvironment.__new__(
                GenesisEnvironment)  # BFS sandbox on candidate
            probe.grid = g.copy()
            dist_locked = probe._bfs(int(spawn[0]), int(
                spawn[1]), treat_door_as_wall=True)
            if locked_gap is not None:
                gy, gx_ = (cut, locked_gap) if axis == 0 else (locked_gap, cut)
                side_a = dist_locked[:S, :S] >= 0
                # both sides must exist pre-unlock, key on spawn side
                key_cands = [(y, x) for y, x in free if side_a[y, x]]
                if not key_cands:
                    continue
            else:
                key_cands = []

            if (dist_locked[:S, :S][free[:, 0], free[:, 1]] < 0).any():
                continue                                     # disconnected pocket → reject

            # goal at deep-BFS cell
            probe.grid = g
            probe.agent_pos = [int(spawn[0]), int(spawn[1])]
            d_open = probe._bfs_open_all()

            far = free[d_open[free[:, 0], free[:, 1]] >= np.quantile(
                d_open[free[:, 0], free[:, 1]], 0.75)]
            if len(far) == 0:
                continue
            goal = far[int(rng.integers(len(far)))]
            g[int(goal[0]), int(goal[1])] = 3                # 3 = Food / Goal
            if locked_gap is not None and not key_cands:
                continue
            if key_cands:
                kc = key_cands[int(rng.integers(len(key_cands)))]
                g[int(kc[0]), int(kc[1])] = 4                # 4 = Key

            # hazards (2)
            corridor = set()
            cy, cx = int(goal[0]), int(goal[1])
            while d_open[cy, cx] > 0:
                corridor.add((cy, cx))
                for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    ny, nx_ = cy+dy, cx+dx
                    if 0 <= ny < S and 0 <= nx_ < S and d_open[ny, nx_] == d_open[cy, cx] - 1:
                        cy, cx = ny, nx_
                        break
            hz_pool = [(y, x) for y, x in free
                       if g[y, x] == 0 and (y, x) != tuple(spawn) and (y, x) not in corridor]
            n_hz = min(len(hz_pool), int(
                round(d.get("hazard_density", 0.01) * S * S)))
            for hy, hx in rng.permutation(hz_pool)[:n_hz]:
                g[hy, hx] = 2                                # 2 = Hazard

            # food (3)
            fd_pool = [(y, x) for y, x in free if g[y, x]
                       == 0 and (y, x) != tuple(spawn)]
            for fy, fx in rng.permutation(fd_pool)[:int(d.get("food", 2))]:
                g[fy, fx] = 3                                # 3 = Food

            direction = int(np.argmax([
                g[spawn[0]-1, spawn[1]] == 0 if spawn[0] > 0 else False,
                g[spawn[0], spawn[1]+1] == 0 if spawn[1] < S - 1 else False,
                g[spawn[0]+1, spawn[1]] == 0 if spawn[0] < S - 1 else False,
                g[spawn[0], spawn[1]-1] == 0 if spawn[1] > 0 else False
            ]))
            return {"grid": g, "spawn": [int(spawn[0]), int(spawn[1])], "dir": direction}
        return None

    def _fallback(self, rng, S):
        g = np.ones((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        g[:S, :S] = 0
        g[0, :S] = 1
        g[S-1, :S] = 1
        g[:S, 0] = 1
        g[:S, S-1] = 1
        g[S-3, S-3] = 3
        return {"grid": g, "spawn": [2, 2], "dir": 1}

    def get_visual_observation(self) -> np.ndarray:
        return numba_get_visual_observation(
            self.grid, self.chem, self.agent_pos[0], self.agent_pos[1], self.agent_dir,
            VISION_SIZE, N_CHANNELS
        )

    def diffuse(self):
        numba_diffuse_chem(self.chem, self.grid,
                           np.float32(0.5), np.float32(1.0/8192.0))

    def step(self, action: int) -> tuple:
        dirs = [(-1, 0), (0, 1), (1, 0), (0, -1)]
        reward = 0.0
        event = None

        if action == 0:  # FORWARD
            dx, dy = dirs[self.agent_dir % 4]
            nx, ny = self.agent_pos[0] + dx, self.agent_pos[1] + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                cell = self.grid[nx, ny]
                if cell == 1:
                    # [E] wasted motion budget
                    reward = -self.tick_cost * COLLISION_K
                elif cell == 5:                                  # 5 = Lock / Door
                    if self.has_key:
                        before = self._reachable_count(*self.agent_pos)
                        self.grid[nx, ny] = 0
                        self.door_opened = True
                        after = self._reachable_count(nx, ny)
                        self.agent_pos = [nx, ny]
                        delta = max(after - before, 2)
                        # [H] measured freed territory
                        reward = U_QUANTUM * math.ceil(math.log2(delta))
                        event = "DOOR_UNLOCKED"
                    else:
                        reward = -self.tick_cost                  # blocked attempt = burned budget
                elif cell == 2:                                  # 2 = Hazard
                    self.agent_pos = [nx, ny]
                    # [E] dose, not spike
                    reward -= self.hazard_dose()
                    if not self.on_hazard:
                        event = "HAZARD_HIT"
                    self.on_hazard = True
                elif cell == 3:                                  # 3 = Food / Goal
                    self.grid[nx, ny] = 0
                    self.agent_pos = [nx, ny]
                    self.on_hazard = False
                    reward += U_QUANTUM
                    event = "FOOD_HARVESTED"
                elif cell == 4:                                  # 4 = Key
                    self.grid[nx, ny] = 0
                    self.has_key = True
                    self.agent_pos = [nx, ny]
                    self.on_hazard = False
                    reward += U_QUANTUM
                    event = "KEY_PICKED"
                else:                                            # 0 = Floor
                    self.agent_pos = [nx, ny]
                    self.on_hazard = False
        elif action in (1, 2):
            self.agent_dir = (self.agent_dir + (-1 if action == 1 else 1)) % 4
            self.on_hazard = False
        elif action == 3:  # INTERACT
            self.on_hazard = False
            cell = self.grid[self.agent_pos[0], self.agent_pos[1]]
            if cell == 4 and not self.has_key:
                self.has_key = True
                self.grid[self.agent_pos[0], self.agent_pos[1]] = 0
                reward += U_QUANTUM
                event = "KEY_PICKED"
            elif cell == 3:
                reward += U_QUANTUM * math.ceil(math.log2(self.size ** 2))
                event = "GOAL_SOLVED"
            elif cell == 0:
                self.chem[self.agent_pos[0], self.agent_pos[1]] = min(
                    1000.0, self.chem[self.agent_pos[0], self.agent_pos[1]] + 256.0)
                event = "PHEROMONE_EMITTED"
        return reward, event

    def hazard_dose(self):
        # runner injects max_energy_hint
        return (self.max_energy_hint / HAZARD_LETHAL_TICKS)


class GenesisEngineRunner:
    def __init__(self):
        self.brain = GenesisPyTorchBrain()
        self.env = GenesisEnvironment()
        self.is_running = False  # Changed to False so simulation waits for UI
        self.speed = 1
        self.tick_count = 0

        # Grounded Initial Energy (Rule 21.3)
        # FOOTPRINT_QUANTUM = 898.0 energy/byte (Exp 91 Baseline)
        footprint_bytes = self.brain.get_footprint_bytes()
        self.max_energy = footprint_bytes / 898.0
        self.energy = self.max_energy

        # Grounded Metabolic Cost
        self.metabolic_cost = footprint_bytes / \
            (898.0 * 2000.0)  # ~ 0.06 per tick

        self.goals_solved = 0
        self.food_harvested = 0
        self.doors_unlocked = 0
        self.hazard_collisions = 0
        self.policy_mode = "DIRECTED"
        self.active_task_text = "EXPLORE & SURVIVE"
        self.connected_websockets = set()

        self.win_income = 0.0
        self.win_ticks = 0
        self.episode_seed = 0

        self.env.tick_cost = self.metabolic_cost
        self.env.max_energy_hint = self.max_energy
        self.env.reset_episode(seed=self.episode_seed)
        self.brain.state_history.clear()

        # Load existing brain if available
        ckpt_path = BRAIN_DIR / "canonical_brain.npz"
        if ckpt_path.exists():
            try:
                self.brain.load_checkpoint(ckpt_path)
                print(
                    f"[GENESIS CORE] Successfully loaded canonical brain from {ckpt_path}")
            except Exception as e:
                print(f"[GENESIS CORE] Checkpoint load note: {e}")

    def _end_episode(self, success: bool):
        self.episode_seed = (self.episode_seed + 1) % (2**31)
        self.env.reset_episode(seed=self.episode_seed)
        self.brain.state_history.clear()

    def step_once(self) -> dict:
        self.tick_count += 1
        self.energy -= self.metabolic_cost

        obs = self.env.get_visual_observation()
        s_curr = self.brain.forward_transformer(obs, self.active_task_text)
        mcts_info = self.brain.run_hierarchical_mcts(s_curr, self.policy_mode)

        # In Substrate 12, we get both option, action and emitted symbol
        probs = np.array(mcts_info["action_probs"], dtype=np.float64)
        probs /= (np.sum(probs) + 1e-9)
        action = int(self.brain.rng.choice(N_ACTIONS, p=probs))

        self.prev_option = mcts_info["selected_option"]
        self.prev_symbol = mcts_info.get("emitted_symbol", 0)

        reward, event = self.env.step(action)
        self.energy = min(self.max_energy, max(0.0, self.energy + reward))

        if event == "FOOD_HARVESTED":
            self.food_harvested += 1
        elif event == "DOOR_UNLOCKED":
            self.doors_unlocked += 1
        elif event == "HAZARD_HIT":
            self.hazard_collisions += 1
        elif event == "GOAL_SOLVED":
            self.goals_solved += 1
            self._end_episode(True)

        # competence accumulator (incomes only — physical gains):
        if reward > 0:
            self.win_income += reward
        self.win_ticks += 1
        COMP_WINDOW = 500        # [S] structural
        EFF_HI, EFF_LO = 1.3, 0.6  # [E] documented surplus-ratio bands
        if self.win_ticks >= COMP_WINDOW:
            eff = self.win_income / \
                max(self.win_ticks * self.metabolic_cost, 1e-9)
            d = self.env.difficulty
            if eff > EFF_HI:
                d["size"] = min(24, d["size"] + 2)
                d["lock"] = True
            elif eff < EFF_LO:
                d["size"] = max(8, d["size"] - 2)
            print(f"[GENESIS] competence={eff:.2f} → {d}")
            self.win_income = 0.0
            self.win_ticks = 0

        self.env.diffuse()
        next_obs = self.env.get_visual_observation()
        s_next = self.brain.forward_transformer(
            next_obs, self.active_task_text)

        is_term = (self.energy <= 0.0) or (event == "GOAL_SOLVED")

        if hasattr(self, 'prev_option'):
            self.brain.update_hierarchical_experience(
                s_curr, self.prev_option, self.prev_symbol, action, reward, s_next, is_term)

        metrics = self.brain.update_neural_weights(
            s_curr, action, reward, s_next, is_terminal=is_term, is_replay=False)

        # Prioritized Mini-batch replay
        if len(self.brain.hippocampus) >= 32:
            surprises = np.array([m.get("surprise", 1e-5)
                                 for m in self.brain.hippocampus], dtype=np.float32)
            np.nan_to_num(surprises, nan=1e-5, posinf=1.0,
                          neginf=1e-5, copy=False)
            np.maximum(surprises, 1e-6, out=surprises)
            s_sum = float(np.sum(surprises))
            if s_sum <= 0.0 or not np.isfinite(s_sum):
                probs = np.ones(len(self.brain.hippocampus),
                                dtype=np.float64) / len(self.brain.hippocampus)
            else:
                probs = (surprises / s_sum).astype(np.float64)
                probs /= np.sum(probs)
            indices = self.brain.rng.choice(
                len(self.brain.hippocampus), size=32, p=probs)

            s_curr_b = np.stack(
                [self.brain.hippocampus[idx]["s_curr"] for idx in indices])
            action_b = np.array([self.brain.hippocampus[idx]["action"]
                                for idx in indices], dtype=np.int64)
            reward_b = np.array([self.brain.hippocampus[idx]["reward"]
                                for idx in indices], dtype=np.float32)
            s_next_b = np.stack(
                [self.brain.hippocampus[idx]["s_next"] for idx in indices])
            term_b = np.array([self.brain.hippocampus[idx].get(
                "is_terminal", False) for idx in indices], dtype=bool)

            batch_metrics = self.brain.update_neural_weights_batch(
                s_curr_b, action_b, reward_b, s_next_b, term_b)

            for i, idx in enumerate(indices):
                self.brain.hippocampus[idx]["surprise"] = float(
                    batch_metrics["td_errs"][i]) + 1e-5

        if self.energy <= 0.0:
            self.energy = self.max_energy
            self._end_episode(False)

        is_sleeping = False
        if self.tick_count > 0 and self.tick_count % 2000 == 0 and len(self.brain.hippocampus) > 100:
            print(
                f"[GENESIS CORE] Circadian Rhythm Triggered: Sleep Consolidation (Tick {self.tick_count})")
            self.brain.sleep_consolidation()
            is_sleeping = True

        if self.tick_count % 1000 == 0:
            save_path = BRAIN_DIR / "canonical_brain.npz"
            self.brain.save_checkpoint(save_path)

        return self._build_payload(obs, mcts_info, metrics, is_sleeping)

    def _build_payload(self, obs, mcts_info, metrics, is_sleeping=False) -> dict:
        s = self.env.size
        grid_flat = self.env.grid[:s, :s].flatten().tolist()
        chem_flat = self.env.chem[:s, :s].flatten().tolist()
        v_curr = float(metrics.get("vCurr", 0.0))
        loss_val = float(metrics.get("loss", 0.0))
        energy_ratio = float(
            max(0.0, min(1.0, self.energy / max(1.0, self.max_energy))))

        opt_id = int(mcts_info.get("selected_option", 0))
        opt_names = ["EXPLORE", "EXPLOIT", "FORAGE", "AVOID",
                     "SEEK-KEY", "FOLLOW-GRAD", "PATROL", "RETREAT"]
        opt_label = opt_names[opt_id % len(opt_names)]

        def sanitize_floats(obj):
            if isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return 0.0
                return obj
            elif isinstance(obj, dict):
                return {k: sanitize_floats(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_floats(v) for v in obj]
            return obj

        payload = {
            "type": "STATE_UPDATE",
            "tick": int(self.tick_count),
            "energy": max(0.0, float(self.energy)),
            "generation": int(self.episode_seed + 1),
            "difficulty": self.env.difficulty,
            "seed": int(self.env.episode_seed),
            "goals": int(self.goals_solved),
            "food": int(self.food_harvested),
            "doors": int(self.doors_unlocked),
            "hazards": int(self.hazard_collisions),
            "hasKey": bool(self.env.has_key),
            "agentPos": [int(self.env.agent_pos[0]), int(self.env.agent_pos[1])],
            "agentDir": int(self.env.agent_dir),
            "grid": grid_flat,
            "chem": chem_flat,
            "obs": obs.tolist() if hasattr(obs, 'tolist') else list(obs),
            "mcts": mcts_info,
            "vVal": v_curr,
            "loss": loss_val,
            "hippoCount": int(len(self.brain.hippocampus)),
            "policyMode": str(self.policy_mode),
            "activeTask": str(self.active_task_text),
            "isSleeping": bool(is_sleeping),
            # Nested schema matching the observation deck perfectly
            "env": {
                "w": s, "h": s,
                "grid": grid_flat,
                "chem": chem_flat,
                "agent": {
                    "x": int(self.env.agent_pos[1]),
                    "y": int(self.env.agent_pos[0]),
                    "dir": int(self.env.agent_dir)
                },
                "hasKey": bool(self.env.has_key)
            },
            "meta": {
                "energy": energy_ratio,
                "hippo": {
                    "count": int(len(self.brain.hippocampus)),
                    "cap": 5000
                },
                "entropyIncome": float(abs(v_curr))
            },
            "cog": {
                "symbol": int(mcts_info.get("emitted_symbol", 0)),
                "optionId": opt_id,
                "optionLabel": opt_label,
                "actionProbs": [float(p) for p in mcts_info.get("action_probs", [0.25, 0.25, 0.25, 0.25])],
                "concepts": [float(c) for c in self.brain.state_history[-1][:16]] if self.brain.state_history else [0.0]*16,
                "tree": mcts_info
            },
            "learning": self.brain.get_learning_telemetry()
        }
        return sanitize_floats(payload)

    async def broadcast_state(self, payload: dict):
        if not self.connected_websockets:
            return
        try:
            msg = json.dumps(payload)
        except Exception as e:
            print(f"[GENESIS SERVER] Payload JSON dump error: {e}", flush=True)
            return

        dead_ws = set()
        for ws in list(self.connected_websockets):
            try:
                if not ws.closed:
                    await ws.send_str(msg)
                else:
                    dead_ws.add(ws)
            except Exception as e:
                print(f"[GENESIS SERVER] WS send error: {e}", flush=True)
                dead_ws.add(ws)
        if dead_ws:
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
    runner.is_running = True
    print(
        f"[GENESIS SERVER] Client connected via WebSocket. Active clients: {len(runner.connected_websockets)}", flush=True)

    # Send current state immediately without blocking
    try:
        init_obs = runner.env.get_visual_observation()
        init_state = runner._build_payload(
            init_obs, {}, {"vCurr": 0.0, "loss": 0.0})
        await ws.send_str(json.dumps(init_state))
    except Exception as e:
        print(f"[GENESIS SERVER] Initial state error: {e}", flush=True)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                cmd = data.get("action") or data.get("type")
                if cmd == "SET_SPEED":
                    runner.speed = int(data.get("value", 1))
                elif cmd == "SET_DIFFICULTY":
                    runner.env.reset_episode(
                        seed=runner.episode_seed, difficulty=data.get("value"))
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
                elif cmd in ("USER_CHAT", "chat"):
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
                    runner.env.reset_episode(
                        seed=0, difficulty=runner.env.base_difficulty())
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
        print(
            f"[GENESIS SERVER] Client disconnected. Active clients: {len(runner.connected_websockets)}", flush=True)
    return ws


async def simulation_loop():
    loop = asyncio.get_running_loop()
    while True:
        try:
            if runner.is_running and runner.connected_websockets:
                # Offload heavy PyTorch/Numba computation to thread pool so WebSocket never starves
                st = await loop.run_in_executor(None, runner.step_once)
                await runner.broadcast_state(st)
                delay = 0.08 / max(1, runner.speed)
                await asyncio.sleep(delay)
            else:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            import traceback
            print(f"[GENESIS SIM LOOP ERROR]: {e}", flush=True)
            traceback.print_exc()
            await asyncio.sleep(0.5)


async def on_startup(app):
    print("[GENESIS SERVER] Starting background simulation loop...", flush=True)
    app['sim_task'] = asyncio.create_task(simulation_loop())


async def on_cleanup(app):
    sim_task = app.get('sim_task')
    if sim_task:
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
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
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
        print(
            f"[TEST SUCCESS] 100 ticks completed. Energy: {runner.energy:.1f}, Goals: {runner.goals_solved}", flush=True)
        sys.exit(0)

    app = init_app()
    port = int(os.environ.get("PORT", 8088))
    print("=" * 70, flush=True)
    print(
        f"🚀 GENESIS Python Brain Server (Substrate 8) Online on Port {port}", flush=True)
    print(
        f"📡 WebSocket & HTTP UI serving at: http://localhost:{port}/embodied_deck.html", flush=True)
    print("=" * 70, flush=True)
    web.run_app(app, host="0.0.0.0", port=port)
