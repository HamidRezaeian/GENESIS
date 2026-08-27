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
MCTS_SIMS_DIRECTED = 32  # Number of PUCT simulations in Directed mode
MCTS_SIMS_EXPLORE = 16  # Number of PUCT simulations in Explore mode


class GenesisPyTorchBrain:
    def __init__(self, device="cuda"):
        self.device = torch.device(
            device if torch.cuda.is_available() else "cpu")
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32

        self.rng = np.random.RandomState(42)
        self.hippocampus = []

        # Symbolic Abstraction (Substrate 11) & Grounding (Substrate 12)
        self.num_concepts = 16
        self.option_hippocampus = []
        self.W_concept_policy = self._rand_mat(
            D_MODEL, self.num_concepts, 0.05)
        self.W_concept_value = self._rand_mat(D_MODEL, self.num_concepts, 0.05)
        self.concept_embeddings = self._rand_mat(
            self.num_concepts, D_MODEL, 0.05)
        self.W_transfer = self._rand_mat(
            self.num_concepts, self.num_concepts, 0.05)
        self.W_concept_to_symbol = self._rand_mat(
            self.num_concepts, VOCAB_SIZE, 0.05)

        # Substrate 13: Causal World Model & Autotelic Goal Discovery
        self.W_causal = self._rand_mat(D_MODEL, D_MODEL, 0.05)
        self.W_goal = self._rand_mat(D_MODEL, D_MODEL, 0.05)
        self.active_intrinsic_goal = None
        self.causal_attribution_history = []
        self.counterfactual_regret_history = []

        # Substrate 14: Metacognitive Precision Field & Epistemic Uncertainty
        self.I_dyn = torch.zeros(
            (D_MODEL + N_ACTIONS, D_MODEL), dtype=torch.float32, device=self.device)
        self.tau2_hat = torch.ones(
            (D_MODEL,), dtype=torch.float32, device=self.device) * 0.05
        self.calib_ema = float(D_MODEL)
        self.ETA_F = 0.01
        self.LAMBDA = 2e-4  # 1e-6 / 0.005 (wd / lr)

        self.option_fisher_diag = {
            "W_concept_to_symbol": torch.zeros((self.num_concepts, VOCAB_SIZE), dtype=self.dtype, device=self.device),
            "W_concept_value": torch.zeros((D_MODEL, self.num_concepts), dtype=self.dtype, device=self.device),
            "concept_embeddings": torch.zeros((self.num_concepts, D_MODEL), dtype=self.dtype, device=self.device)
        }
        self.option_anchor_weights = {
            "W_concept_value": self.W_concept_value.clone(),
            "concept_embeddings": self.concept_embeddings.clone(),
            "W_concept_to_symbol": self.W_concept_to_symbol.clone()
        }

        self.state_history = []
        self.init_weights()
        self.fisher_diag = {
            "W_dyn": torch.zeros((D_MODEL + N_ACTIONS, D_MODEL), dtype=self.dtype, device=self.device),
            "W_causal": torch.zeros((D_MODEL, D_MODEL), dtype=self.dtype, device=self.device),
            "W_goal": torch.zeros((D_MODEL, D_MODEL), dtype=self.dtype, device=self.device)
        }
        self.anchor_weights = {
            "W_dyn": self.W_dyn.clone(),
            "W_causal": self.W_causal.clone(),
            "W_goal": self.W_goal.clone()
        }

        # Continual Learning Instrumentation (Milestone 1)
        self.last_td_error = 0.0
        self.td_error_ema = 1.0
        self.last_value_loss = 0.0
        self.last_policy_loss = 0.0
        self.last_wm_loss = 0.0
        self.consolidation_count = 0
        self.last_ewc_penalty = 0.0
        self.last_grad_norm = 0.0
        self.learn_step_count = 0
        self._snapshot_initial_params()

        # Substrate 16: Autotelic Dynamics & Curiosity (Rule 9)
        self.curiosity_alpha = 0.2
        self.is_bored = False
        self.wm_loss_ema = 1.0

    def _snapshot_initial_params(self):
        self.initial_params = {}
        for attr in dir(self):
            if attr.startswith("W_"):
                val = getattr(self, attr)
                if isinstance(val, torch.Tensor):
                    self.initial_params[attr] = val.detach().clone()

    def _rand_mat(self, rows, cols, std=0.05):
        val = (self.rng.uniform(-1.0, 1.0, (rows, cols)) * math.sqrt(3) * std)
        return torch.tensor(val, dtype=self.dtype, device=self.device)

    def _sanitize(self, t: torch.Tensor, fill: float = 0.0) -> torch.Tensor:
        """Replace NaN/Inf with fill value. Prevents NaN-poisoning in MCTS."""
        return torch.nan_to_num(t, nan=fill, posinf=fill, neginf=fill)

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
        self.W_forget = self._rand_mat(D_MODEL, 1, 0.05)
        self.W_import = self._rand_mat(D_MODEL, 1, 0.05)

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

        forget_gate = torch.sigmoid(torch.matmul(hist_tensor, self.W_forget))
        import_gate = torch.sigmoid(torch.matmul(hist_tensor, self.W_import))
        weighted_history = hist_tensor * forget_gate * import_gate

        Q_opt = self.W_opt_q
        K_hist = torch.matmul(weighted_history, self.W_k_hist)
        V_hist = torch.matmul(weighted_history, self.W_v_hist)

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
        out = self._sanitize(mixed + ff2)
        return out.cpu().numpy().astype(np.float32)

    @torch.no_grad()
    def epistemic_entropy(self, s: torch.Tensor, a_idx: int) -> float:
        """Substrate 14: Predictive epistemic uncertainty in bits."""
        try:
            onehot = torch.zeros(
                N_ACTIONS, dtype=self.dtype, device=self.device)
            onehot[a_idx] = 1.0
            phi = torch.cat([s, onehot])
            z = torch.matmul(phi, self.W_dyn)
            sh = torch.tanh(z)
            J2 = torch.clamp((1.0 - sh.float() ** 2) ** 2, min=1e-8, max=1.0)
            phi2 = torch.nan_to_num(
                phi.float() ** 2, nan=0.0, posinf=1.0, neginf=0.0)

            param_cov = 1.0 / (torch.clamp(self.I_dyn, min=0.0) + self.LAMBDA)
            sigma2 = J2 * torch.matmul(phi2, param_cov)
            sigma2 = torch.clamp(torch.nan_to_num(
                sigma2, nan=0.0, posinf=100.0, neginf=0.0), min=0.0, max=1000.0)

            tau_safe = torch.clamp(torch.nan_to_num(
                self.tau2_hat, nan=0.05, posinf=1.0, neginf=0.05), min=1e-6, max=100.0)
            bits = 0.5 * torch.log2(1.0 + sigma2 / (tau_safe + 1e-9))
            res = float(torch.clamp(torch.nan_to_num(
                bits.mean(), nan=0.0, posinf=5.0, neginf=0.0), min=0.0, max=10.0).item())
            return res if math.isfinite(res) else 0.0
        except Exception:
            return 0.0

    @torch.no_grad()
    def compute_causal_attribution(self, s_curr: torch.Tensor, err_dyn: torch.Tensor) -> dict:
        if len(self.state_history) < 2:
            return {"cause_index": -1, "attribution_scores": [1.0], "dominant_cause_state": s_curr}

        hist_tensor = torch.stack(self.state_history)  # [T, 32]
        query = torch.matmul(err_dyn, self.W_causal)   # [32]
        scores = torch.matmul(hist_tensor, query) / 5.656854
        attn = torch.softmax(scores, dim=0)
        dominant_idx = torch.argmax(attn).item()
        s_cause = hist_tensor[dominant_idx]
        return {
            "cause_index": dominant_idx,
            "attribution_scores": attn.cpu().numpy().tolist(),
            "dominant_cause_state": s_cause
        }

    @torch.no_grad()
    def evaluate_counterfactual(self, s_cause: torch.Tensor, actual_action: int, actual_value: float) -> dict:
        best_alt_action = actual_action
        best_cf_value = -1e9
        cf_values = []

        for a_alt in range(N_ACTIONS):
            if a_alt == actual_action:
                cf_values.append(actual_value)
                continue
            sa_cf = torch.zeros(36, dtype=self.dtype, device=self.device)
            sa_cf[:32] = s_cause
            sa_cf[32 + a_alt] = 1.0
            s_cf_next = torch.tanh(torch.matmul(sa_cf, self.W_dyn))
            r_cf = torch.dot(sa_cf, self.W_rew).item()
            v_cf = r_cf + 0.95 * torch.dot(s_cf_next, self.W_val).item()
            cf_values.append(v_cf)
            if v_cf > best_cf_value:
                best_cf_value = v_cf
                best_alt_action = a_alt

        regret = max(0.0, best_cf_value - actual_value)
        return {
            "cf_values": cf_values,
            "best_alt_action": best_alt_action,
            "counterfactual_regret": float(regret)
        }

    @torch.no_grad()
    def synthesize_autotelic_goal(self, concept_id: int) -> np.ndarray:
        concept_emb = self.concept_embeddings[concept_id]
        z_goal = torch.tanh(torch.matmul(concept_emb, self.W_goal))
        self.active_intrinsic_goal = z_goal
        return z_goal.cpu().numpy().astype(np.float32)

    @torch.no_grad()
    def run_mcts(self, root_state_np: np.ndarray, policy_mode: str = "DIRECTED") -> dict:
        root_state = self._sanitize(torch.tensor(
            root_state_np, dtype=self.dtype, device=self.device))

        logits = self._sanitize(torch.matmul(root_state, self.W_policy))
        exp_l = torch.exp(logits - torch.max(logits))
        priors = exp_l / (torch.sum(exp_l) + 1e-9)
        # If priors are NaN (all-NaN logits), fall back to uniform
        if torch.any(torch.isnan(priors)):
            priors = torch.ones(N_ACTIONS, dtype=self.dtype,
                                device=self.device) / N_ACTIONS

        noise = -torch.log(torch.clamp(torch.rand(N_ACTIONS,
                           device=self.device), min=1e-6))
        noise /= (torch.sum(noise) + 1e-9)
        eps_noise = 0.20 if policy_mode == "DIRECTED" else 0.40
        noisy_priors = (1.0 - eps_noise) * priors + eps_noise * noise

        # Substrate 14: Metacognitive Simulation Budget (System 1 vs System 2)
        unc_vals = [self.epistemic_entropy(
            root_state, a) for a in range(N_ACTIONS)]
        root_uncertainty = float(np.nan_to_num(
            sum(unc_vals) / max(1, len(unc_vals)), nan=0.0))
        N_min = 8 if policy_mode == "EXPLORE" else 12
        N_max = 32 if policy_mode == "EXPLORE" else 48
        sim_delta = int(
            2.0 ** root_uncertainty) if math.isfinite(root_uncertainty) else 0
        sims = int(np.clip(N_min + sim_delta, N_min, N_max))

        depth = 6
        cpuct = 0.8 if policy_mode == "DIRECTED" else 1.4

        q_sum = torch.zeros(N_ACTIONS, dtype=self.dtype, device=self.device)
        n_visits = torch.zeros(N_ACTIONS, dtype=self.dtype, device=self.device)
        sims_conducted = 0

        for sim_idx in range(sims):
            sims_conducted += 1
            q_mean = self._sanitize(torch.where(
                n_visits > 0, q_sum / n_visits, torch.zeros_like(q_sum)))
            q_min = torch.min(q_mean)
            q_max = torch.max(q_mean)
            if q_max > q_min:
                q_norm = (q_mean - q_min) / (q_max - q_min)
            else:
                q_norm = torch.zeros_like(q_mean)

            N_parent = torch.sum(n_visits)
            puct_scores = q_norm + cpuct * noisy_priors * \
                torch.sqrt(N_parent + 1.0) / (1.0 + n_visits)
            # Replace any remaining NaN in PUCT with -inf so argmax skips them
            puct_scores = torch.where(torch.isnan(
                puct_scores), torch.tensor(-1e9, dtype=self.dtype, device=self.device), puct_scores)
            a = torch.argmax(puct_scores).item()

            curr_s = root_state.clone()
            sa = torch.zeros(36, dtype=self.dtype, device=self.device)
            sa[:32] = curr_s
            sa[32 + a] = 1.0

            discount = 1.0
            path_return = 0.0

            for d in range(depth):
                next_s = torch.tanh(self._sanitize(
                    torch.matmul(sa, self.W_dyn)))
                r_raw = torch.matmul(
                    sa, self.W_rew.unsqueeze(-1)).squeeze(-1).item()
                r = r_raw if math.isfinite(r_raw) else 0.0

                # Substrate 14: Epistemic Information-Gain Reward
                r_epi = self.epistemic_entropy(curr_s, a) / float(D_MODEL)
                r += r_epi

                # Autotelic Intrinsic Goal Potential (Substrate 13)
                if self.active_intrinsic_goal is not None:
                    dist_curr = torch.norm(
                        curr_s - self.active_intrinsic_goal).item()
                    dist_next = torch.norm(
                        next_s - self.active_intrinsic_goal).item()
                    if math.isfinite(dist_curr) and math.isfinite(dist_next):
                        r += 0.1 * (dist_curr - dist_next)

                path_return += discount * r
                discount *= 0.95
                curr_s = next_s

                if d < depth - 1:
                    next_a = torch.randint(
                        0, N_ACTIONS, (1,), device=self.device).item()
                    sa = torch.zeros(36, dtype=self.dtype, device=self.device)
                    sa[:32] = curr_s
                    sa[32 + next_a] = 1.0

            leaf_v = torch.matmul(
                curr_s, self.W_val.unsqueeze(-1)).squeeze(-1).item()
            if not math.isfinite(leaf_v):
                leaf_v = 0.0
            path_return += discount * leaf_v

            # Final guard: if path_return is still NaN, use 0
            if not math.isfinite(path_return):
                path_return = 0.0

            q_sum[a] += path_return
            n_visits[a] += 1.0

            # Metacognitive VOC Early-Stopping Gate (System 1)
            if sim_idx >= N_min and torch.min(n_visits).item() >= 2:
                q_cur = self._sanitize(torch.where(
                    n_visits > 0, q_sum / n_visits, torch.zeros_like(q_sum)))
                top2 = torch.topk(q_cur, 2)
                d_hat = float(top2.values[0] - top2.values[1])
                ucb_bound = cpuct * \
                    math.sqrt(N_parent + 1.0) / \
                    (1.0 + torch.min(n_visits).item())
                if math.isfinite(d_hat) and d_hat > ucb_bound:
                    break

        temperature = 0.5 if policy_mode == "DIRECTED" else 1.5
        probs_tensor = n_visits ** (1.0 / temperature)
        probs_tensor /= (torch.sum(probs_tensor) + 1e-9)

        q_values = self._sanitize(torch.where(
            n_visits > 0, q_sum / n_visits, torch.zeros_like(q_sum)))

        return {
            "probs": probs_tensor.cpu().numpy().tolist(),
            "qValues": q_values.cpu().numpy().tolist(),
            "visitCounts": n_visits.cpu().numpy().astype(np.int32).tolist(),
            "epistemic_uncertainty": float(root_uncertainty),
            "sims_conducted": sims_conducted
        }

    @torch.no_grad()
    def _calculate_entropy_gain(self, state_before, state_after):
        s_b = torch.clamp(state_before, min=1e-9)
        p_b = s_b / torch.sum(s_b)
        ent_b = -torch.sum(p_b * torch.log2(p_b + 1e-9))

        s_a = torch.clamp(state_after, min=1e-9)
        p_a = s_a / torch.sum(s_a)
        ent_a = -torch.sum(p_a * torch.log2(p_a + 1e-9))

        return (ent_b - ent_a).item()

    @torch.no_grad()
    def _simulate_concept_entropy(self, root_state, concept_id, depth):
        concept_emb = self.concept_embeddings[concept_id]
        attn = torch.softmax(self._sanitize(
            torch.matmul(concept_emb, self.W_opt_q.T)), dim=-1)
        option_context = torch.matmul(attn, self.W_opt_q)
        curr_s = self._sanitize(root_state + option_context)

        entropy_estimate = 0.0
        discount = 1.0

        for d in range(depth):
            sa = torch.zeros(36, dtype=self.dtype, device=self.device)
            sa[:32] = curr_s
            next_a = torch.randint(
                0, N_ACTIONS, (1,), device=self.device).item()
            sa[32 + next_a] = 1.0

            next_s = torch.tanh(self._sanitize(torch.matmul(sa, self.W_dyn)))
            gain = self._calculate_entropy_gain(curr_s, next_s)
            if not math.isfinite(gain):
                gain = 0.0

            entropy_estimate += discount * gain
            discount *= 0.95
            curr_s = next_s

        return entropy_estimate

    @torch.no_grad()
    def _high_level_mcts(self, root_state, policy_mode):
        logits = self._sanitize(torch.matmul(
            root_state, self.W_concept_policy))
        priors = torch.softmax(logits, dim=-1)
        if torch.any(torch.isnan(priors)):
            priors = torch.ones(self.num_concepts, dtype=self.dtype,
                                device=self.device) / self.num_concepts

        noise = - \
            torch.log(torch.clamp(torch.rand(
                self.num_concepts, device=self.device), min=1e-6))
        noise /= (torch.sum(noise) + 1e-9)
        eps_noise = 0.20 if policy_mode == "DIRECTED" else 0.40
        noisy_priors = (1.0 - eps_noise) * priors + eps_noise * noise

        sims = 8 if policy_mode == "DIRECTED" else 4
        depth = 3
        cpuct = 1.2 if policy_mode == "DIRECTED" else 1.8

        q_sum = torch.zeros(self.num_concepts,
                            dtype=self.dtype, device=self.device)
        n_visits = torch.zeros(
            self.num_concepts, dtype=self.dtype, device=self.device)

        for _ in range(sims):
            q_mean = self._sanitize(torch.where(
                n_visits > 0, q_sum / n_visits, torch.zeros_like(q_sum)))
            q_min = torch.min(q_mean)
            q_max = torch.max(q_mean)
            if q_max > q_min:
                q_norm = (q_mean - q_min) / (q_max - q_min)
            else:
                q_norm = torch.zeros_like(q_mean)

            N_parent = torch.sum(n_visits)
            puct_scores = q_norm + cpuct * noisy_priors * \
                torch.sqrt(N_parent + 1.0) / (1.0 + n_visits)
            puct_scores = torch.where(torch.isnan(
                puct_scores), torch.tensor(-1e9, dtype=self.dtype, device=self.device), puct_scores)
            option = torch.argmax(puct_scores).item()

            ent_est = self._simulate_concept_entropy(root_state, option, depth)
            if not math.isfinite(ent_est):
                ent_est = 0.0

            q_sum[option] += ent_est
            n_visits[option] += 1.0

        temperature = 0.5 if policy_mode == "DIRECTED" else 1.5
        probs = n_visits ** (1.0 / temperature)
        probs /= (torch.sum(probs) + 1e-9)

        q_values = self._sanitize(torch.where(
            n_visits > 0, q_sum / n_visits, torch.zeros_like(q_sum)))

        return {
            "probs": probs.cpu().numpy().tolist(),
            "qValues": q_values.cpu().numpy().tolist(),
            "visitCounts": n_visits.cpu().numpy().astype(int).tolist(),
            "selected_option": torch.argmax(probs).item()
        }

    @torch.no_grad()
    def synthesize_autotelic_goal(self, opt_id: int):
        concept_emb = self.concept_embeddings[opt_id]
        self.active_intrinsic_goal = torch.tanh(
            torch.matmul(concept_emb, self.W_goal))

    @torch.no_grad()
    def evaluate_counterfactual(self, root_state: torch.Tensor, selected_action: int, selected_q: float) -> dict:
        alt_actions = [a for a in range(N_ACTIONS) if a != selected_action]
        best_alt_q = -1e9
        best_alt_a = selected_action
        for a in alt_actions:
            onehot = torch.zeros(
                N_ACTIONS, dtype=self.dtype, device=self.device)
            onehot[a] = 1.0
            phi = torch.cat([root_state, onehot])
            q_est = float(torch.matmul(phi, self.W_rew).item())
            if q_est > best_alt_q:
                best_alt_q = q_est
                best_alt_a = a
        regret = max(0.0, best_alt_q - float(selected_q))
        return {
            "counterfactual_regret": float(regret),
            "best_alt_action": int(best_alt_a)
        }

    @torch.no_grad()
    def run_hierarchical_mcts(self, root_state_np: np.ndarray, policy_mode: str = "DIRECTED") -> dict:
        root_state = torch.tensor(
            root_state_np, dtype=self.dtype, device=self.device)

        # High Level Option Selection (Substrate 10/11)
        hl_res = self._high_level_mcts(root_state, policy_mode)
        opt_id = hl_res["selected_option"]

        # Substrate 13: Synthesize Autotelic Intrinsic Goal if not active
        if self.active_intrinsic_goal is None or self.rng.rand() < 0.1:
            self.synthesize_autotelic_goal(opt_id)

        # Condition Low Level on Concept Context
        concept_emb = self.concept_embeddings[opt_id]
        attn = torch.softmax(torch.matmul(concept_emb, self.W_opt_q.T), dim=-1)
        opt_ctx = torch.matmul(attn, self.W_opt_q)

        # Substrate 15: Epistemic Doubt Token
        unc_vals = [self.epistemic_entropy(
            root_state, a) for a in range(N_ACTIONS)]
        base_uncertainty = float(np.nan_to_num(
            sum(unc_vals) / max(1, len(unc_vals)), nan=0.0))
        p_doubt = 1.0 - (2.0 ** (-base_uncertainty)
                         ) if math.isfinite(base_uncertainty) else 1.0

        if self.rng.rand() < p_doubt:
            emitted_symbol = 63  # Doubt Token '?'
        else:
            sym_logits = self.W_concept_to_symbol[opt_id]
            sym_probs = torch.softmax(sym_logits, dim=-1)
            emitted_symbol = torch.multinomial(sym_probs, 1).item()

        sym_emb = self.W_lang[emitted_symbol]

        enriched_state = root_state + opt_ctx + sym_emb

        # Run MCTS on enriched state with Substrate 14 Epistemic Budget
        ll_res = self.run_mcts(enriched_state.cpu().numpy(), policy_mode)
        selected_action = int(np.argmax(ll_res["probs"]))

        # Substrate 13: Counterfactual Evaluation
        cf_res = self.evaluate_counterfactual(
            root_state, selected_action, ll_res["qValues"][selected_action])

        return {
            "option_probs": hl_res["probs"],
            "option_qValues": hl_res["qValues"],
            "action_probs": ll_res["probs"],
            "action_qValues": ll_res["qValues"],
            "selected_option": opt_id,
            "selected_action": selected_action,
            "emitted_symbol": emitted_symbol,
            "counterfactual_regret": cf_res["counterfactual_regret"],
            "best_counterfactual_action": cf_res["best_alt_action"],
            "epistemic_uncertainty": ll_res.get("epistemic_uncertainty", 0.0),
            "sims_conducted": ll_res.get("sims_conducted", 32)
        }

    @torch.no_grad()
    def update_hierarchical_experience(self, s_curr_np, concept_id, symbol_id, action_id, reward, s_next_np, is_terminal=False):
        s_c = torch.tensor(s_curr_np, dtype=self.dtype, device=self.device)
        s_n = torch.tensor(s_next_np, dtype=self.dtype, device=self.device)
        ent_gain = self._calculate_entropy_gain(s_c, s_n)
        intrinsic_reward = float(torch.exp(torch.tensor(-ent_gain)).item())

        # Substrate 13: Causal Attribution
        sa_check = torch.zeros(36, dtype=self.dtype, device=self.device)
        sa_check[:32] = s_c
        sa_check[32 + action_id] = 1.0
        pred_next = torch.tanh(torch.matmul(sa_check, self.W_dyn))
        err_dyn = s_n - pred_next
        causal_meta = self.compute_causal_attribution(s_c, err_dyn)

        # Low Level Update (Physical environment reward)
        concept_emb = self.concept_embeddings[concept_id]
        attn = torch.softmax(torch.matmul(concept_emb, self.W_opt_q.T), dim=-1)
        opt_ctx = torch.matmul(attn, self.W_opt_q).cpu().numpy()
        sym_emb = self.W_lang[symbol_id].cpu().numpy()
        enriched_s_curr = s_curr_np + opt_ctx + sym_emb
        self.update_neural_weights(
            enriched_s_curr, action_id, reward, s_next_np, is_terminal)

        # High Level Update (Option buffer)
        if len(self.option_hippocampus) >= 5000:
            self.option_hippocampus.pop(0)

        self.option_hippocampus.append({
            "s_curr": s_curr_np.copy(),
            "option": concept_id,
            "entropy_gain": intrinsic_reward,
            "symbol": symbol_id,
            "cause_idx": causal_meta["cause_index"]
        })

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

        loss_dyn = torch.mean(err_dyn ** 2)
        grad_dyn = torch.outer(sa, (1.0 - pred_next ** 2) * err_dyn)

        # Substrate 13: Causal Weight Plasticity Update
        if len(self.state_history) > 1:
            s_prev = self.state_history[-2]
            grad_causal = torch.outer(err_dyn, s_prev)
            self.W_causal = self._sanitize(
                self.W_causal + 0.005 * grad_causal - 1e-6 * self.W_causal)

        # Substrate 14: True Fisher precision accumulation & Chi-Square calibration
        if not is_replay:
            J = 1.0 - pred_next.float() ** 2
            fisher_obs = torch.outer(
                sa.float() ** 2, J ** 2) / (self.tau2_hat + 1e-9)
            self.I_dyn = torch.nan_to_num(
                self.I_dyn + self.ETA_F * fisher_obs, nan=0.0, posinf=0.0, neginf=0.0)
            err2 = err_dyn.float() ** 2
            self.tau2_hat = torch.nan_to_num(
                (1.0 - self.ETA_F) * self.tau2_hat + self.ETA_F * err2, nan=0.05, posinf=1.0, neginf=0.05)

            param_cov = 1.0 / (self.I_dyn + self.LAMBDA)
            sigma2_pred = J ** 2 * torch.matmul(sa.float() ** 2, param_cov)
            e_calib = float(
                (err2 / (sigma2_pred + self.tau2_hat + 1e-9)).sum().item())
            if not math.isfinite(e_calib):
                e_calib = float(D_MODEL)
            self.calib_ema = 0.99 * self.calib_ema + 0.01 * e_calib
            if self.calib_ema > D_MODEL:
                self.I_dyn *= (D_MODEL / self.calib_ema)

        # EWC Regularization for Zero Forgetting (Rule 24)
        ewc_penalty = 0.5 * \
            self.fisher_diag["W_dyn"] * \
            (self.W_dyn - self.anchor_weights["W_dyn"])
        self.W_dyn = self._sanitize(
            self.W_dyn + 0.005 * grad_dyn - 1e-6 * self.W_dyn - 0.005 * ewc_penalty)

        # Reward Prediction
        pred_rew = torch.matmul(sa, self.W_rew.unsqueeze(-1)).squeeze(-1)
        err_rew = rew_val - pred_rew
        self.W_rew = self._sanitize(
            self.W_rew + 0.005 * (sa * err_rew) - 1e-6 * self.W_rew)

        # Value Function (TD Learning) with Substrate 16 Autotelic Reward
        v_curr = torch.matmul(s_curr, self.W_val.unsqueeze(-1)).squeeze(-1)
        v_next = torch.matmul(s_next, self.W_val_target.unsqueeze(
            -1)).squeeze(-1) if not is_terminal else torch.tensor(0.0, dtype=self.dtype, device=self.device)

        intrinsic_reward = self.curiosity_alpha * float(loss_dyn.item())
        composite_reward = rew_val + \
            torch.tensor(intrinsic_reward, dtype=self.dtype,
                         device=self.device)

        target_v = composite_reward + 0.95 * v_next
        td_err = target_v - v_curr

        self.W_val = self._sanitize(
            self.W_val + 0.005 * (s_curr * td_err) - 1e-6 * self.W_val)
        self.W_val_target = self._sanitize(
            0.995 * self.W_val_target + 0.005 * self.W_val)

        # Policy Gradient Update
        logits = torch.matmul(s_curr, self.W_policy)
        probs = torch.softmax(logits, dim=-1)
        target_policy = torch.zeros(
            N_ACTIONS, dtype=self.dtype, device=self.device)
        target_policy[action] = 1.0
        grad_pol = torch.outer(s_curr, target_policy - probs)
        self.W_policy = self._sanitize(
            self.W_policy + 0.005 * grad_pol - 1e-6 * self.W_policy)

        surprise = float(torch.abs(td_err).item())
        if not math.isfinite(surprise):
            surprise = 1e-5

        # Continual Learning Telemetry Recording
        self.last_td_error = surprise
        self.td_error_ema = 0.99 * self.td_error_ema + 0.01 * surprise
        self.last_value_loss = float((td_err ** 2).item())
        self.last_policy_loss = float(-torch.log(
            torch.clamp(probs[action], min=1e-6)).item())

        l_dyn = float(loss_dyn.item() / 32.0)
        self.last_wm_loss = l_dyn

        # Substrate 16: Boredom / Curiosity Dynamics
        self.wm_loss_ema = 0.99 * self.wm_loss_ema + 0.01 * l_dyn
        if self.wm_loss_ema < 0.002:
            self.is_bored = True
            self.curiosity_alpha = 1.0  # Spike intrinsic drive
        elif self.wm_loss_ema > 0.03:
            self.is_bored = False
            self.curiosity_alpha = 0.2  # Return to baseline

        self.last_ewc_penalty = float(torch.norm(ewc_penalty).item())
        self.last_grad_norm = float(torch.norm(
            grad_dyn).item() + torch.norm(grad_pol).item())
        self.learn_step_count += 1

        if not is_replay:
            if len(self.hippocampus) >= 5000:
                self.hippocampus.pop(0)
            self.hippocampus.append({
                "s_curr": s_curr_np.copy(),
                "action": action,
                "reward": reward,
                "s_next": s_next_np.copy(),
                "is_terminal": is_terminal,
                "surprise": surprise + 1e-5
            })

        return {
            "loss": loss_dyn.item() / 32.0,
            "vCurr": v_curr.item(),
            "surprise": surprise
        }

    @torch.no_grad()
    def update_neural_weights_batch(self, s_curr_b: np.ndarray, action_b: np.ndarray, reward_b: np.ndarray, s_next_b: np.ndarray, term_b: np.ndarray) -> dict:
        s_curr = torch.tensor(s_curr_b, dtype=self.dtype, device=self.device)
        action = torch.tensor(action_b, dtype=torch.long, device=self.device)
        reward = torch.tensor(reward_b, dtype=self.dtype, device=self.device)
        s_next = torch.tensor(s_next_b, dtype=self.dtype, device=self.device)
        term = torch.tensor(term_b, dtype=torch.bool, device=self.device)

        B = s_curr.shape[0]
        sa = torch.zeros((B, 36), dtype=self.dtype, device=self.device)
        sa[:, :32] = s_curr
        sa[torch.arange(B), 32 + action] = 1.0

        pred_next = torch.tanh(torch.matmul(sa, self.W_dyn))
        err_dyn = s_next - pred_next
        loss_dyn_b = torch.mean(err_dyn ** 2, dim=-1)

        grad_dyn = (1.0 - pred_next ** 2) * err_dyn
        batch_grad = torch.matmul(sa.T, grad_dyn) / B

        G = batch_grad ** 2
        self.fisher_diag["W_dyn"] += 0.01 * G

        ewc_penalty = 0.5 * \
            self.fisher_diag["W_dyn"] * \
            (self.W_dyn - self.anchor_weights["W_dyn"])
        self.W_dyn += 0.005 * batch_grad - 1e-6 * self.W_dyn - 0.005 * ewc_penalty

        pred_rew = torch.matmul(sa, self.W_rew.unsqueeze(-1)).squeeze(-1)
        err_rew = reward - pred_rew
        grad_rew = torch.matmul(sa.T, err_rew) / B
        self.W_rew += 0.005 * grad_rew - 1e-6 * self.W_rew

        v_curr = torch.matmul(s_curr, self.W_val.unsqueeze(-1)).squeeze(-1)
        v_next = torch.matmul(
            s_next, self.W_val_target.unsqueeze(-1)).squeeze(-1)
        v_next = torch.where(term, torch.zeros_like(v_next), v_next)
        target_v = reward + 0.95 * v_next
        td_err = target_v - v_curr
        grad_val = torch.matmul(s_curr.T, td_err) / B
        self.W_val += 0.005 * grad_val - 1e-6 * self.W_val
        self.W_val_target = 0.995 * self.W_val_target + 0.005 * self.W_val

        logits = torch.matmul(s_curr, self.W_policy)
        probs = torch.softmax(logits, dim=-1)
        target_pol = torch.zeros(
            (B, N_ACTIONS), dtype=self.dtype, device=self.device)
        target_pol[torch.arange(B), action] = 1.0
        grad_pol = torch.matmul(s_curr.T, target_pol - probs) / B
        self.W_policy += 0.005 * grad_pol - 1e-6 * self.W_policy

        return {
            "loss": loss_dyn_b.mean().item() / 32.0,
            "vCurr": v_curr.mean().item(),
            "td_errs": torch.abs(td_err).cpu().numpy()
        }

    def sleep_consolidation(self) -> int:
        if len(self.hippocampus) < 10:
            return 0
        replays = min(50, len(self.hippocampus))

        indices = self.rng.choice(
            len(self.hippocampus), size=replays, replace=False)
        s_curr_b = np.stack([self.hippocampus[idx]["s_curr"]
                            for idx in indices])
        action_b = np.array([self.hippocampus[idx]["action"]
                            for idx in indices], dtype=np.int64)
        reward_b = np.array([self.hippocampus[idx]["reward"]
                            for idx in indices], dtype=np.float32)
        s_next_b = np.stack([self.hippocampus[idx]["s_next"]
                            for idx in indices])
        term_b = np.array([self.hippocampus[idx].get(
            "is_terminal", False) for idx in indices], dtype=bool)

        batch_metrics = self.update_neural_weights_batch(
            s_curr_b, action_b, reward_b, s_next_b, term_b)

        for i, idx in enumerate(indices):
            self.hippocampus[idx]["surprise"] = float(
                batch_metrics["td_errs"][i]) + 1e-5

        self.anchor_weights["W_dyn"] = self.W_dyn.clone()
        self.anchor_weights["W_causal"] = self.W_causal.clone()
        self.consolidation_count += 1
        return replays

    def get_learning_telemetry(self) -> dict:
        param_drift = 0.0
        for name, init_p in getattr(self, "initial_params", {}).items():
            if hasattr(self, name):
                p = getattr(self, name)
                if isinstance(p, torch.Tensor):
                    param_drift += float(torch.norm(p - init_p).item())

        fisher_norm = float(torch.norm(self.fisher_diag.get(
            "W_dyn", torch.zeros(1, device=self.device))).item())

        return {
            "td_error": float(self.last_td_error),
            "td_error_ema": float(self.td_error_ema),
            "value_loss": float(self.last_value_loss),
            "policy_loss": float(self.last_policy_loss),
            "world_model_loss": float(self.last_wm_loss),
            "wm_loss_ema": float(self.wm_loss_ema),
            "is_bored": bool(self.is_bored),
            "curiosity_alpha": float(self.curiosity_alpha),
            "consolidation_count": int(self.consolidation_count),
            "ewc_penalty": float(self.last_ewc_penalty),
            "fisher_norm": float(fisher_norm),
            "grad_norm": float(self.last_grad_norm),
            "param_drift": float(param_drift),
            "learn_steps": int(self.learn_step_count),
            "hippo_size": int(len(self.hippocampus)),
            "option_hippo_size": int(len(self.option_hippocampus))
        }

    @torch.no_grad()
    def decode_neural_language(self, s_curr_np: np.ndarray, user_prompt: str) -> dict:
        s_curr = torch.tensor(s_curr_np, dtype=self.dtype, device=self.device)
        vocab_logits = torch.matmul(s_curr, self.W_lang.T)
        exp_v = torch.exp(vocab_logits - torch.max(vocab_logits))
        probs = exp_v / (torch.sum(exp_v) + 1e-9)

        top_ids = torch.argsort(probs, descending=True)[:8].cpu().numpy()
        emitted = "".join(chr(65 + (int(tid) % 26)) for tid in top_ids)
        v_val = float(torch.matmul(s_curr, self.W_val.unsqueeze(-1)).item())
        return {
            "top_tokens": emitted,
            "state_sample": [round(float(x), 3) for x in s_curr_np[:4]],
            "v_val": v_val
        }

    def save_checkpoint(self, path: Path):
        h_s_curr = np.array([m["s_curr"] for m in self.hippocampus],
                            dtype=np.float32) if self.hippocampus else np.empty((0, 32), dtype=np.float32)
        h_action = np.array([m["action"] for m in self.hippocampus],
                            dtype=np.int32) if self.hippocampus else np.empty((0,), dtype=np.int32)
        h_reward = np.array([m["reward"] for m in self.hippocampus],
                            dtype=np.float32) if self.hippocampus else np.empty((0,), dtype=np.float32)
        h_s_next = np.array([m["s_next"] for m in self.hippocampus],
                            dtype=np.float32) if self.hippocampus else np.empty((0, 32), dtype=np.float32)
        h_surprise = np.array([m["surprise"] for m in self.hippocampus],
                              dtype=np.float32) if self.hippocampus else np.empty((0,), dtype=np.float32)

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
            W_forget=self.W_forget.cpu().numpy().astype(np.float32),
            W_import=self.W_import.cpu().numpy().astype(np.float32),
            W_dyn=self.W_dyn.cpu().numpy().astype(np.float32),
            W_rew=self.W_rew.cpu().numpy().astype(np.float32),
            W_val=self.W_val.cpu().numpy().astype(np.float32),
            W_val_target=self.W_val_target.cpu().numpy().astype(np.float32),
            W_policy=self.W_policy.cpu().numpy().astype(np.float32),
            W_causal=self.W_causal.cpu().numpy().astype(np.float32),
            W_goal=self.W_goal.cpu().numpy().astype(np.float32),
            I_dyn=self.I_dyn.cpu().numpy().astype(np.float32),
            tau2_hat=self.tau2_hat.cpu().numpy().astype(np.float32),
            h_s_curr=h_s_curr,
            h_action=h_action,
            h_reward=h_reward,
            h_s_next=h_s_next,
            h_surprise=h_surprise
        )

    def load_checkpoint(self, path: Path):
        data = np.load(path)
        if "W_vis" in data:
            if data["W_vis"].shape == self.W_vis.shape:
                self.W_vis = torch.tensor(
                    data["W_vis"], dtype=self.dtype, device=self.device)
            self.W_lang = torch.tensor(
                data["W_lang"], dtype=self.dtype, device=self.device)
            self.W_fuse_vis = torch.tensor(
                data["W_fuse_vis"], dtype=self.dtype, device=self.device)
            self.W_fuse_lang = torch.tensor(
                data["W_fuse_lang"], dtype=self.dtype, device=self.device)
            self.W_q = torch.tensor(
                data["W_q"], dtype=self.dtype, device=self.device)
            self.W_k = torch.tensor(
                data["W_k"], dtype=self.dtype, device=self.device)
            self.W_v = torch.tensor(
                data["W_v"], dtype=self.dtype, device=self.device)
            self.W_out = torch.tensor(
                data["W_out"], dtype=self.dtype, device=self.device)
            self.W_ff1 = torch.tensor(
                data["W_ff1"], dtype=self.dtype, device=self.device)
            self.W_ff2 = torch.tensor(
                data["W_ff2"], dtype=self.dtype, device=self.device)
            self.W_dyn = torch.tensor(
                data["W_dyn"], dtype=self.dtype, device=self.device)
            self.W_rew = torch.tensor(
                data["W_rew"], dtype=self.dtype, device=self.device)
            self.W_val = torch.tensor(
                data["W_val"], dtype=self.dtype, device=self.device)
            if "W_val_target" in data:
                self.W_val_target = torch.tensor(
                    data["W_val_target"], dtype=self.dtype, device=self.device)
            else:
                self.W_val_target = self.W_val.clone()
            self.W_policy = torch.tensor(
                data["W_policy"], dtype=self.dtype, device=self.device)

            if "W_causal" in data:
                self.W_causal = torch.tensor(
                    data["W_causal"], dtype=self.dtype, device=self.device)
            if "W_goal" in data:
                self.W_goal = torch.tensor(
                    data["W_goal"], dtype=self.dtype, device=self.device)
            if "I_dyn" in data:
                self.I_dyn = torch.tensor(
                    data["I_dyn"], dtype=torch.float32, device=self.device)
            if "tau2_hat" in data:
                self.tau2_hat = torch.tensor(
                    data["tau2_hat"], dtype=torch.float32, device=self.device)

            if "W_opt_q" in data:
                self.W_opt_q = torch.tensor(
                    data["W_opt_q"], dtype=self.dtype, device=self.device)
                self.W_k_hist = torch.tensor(
                    data["W_k_hist"], dtype=self.dtype, device=self.device)
                self.W_v_hist = torch.tensor(
                    data["W_v_hist"], dtype=self.dtype, device=self.device)

            if "W_concept_policy" in data:
                self.W_concept_policy = torch.tensor(
                    data["W_concept_policy"], dtype=self.dtype, device=self.device)
                self.W_concept_value = torch.tensor(
                    data["W_concept_value"], dtype=self.dtype, device=self.device)
                self.option_anchor_weights["W_concept_value"] = self.W_concept_value.clone(
                )
            self.option_anchor_weights["concept_embeddings"] = self.concept_embeddings.clone(
            )

            if "W_forget" in data:
                self.W_forget = torch.tensor(
                    data["W_forget"], dtype=self.dtype, device=self.device)
                self.W_import = torch.tensor(
                    data["W_import"], dtype=self.dtype, device=self.device)

        # Sanitize ALL weight matrices — purge NaN/Inf baked into checkpoint
        nan_count = 0
        for attr_name in dir(self):
            if attr_name.startswith("W_"):
                attr = getattr(self, attr_name)
                if isinstance(attr, torch.Tensor):
                    bad = torch.isnan(attr) | torch.isinf(attr)
                    if torch.any(bad):
                        nan_count += int(bad.sum().item())
                        setattr(self, attr_name, self._sanitize(attr))
        if nan_count > 0:
            print(
                f"[GENESIS CORE] Sanitized {nan_count} NaN/Inf values in weight matrices")

        self.I_dyn = torch.nan_to_num(
            self.I_dyn, nan=0.0, posinf=0.0, neginf=0.0)
        self.tau2_hat = torch.nan_to_num(
            self.tau2_hat, nan=0.05, posinf=1.0, neginf=0.05)

        self.anchor_weights["W_dyn"] = self.W_dyn.clone()
        self.anchor_weights["W_causal"] = self.W_causal.clone()
        self.anchor_weights["W_goal"] = self.W_goal.clone()
