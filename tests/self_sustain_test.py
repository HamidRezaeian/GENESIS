"""
Self-sustainability experiment — Result.md Exp 4 follow-up / Roadmap P2.

CENTRAL QUESTION
----------------
Does a population survive on renewable FOOD INCOME, or does it merely coast on the
`initial_energy` seed buffer and get resurrected by the Ark on a timer (the Exp 4
pathology: clockwork total extinction every ~8,640 ticks, zero ascension)?

DIAGNOSTIC
----------
Sweep the seed buffer (`initial_energy`) and food rate with the Ark DISABLED, so
extinction is TERMINAL and we can measure how long a cohort survives on its own.

  - If survival time scales with the seed buffer  -> the cohort is COASTING on the
    buffer, not self-sustaining. Halving the buffer should roughly halve survival.
  - If, at a SMALL buffer, the population survives to the horizon and mean energy
    levels off at a positive value -> it is living on food income (the goal). Survival
    becomes buffer-INDEPENDENT.

An Ark-ON control at the default buffer is included to show the resurrection loop for
comparison.

No hot-path (njit) changes: every signal comes from population + mean-energy trajectories
already exposed as `genesis_lab` module globals. `genesis_lab` is reloaded between configs
for a pristine universe (fresh global arrays, empty Ark/fossil pool).

USAGE
-----
    python tests/self_sustain_test.py                 # default sweep
    python tests/self_sustain_test.py 4000            # horizon = 4000 world-ticks
"""
import sys, os, time, random, importlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import numpy as np
import genesis_lab as gl

GLOBAL_CYCLE_POOL = 3000


def _world_tick(steps):
    """Call the njit world update with the exact argument list sim_loop/smoke_test use."""
    return gl.world_tick_numba(
        gl.g_ram, gl.g_org_grid, gl.g_positions, gl.g_alive, gl.g_energy, gl.g_age,
        gl.g_global_v, gl.g_global_ref, gl.g_global_t_last, gl.g_global_thresh, gl.g_global_tau, gl.g_global_rec_id,
        gl.g_global_conn_src, gl.g_global_conn_dst, gl.g_global_conn_weight,
        gl.g_neuron_map, gl.g_synapse_map, gl.g_genome_map,
        gl.g_org_n_ptr, gl.g_org_n_count, gl.g_org_s_ptr, gl.g_org_s_count,
        gl.g_global_genome, gl.g_org_g_ptr, gl.g_org_g_count,
        gl.o_rec_a_plus, gl.o_rec_a_minus, gl.o_rec_tau_p, gl.o_rec_tau_m,
        gl.o_rec_v_rest, gl.o_rec_v_reset, gl.o_rec_tau_def, gl.o_rec_spk_max,
        gl.g_viscosity, gl.global_time, gl.g_org_lif_steps,  # per-org architecture-derived steps
        gl.g_b_pos, gl.g_b_parent, gl.g_b_g_start, gl.g_b_g_count, gl.g_b_genomes, gl.g_b_energy,
        gl.g_oracle_val, gl.g_oracle_target, gl.voice_buf, gl.vocal_cords, gl.g_read_log,
    )


def _process_births(n_births):
    """Mirror sim_loop's birth handling exactly."""
    for i in range(n_births):
        child_dna = gl.mutate_dna(gl.g_b_genomes[i, :gl.g_b_g_count[i]])
        slot = -1
        for j in range(gl.MAX_ORGANISMS):
            if not gl.g_alive[j]:
                slot = j
                break
        if slot == -1:
            continue
        child_pos = gl.g_b_pos[i]
        offset = 1
        while gl.g_org_grid[child_pos] != -1 and offset < 100:
            child_pos = (gl.g_b_pos[i] + offset) % gl.RAM_SIZE
            offset += 1
        gl.spawn_organism(slot, child_pos, child_dna, initial_energy=gl.g_b_energy[i])


def run_config(initial_energy, food_rate, ark_enabled, n_ticks, rng_seed=1234):
    """Run one configuration on a pristine universe; return a metrics dict."""
    importlib.reload(gl)              # fresh global arrays, empty Ark/fossil pool
    random.seed(rng_seed)
    np.random.seed(rng_seed)

    gl.seed_universe(300, initial_energy=initial_energy)

    energy_trace, pop_trace = [], []
    first_extinct_tick = None
    ark_reseeds = 0

    for t in range(n_ticks):
        alive = int(np.sum(gl.g_alive))
        if alive == 0:
            if first_extinct_tick is None:
                first_extinct_tick = t
            if ark_enabled:
                ark_reseeds += 1
                gl.seed_universe(300, use_ark=True, initial_energy=initial_energy)
                continue
            break                     # Ark OFF: extinction is terminal

        # Food respawn (pristine-memory 0x55), identical to sim_loop / smoke_test.
        whole = int(food_rate)
        for _ in range(whole):
            idx = random.randint(0, gl.RAM_SIZE - 1)
            if gl.g_ram[idx] == 0x00:
                gl.g_ram[idx] = 0x55
        if random.random() < (food_rate - whole):
            idx = random.randint(0, gl.RAM_SIZE - 1)
            if gl.g_ram[idx] == 0x00:
                gl.g_ram[idx] = 0x55

        steps = max(1, int(GLOBAL_CYCLE_POOL / max(1, alive)))
        _, n_births = _world_tick(steps)
        _process_births(n_births)
        gl.global_time += steps

        energies = gl.g_energy[gl.g_alive]
        energy_trace.append(float(np.mean(energies)) if len(energies) else 0.0)
        pop_trace.append(int(np.sum(gl.g_alive)))

    def e_at(frac):
        if not energy_trace:
            return 0.0
        return energy_trace[min(len(energy_trace) - 1, int(frac * len(energy_trace)))]

    tail = pop_trace[len(pop_trace) // 2:] if len(pop_trace) > 2 else pop_trace
    # "Sustained" = survived the horizon with the Ark OFF AND mean energy stopped falling
    # (late energy within 85% of mid-run energy) — i.e. a positive equilibrium, not burndown.
    late_ok = (len(energy_trace) > 4 and energy_trace[-1] > 0.0
               and energy_trace[-1] >= 0.85 * max(1.0, energy_trace[len(energy_trace) // 2]))
    sustained = late_ok and not (first_extinct_tick is not None and not ark_enabled)
    return {
        "initial_energy": initial_energy,
        "food_rate": food_rate,
        "ark": ark_enabled,
        "survived_ticks": (first_extinct_tick if (first_extinct_tick is not None and not ark_enabled) else n_ticks),
        "went_extinct": (first_extinct_tick is not None and not ark_enabled),
        "ark_reseeds": ark_reseeds,
        "e_early": e_at(0.10),
        "e_mid": e_at(0.50),
        "e_late": e_at(0.90),
        "peak_pop": max(pop_trace) if pop_trace else 0,
        "final_pop": int(np.sum(gl.g_alive)),
        "min_pop_tail": min(tail) if tail else 0,
        "sustained": sustained,
    }


def main():
    n_ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 600

    print(f"\n=== SELF-SUSTAINABILITY / ECONOMY SWEEP (horizon = {n_ticks} world-ticks) ===")
    hdr = (f"{'grp':>9} {'ark':>4} {'init_E':>8} {'food':>7} {'survived':>8} {'extinct':>7} "
           f"{'e_early':>8} {'e_mid':>8} {'e_late':>8} {'peak':>5} {'min_tail':>8} {'SUSTAIN':>7}")

    def show(grp, tag, r):
        print(f"{grp:>9} {tag:>4} {r['initial_energy']:>8.0f} {r['food_rate']:>7.1f} "
              f"{r['survived_ticks']:>8} {str(r['went_extinct']):>7} "
              f"{r['e_early']:>8.0f} {r['e_mid']:>8.0f} {r['e_late']:>8.0f} "
              f"{r['peak_pop']:>5} {r['min_pop_tail']:>8} {str(r['sustained']):>7}")

    print(hdr)
    # Control: the Ark resurrection loop at the default economy.
    show("ark-ctrl", "ON", run_config(250000.0, 0.1, ark_enabled=True, n_ticks=n_ticks))

    # (A) Buffer sweep, Ark OFF, default food — does survival track the buffer? (coasting test)
    for buf in (250000.0, 50000.0, 10000.0):
        show("buffer", "OFF", run_config(buf, 0.1, ark_enabled=False, n_ticks=n_ticks))

    # (B) Food-supply sweep, Ark OFF, SMALL buffer (10k dies ~31 ticks on its own): can far more
    #     food close the food->energy loop and flatten energy above zero? Pure-Python seeding,
    #     no engine edits — the cheapest decisive test of "supply vs behaviour".
    for fr in (1.0, 100.0, 1000.0, 5000.0):  # 5000/tick saturates the 65536-byte substrate in ~13 ticks
        show("food", "OFF", run_config(10000.0, fr, ark_enabled=False, n_ticks=n_ticks))

    print("\nREAD IT:")
    print("  (A) buffer rows: 'survived' tracks init_E  -> COASTING on the battery, not eating.")
    print("  (B) food rows: if raising food flips SUSTAIN True (survives horizon, e_late ~ e_mid,")
    print("      min_tail > 0) -> the food->energy loop CAN close; supply was the binding lever.")
    print("      If even food=400 stays extinct -> they are not effectively EATING (a behaviour/")
    print("      motor-evolution problem), which is deeper than supply.")


if __name__ == "__main__":
    main()
