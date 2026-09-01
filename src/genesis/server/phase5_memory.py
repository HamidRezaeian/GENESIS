"""
GENESIS Phase-5: External Gated Addressable Memory Substrate.
Binding specification: Docs/Architecture/PHASE5_DUAL_MEMORY_SPEC.md (§2.2).

Invariants:
- Rule 9: Autotelic self-generated address keys (states[:, -4:]), never author-supplied.
- Rule 17: Scale-free cosine similarity, mathematical invariant T_ret = 1/sqrt(d).
- Rule 19: Dynamic compact RAM with zero unallocated waste and audited slot eviction.
- Rule 21: Measured Landauer associative FLOPs and storage traffic energy accounting.
"""

import math
from typing import Dict, Any, Tuple, Optional
import torch
import torch.nn.functional as F


class BatchedExternalMemoryBank:
    """
    Batched external associative memory bank for all organisms across all worlds.
    Topology: [W, N, K, b] where W=worlds, N=organisms, K=slots, b=slot_dim.
    Key topology: [W, N, K, d] where d=key_dim (4-channel autotelic motor symbol).
    """
    def __init__(
        self,
        n_worlds: int = 32,
        pop_per_world: int = 128,
        k_slots: int = 16,
        b_dim: int = 16,
        d_key_dim: int = 4,
        e_flop: float = 1e-4,
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        self.n_worlds = n_worlds
        self.pop_per_world = pop_per_world
        self.k_slots = k_slots
        self.b_dim = b_dim
        self.d_key_dim = d_key_dim
        self.e_flop = e_flop
        self.device = device

        # Mathematical Invariant [M]: T_ret = 1 / sqrt(d)
        self.t_ret = 1.0 / math.sqrt(float(d_key_dim))

        # Memory slot bank [W, N, K, b]
        self.mem = torch.zeros((n_worlds, pop_per_world, k_slots, b_dim), dtype=torch.float32, device=device)
        # Content key bank [W, N, K, d]
        self.keys = torch.zeros((n_worlds, pop_per_world, k_slots, d_key_dim), dtype=torch.float32, device=device)
        # Occupancy mask [W, N, K]
        self.valid = torch.zeros((n_worlds, pop_per_world, k_slots), dtype=torch.bool, device=device)
        # Telemetry & compaction accounting
        self.retrieval_counts = torch.zeros((n_worlds, pop_per_world, k_slots), dtype=torch.int32, device=device)
        self.total_writes = 0
        self.total_reads = 0
        self.cumulative_flop_energy = 0.0

    def step(
        self,
        write_gate: torch.Tensor,      # [W, N] boolean / binary motor spike a_write
        read_gate: torch.Tensor,       # [W, N] boolean / binary motor spike a_read
        k_write: torch.Tensor,         # [W, N, d] autotelic key vector
        k_read: torch.Tensor,          # [W, N, d] autotelic retrieval key
        write_payload: torch.Tensor    # [W, N, b] state vector to encode
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Executes associative write and read operations across all organisms.
        Returns:
            retrieved_out: [W, N, b] retrieved memory content (zeroed if not read).
            energy_cost: [W, N] host energy debited for associative operations.
        """
        W, N, K, b = self.mem.shape
        d = self.d_key_dim
        energy_cost = torch.zeros((W, N), dtype=torch.float32, device=self.device)
        retrieved_out = torch.zeros((W, N, b), dtype=torch.float32, device=self.device)

        # Normalize keys for scale-free cosine similarity
        norm_keys = F.normalize(self.keys, p=2, dim=-1, eps=1e-8)  # [W, N, K, d]

        # ── 1. ASSOCIATIVE WRITE OPERATION ──
        # Write condition: write_gate is active
        w_active = write_gate.bool()
        if w_active.any():
            norm_kw = F.normalize(k_write, p=2, dim=-1, eps=1e-8)  # [W, N, d]
            sim_w = torch.einsum('wnkd,wnd->wnk', norm_keys, norm_kw)  # [W, N, K]

            # Slot allocation score: empty slots prioritized (valid==0), then closest key match
            slot_score = (~self.valid).float() * 2.0 + sim_w
            j_star = torch.argmax(slot_score, dim=-1)  # [W, N] target slot

            # Gather indices for vectorized write
            batch_w = torch.arange(W, device=self.device).view(W, 1).expand(W, N)[w_active]
            batch_n = torch.arange(N, device=self.device).view(1, N).expand(W, N)[w_active]
            target_j = j_star[w_active]

            self.mem[batch_w, batch_n, target_j] = write_payload[w_active]
            self.keys[batch_w, batch_n, target_j] = k_write[w_active]
            self.valid[batch_w, batch_n, target_j] = True

            # Energy billing (Rule 21): b * K FLOPs associative search + b bits traffic
            write_flops = float(b * K + b)
            energy_cost[w_active] += write_flops * self.e_flop
            self.total_writes += int(w_active.sum().item())

        # ── 2. ASSOCIATIVE READ OPERATION ──
        # Read condition: read_gate is active
        r_active = read_gate.bool()
        if r_active.any():
            norm_kr = F.normalize(k_read, p=2, dim=-1, eps=1e-8)  # [W, N, d]
            sim_r = torch.einsum('wnkd,wnd->wnk', norm_keys, norm_kr)  # [W, N, K]

            # Mask out invalid (empty) slots with large negative value
            sim_r_masked = sim_r.clone()
            sim_r_masked[~self.valid] = -1e9

            # Softmax retrieval distribution with invariant T_ret = 1/sqrt(d)
            alpha = F.softmax(sim_r_masked / self.t_ret, dim=-1)  # [W, N, K]

            # Retrieve content: sum_j alpha_j * mem[j]
            retrieved = torch.einsum('wnk,wnkb->wnb', alpha, self.mem)  # [W, N, b]
            retrieved_out[r_active] = retrieved[r_active]

            # Increment retrieval audit counts for active reads
            self.retrieval_counts[r_active] += 1

            # Energy billing (Rule 21): K FLOPs associative lookup
            read_flops = float(K)
            energy_cost[r_active] += read_flops * self.e_flop
            self.total_reads += int(r_active.sum().item())

        self.cumulative_flop_energy += float(energy_cost.sum().item())
        return retrieved_out, energy_cost

    def reset_organism(self, world_idx: int, org_idx: int):
        """Clears memory bank for dead organisms on reseed (Rule 19 Zero-Waste)."""
        self.mem[world_idx, org_idx].zero_()
        self.keys[world_idx, org_idx].zero_()
        self.valid[world_idx, org_idx] = False
        self.retrieval_counts[world_idx, org_idx].zero_()

    def get_telemetry(self) -> Dict[str, Any]:
        """Provides observation-only memory statistics."""
        valid_f = self.valid.float()
        total_slots = self.n_worlds * self.pop_per_world * self.k_slots
        occupied_slots = int(valid_f.sum().item())
        mean_occupancy = float(occupied_slots / max(1, total_slots))

        return {
            "total_slots": total_slots,
            "occupied_slots": occupied_slots,
            "mean_occupancy": mean_occupancy,
            "total_writes": self.total_writes,
            "total_reads": self.total_reads,
            "cumulative_memory_flop_energy": self.cumulative_flop_energy
        }
