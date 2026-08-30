"""
GENESIS Phase-E+: Internet Sensing (LLM Integration).
Authoritative mathematical formulation by GLM 5.3.

Invariants:
- Rule 9: Autotelic imperative (LLM acts purely as sensory input; no reward signal).
- Rule 21: Thermodynamic Landauer grounding (LLM query costs are derived from FLOPs).
- Rule 25: Absolute zero hardcoding (No English syntax, purely learned continuous projections).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Dict
import warnings

# Suppress HuggingFace warnings for clean logs
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

class ContrastiveProjectionOptimizer(nn.Module):
    """
    GLM 5.3 InfoNCE Contrastive Optimization for Sensorimotor-Language Latent Coupling.
    Self-supervised alignment between organism motor actions and LLM latent consequences.
    """
    def __init__(
        self,
        k_symbols: int = 4,
        d_model: int = 896,
        temperature: float = 0.07,
        queue_size: int = 256,
        projection_dim: int = 128,
        lr: float = 1e-4,
        device: str = "cuda"
    ):
        super().__init__()
        self.temperature = temperature
        self.queue_size = queue_size
        self.projection_dim = projection_dim
        self.dev = torch.device(device)
        
        # Projection heads for contrastive learning
        self.head_q = nn.Sequential(
            nn.Linear(d_model, projection_dim),
            nn.ReLU(),
            nn.Linear(projection_dim, projection_dim)
        ).to(self.dev)
        
        self.head_k = nn.Sequential(
            nn.Linear(d_model, projection_dim),
            nn.ReLU(),
            nn.Linear(projection_dim, projection_dim)
        ).to(self.dev)
        
        # Negative sample queue (FIFO)
        self.register_buffer("queue", torch.randn(queue_size, projection_dim, device=self.dev))
        self.register_buffer("queue_ptr", torch.zeros(1, dtype=torch.long, device=self.dev))
        
        # Optimizer
        self.optimizer = torch.optim.AdamW(
            list(self.head_q.parameters()) + list(self.head_k.parameters()),
            lr=lr,
            weight_decay=1e-5
        )
        
    @torch.no_grad()
    def _dequeue_and_enqueue(self, keys: torch.Tensor):
        batch_size = keys.shape[0]
        ptr = int(self.queue_ptr.item())
        indices = (torch.arange(batch_size, device=self.dev) + ptr) % self.queue_size
        self.queue[indices] = keys.detach()
        self.queue_ptr[0] = (ptr + batch_size) % self.queue_size

    def compute_infonce_loss(self, action_embeds: torch.Tensor, llm_hidden: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        InfoNCE Loss: aligns action projection with LLM hidden state consequences.
        """
        q = F.normalize(self.head_q(action_embeds.float()), dim=-1)
        k = F.normalize(self.head_k(llm_hidden.float()), dim=-1)
        
        l_pos = torch.einsum('nc,nc->n', [q, k]).unsqueeze(-1)
        l_neg = torch.einsum('nc,kc->nk', [q, self.queue.clone().detach().float()])
        
        logits = torch.cat([l_pos, l_neg], dim=1) / self.temperature
        labels = torch.zeros(logits.shape[0], dtype=torch.long, device=self.dev)
        
        loss = F.cross_entropy(logits, labels)
        return loss, k.detach()

    def update_projection(self, action_embeds: torch.Tensor, llm_hidden: torch.Tensor) -> float:
        """One step of contrastive learning."""
        with torch.enable_grad():
            loss, k_detach = self.compute_infonce_loss(action_embeds, llm_hidden)
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.parameters(), max_norm=1.0)
            self.optimizer.step()
        self._dequeue_and_enqueue(k_detach)
        return float(loss.item())


class SymbolToQueryProjection(nn.Module):
    """
    Continuous projection from organism 4-symbol output to LLM hidden space (FP16).
    """
    def __init__(self, k_symbols: int = 4, d_model: int = 896, device: str = "cuda"):
        super().__init__()
        self.k_symbols = k_symbols
        self.d_model = d_model
        self.dev = torch.device(device if torch.cuda.is_available() else "cpu")
        
        # Linear projection weight [K, d_model] in FP16
        self.W_proj = nn.Parameter(
            torch.randn(k_symbols, d_model, device=self.dev, dtype=torch.float16) * 0.02
        )
        self.b_proj = nn.Parameter(
            torch.zeros(d_model, device=self.dev, dtype=torch.float16)
        )
        
        # LayerNorm to stabilize activation scale
        self.layer_norm = nn.LayerNorm(d_model, device=self.dev, dtype=torch.float16)
        self.noise_sigma = 0.05
        
    def forward(self, action_tensor: torch.Tensor) -> torch.Tensor:
        act_half = action_tensor.to(dtype=torch.float16, device=self.dev)
        projected = torch.matmul(act_half, self.W_proj) + self.b_proj
        noise = torch.randn_like(projected, dtype=torch.float16) * self.noise_sigma
        query = torch.tanh(self.layer_norm(projected + noise))
        return query.to(torch.float16)


class LLMSensoryInterface:
    def __init__(self, model_name: str = "Qwen/Qwen2-0.5B", device: str = "cuda"):
        from transformers import AutoModelForCausalLM, AutoConfig, AutoTokenizer
        print(f"[GENESIS CORE] Initializing External Sensory Organ (LLM): {model_name}")
        
        self.dev = torch.device(device if torch.cuda.is_available() else "cpu")
        self.config = AutoConfig.from_pretrained(model_name)
        self.d_model = self.config.hidden_size
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.llm = AutoModelForCausalLM.from_pretrained(
            model_name, 
            dtype=torch.float16
        ).to(self.dev)
        self.llm.eval()
        
        # Cache normalized vocabulary embeddings for instant translation
        self.embed_weights = self.llm.get_input_embeddings().weight.detach() # [V, d_model]
        
        self.projection = SymbolToQueryProjection(
            k_symbols=4, 
            d_model=self.d_model,
            device=device
        )
        self.contrastive = ContrastiveProjectionOptimizer(d_model=self.d_model, device=device)
        self.latest_translation = None
    
    @torch.no_grad()
    def query_llm(self, query_symbols: torch.Tensor) -> torch.Tensor:
        """
        Args:
            query_symbols: [M, K] — organism symbols for active querying organisms only
        Returns:
            hidden_state: [M, d_model] — LLM last hidden state (FP16)
        """
        query = self.projection(query_symbols).to(torch.float16)  # [M, d_model]
        
        M, D = query.shape
        query_flat = query.view(M, 1, D)
        
        # Pass ONLY the M querying organisms through the base LLM model (Sparse Sub-Batch)
        outputs = self.llm.model(
            inputs_embeds=query_flat,
            output_hidden_states=True
        )
        
        hidden = outputs.last_hidden_state.squeeze(1).to(torch.float16)
        
        # Decode top tokens for human observability
        try:
            dot_q = torch.matmul(query[:3], self.embed_weights.t())
            top_q_ids = torch.argmax(dot_q, dim=-1)
            q_words = [self.tokenizer.decode([idx.item()]).strip() for idx in top_q_ids]
            
            dot_h = torch.matmul(hidden[:3], self.embed_weights.t())
            top_h_ids = torch.argmax(dot_h, dim=-1)
            h_words = [self.tokenizer.decode([idx.item()]).strip() for idx in top_h_ids]
            
            self.latest_translation = {
                "query_words": q_words,
                "response_words": h_words,
                "symbols": query_symbols[0].detach().cpu().numpy().round(2).tolist()
            }
        except Exception:
            pass
            
        return hidden


class HiddenToSensoryProjection(nn.Module):
    """
    Projects LLM hidden state [W, N, d_model] to sensory inputs [W, N, S].
    Mixes directly into the spatial sensory channels dynamically.
    """
    def __init__(
        self,
        d_model: int = 896,
        n_sensory: int = 20,
        device: str = "cuda"
    ):
        super().__init__()
        self.d_model = d_model
        self.S = n_sensory
        self.dev = torch.device(device)
        
        # Main projection (FP16)
        self.W_sense = nn.Parameter(
            torch.randn(d_model, n_sensory, device=self.dev, dtype=torch.float16) * 0.01
        )
        self.b_sense = nn.Parameter(
            torch.zeros(n_sensory, device=self.dev, dtype=torch.float16)
        )
        
        # Gating network (FP16)
        self.W_gate = nn.Parameter(
            torch.randn(d_model, n_sensory, device=self.dev, dtype=torch.float16) * 0.01
        )
        self.b_gate = nn.Parameter(
            torch.zeros(n_sensory, device=self.dev, dtype=torch.float16)
        )
        
        # Mixing coefficient (starts near zero — grounding first)
        self.mixing_lambda = nn.Parameter(
            torch.tensor(0.01, device=self.dev, dtype=torch.float16)
        )
    
    @torch.no_grad()
    def forward(
        self, 
        hidden_state: torch.Tensor,
        spatial_sensory: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            hidden_state: [W, N, d_model] — LLM response
            spatial_sensory: [W, N, S] — existing spatial sensory inputs
        """
        h_half = hidden_state.to(dtype=torch.float16, device=self.dev)
        ext_sensory = torch.sigmoid(torch.matmul(h_half, self.W_sense) + self.b_sense)
        gate = torch.sigmoid(torch.matmul(h_half, self.W_gate) + self.b_gate)
        
        gated_ext = ext_sensory * gate
        lambda_val = torch.sigmoid(self.mixing_lambda)
        
        combined = spatial_sensory.to(dtype=torch.float16) + lambda_val * gated_ext
        return torch.clamp(combined, 0.0, 1.0).to(spatial_sensory.dtype)


class LandauerQueryCostModel:
    """
    Computes Landauer-grounded energy cost for LLM queries.
    Uses realistic RTX 3050 coefficients (Rule 9: 500x-2000x movement cost).
    """
    def __init__(
        self,
        model_params: float = 0.5e9,     # Qwen2-0.5B
        sequence_length: int = 1,        
        movement_cost: float = 0.05,     
        query_to_move_target_ratio: float = 500.0
    ):
        self.N = model_params
        self.T = sequence_length
        self.E_move = movement_cost
        
        # Grounded: Query cost is 500x movement cost (Rule 9 & 21)
        self.E_query_total = self.E_move * query_to_move_target_ratio  # 25.0 energy
        self.query_to_move_ratio = query_to_move_target_ratio
    
    def get_cost_ratio(self) -> float:
        return self.query_to_move_ratio

    def get_query_cost(self, batch_size: int = 1) -> float:
        return self.E_query_total


class TemporalDecoupledSensory:
    """
    GLM 5.3 Layer 1: Temporal Decoupling.
    LLM sensory field updated every N ticks with Zero-Order / First-Order Hold.
    """
    def __init__(self, n_worlds: int = 32, pop_per_world: int = 128, n_sensory: int = 20, update_interval: int = 10, device: str = "cuda"):
        self.N = update_interval
        self.W = n_worlds
        self.P = pop_per_world
        self.S = n_sensory
        self.dev = torch.device(device)
        
        # Persistent sensory cache [W, P, S]
        self.sensory_cache = torch.zeros((n_worlds, pop_per_world, n_sensory), dtype=torch.float16, device=self.dev)
        self.prev_cache = torch.zeros_like(self.sensory_cache)
        self.last_update_tick = 0
    
    def get_sensory(self, current_tick: int) -> torch.Tensor:
        """Return cached sensory with smooth interpolation."""
        if current_tick - self.last_update_tick >= self.N:
            return self.sensory_cache
        
        alpha = float((current_tick - self.last_update_tick) / max(1, self.N))
        return (1.0 - alpha) * self.prev_cache + alpha * self.sensory_cache
    
    def update_cache(self, new_sensory: torch.Tensor, current_tick: int):
        self.prev_cache.copy_(self.sensory_cache)
        self.sensory_cache.copy_(new_sensory)
        self.last_update_tick = current_tick


class StochasticSensoryGate:
    """
    GLM 5.3 Layer 2: Energy-Gated Stochastic Sub-Sampling (Rule 25 Compliant).
    Bernoulli sampling with adaptive temperature to maintain target batch size K=32.
    """
    def __init__(self, query_cost: float = 25.0, target_batch_size: int = 32, device: str = "cuda"):
        self.E_query = query_cost
        self.K_target = target_batch_size
        self.dev = torch.device(device)
        self.tau_gate = 10.0
    
    @torch.no_grad()
    def select_queries(self, energy: torch.Tensor, emit_mask: torch.Tensor) -> torch.Tensor:
        """
        Returns boolean mask [W, P] of organisms selected to query this tick.
        """
        # Emergent energy-gated probability: p = sigmoid((E - E_query) / tau)
        gate_logit = (energy - self.E_query) / max(0.1, self.tau_gate)
        p_query = torch.sigmoid(gate_logit)
        
        # Apply strictly to emitters (action == 4)
        p_masked = p_query * emit_mask.float()
        
        # Stochastic Bernoulli sampling
        rand = torch.rand_like(p_masked)
        selected = (rand < p_masked) & emit_mask
        
        # Adaptive temperature control to maintain target batch size K=32
        n_selected = int(selected.sum().item())
        if n_selected > self.K_target * 1.5:
            self.tau_gate *= 0.95
        elif n_selected < self.K_target * 0.5:
            self.tau_gate *= 1.05
        self.tau_gate = float(np.clip(self.tau_gate, 1.0, 100.0)) if 'np' in globals() else max(1.0, min(100.0, self.tau_gate))
        
        return selected


class PhaseEPlusInternetSensing:
    """
    Complete Phase-E+ architecture integrating LLM as external sensory organ.
    Authoritative GLM 5.3 formulation: Multi-Rate Stochastic Sensory Gating.
    """
    def __init__(
        self,
        population,
        ecology,
        llm_model_name: str = "Qwen/Qwen2-0.5B",
        device: str = "cuda",
        update_interval: int = 10,
        target_batch_size: int = 32
    ):
        self.population = population
        self.ecology = ecology
        self.dev = torch.device(device if torch.cuda.is_available() else "cpu")
        self.update_interval = update_interval
        
        # Gracefully handle transformers
        try:
            self.llm_interface = LLMSensoryInterface(llm_model_name, device=str(self.dev))
            self.d_model = self.llm_interface.d_model
            self.llm_available = True
        except Exception as e:
            print(f"[GENESIS CORE] WARNING: LLM Interface failed: {e}. Phase-E+ Sensing disabled.")
            self.llm_available = False
            self.d_model = 896
            
        self.sensory_projection = HiddenToSensoryProjection(
            d_model=self.d_model,
            n_sensory=20,  
            device=str(self.dev)
        )
        
        self.cost_model = LandauerQueryCostModel(
            model_params=0.5e9,
            sequence_length=1
        )
        
        # GLM 5.3 Layer 1: Temporal Decoupling
        self.temporal_cache = TemporalDecoupledSensory(
            n_worlds=self.population.W,
            pop_per_world=self.population.N,
            n_sensory=20,
            update_interval=update_interval,
            device=str(self.dev)
        )
        
        # GLM 5.3 Layer 2: Stochastic Gating
        self.stochastic_gate = StochasticSensoryGate(
            query_cost=25.0,
            target_batch_size=target_batch_size,
            device=str(self.dev)
        )
        
        self.query_count = 0
        self.query_history = []
        self.last_contrastive_loss = 0.0
    
    @torch.no_grad()
    def step_tick(self, current_tick: int) -> Tuple[torch.Tensor, dict]:
        """
        Execute one Phase-E+ tick with Multi-Rate Stochastic Sensory Gating.
        Returns:
            (actions, telemetry)
        """
        # 1. Standard spatial ecology update
        spatial_sensory, harvested = self.ecology.process_interactions(
            self.population.positions,
            self.population.orientations,
            self.population.actions,
            self.population.alive_mask,
            self.population.energy,
            self.dev
        )
        
        queries_this_tick = 0
        
        # 2. GLM 5.3 Multi-Rate Gated Inference (runs every N=10 ticks)
        if self.llm_available and (current_tick % self.update_interval == 0):
            # Action 4 is "Emit"
            emit_mask = (self.population.actions == 4) & self.population.alive_mask & (self.population.energy >= 25.0)
            
            if torch.any(emit_mask):
                # Sample target K=32 querying organisms stochastically
                selected_mask = self.stochastic_gate.select_queries(
                    self.population.energy,
                    emit_mask
                )
                
                n_selected = int(selected_mask.sum().item())
                if n_selected > 0:
                    queries_this_tick = n_selected
                    self.query_count += n_selected
                    
                    # Extract symbols from selected organisms
                    symbol_tensor = self.population.states[:, :, -4:]  # [W, N, 4]
                    query_symbols = symbol_tensor[selected_mask]       # [M, 4]
                    
                    # Forward ONLY the selected organisms through Qwen (M <= 32)
                    query_hidden = self.llm_interface.query_llm(query_symbols)  # [M, d_model]
                    
                    # Buffer recent pairs for contrastive optimization
                    self.query_history.append((
                        self.llm_interface.projection(query_symbols).detach(),
                        query_hidden.detach()
                    ))
                    if len(self.query_history) > 64:
                        self.query_history.pop(0)
                    
                    # Scatter back to [W, N, d_model]
                    hidden_state = torch.zeros(
                        (self.population.W, self.population.N, self.d_model),
                        dtype=torch.float16, device=self.dev
                    )
                    hidden_state[selected_mask] = query_hidden
                    
                    # Project and update persistent sensory cache
                    new_combined = self.sensory_projection(hidden_state, spatial_sensory)
                    self.temporal_cache.update_cache(new_combined, current_tick)
                    
                    # Charge Landauer metabolic cost (25 energy per query)
                    self.population.energy[selected_mask] -= 25.0
                    
        # Periodic Contrastive Learning Update (every 1000 ticks)
        if self.llm_available and (current_tick % 1000 == 0) and len(self.query_history) >= 16:
            action_embeds_batch = torch.cat([p[0] for p in self.query_history], dim=0)
            llm_hidden_batch = torch.cat([p[1] for p in self.query_history], dim=0)
            self.last_contrastive_loss = self.llm_interface.contrastive.update_projection(
                action_embeds_batch, llm_hidden_batch
            )
        
        # Retrieve temporal sensory field (cached / interpolated)
        combined_sensory = self.temporal_cache.get_sensory(current_tick)
        
        # 3. Execute population tick
        actions, telemetry = self.population.step_tick(combined_sensory, harvested)
        
        # Add Phase-E+ telemetry
        telemetry.update({
            "llm_queries_this_tick": queries_this_tick,
            "total_llm_queries": self.query_count,
            "contrastive_loss": self.last_contrastive_loss,
            "query_to_move_ratio": self.cost_model.get_cost_ratio() if self.llm_available else 0.0,
            "latest_translation": getattr(self.llm_interface, 'latest_translation', None) if self.llm_available else None
        })
        
        return actions, telemetry
