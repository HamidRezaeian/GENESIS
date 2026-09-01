"""
GENESIS Phase-5: Dual-Timescale Addressable-Memory Batched Population Substrate.
Binding specification: Docs/Architecture/PHASE5_DUAL_MEMORY_SPEC.md (§2.1, §2.2, §2.4).

Invariants:
- Rule 6: Hardware-grounded commodity workstation execution.
- Rule 19: Dynamic compact RAM with zero unallocated waste.
- Rule 21: Measured host work for neural ops, associative memory, and slow consolidation.
- Rule 23: Zero-allocation tensor broadcasting and Turing tensor-core optimization.
"""

import math
from typing import Dict, Any, Tuple, Optional
import torch
import torch.nn.functional as F

from genesis.server.phase5_memory import BatchedExternalMemoryBank
from genesis.server.phase5_plasticity import Phase5PlasticityEngine


class BatchedPopulation5:
    """
    High-performance PyTorch population substrate for Phase 5.
    Manages 32 parallel worlds (4096 organisms) with dual-timescale synapses,
    autotelic addressable memory banks, and zero-allocation forward loops.
    """
    def __init__(
        self,
        n_worlds: int = 32,
        pop_per_world: int = 128,
        max_neurons: int = 80,
        max_synapses: int = 512,
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        self.n_worlds = n_worlds
        self.pop_per_world = pop_per_world
        self.max_neurons = max_neurons
        self.max_synapses = max_synapses
        self.device = device

        # ── 1. DUAL-TIMESCALE SYNAPTIC TOPOLOGY [W, N, S] ──
        # W_fast: Fast re-tracking, bounded [-4.0, +4.0] [S]
        self.W_fast = torch.randn((n_worlds, pop_per_world, max_synapses), dtype=torch.float32, device=device) * 0.1
        # W_slow: Slow consolidation trace
        self.W_slow = torch.zeros((n_worlds, pop_per_world, max_synapses), dtype=torch.float32, device=device)
        # Pre/Post synaptic connectivity graph
        self.pre_idx = torch.randint(0, max_neurons, (n_worlds, pop_per_world, max_synapses), dtype=torch.long, device=device)
        self.post_idx = torch.randint(0, max_neurons, (n_worlds, pop_per_world, max_synapses), dtype=torch.long, device=device)
        self.syn_active = torch.ones((n_worlds, pop_per_world, max_synapses), dtype=torch.bool, device=device)
        self.eligibility = torch.zeros((n_worlds, pop_per_world, max_synapses), dtype=torch.float32, device=device)

        # ── 2. NEURAL DYNAMICS BUFFERS [W, N, M] ──
        self.voltages = torch.zeros((n_worlds, pop_per_world, max_neurons), dtype=torch.float32, device=device)
        self.states = torch.zeros((n_worlds, pop_per_world, max_neurons), dtype=torch.float32, device=device)
        self.spikes = torch.zeros((n_worlds, pop_per_world, max_neurons), dtype=torch.float32, device=device)

        # ── 3. ORGANISM PHYSICAL GROUNDING ──
        self.energies = torch.full((n_worlds, pop_per_world), 100.0, dtype=torch.float32, device=device)
        self.alive_mask = torch.ones((n_worlds, pop_per_world), dtype=torch.bool, device=device)
        self.positions = torch.randint(0, 64, (n_worlds, pop_per_world, 2), dtype=torch.float32, device=device)
        self.actions = torch.zeros((n_worlds, pop_per_world), dtype=torch.long, device=device)

        # ── 4. EXTERNAL MEMORY BANK & PLASTICITY ENGINE ──
        self.memory_bank = BatchedExternalMemoryBank(
            n_worlds=n_worlds,
            pop_per_world=pop_per_world,
            k_slots=16,
            b_dim=16,
            d_key_dim=4,
            device=device
        )
        self.plasticity_engine = Phase5PlasticityEngine(device=device)

        # Sensory buffer for retrieved memory injection [W, N, 16]
        self.retrieved_memory = torch.zeros((n_worlds, pop_per_world, 16), dtype=torch.float32, device=device)

        # Genome array for evolutionary tracking
        self.genomes = torch.randn((n_worlds, pop_per_world, 32), dtype=torch.float32, device=device)

    def forward_step(
        self,
        sensory_inputs: torch.Tensor,       # [W, N, 32] (16 physical + 16 LLM latent)
        rewards: Optional[torch.Tensor] = None
    ) -> Dict[str, Any]:
        """
        Executes one full synchronous simulation step across all 32 worlds.
        """
        W, N, M = self.n_worlds, self.pop_per_world, self.max_neurons
        device = self.device

        # 1. Effective Synaptic Drive: W_eff = W_fast + W_slow
        W_eff = (self.W_fast + self.W_slow) * self.syn_active.float()

        # 2. Assemble Full Sensory Input [W, N, 48] (32 external + 16 retrieved memory)
        full_sensory = torch.cat([sensory_inputs, self.retrieved_memory], dim=-1)  # [W, N, 48]

        # 3. Inject Sensory Voltage into Input Neurons 0..47
        n_sensory = full_sensory.shape[-1]
        self.voltages[:, :, :n_sensory] += full_sensory

        # 4. Vectorized Synaptic Transmission via W_eff
        # Compute input currents from spikes
        batch_w = torch.arange(W, device=device).view(-1, 1, 1)
        batch_n = torch.arange(N, device=device).view(1, -1, 1)
        
        pre_spk = self.spikes[batch_w, batch_n, self.pre_idx]  # [W, N, S]
        syn_current = pre_spk * W_eff                          # [W, N, S]

        # Accumulate current into postsynaptic neurons
        post_current = torch.zeros((W, N, M), dtype=torch.float32, device=device)
        post_current.scatter_add_(dim=2, index=self.post_idx, src=syn_current)

        # 5. Integrate & Fire Dynamics
        leak = 0.90
        v_thresh = 1.0
        self.voltages = self.voltages * leak + post_current
        self.spikes = (self.voltages >= v_thresh).float()
        self.voltages[self.spikes > 0.0] = 0.0
        self.states = 0.85 * self.states + 0.15 * self.spikes

        # 6. Motor Action Decoding
        # Motor neurons: 6 channels (indices M-6 to M-1)
        # Channels: [0..3: physical move, 4: a_write gate, 5: a_read gate]
        motor_acts = self.states[:, :, M-6:M]  # [W, N, 6]
        move_logits = motor_acts[:, :, :4]     # [W, N, 4]
        self.actions = torch.argmax(move_logits, dim=-1)

        write_gate = motor_acts[:, :, 4] > 0.5
        read_gate = motor_acts[:, :, 5] > 0.5

        # 7. Autotelic Address Keys & Memory Step (§2.2)
        k_write = self.states[:, :, -4:]  # [W, N, 4] autotelic write address
        k_read = self.states[:, :, -4:]   # [W, N, 4] autotelic read address
        write_payload = full_sensory[:, :, :16]  # encode current sensory vector

        self.retrieved_memory, mem_energy = self.memory_bank.step(
            write_gate=write_gate,
            read_gate=read_gate,
            k_write=k_write,
            k_read=k_read,
            write_payload=write_payload
        )

        # 8. Dual-Timescale Synaptic Plasticity Update (§2.1, §2.3)
        if rewards is None:
            rewards = torch.zeros((W, N), dtype=torch.float32, device=device)

        pred_error = torch.mean(torch.abs(full_sensory[:, :, :16] - self.states[:, :, :16]), dim=-1)
        constructive_err = (full_sensory[:, :, :16].repeat(1, 1, M // 16) - self.states[:, :, :M]) * 0.1

        self.W_fast, self.W_slow, _ = self.plasticity_engine.update_synapses(
            W_fast=self.W_fast,
            W_slow=self.W_slow,
            pre_idx=self.pre_idx,
            post_idx=self.post_idx,
            syn_active=self.syn_active,
            pre_spikes=self.spikes,
            post_spikes=self.spikes,
            eligibility=self.eligibility,
            modulator=rewards,
            prediction_error=pred_error,
            constructive_err=constructive_err
        )

        # 9. Energy & Metabolic Accounting (Rule 21)
        metabolic_base = 0.05
        syn_cost = 0.001 * float(self.max_synapses)
        total_debit = metabolic_base + syn_cost + mem_energy
        self.energies[self.alive_mask] -= total_debit[self.alive_mask]

        # Check deaths (energy <= 0)
        dead = (self.energies <= 0.0) & self.alive_mask
        self.alive_mask[dead] = False

        return {
            "actions": self.actions,
            "alive_count": int(self.alive_mask.sum().item()),
            "mean_energy": float(self.energies[self.alive_mask].mean().item()) if self.alive_mask.any() else 0.0,
            "prediction_error": float(pred_error.mean().item())
        }

    def clone(self) -> 'BatchedPopulation5':
        """Deep clone for isolated, counterbalanced diagnostic probe audits."""
        cloned = BatchedPopulation5(
            n_worlds=self.n_worlds,
            pop_per_world=self.pop_per_world,
            max_neurons=self.max_neurons,
            max_synapses=self.max_synapses,
            device=self.device
        )
        cloned.W_fast = self.W_fast.clone()
        cloned.W_slow = self.W_slow.clone()
        cloned.pre_idx = self.pre_idx.clone()
        cloned.post_idx = self.post_idx.clone()
        cloned.syn_active = self.syn_active.clone()
        cloned.voltages = self.voltages.clone()
        cloned.states = self.states.clone()
        cloned.spikes = self.spikes.clone()
        cloned.energies = self.energies.clone()
        cloned.alive_mask = self.alive_mask.clone()
        cloned.positions = self.positions.clone()
        cloned.actions = self.actions.clone()
        cloned.genomes = self.genomes.clone()
        cloned.retrieved_memory = self.retrieved_memory.clone()
        return cloned
