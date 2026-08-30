import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import torch
from genesis.server.phase_e_substrate import BatchedPopulation
from genesis.server.phase_e_ecology import EcologyField
from genesis.server.phase_e_plus import PhaseEPlusInternetSensing

device = "cuda" if torch.cuda.is_available() else "cpu"
pop = BatchedPopulation(n_worlds=32, pop_per_world=128, device=device)
eco = EcologyField(n_worlds=32, grid_size=32, device=device)
sensing = PhaseEPlusInternetSensing(population=pop, ecology=eco, device=device)

# Warmup
for t in range(50):
    sensing.step_tick(t)

torch.cuda.synchronize()

n_iters = 500
t_eco = 0.0
t_llm = 0.0
t_pop = 0.0

start_total = time.perf_counter()
for t in range(n_iters):
    # 1. Eco
    t0 = time.perf_counter()
    spatial_sensory, harvested = eco.process_interactions(
        pop.positions, pop.orientations, pop.actions, pop.alive_mask, pop.energy, pop.dev
    )
    torch.cuda.synchronize()
    t1 = time.perf_counter()
    t_eco += (t1 - t0)
    
    # 2. LLM check
    t0 = time.perf_counter()
    if sensing.llm_available and (t % sensing.update_interval == 0):
        emit_mask = (pop.actions == 4) & pop.alive_mask & (pop.energy >= 25.0)
        if torch.any(emit_mask):
            selected_mask = sensing.stochastic_gate.select_queries(pop.energy, emit_mask)
            n_selected = int(selected_mask.sum().item())
            if n_selected > 0:
                query_symbols = pop.states[:, :, -4:][selected_mask]
                query_hidden = sensing.llm_interface.query_llm(query_symbols, t)
                sensing._hidden_state.zero_()
                sensing._hidden_state[selected_mask] = query_hidden
                new_combined = sensing.sensory_projection(sensing._hidden_state, spatial_sensory)
                sensing.temporal_cache.update_cache(new_combined, t)
    combined_sensory = sensing.temporal_cache.get_sensory(t)
    torch.cuda.synchronize()
    t1 = time.perf_counter()
    t_llm += (t1 - t0)
    
    # 3. Population tick
    t0 = time.perf_counter()
    actions, telem = pop.step_tick(combined_sensory, harvested)
    torch.cuda.synchronize()
    t1 = time.perf_counter()
    t_pop += (t1 - t0)

torch.cuda.synchronize()
total_time = time.perf_counter() - start_total

print(f"Total time for {n_iters} ticks: {total_time:.3f}s ({n_iters/total_time:.1f} TPS)")
print(f"Ecology & Grid Time : {t_eco:.3f}s ({(t_eco/total_time)*100:.1f}%)")
print(f"LLM Sensing Time    : {t_llm:.3f}s ({(t_llm/total_time)*100:.1f}%)")
print(f"Population STDP Time: {t_pop:.3f}s ({(t_pop/total_time)*100:.1f}%)")
