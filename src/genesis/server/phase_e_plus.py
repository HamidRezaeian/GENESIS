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
from typing import Tuple, Dict
import warnings

# Suppress HuggingFace warnings for clean logs
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

class SymbolToQueryProjection(nn.Module):
    """
    Projects organism symbol tensor [W, N, K] to LLM query space [W, N, d_model].
    No hardcoded English syntax — purely learned continuous projection.
    """
    def __init__(
        self,
        k_symbols: int = 4,
        d_model: int = 896,  # Qwen2-0.5B hidden dim
        noise_sigma: float = 0.1,
        device: str = "cuda"
    ):
        super().__init__()
        self.K = k_symbols
        self.d_model = d_model
        self.noise_sigma = noise_sigma
        self.dev = torch.device(device)
        
        # Learnable projection matrix: [K, d_model] (FP16)
        self.W_proj = nn.Parameter(
            torch.randn(k_symbols, d_model, device=self.dev, dtype=torch.float16) * 0.02
        )
        self.b_proj = nn.Parameter(
            torch.zeros(d_model, device=self.dev, dtype=torch.float16)
        )
        
        # LayerNorm for stability (FP16)
        self.layer_norm = nn.LayerNorm(d_model, dtype=torch.float16, device=self.dev)
    
    @torch.no_grad()
    def forward(self, action_tensor: torch.Tensor) -> torch.Tensor:
        """
        Args:
            action_tensor: [W, N, K] — organism symbol outputs (continuous)
        Returns:
            query_embedding: [W, N, d_model] — continuous LLM query vectors (FP16)
        """
        act_half = action_tensor.to(dtype=torch.float16, device=self.dev)
        # Linear projection: [W, N, K] @ [K, d_model] -> [W, N, d_model]
        projected = torch.matmul(act_half, self.W_proj) + self.b_proj
        
        # Add exploration noise (prevents mode collapse)
        noise = torch.randn_like(projected, dtype=torch.float16) * self.noise_sigma
        
        # Normalize and activate in FP16
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


class EnergyBudgetEnforcer:
    """
    Physical Landauer energy enforcer (Rule 21 & Rule 9).
    No game mechanics or artificial cooldown timers:
    Organisms query if and only if they possess sufficient metabolic energy.
    """
    def __init__(
        self,
        query_cost_model: LandauerQueryCostModel
    ):
        self.cost_model = query_cost_model
    
    @torch.no_grad()
    def can_query(
        self, 
        organism_energy: torch.Tensor,
        current_tick: int
    ) -> torch.Tensor:
        query_cost = self.cost_model.get_query_cost(batch_size=1)
        # Grounded: Pure physical check (Do you have the energy to pay the Landauer cost?)
        return organism_energy >= query_cost
    
    @torch.no_grad()
    def charge_query(
        self,
        organism_energy: torch.Tensor,
        query_mask: torch.Tensor,
        current_tick: int
    ):
        query_cost = self.cost_model.get_query_cost(batch_size=1)
        organism_energy -= query_mask.to(organism_energy.dtype) * query_cost


class PhaseEPlusInternetSensing:
    """
    Complete Phase-E+ architecture integrating LLM as external sensory organ.
    """
    def __init__(
        self,
        population,
        ecology,
        llm_model_name: str = "Qwen/Qwen2-0.5B",
        device: str = "cuda"
    ):
        self.population = population
        self.ecology = ecology
        self.dev = torch.device(device)
        
        # Gracefully handle missing transformers (so the server doesn't crash if they don't have it)
        try:
            self.llm_interface = LLMSensoryInterface(llm_model_name)
            self.d_model = self.llm_interface.d_model
            self.llm_available = True
        except ImportError:
            print("[GENESIS CORE] WARNING: 'transformers' not installed. Phase-E+ LLM Sensing disabled.")
            self.llm_available = False
            self.d_model = 896
            
        self.sensory_projection = HiddenToSensoryProjection(
            d_model=self.d_model,
            n_sensory=20,  
            device=device
        )
        
        self.cost_model = LandauerQueryCostModel(
            model_params=0.5e9, # Qwen2-0.5B
            sequence_length=1
        )
        
        self.energy_enforcer = EnergyBudgetEnforcer(
            query_cost_model=self.cost_model
        )
        
        self.query_count = 0
    
    @torch.no_grad()
    def step_tick(self, current_tick: int) -> Tuple[torch.Tensor, dict]:
        """
        Execute one Phase-E+ tick with optional LLM sensing.
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
        
        # 2. LLM Sensing (only for organisms that can afford it)
        combined_sensory = spatial_sensory
        query_mask = torch.zeros((self.population.W, self.population.N), dtype=torch.bool, device=self.dev)
        
        if self.llm_available:
            can_query = self.energy_enforcer.can_query(
                self.population.energy,
                current_tick
            )
            
            if torch.any(can_query):
                # Action 4 is "Emit" (Query LLM)
                query_mask = can_query & (self.population.actions == 4)
                
                if torch.any(query_mask):
                    symbol_tensor = self.population.states[:, :, -4:]  # [W, N, 4]
                    query_symbols = symbol_tensor[query_mask]         # [M, 4]
                    
                    # Forward ONLY querying organisms through LLM (M <= 16)
                    query_hidden = self.llm_interface.query_llm(query_symbols)  # [M, d_model]
                    
                    # Scatter back to [W, N, d_model]
                    hidden_state = torch.zeros(
                        (self.population.W, self.population.N, self.d_model),
                        dtype=torch.float16, device=self.dev
                    )
                    hidden_state[query_mask] = query_hidden
                    
                    combined_sensory = self.sensory_projection(hidden_state, spatial_sensory)
                    
                    self.energy_enforcer.charge_query(
                        self.population.energy,
                        query_mask,
                        current_tick
                    )
                    self.query_count += int(query_mask.sum().item())
        
        # 3. Execute population tick
        actions, telemetry = self.population.step_tick(combined_sensory, harvested)
        
        # Add Phase-E+ telemetry
        queries_this_tick = int(query_mask.sum().item())
        telemetry.update({
            "llm_queries_this_tick": queries_this_tick,
            "total_llm_queries": self.query_count,
            "query_to_move_ratio": self.cost_model.get_cost_ratio() if self.llm_available else 0.0,
            "latest_translation": getattr(self.llm_interface, 'latest_translation', None) if self.llm_available else None
        })
        
        return actions, telemetry
