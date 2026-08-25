import torch
import torch.nn.functional as F
import numpy as np
import math
from pathlib import Path

VISUAL_DIM = 7 * 7 * 6  # 294
D_MODEL = 32
N_ACTIONS = 4
MAX_TEXT_LEN = 16
VOCAB_SIZE = 64
MCTS_SIMS_DIRECTED = 6 # Depth of quantum parallel search
MCTS_SIMS_EXPLORE = 6 # Depth

class GenesisPyTorchBrain:
    def __init__(self, device="cuda"):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        
        self.rng = np.random.RandomState(42)
        self.hippocampus = []
        self.init_weights()
        self.fisher_diag = {"W_dyn": torch.zeros((D_MODEL + N_ACTIONS, D_MODEL), dtype=self.dtype, device=self.device)}
        self.anchor_weights = {"W_dyn": self.W_dyn.clone()}

    def _rand_mat(self, rows, cols, std=0.05):
        val = (self.rng.uniform(-1.0, 1.0, (rows, cols)) * math.sqrt(3) * std)
        return torch.tensor(val, dtype=self.dtype, device=self.device)

    def get_footprint_bytes(self) -> int:
        total_bytes = 0
        for attr_name in dir(self):
            if attr_name.startswith("W_"):
                attr = getattr(self, attr_name)
                if isinstance(attr, torch.Tensor):
                    total_bytes += attr.element_size() * attr.numel()
        return total_bytes

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
        # 1D for rewards and vals
        self.W_rew = self._rand_mat(D_MODEL + N_ACTIONS, 1, 0.05).squeeze(-1)
        self.W_val = self._rand_mat(D_MODEL, 1, 0.05).squeeze(-1)
        self.W_policy = self._rand_mat(D_MODEL, N_ACTIONS, 0.05)

    def encode_text(self, text_str: str) -> torch.Tensor:
        clean = (text_str or "").upper()[:MAX_TEXT_LEN]
        tokens = [ord(c) % VOCAB_SIZE for c in clean]
        if not tokens:
            tokens = [0]
        # Get mean of language embeddings
        embs = torch.stack([self.W_lang[t] for t in tokens])
        return embs.mean(dim=0)

    @torch.no_grad()
    def forward_transformer(self, obs_vis: np.ndarray, text_str: str) -> np.ndarray:
        obs = torch.tensor(obs_vis, dtype=self.dtype, device=self.device)
        text_emb = self.encode_text(text_str)
        
        z_vis = torch.matmul(obs, self.W_vis)
        fused_v = torch.matmul(z_vis, self.W_fuse_vis)
        fused_l = torch.matmul(text_emb, self.W_fuse_lang)
        fused = torch.tanh(fused_v + fused_l)
        
        Q = torch.matmul(fused, self.W_q)
        K = torch.matmul(fused, self.W_k)
        V = torch.matmul(fused, self.W_v)
        
        score = torch.matmul(Q, K) / 5.656854
        attn = torch.sigmoid(score)
        mixed = fused + attn * V
        
        ff1 = torch.relu(torch.matmul(mixed, self.W_ff1))
        ff2 = torch.matmul(ff1, self.W_ff2)
        out = mixed + ff2
        return out.cpu().numpy().astype(np.float32)

    @torch.no_grad()
    def run_mcts(self, root_state_np: np.ndarray, policy_mode: str = "DIRECTED") -> dict:
        # Quantum Search (Batched Tensor Rollout)
        root_state = torch.tensor(root_state_np, dtype=self.dtype, device=self.device)
        
        logits = torch.matmul(root_state, self.W_policy)
        max_l = torch.max(logits)
        exp_l = torch.exp(logits - max_l)
        priors = exp_l / (torch.sum(exp_l) + 1e-9)
        
        noise_np = -np.log(np.maximum(1e-6, self.rng.uniform(0.0, 1.0, N_ACTIONS)))
        noise_np /= (np.sum(noise_np) + 1e-9)
        noise = torch.tensor(noise_np, dtype=self.dtype, device=self.device)
        
        eps_noise = 0.20 if policy_mode == "DIRECTED" else 0.40
        noisy_priors = (1.0 - eps_noise) * priors + eps_noise * noise
        
        depth = MCTS_SIMS_DIRECTED if policy_mode == "DIRECTED" else MCTS_SIMS_EXPLORE
        
        states = root_state.unsqueeze(0)
        total_paths = 4 ** depth
        returns = torch.zeros(total_paths, device=self.device, dtype=self.dtype)
        first_actions = torch.arange(4, device=self.device).repeat_interleave(4 ** (depth - 1))
        
        discount = 1.0
        for d in range(depth):
            num_paths = states.shape[0]
            states = states.repeat_interleave(4, dim=0)
            actions = torch.arange(4, device=self.device).repeat(num_paths)
            actions_onehot = F.one_hot(actions, num_classes=4).to(dtype=self.dtype)
            
            sa = torch.cat([states, actions_onehot], dim=1)
            next_states = torch.tanh(torch.matmul(sa, self.W_dyn))
            r = torch.matmul(sa, self.W_rew.unsqueeze(-1)).squeeze(-1)
            
            r_expanded = r.repeat_interleave(4 ** (depth - d - 1))
            returns += discount * r_expanded
            states = next_states
            discount *= 0.95
            
        leaf_vals = torch.matmul(states, self.W_val.unsqueeze(-1)).squeeze(-1)
        returns += discount * leaf_vals
        
        q_values = torch.zeros(4, device=self.device, dtype=self.dtype)
        for a in range(4):
            mask = (first_actions == a)
            q_values[a] = returns[mask].mean()
            
        # Min-Max normalize Q-values (AlphaZero standard) to prevent softmax saturation
        q_min = torch.min(q_values)
        q_max = torch.max(q_values)
        if q_max > q_min:
            q_norm = (q_values - q_min) / (q_max - q_min)
        else:
            q_norm = torch.zeros_like(q_values)
            
        cpuct = 0.8 if policy_mode == "DIRECTED" else 1.4
        score = q_norm + cpuct * noisy_priors
        
        temperature = 0.5 if policy_mode == "DIRECTED" else 1.5
        scaled_score = score / temperature
        
        max_score = torch.max(scaled_score)
        exp_score = torch.exp(scaled_score - max_score)
        probs_tensor = exp_score / (torch.sum(exp_score) + 1e-9)
        
        probs = probs_tensor.cpu().numpy().astype(np.float32)
        visit_counts = np.full(4, 4**(depth-1), dtype=np.int32)
        
        return {
            "probs": probs.tolist(),
            "qValues": q_values.cpu().numpy().astype(np.float32).tolist(),
            "visitCounts": visit_counts.tolist()
        }

    @torch.no_grad()
    def update_neural_weights(self, s_curr_np: np.ndarray, action: int, reward: float, s_next_np: np.ndarray) -> dict:
        s_curr = torch.tensor(s_curr_np, dtype=self.dtype, device=self.device)
        s_next = torch.tensor(s_next_np, dtype=self.dtype, device=self.device)
        rew_val = float(reward)
        
        sa = torch.zeros(36, dtype=self.dtype, device=self.device)
        sa[:32] = s_curr
        sa[32 + action] = 1.0
        
        pred_next = torch.tanh(torch.matmul(sa, self.W_dyn))
        err_dyn = s_next - pred_next
        loss_dyn = torch.sum(err_dyn ** 2)
        
        grad_d = err_dyn * (1.0 - pred_next ** 2)
        G = torch.outer(sa, grad_d)
        self.fisher_diag["W_dyn"] += (G ** 2) * 0.01
        ewc_pen = 0.5 * self.fisher_diag["W_dyn"] * (self.W_dyn - self.anchor_weights["W_dyn"])
        self.W_dyn += 0.005 * G - 1e-6 * self.W_dyn - 0.005 * ewc_pen
        
        pred_rew = torch.matmul(sa, self.W_rew.unsqueeze(-1)).squeeze(-1)
        err_rew = rew_val - pred_rew
        self.W_rew += 0.005 * sa * err_rew - 1e-6 * self.W_rew
        
        v_curr = torch.matmul(s_curr, self.W_val.unsqueeze(-1)).squeeze(-1)
        v_next = torch.matmul(s_next, self.W_val.unsqueeze(-1)).squeeze(-1)
        td_err = rew_val + 0.95 * v_next - v_curr
        self.W_val += 0.005 * s_curr * td_err - 1e-6 * self.W_val
        
        logits = torch.matmul(s_curr, self.W_policy)
        exp_l = torch.exp(logits - torch.max(logits))
        probs = exp_l / (torch.sum(exp_l) + 1e-9)
        grad_p = -probs
        grad_p[action] += 1.0
        self.W_policy += 0.005 * torch.outer(s_curr, grad_p * td_err) - 1e-6 * self.W_policy
        
        # Hippocampus
        loss_val = float(loss_dyn.item() / 32.0)
        v_curr_val = float(v_curr.item())
        
        self.hippocampus.append({
            "s_curr": s_curr_np.copy(),
            "action": action,
            "reward": reward,
            "s_next": s_next_np.copy(),
            "surprise": loss_val + abs(reward)
        })
        if len(self.hippocampus) > 5000:
            self.hippocampus.pop(0)
            
        return {"loss": loss_val, "vCurr": v_curr_val}

    def sleep_consolidation(self) -> int:
        if len(self.hippocampus) < 10:
            return 0
        replays = min(50, len(self.hippocampus))
        for _ in range(replays):
            idx = self.rng.randint(0, len(self.hippocampus))
            mem = self.hippocampus[idx]
            self.update_neural_weights(mem["s_curr"], mem["action"], mem["reward"], mem["s_next"])
        self.anchor_weights["W_dyn"] = self.W_dyn.clone()
        return replays

    @torch.no_grad()
    def decode_neural_language(self, s_curr_np: np.ndarray, user_prompt: str) -> dict:
        s_curr = torch.tensor(s_curr_np, dtype=self.dtype, device=self.device)
        vocab_logits = torch.matmul(s_curr, self.W_lang.T)
        exp_v = torch.exp(vocab_logits - torch.max(vocab_logits))
        probs = exp_v / (torch.sum(exp_v) + 1e-9)
        
        # top 8
        top_ids = torch.argsort(probs, descending=True)[:8].cpu().numpy()
        emitted = "".join(chr(65 + (int(tid) % 26)) for tid in top_ids)
        v_val = float(torch.matmul(s_curr, self.W_val.unsqueeze(-1)).item())
        return {
            "top_tokens": emitted,
            "state_sample": [round(float(x), 3) for x in s_curr_np[:4]],
            "v_val": v_val
        }

    def save_checkpoint(self, path: Path):
        h_s_curr = np.array([m["s_curr"] for m in self.hippocampus], dtype=np.float32) if self.hippocampus else np.empty((0, 32), dtype=np.float32)
        h_action = np.array([m["action"] for m in self.hippocampus], dtype=np.int32) if self.hippocampus else np.empty((0,), dtype=np.int32)
        h_reward = np.array([m["reward"] for m in self.hippocampus], dtype=np.float32) if self.hippocampus else np.empty((0,), dtype=np.float32)
        h_s_next = np.array([m["s_next"] for m in self.hippocampus], dtype=np.float32) if self.hippocampus else np.empty((0, 32), dtype=np.float32)
        h_surprise = np.array([m["surprise"] for m in self.hippocampus], dtype=np.float32) if self.hippocampus else np.empty((0,), dtype=np.float32)
        
        np.savez_compressed(
            path,
            W_vis=self.W_vis.cpu().numpy().astype(np.float32),
            W_lang=self.W_lang.cpu().numpy().astype(np.float32),
            W_fuse_vis=self.W_fuse_vis.cpu().numpy().astype(np.float32),
            W_fuse_lang=self.W_fuse_lang.cpu().numpy().astype(np.float32),
            W_q=self.W_q.cpu().numpy().astype(np.float32),
            W_k=self.W_k.cpu().numpy().astype(np.float32),
            W_v=self.W_v.cpu().numpy().astype(np.float32),
            W_out=self.W_out.cpu().numpy().astype(np.float32),
            W_ff1=self.W_ff1.cpu().numpy().astype(np.float32),
            W_ff2=self.W_ff2.cpu().numpy().astype(np.float32),
            W_dyn=self.W_dyn.cpu().numpy().astype(np.float32),
            W_rew=self.W_rew.cpu().numpy().astype(np.float32),
            W_val=self.W_val.cpu().numpy().astype(np.float32),
            W_policy=self.W_policy.cpu().numpy().astype(np.float32),
            hippo_s_curr=h_s_curr,
            hippo_action=h_action,
            hippo_reward=h_reward,
            hippo_s_next=h_s_next,
            hippo_surprise=h_surprise
        )

    def load_checkpoint(self, path: Path):
        data = np.load(path)
        for k in ["W_vis", "W_lang", "W_fuse_vis", "W_fuse_lang", "W_q", "W_k", "W_v", "W_out", "W_ff1", "W_ff2", "W_dyn", "W_rew", "W_val", "W_policy"]:
            if k in data:
                arr = data[k].astype(np.float32)
                if k in ["W_rew", "W_val"] and arr.ndim > 1:
                    arr = arr.reshape(-1)
                setattr(self, k, torch.tensor(arr, dtype=self.dtype, device=self.device))
        
        if "hippo_action" in data and len(data["hippo_action"]) > 0:
            self.hippocampus = []
            for i in range(len(data["hippo_action"])):
                self.hippocampus.append({
                    "s_curr": data["hippo_s_curr"][i],
                    "action": int(data["hippo_action"][i]),
                    "reward": float(data["hippo_reward"][i]),
                    "s_next": data["hippo_s_next"][i],
                    "surprise": float(data["hippo_surprise"][i])
                })
        
        self.anchor_weights["W_dyn"] = self.W_dyn.clone()
