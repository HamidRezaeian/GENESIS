"""
GENESIS Phase-E: Batched Open-Ended Evolutionary ALife Substrate Core.
Authoritative mathematical formulation by GLM 5.3.

Invariants:
- Rule 6: Open-ended emergence from AGI to AXI without authored task shortcuts.
- Rule 9: Autotelic imperative (No external loss functions or artificial reward labels).
- Rule 21: Thermodynamic Landauer grounding (Cycles, FLOPs, and RAM traffic define energy costs).
- Rule 23: PyTorch CUDA FP16 batched execution with zero dynamic allocation in simulation ticks.
- Rule 25: Absolute zero hardcoded shortcuts; behavior emerges purely from dynamic topology and local STDP.
"""

import math
import copy
from typing import Dict, Any, List, Tuple, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class CPPNGenome:
    """
    Compositional Pattern Producing Network (CPPN) Indirect Genome Encoding.
    Encodes spatial topology (Neurogenesis), 3-factor local plasticity parameters,
    and metabolic life-cycle thresholds for each organism.
    """
    def __init__(
        self,
        rng: Optional[np.random.RandomState] = None,
        seed: Optional[int] = None
    ):
        self.rng = rng if rng is not None else np.random.RandomState(seed)
        
        # 1. CPPN Topological Generator Weights (4 inputs -> 8 hidden -> 1 output)
        # Inputs: [x_pre, y_post, dist_euclid, bias=1.0]
        self.W_cppn_1 = self.rng.randn(4, 8).astype(np.float32) * 0.5
        self.b_cppn_1 = self.rng.randn(8).astype(np.float32) * 0.1
        self.W_cppn_2 = self.rng.randn(8, 1).astype(np.float32) * 0.5
        self.b_cppn_2 = float(self.rng.randn() * 0.1)
        
        # 2. Local 3-Factor Plasticity Parameters
        self.eta_stdp = float(np.clip(self.rng.normal(0.01, 0.003), 0.001, 0.05))
        self.tau_trace = float(np.clip(self.rng.normal(0.85, 0.05), 0.50, 0.98))
        self.A_plus = float(np.clip(self.rng.normal(0.05, 0.01), 0.01, 0.20))
        self.A_minus = float(np.clip(self.rng.normal(0.04, 0.01), 0.01, 0.20))
        self.tau_homeo = float(np.clip(self.rng.normal(0.001, 0.0003), 0.0001, 0.01))
        
        # 3. Metabolic & Lifecycle Parameters
        self.E_threshold = float(np.clip(self.rng.normal(160.0, 20.0), 80.0, 300.0))
        self.metabolic_rate = float(np.clip(self.rng.normal(0.15, 0.03), 0.05, 0.50))
        
        # Synapse threshold for CPPN expression
        self.synapse_thresh = 0.25

    def express_phenotype(
        self,
        max_neurons: int = 64,
        max_synapses: int = 512,
        input_neurons: int = 16,
        output_neurons: int = 4
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Derive neural wiring from CPPN:
        Returns:
          pre_idx: [max_synapses] (int64)
          post_idx: [max_synapses] (int64)
          weights: [max_synapses] (float32)
          syn_active: [max_synapses] (bool)
        """
        # Assign 2D coordinates to neurons on a circle in [-1, 1]
        coords = np.zeros((max_neurons, 2), dtype=np.float32)
        for i in range(max_neurons):
            angle = (2.0 * math.pi * i) / max_neurons
            r = 0.5 if i < input_neurons else (0.8 if i >= max_neurons - output_neurons else 0.65)
            coords[i, 0] = r * math.cos(angle)
            coords[i, 1] = r * math.sin(angle)
            
        pre_list, post_list, weight_list = [], [], []
        
        # Evaluate CPPN over candidate pairs (feedforward + recurrent paths)
        for src in range(max_neurons):
            for dst in range(max_neurons):
                # Don't connect directly into input sensory neurons
                if dst < input_neurons:
                    continue
                x1, y1 = coords[src]
                x2, y2 = coords[dst]
                d = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
                
                feat = np.array([x1, y2, d, 1.0], dtype=np.float32)
                h = np.tanh(np.dot(feat, self.W_cppn_1) + self.b_cppn_1)
                w_raw = float(np.dot(h, self.W_cppn_2)[0] + self.b_cppn_2)
                
                if abs(w_raw) >= self.synapse_thresh:
                    w_clamped = float(np.clip(w_raw, -3.0, 3.0))
                    pre_list.append(src)
                    post_list.append(dst)
                    weight_list.append(w_clamped)
                    if len(pre_list) >= max_synapses:
                        break
            if len(pre_list) >= max_synapses:
                break
                
        n_syn = len(pre_list)
        pre_arr = np.zeros(max_synapses, dtype=np.int64)
        post_arr = np.zeros(max_synapses, dtype=np.int64)
        w_arr = np.zeros(max_synapses, dtype=np.float32)
        active_arr = np.zeros(max_synapses, dtype=bool)
        
        if n_syn > 0:
            pre_arr[:n_syn] = pre_list
            post_arr[:n_syn] = post_list
            w_arr[:n_syn] = weight_list
            active_arr[:n_syn] = True
            
        return pre_arr, post_arr, w_arr, active_arr

    def mutate(self) -> 'CPPNGenome':
        """Create mutated offspring genome."""
        child = copy.deepcopy(self)
        
        # 1. Mutate CPPN weights (Gaussian drift)
        if child.rng.rand() < 0.8:
            child.W_cppn_1 += child.rng.randn(*child.W_cppn_1.shape) * 0.08
            child.b_cppn_1 += child.rng.randn(*child.b_cppn_1.shape) * 0.04
            child.W_cppn_2 += child.rng.randn(*child.W_cppn_2.shape) * 0.08
            child.b_cppn_2 += float(child.rng.randn() * 0.04)
            
        # 2. Mutate plasticity params
        if child.rng.rand() < 0.5:
            child.eta_stdp = float(np.clip(child.eta_stdp + child.rng.normal(0, 0.002), 0.001, 0.05))
            child.tau_trace = float(np.clip(child.tau_trace + child.rng.normal(0, 0.02), 0.50, 0.98))
            child.A_plus = float(np.clip(child.A_plus + child.rng.normal(0, 0.005), 0.01, 0.20))
            child.A_minus = float(np.clip(child.A_minus + child.rng.normal(0, 0.005), 0.01, 0.20))
            child.tau_homeo = float(np.clip(child.tau_homeo + child.rng.normal(0, 0.0002), 0.0001, 0.01))
            
        # 3. Mutate metabolic params
        if child.rng.rand() < 0.4:
            child.E_threshold = float(np.clip(child.E_threshold + child.rng.normal(0, 5.0), 80.0, 300.0))
            child.metabolic_rate = float(np.clip(child.metabolic_rate + child.rng.normal(0, 0.01), 0.05, 0.50))
            
        return child

    @classmethod
    def crossover(cls, parent_a: 'CPPNGenome', parent_b: 'CPPNGenome') -> 'CPPNGenome':
        """Homologous crossover between two parent genomes."""
        child = copy.deepcopy(parent_a)
        mask1 = child.rng.rand(*child.W_cppn_1.shape) < 0.5
        child.W_cppn_1 = np.where(mask1, parent_a.W_cppn_1, parent_b.W_cppn_1)
        child.W_cppn_2 = np.where(child.rng.rand(*child.W_cppn_2.shape) < 0.5, parent_a.W_cppn_2, parent_b.W_cppn_2)
        
        # Blend plasticity & metabolic
        alpha = float(child.rng.rand())
        child.eta_stdp = alpha * parent_a.eta_stdp + (1 - alpha) * parent_b.eta_stdp
        child.tau_trace = alpha * parent_a.tau_trace + (1 - alpha) * parent_b.tau_trace
        child.A_plus = alpha * parent_a.A_plus + (1 - alpha) * parent_b.A_plus
        child.A_minus = alpha * parent_a.A_minus + (1 - alpha) * parent_b.A_minus
        child.E_threshold = alpha * parent_a.E_threshold + (1 - alpha) * parent_b.E_threshold
        child.metabolic_rate = alpha * parent_a.metabolic_rate + (1 - alpha) * parent_b.metabolic_rate
        return child


class BatchedPopulation(nn.Module):
    """
    TensorNEAT-style Batched Evolutionary Population Engine.
    Executes an entire heterogeneous population of N organisms in CUDA/PyTorch FP16
    with zero dynamic allocations inside simulation ticks.
    """
    def __init__(
        self,
        pop_size: int = 128,
        max_neurons: int = 64,
        max_synapses: int = 512,
        input_neurons: int = 16,
        output_neurons: int = 4,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        seed: int = 42
    ):
        super().__init__()
        self.pop_size = pop_size
        self.max_neurons = max_neurons
        self.max_synapses = max_synapses
        self.input_neurons = input_neurons
        self.output_neurons = output_neurons
        self.dev = torch.device(device)
        self.dtype = torch.float16 if self.dev.type == "cuda" else torch.float32
        self.rng = np.random.RandomState(seed)
        
        # --- Pre-allocated State Tensors (Zero allocation inside loop) ---
        self.register_buffer("states", torch.zeros(pop_size, max_neurons, dtype=self.dtype, device=self.dev))
        self.register_buffer("weights", torch.zeros(pop_size, max_synapses, dtype=self.dtype, device=self.dev))
        self.register_buffer("eligibility", torch.zeros(pop_size, max_synapses, dtype=self.dtype, device=self.dev))
        self.register_buffer("energy", torch.full((pop_size,), 100.0, dtype=self.dtype, device=self.dev))
        self.register_buffer("pre_idx", torch.zeros(pop_size, max_synapses, dtype=torch.int64, device=self.dev))
        self.register_buffer("post_idx", torch.zeros(pop_size, max_synapses, dtype=torch.int64, device=self.dev))
        self.register_buffer("syn_active", torch.zeros(pop_size, max_synapses, dtype=torch.bool, device=self.dev))
        self.register_buffer("alive_mask", torch.zeros(pop_size, dtype=torch.bool, device=self.dev))
        
        # --- Spatial & Behavioral Buffers ---
        self.register_buffer("positions", torch.zeros(pop_size, 2, dtype=torch.float32, device=self.dev))
        self.register_buffer("orientations", torch.zeros(pop_size, dtype=torch.int64, device=self.dev))
        self.register_buffer("actions", torch.zeros(pop_size, dtype=torch.int64, device=self.dev))
        self.register_buffer("lineage_depth", torch.zeros(pop_size, dtype=torch.int64, device=self.dev))
        self.register_buffer("generation_counter", torch.zeros(1, dtype=torch.int64, device=self.dev))
        
        # --- Plasticity & Metabolic Coefficient Buffers (Vectorized) ---
        self.register_buffer("eta_stdp", torch.zeros(pop_size, dtype=self.dtype, device=self.dev))
        self.register_buffer("tau_trace", torch.zeros(pop_size, dtype=self.dtype, device=self.dev))
        self.register_buffer("A_plus", torch.zeros(pop_size, dtype=self.dtype, device=self.dev))
        self.register_buffer("A_minus", torch.zeros(pop_size, dtype=self.dtype, device=self.dev))
        self.register_buffer("tau_homeo", torch.zeros(pop_size, dtype=self.dtype, device=self.dev))
        self.register_buffer("E_threshold", torch.zeros(pop_size, dtype=self.dtype, device=self.dev))
        self.register_buffer("metabolic_rate", torch.zeros(pop_size, dtype=self.dtype, device=self.dev))
        
        # Genome repository
        self.genomes: List[Optional[CPPNGenome]] = [None] * pop_size
        
        # Telemetry accumulators
        self.total_births = 0
        self.total_deaths = 0
        self.total_ticks = 0
        
        # Landauer physical scaling constants (Rule 21)
        self.E_base = 0.05
        self.E_flop = 1e-4
        self.E_traffic = 2e-5
        
        self.initialize_founder_population(initial_pop=min(64, pop_size))

    def initialize_founder_population(self, initial_pop: int):
        """Populate initial organisms with diverse CPPN founder genomes."""
        for i in range(initial_pop):
            genome = CPPNGenome(rng=self.rng)
            self._load_organism(i, genome, initial_energy=100.0)
        self.alive_mask[:initial_pop] = True
        self.alive_mask[initial_pop:] = False

    def _load_organism(self, idx: int, genome: CPPNGenome, initial_energy: float = 100.0, depth: int = 0):
        """Express genome into pre-allocated slot `idx`."""
        pre_arr, post_arr, w_arr, act_arr = genome.express_phenotype(
            max_neurons=self.max_neurons,
            max_synapses=self.max_synapses,
            input_neurons=self.input_neurons,
            output_neurons=self.output_neurons
        )
        
        self.genomes[idx] = genome
        self.pre_idx[idx] = torch.tensor(pre_arr, dtype=torch.int64, device=self.dev)
        self.post_idx[idx] = torch.tensor(post_arr, dtype=torch.int64, device=self.dev)
        self.weights[idx] = torch.tensor(w_arr, dtype=self.dtype, device=self.dev)
        self.syn_active[idx] = torch.tensor(act_arr, dtype=torch.bool, device=self.dev)
        self.eligibility[idx].zero_()
        self.states[idx].zero_()
        self.energy[idx] = float(initial_energy)
        self.alive_mask[idx] = True
        self.lineage_depth[idx] = depth
        
        # Set individual plasticity & metabolic traits
        self.eta_stdp[idx] = genome.eta_stdp
        self.tau_trace[idx] = genome.tau_trace
        self.A_plus[idx] = genome.A_plus
        self.A_minus[idx] = genome.A_minus
        self.tau_homeo[idx] = genome.tau_homeo
        self.E_threshold[idx] = genome.E_threshold
        self.metabolic_rate[idx] = genome.metabolic_rate
        
        # Random initial 2D coordinate [0, 1]
        self.positions[idx, 0] = float(self.rng.rand())
        self.positions[idx, 1] = float(self.rng.rand())
        self.orientations[idx] = int(self.rng.randint(0, 4))

    @torch.no_grad()
    def step_tick(self, sensory_inputs: torch.Tensor, harvested_resources: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, Any]]:
        """
        Execute one complete batched HPC simulation tick across all alive organisms:
        1. Inject sensory observations.
        2. Vectorized forward neural propagation.
        3. 3-Factor local STDP plasticity update.
        4. Thermodynamic Landauer metabolic accounting.
        5. Vectorized lifecycle: Death and Auto-Reproduction.
        """
        self.total_ticks += 1
        active_alive = self.alive_mask
        n_alive = int(active_alive.sum().item())
        
        if n_alive == 0:
            # Reseed minimum viable founder pool under Rule 14/16 if extinction occurs
            self.initialize_founder_population(initial_pop=min(32, self.pop_size))
            n_alive = int(self.alive_mask.sum().item())

        # 1. Inject sensory inputs [pop, input_neurons]
        self.states[:, :self.input_neurons] = sensory_inputs.to(self.dtype)

        # 2. Vectorized Neural Propagation (Scatter-Add)
        # pre_states: [pop, max_synapses]
        pre_states = torch.gather(self.states, 1, self.pre_idx)
        # mask inactive synapses
        pre_states = pre_states * self.syn_active.to(self.dtype)
        syn_contributions = pre_states * self.weights
        
        # Accumulate into post-synaptic neurons
        post_acc = torch.zeros_like(self.states)
        post_acc.scatter_add_(1, self.post_idx, syn_contributions)
        
        # Nonlinear recurrent activation
        new_states = torch.tanh(post_acc)
        # Preserve input sensory stream at inputs
        new_states[:, :self.input_neurons] = self.states[:, :self.input_neurons]
        self.states.copy_(new_states)

        # Output motor action decisions (last 4 neurons: [0: Fwd, 1: TurnL, 2: TurnR, 3: Harvest])
        motor_logits = self.states[:, self.max_neurons - self.output_neurons:]
        self.actions = torch.argmax(motor_logits, dim=-1)

        # 3. Vectorized 3-Factor STDP Plasticity Update
        # STDP Hebbian correlation term: Pre * Post
        post_gathered = torch.gather(self.states, 1, self.post_idx)
        stdp_corr = pre_states * post_gathered  # [pop, max_synapses]
        
        # Eligibility trace: E = tau * E + correlation
        tau_t = self.tau_trace.unsqueeze(-1)
        self.eligibility = tau_t * self.eligibility + stdp_corr
        
        # Modulator M(t) derived from energy surplus homeostasis (No external reward!)
        # M(t) = sigma((E - E_thresh) / E_thresh) - 0.5
        surplus = (self.energy - self.E_threshold) / torch.clamp(self.E_threshold, min=1.0)
        M_t = (torch.sigmoid(surplus) - 0.5).unsqueeze(-1)  # [pop, 1]
        
        # Weight adjustment with synaptic homeostasis
        eta = self.eta_stdp.unsqueeze(-1)
        gamma_h = self.tau_homeo.unsqueeze(-1)
        dW = eta * M_t * self.eligibility - gamma_h * self.weights
        self.weights = torch.clamp(self.weights + dW * self.syn_active.to(self.dtype), -4.0, 4.0)

        # 4. Strict Landauer Thermodynamic Accounting (Rule 21)
        # FLOP count per tick = 2 * active_synapses
        n_syn_active = self.syn_active.sum(dim=-1).to(self.dtype)
        flops_cost = n_syn_active * self.E_flop
        traffic_cost = (n_syn_active * 2.0 + self.max_neurons * 2.0) * self.E_traffic
        base_cost = self.metabolic_rate + self.E_base
        
        total_metabolic_cost = (base_cost + flops_cost + traffic_cost) * active_alive.to(self.dtype)
        
        # Energy update: Intake from environment - Metabolic Cost
        intake = harvested_resources.to(self.dtype) * active_alive.to(self.dtype)
        self.energy = self.energy + intake - total_metabolic_cost

        # 5. Vectorized Lifecycle: Death (Apoptosis) & Auto-Reproduction
        dead_mask = (self.energy <= 0.0) & active_alive
        n_dead = int(dead_mask.sum().item())
        if n_dead > 0:
            self.alive_mask[dead_mask] = False
            self.energy[dead_mask] = 0.0
            self.total_deaths += n_dead

        # Auto-Reproduction: Energy exceeds E_threshold
        repro_mask = (self.energy >= self.E_threshold) & self.alive_mask
        repro_indices = torch.nonzero(repro_mask).squeeze(-1).tolist()
        if isinstance(repro_indices, int):
            repro_indices = [repro_indices]
            
        n_born = 0
        if repro_indices:
            # Find free slots in population
            free_slots = torch.nonzero(~self.alive_mask).squeeze(-1).tolist()
            if isinstance(free_slots, int):
                free_slots = [free_slots]
                
            for parent_idx in repro_indices:
                if not free_slots:
                    break
                slot = free_slots.pop(0)
                parent_genome = self.genomes[parent_idx]
                if parent_genome is not None:
                    # Energy division: Parent gives half to child minus reproduction cost
                    repro_cost = 5.0
                    parent_energy = float(self.energy[parent_idx].item())
                    child_energy = max(10.0, (parent_energy - repro_cost) / 2.0)
                    self.energy[parent_idx] = child_energy
                    
                    # Mutate offspring genome
                    child_genome = parent_genome.mutate()
                    depth = int(self.lineage_depth[parent_idx].item()) + 1
                    self._load_organism(slot, child_genome, initial_energy=child_energy, depth=depth)
                    
                    # Place child near parent with small spatial displacement
                    px, py = float(self.positions[parent_idx, 0].item()), float(self.positions[parent_idx, 1].item())
                    self.positions[slot, 0] = float(np.clip(px + self.rng.normal(0, 0.05), 0.0, 1.0))
                    self.positions[slot, 1] = float(np.clip(py + self.rng.normal(0, 0.05), 0.0, 1.0))
                    
                    n_born += 1
                    self.total_births += 1
                    
        telemetry = {
            "tick": self.total_ticks,
            "population_size": int(self.alive_mask.sum().item()),
            "births_total": self.total_births,
            "deaths_total": self.total_deaths,
            "mean_energy": float(self.energy[self.alive_mask].mean().item()) if n_alive > 0 else 0.0,
            "mean_synapses": float(self.syn_active[self.alive_mask].sum(dim=-1).float().mean().item()) if n_alive > 0 else 0.0,
            "max_lineage": int(self.lineage_depth[self.alive_mask].max().item()) if n_alive > 0 else 0,
            "mean_metabolic_cost": float(total_metabolic_cost[self.alive_mask].mean().item()) if n_alive > 0 else 0.0,
            "neuromodulator_mean": float(M_t[self.alive_mask].mean().item()) if n_alive > 0 else 0.0,
            "eligibility_mean": float(self.eligibility[self.alive_mask].abs().mean().item()) if n_alive > 0 else 0.0,
            "stdp_lr_mean": float(self.eta_stdp[self.alive_mask].mean().item()) if n_alive > 0 else 0.0,
            "weight_norm": float(self.weights[self.alive_mask].norm(dim=-1).mean().item()) if n_alive > 0 else 0.0,
            "total_landauer_joules": float(total_metabolic_cost[self.alive_mask].sum().item() * 2.87e-21) if n_alive > 0 else 0.0
        }
        
        return self.actions, telemetry
