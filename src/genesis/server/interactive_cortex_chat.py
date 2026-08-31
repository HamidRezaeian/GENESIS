import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator

import torch
import torch.nn as nn
from aiohttp import web

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from genesis.server.phase_e_substrate import BatchedPopulation
from genesis.server.phase_e_plus import (
    SymbolToQueryProjection,
    HiddenToSensoryProjection,
    LLMSensoryInterface
)


class CortexBrain5MLoader:
    """
    Loads the evolved 5M master brain (`canonical_brain_5M.npz` or fallback)
    into a frozen artifact clone for deterministic, low-latency reasoning.
    Rule 23 & 24 compliant: Read-only, plasticity frozen (eta_stdp = 0).
    """
    def __init__(
        self,
        brain_path: str = "Brain/canonical_brain_5M.npz",
        device: str = "cuda",
        pop_size: int = 64
    ):
        self.dev = torch.device(device if torch.cuda.is_available() else "cpu")
        self.pop_size = pop_size
        self.brain_path = REPO_ROOT / brain_path
        if not self.brain_path.exists():
            self.brain_path = REPO_ROOT / "Brain" / "canonical_brain.npz"
            
        self.pop = BatchedPopulation(
            n_worlds=1,
            pop_per_world=pop_size,
            device=device
        )
        self._load_and_freeze()

    def _load_and_freeze(self):
        """Loads canonical weights and zeroes eta_stdp for deterministic inference."""
        if self.brain_path.exists():
            import numpy as np
            data = np.load(str(self.brain_path))
            if "weights" in data:
                weights = torch.tensor(data["weights"], dtype=self.pop.dtype, device=self.dev)
                self.pop.weights[0].copy_(weights[:self.pop_size])
            if "eta_stdp" in data:
                eta = torch.tensor(data["eta_stdp"], dtype=self.pop.dtype, device=self.dev)
                self.pop.eta_stdp[0].copy_(eta[:self.pop_size])
        # Freeze plasticity for interactive deployment (Rule 23)
        self.pop.eta_stdp.zero_()


class PromptToVoltageInjector:
    """
    Transforms user text into sensory voltage stimuli using Qwen token embeddings
    and HiddenToSensoryProjection.
    """
    def __init__(self, llm_interface: LLMSensoryInterface, pop: BatchedPopulation):
        self.llm_if = llm_interface
        self.pop = pop
        self.dev = llm_interface.dev
        self.hidden_to_sensory = HiddenToSensoryProjection(
            d_model=llm_interface.d_model,
            n_sensory=pop.input_neurons,
            device=str(self.dev)
        )

    @torch.no_grad()
    def text_to_sensory(self, text: str) -> torch.Tensor:
        """Converts user text into [1, K, 20] sensory voltage injection."""
        inputs = self.llm_if.tokenizer(text, return_tensors="pt").to(self.dev)
        with torch.no_grad():
            token_embeds = self.llm_if.llm.get_input_embeddings()(inputs.input_ids) # [1, Seq, d_model]
            mean_hidden = token_embeds.mean(dim=1, keepdim=True).to(torch.float16) # [1, 1, d_model]
            
            # Broadcast to [1, K, d_model]
            hidden_expanded = mean_hidden.expand(1, self.pop.N, -1)
            base_sensory = torch.zeros(1, self.pop.N, self.pop.input_neurons, dtype=self.pop.dtype, device=self.dev)
            
            sensory_batch = self.hidden_to_sensory(hidden_expanded, base_sensory)
            return sensory_batch


class CorticalReasoningLoop:
    """
    Executes H reasoning ticks over the cortical SNN with persistent states.
    Armed with a Rule 24 halt switch.
    """
    def __init__(self, pop: BatchedPopulation, h_ticks: int = 10):
        self.pop = pop
        self.h_ticks = h_ticks
        self.dev = pop.dev
        self.dummy_harvest = torch.zeros(1, pop.N, dtype=torch.float32, device=self.dev)
        self.halt_event = asyncio.Event()

    @torch.no_grad()
    def reason(self, sensory: torch.Tensor) -> Dict[str, Any]:
        """Runs H ticks of step_tick, collecting states and symbol trajectory."""
        emit_history = []
        state_history = []
        
        for tick in range(self.h_ticks):
            if self.halt_event.is_set():
                break
            actions, _ = self.pop.step_tick(sensory, self.dummy_harvest)
            emit_active = (actions[0] == 4).float()
            symbols = torch.tanh(self.pop.states[0, :, -4:].clone()) # [K, 4]
            
            emit_history.append(emit_active)
            state_history.append(symbols)
            
        mean_symbols = torch.stack(state_history).mean(dim=0) # [K, 4]
        return {
            "mean_symbols": mean_symbols,
            "final_states": self.pop.states[0].clone(),
            "emit_activity": torch.stack(emit_history).mean().item()
        }


class SoftPrefixConditioner:
    """
    Converts cortical symbol trajectory into soft prefix token embeddings
    for conditioning Qwen's autoregressive response.
    """
    def __init__(self, llm_interface: LLMSensoryInterface):
        self.llm_if = llm_interface
        self.dev = llm_interface.dev

    @torch.no_grad()
    def generate_conditioned_response(
        self,
        user_text: str,
        cortical_symbols: torch.Tensor,
        max_new_tokens: int = 64
    ) -> str:
        """Condition Qwen generate() on soft prefix embeddings from cortical brain."""
        inputs = self.llm_if.tokenizer(user_text, return_tensors="pt").to(self.dev)
        user_embeds = self.llm_if.llm.get_input_embeddings()(inputs.input_ids).to(torch.float16) # [1, Seq, d_model]
        
        # Project pooled cortical symbols [1, 4] -> [1, 1, d_model]
        pooled_symbols = cortical_symbols.mean(dim=0, keepdim=True).to(torch.float16) # [1, 4]
        prefix_embed = self.llm_if.projection(pooled_symbols).unsqueeze(0).to(torch.float16) # [1, 1, d_model]
        
        # Concatenate prefix + user embeddings: [1, 1 + Seq, d_model]
        combined_embeds = torch.cat([prefix_embed, user_embeds], dim=1)
        
        output_ids = self.llm_if.llm.generate(
            inputs_embeds=combined_embeds,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            top_p=0.9,
            temperature=0.7,
            pad_token_id=self.llm_if.tokenizer.eos_token_id
        )
        response_text = self.llm_if.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return response_text


class InteractiveCortexChat:
    """
    Complete production interactive chat service for GENESIS Post-5M Master Brain.
    """
    def __init__(self, device: str = "cuda"):
        self.loader = CortexBrain5MLoader(device=device)
        self.llm_if = LLMSensoryInterface(device=device)
        self.injector = PromptToVoltageInjector(self.llm_if, self.loader.pop)
        self.loop = CorticalReasoningLoop(self.loader.pop)
        self.conditioner = SoftPrefixConditioner(self.llm_if)

    async def handle_prompt(self, prompt: str) -> Dict[str, Any]:
        """Full end-to-end interactive reasoning turn."""
        t0 = time.perf_counter()
        
        # 1. Map user text -> Sensory Voltage
        sensory = self.injector.text_to_sensory(prompt)
        
        # 2. Cortical Reasoning over H ticks
        reasoning_res = self.loop.reason(sensory)
        
        # 3. Generate conditioned LLM response
        response = self.conditioner.generate_conditioned_response(
            user_text=prompt,
            cortical_symbols=reasoning_res["mean_symbols"]
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        
        return {
            "response": response,
            "latency_ms": latency_ms,
            "cortical_emit_rate": reasoning_res["emit_activity"],
            "claim_boundary": "CERTIFIED_LEVEL_1_ARTIFACT_ANALYSIS_FRAME"
        }
