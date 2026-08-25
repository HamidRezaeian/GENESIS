import torch
import torch.nn.functional as F
import numpy as np
import math
from pathlib import Path

VISUAL_DIM = 7 * 7 * 7  # 343
D_MODEL = 32
N_ACTIONS = 4
MAX_TEXT_LEN = 16
VOCAB_SIZE = 64
MCTS_SIMS_DIRECTED = 32 # Number of PUCT simulations in Directed mode
MCTS_SIMS_EXPLORE = 16 # Number of PUCT simulations in Explore mode

class GenesisPyTorchBrain:
    def __init__(self, device="cuda"):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        
        self.rng = np.random.RandomState(42)
        self.hippocampus = []
        self.state_history = []
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

        # Substrate 9: Temporal Abstraction (Option Queries)
        self.NUM_OPTIONS = 8
        self.W_opt_q = self._rand_mat(self.NUM_OPTIONS, D_MODEL, 0.05)
        self.W_k_hist = self._rand_mat(D_MODEL, D_MODEL, 0.05)
        self.W_v_hist = self._rand_mat(D_MODEL, D_MODEL, 0.05)

        self.W_dyn = self._rand_mat(D_MODEL + N_ACTIONS, D_MODEL, 0.05)
        # 1D for rewards and vals
        self.W_rew = self._rand_mat(D_MODEL + N_ACTIONS, 1, 0.05).squeeze(-1)
        self.W_val = self._rand_mat(D_MODEL, 1, 0.05).squeeze(-1)
        self.W_val_target = self.W_val.clone()
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
        
        self.state_history.append(fused)
        if len(self.state_history) > 16:
            self.state_history.pop(0)
            
        hist_tensor = torch.stack(self.state_history)
        
        Q_opt = self.W_opt_q
        K_hist = torch.matmul(hist_tensor, self.W_k_hist)
        V_hist = torch.matmul(hist_tensor, self.W_v_hist)
        
        score_opt = torch.matmul(Q_opt, K_hist.T) / 5.656854
        attn_opt = torch.softmax(score_opt, dim=-1)
        mixed_opt = torch.matmul(attn_opt, V_hist)
        
        temporal_context = mixed_opt.mean(dim=0)
        fused_with_time = fused + temporal_context
        
        Q = torch.matmul(fused_with_time, self.W_q)
        K = torch.matmul(fused_with_time, self.W_k)
        V = torch.matmul(fused_with_time, self.W_v)
        
        score = torch.matmul(Q, K) / 5.656854
        attn = torch.sigmoid(score)
        mixed = fused_with_time + attn * V
        
        ff1 = torch.relu(torch.matmul(mixed, self.W_ff1))
        ff2 = torch.matmul(ff1, self.W_ff2)
        out = mixed + ff2
        return out.cpu().numpy().astype(np.float32)

    @torch.no_grad()
    def run_mcts(self, root_state_np: np.ndarray, policy_mode: str = "DIRECTED") -> dict:
        root_state = torch.tensor(root_state_np, dtype=self.dtype, device=self.device)
        
        logits = torch.matmul(root_state, self.W_policy)
        exp_l = torch.exp(logits - torch.max(logits))
        priors = exp_l / (torch.sum(exp_l) + 1e-9)
        
        noise = -torch.log(torch.clamp(torch.rand(N_ACTIONS, device=self.device), min=1e-6))
        noise /= (torch.sum(noise) + 1e-9)
        eps_noise = 0.20 if policy_mode == "DIRECTED" else 0.40
        noisy_priors = (1.0 - eps_noise) * priors + eps_noise * noise
        
        sims = MCTS_SIMS_DIRECTED if policy_mode == "DIRECTED" else MCTS_SIMS_EXPLORE
        depth = 6
        cpuct = 0.8 if policy_mode == "DIRECTED" else 1.4
        
        q_sum = torch.zeros(N_ACTIONS, dtype=self.dtype, device=self.device)
        n_visits = torch.zeros(N_ACTIONS, dtype=self.dtype, device=self.device)
        
        for _ in range(sims):
            q_mean = torch.where(n_visits > 0, q_sum / n_visits, torch.zeros_like(q_sum))
            q_min = torch.min(q_mean)
            q_max = torch.max(q_mean)
            if q_max > q_min:
                q_norm = (q_mean - q_min) / (q_max - q_min)
            else:
                q_norm = torch.zeros_like(q_mean)
                
            N_parent = torch.sum(n_visits)
            puct_scores = q_norm + cpuct * noisy_priors * torch.sqrt(N_parent + 1.0) / (1.0 + n_visits)
            a = torch.argmax(puct_scores).item()
            
            curr_s = root_state.clone()
            sa = torch.zeros(36, dtype=self.dtype, device=self.device)
            sa[:32] = curr_s
            sa[32 + a] = 1.0
            
            discount = 1.0
            path_return = 0.0
            
            for d in range(depth):
                curr_s = torch.tanh(torch.matmul(sa, self.W_dyn))
                r = torch.matmul(sa, self.W_rew.unsqueeze(-1)).squeeze(-1).item()
                path_return += discount * r
                discount *= 0.95
                
                if d < depth - 1:
                    # Rollout policy uses uniform random for speed
                    next_a = torch.randint(0, N_ACTIONS, (1,), device=self.device).item()
                    sa = torch.zeros(36, dtype=self.dtype, device=self.device)
                    sa[:32] = curr_s
                    sa[32 + next_a] = 1.0
                    
            leaf_v = torch.matmul(curr_s, self.W_val.unsqueeze(-1)).squeeze(-1).item()
            path_return += discount * leaf_v
            
            q_sum[a] += path_return
            n_visits[a] += 1.0

        temperature = 0.5 if policy_mode == "DIRECTED" else 1.5
        probs_tensor = n_visits ** (1.0 / temperature)
        probs_tensor /= (torch.sum(probs_tensor) + 1e-9)
        
        q_values = torch.where(n_visits > 0, q_sum / n_visits, torch.zeros_like(q_sum))
        
        return {
            "probs": probs_tensor.cpu().numpy().tolist(),
            "qValues": q_values.cpu().numpy().tolist(),
            "visitCounts": n_visits.cpu().numpy().astype(np.int32).tolist()
        }

    @torch.no_grad()
    def update_neural_weights(self, s_curr_np: np.ndarray, action: int, reward: float, s_next_np: np.ndarray, is_terminal: bool = False, is_replay: bool = False) -> dict:
        s_curr = torch.tensor(s_curr_np, dtype=self.dtype, device=self.device)
        s_next = torch.tensor(s_next_np, dtype=self.dtype, device=self.device)
        rew_val = torch.tensor(reward, dtype=self.dtype, device=self.device)
        
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
        
        # Target Network for stable bootstrapping
        v_curr = torch.matmul(s_curr, self.W_val.unsqueeze(-1)).squeeze(-1)
        if is_terminal:
            td_target = rew_val
        else:
            v_next_target = torch.matmul(s_next, self.W_val_target.unsqueeze(-1)).squeeze(-1)
            td_target = rew_val + 0.95 * v_next_target
            
        td_err = td_target - v_curr
        self.W_val += 0.005 * s_curr * td_err - 1e-6 * self.W_val
        
        # Polyak averaging for target network
        tau = 0.01
        self.W_val_target = (1.0 - tau) * self.W_val_target + tau * self.W_val
        
        logits = torch.matmul(s_curr, self.W_policy)
        exp_l = torch.exp(logits - torch.max(logits))
        probs = exp_l / (torch.sum(exp_l) + 1e-9)
        grad_p = -probs
        grad_p[action] += 1.0
        
        # Standard Actor-Critic policy gradient with clamped advantage for stability
        clamped_td = torch.clamp(td_err, min=-10.0, max=10.0)
        policy_grad = grad_p * clamped_td
        
        self.W_policy += 0.005 * torch.outer(s_curr, policy_grad) - 1e-6 * self.W_policy
        
        # Hippocampus uses |td_err| as priority signal, and avoids duplicate injection during replays
        loss_val = float(loss_dyn.item() / 32.0)
        v_curr_val = float(v_curr.item())
        td_err_val = float(abs(td_err.item()))
        
        if not is_replay:
            self.hippocampus.append({
                "s_curr": s_curr_np.copy(),
                "action": action,
                "reward": reward,
                "s_next": s_next_np.copy(),
                "is_terminal": is_terminal,
                "surprise": td_err_val + 1e-5
            })
            if len(self.hippocampus) > 5000:
                self.hippocampus.pop(0)
            
        return {"loss": loss_val, "vCurr": v_curr_val}

    @torch.no_grad()
    def update_neural_weights_batch(self, s_curr_np, action_np, reward_np, s_next_np, is_terminal_np):
        """Highly optimized batched manual PyTorch parameter update."""
        s_curr_b = torch.tensor(s_curr_np, dtype=self.dtype, device=self.device)
        action_b = torch.tensor(action_np, dtype=torch.long, device=self.device)
        reward_b = torch.tensor(reward_np, dtype=self.dtype, device=self.device)
        s_next_b = torch.tensor(s_next_np, dtype=self.dtype, device=self.device)
        is_terminal_b = torch.tensor(is_terminal_np, dtype=torch.bool, device=self.device)
        
        B = s_curr_b.shape[0]
        if B == 0:
            return {"loss": 0.0, "vCurr": 0.0, "td_errs": np.array([])}
            
        sa = torch.zeros((B, 36), dtype=self.dtype, device=self.device)
        sa[:, :32] = s_curr_b
        sa[torch.arange(B, device=self.device), 32 + action_b] = 1.0
        
        # 1. Dynamics
        pred_next = torch.tanh(torch.matmul(sa, self.W_dyn)) # [B, 32]
        err_dyn = s_next_b - pred_next # [B, 32]
        loss_dyn_b = torch.sum(err_dyn ** 2, dim=1) # [B]
        
        grad_d = err_dyn * (1.0 - pred_next ** 2) # [B, 32]
        G_mean = torch.matmul(sa.T, grad_d) / B # [36, B] @ [B, 32] -> [36, 32]
        
        delta_fish = torch.matmul((sa * sa).T, (grad_d * grad_d)) / B # [36, 32]
        self.fisher_diag["W_dyn"] += delta_fish * 0.01
        
        ewc_pen = 0.5 * self.fisher_diag["W_dyn"] * (self.W_dyn - self.anchor_weights["W_dyn"])
        self.W_dyn += 0.005 * G_mean - 1e-6 * self.W_dyn - 0.005 * ewc_pen
        
        # 2. Reward
        pred_rew = torch.matmul(sa, self.W_rew.unsqueeze(-1)).squeeze(-1) # [B]
        err_rew = reward_b - pred_rew # [B]
        grad_r_mean = torch.matmul(sa.T, err_rew) / B # [36, B] @ [B] -> [36]
        self.W_rew += 0.005 * grad_r_mean - 1e-6 * self.W_rew
        
        # 3. Value
        v_curr = torch.matmul(s_curr_b, self.W_val.unsqueeze(-1)).squeeze(-1) # [B]
        v_next_target = torch.matmul(s_next_b, self.W_val_target.unsqueeze(-1)).squeeze(-1) # [B]
        
        td_target = reward_b + 0.95 * v_next_target * (~is_terminal_b).to(self.dtype)
        td_err = td_target - v_curr # [B]
        
        grad_v_mean = torch.matmul(s_curr_b.T, td_err) / B # [32, B] @ [B] -> [32]
        self.W_val += 0.005 * grad_v_mean - 1e-6 * self.W_val
        
        # Polyak averaging target network - adjusted for effective batch
        tau = 0.01
        tau_eff = 1.0 - (1.0 - tau) ** B
        self.W_val_target = (1.0 - tau_eff) * self.W_val_target + tau_eff * self.W_val
        
        # 4. Policy
        logits = torch.matmul(s_curr_b, self.W_policy) # [B, 4]
        max_l, _ = torch.max(logits, dim=1, keepdim=True)
        exp_l = torch.exp(logits - max_l)
        probs = exp_l / (torch.sum(exp_l, dim=1, keepdim=True) + 1e-9)
        
        grad_p = -probs # [B, 4]
        grad_p[torch.arange(B, device=self.device), action_b] += 1.0
        
        clamped_td = torch.clamp(td_err, min=-10.0, max=10.0) # [B]
        policy_grad = grad_p * clamped_td.unsqueeze(1) # [B, 4] * [B, 1] -> [B, 4]
        
        grad_pol_mean = torch.matmul(s_curr_b.T, policy_grad) / B # [32, B] @ [B, 4] -> [32, 4]
        self.W_policy += 0.005 * grad_pol_mean - 1e-6 * self.W_policy
        
        return {
            "loss": loss_dyn_b.mean().item() / 32.0,
            "vCurr": v_curr.mean().item(),
            "td_errs": torch.abs(td_err).cpu().numpy()
        }

    def sleep_consolidation(self) -> int:
        if len(self.hippocampus) < 10:
            return 0
        replays = min(50, len(self.hippocampus))
        
        indices = self.rng.choice(len(self.hippocampus), size=replays, replace=False)
        s_curr_b = np.stack([self.hippocampus[idx]["s_curr"] for idx in indices])
        action_b = np.array([self.hippocampus[idx]["action"] for idx in indices], dtype=np.int64)
        reward_b = np.array([self.hippocampus[idx]["reward"] for idx in indices], dtype=np.float32)
        s_next_b = np.stack([self.hippocampus[idx]["s_next"] for idx in indices])
        term_b = np.array([self.hippocampus[idx].get("is_terminal", False) for idx in indices], dtype=bool)
        
        batch_metrics = self.update_neural_weights_batch(s_curr_b, action_b, reward_b, s_next_b, term_b)
        
        for i, idx in enumerate(indices):
            self.hippocampus[idx]["surprise"] = float(batch_metrics["td_errs"][i]) + 1e-5
            
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
            W_opt_q=self.W_opt_q.cpu().numpy().astype(np.float32),
            W_k_hist=self.W_k_hist.cpu().numpy().astype(np.float32),
            W_v_hist=self.W_v_hist.cpu().numpy().astype(np.float32),
            W_dyn=self.W_dyn.cpu().numpy().astype(np.float32),
            W_rew=self.W_rew.cpu().numpy().astype(np.float32),
            W_val=self.W_val.cpu().numpy().astype(np.float32),
            W_val_target=self.W_val_target.cpu().numpy().astype(np.float32),
            W_policy=self.W_policy.cpu().numpy().astype(np.float32),
            h_s_curr=h_s_curr,
            h_action=h_action,
            h_reward=h_reward,
            h_s_next=h_s_next,
            h_surprise=h_surprise
        )

    def load_checkpoint(self, path: Path):
        data = np.load(path)
        if "W_vis" in data:
            self.W_vis = torch.tensor(data["W_vis"], dtype=self.dtype, device=self.device)
            self.W_lang = torch.tensor(data["W_lang"], dtype=self.dtype, device=self.device)
            self.W_fuse_vis = torch.tensor(data["W_fuse_vis"], dtype=self.dtype, device=self.device)
            self.W_fuse_lang = torch.tensor(data["W_fuse_lang"], dtype=self.dtype, device=self.device)
            self.W_q = torch.tensor(data["W_q"], dtype=self.dtype, device=self.device)
            self.W_k = torch.tensor(data["W_k"], dtype=self.dtype, device=self.device)
            self.W_v = torch.tensor(data["W_v"], dtype=self.dtype, device=self.device)
            self.W_out = torch.tensor(data["W_out"], dtype=self.dtype, device=self.device)
            self.W_ff1 = torch.tensor(data["W_ff1"], dtype=self.dtype, device=self.device)
            self.W_ff2 = torch.tensor(data["W_ff2"], dtype=self.dtype, device=self.device)
            self.W_dyn = torch.tensor(data["W_dyn"], dtype=self.dtype, device=self.device)
            self.W_rew = torch.tensor(data["W_rew"], dtype=self.dtype, device=self.device)
            self.W_val = torch.tensor(data["W_val"], dtype=self.dtype, device=self.device)
            if "W_val_target" in data:
                self.W_val_target = torch.tensor(data["W_val_target"], dtype=self.dtype, device=self.device)
            else:
                self.W_val_target = self.W_val.clone()
            self.W_policy = torch.tensor(data["W_policy"], dtype=self.dtype, device=self.device)
            
            if "W_opt_q" in data:
                self.W_opt_q = torch.tensor(data["W_opt_q"], dtype=self.dtype, device=self.device)
                self.W_k_hist = torch.tensor(data["W_k_hist"], dtype=self.dtype, device=self.device)
                self.W_v_hist = torch.tensor(data["W_v_hist"], dtype=self.dtype, device=self.device)
            else:
                self.NUM_OPTIONS = 8
                self.W_opt_q = self._rand_mat(self.NUM_OPTIONS, D_MODEL, 0.05)
                self.W_k_hist = self._rand_mat(D_MODEL, D_MODEL, 0.05)
                self.W_v_hist = self._rand_mat(D_MODEL, D_MODEL, 0.05)
                
            self.hippocampus = []
            self.state_history = []
            for i in range(len(data["h_action"])):
                self.hippocampus.append({
                    "s_curr": data["h_s_curr"][i],
                    "action": data["h_action"][i],
                    "reward": data["h_reward"][i],
                    "s_next": data["h_s_next"][i],
                    "is_terminal": False, # Backwards compatibility
                    "surprise": data["h_surprise"][i]
                })
        
        self.anchor_weights["W_dyn"] = self.W_dyn.clone()
