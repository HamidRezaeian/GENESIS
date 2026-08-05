"""Option 3 NEUROEVOLUTION — smoke + divergence probe (2026-08-05).

Step-2 verification for the Option-3 implementation (Docs/Architecture/
Option3_Neuroevolution_Design.md):

 (c) GENESIS_NEUROEVOLUTION=1 smoke: a small population runs a short NE session WITHOUT
     crashing, founder decode-equivalence holds (the ancestor projects losslessly onto the
     flat genome), and the generational machinery (tournament/crossover/mutation) produces
     offspring.
 (d) divergence: the SAME probe under GENESIS_NEUROEVOLUTION=0 (identical composed physics
     and identical seed, but a FROZEN static cohort — evolution off) must produce DIFFERENT
     end-state weight/genome hashes than under =1. Run BOTH arms and compare WHASH/GHASH:
        GENESIS_NEUROEVOLUTION=1 python tests/neuroevolution_smoke_probe.py
        GENESIS_NEUROEVOLUTION=0 python tests/neuroevolution_smoke_probe.py

Gates (exit non-zero on failure):
 G1 flag mirror: engine flag reflects the env var; the fingerprint-keyed numba cache dir is
    printed for both arms (cache isolation evidence, complements compile_fingerprint_test).
 G2 (flag 1 only) founder decode-equivalence: ne_encode_genome(ne_project_byte_genome(A))
    expresses the SAME nonzero synapse multiset + hidden-neuron params + receptor-0 bytes
    as the ancestor A itself.
 G3 the short run completes all ticks + evolve steps without an exception, with finite
    fitness and a valid population throughout.
 G4 (flag 1 only) at least one tournament offspring was produced; and under flag 0 the
    g_ne_bytes counter stays exactly 0 (engine hooks dead -> default byte-identical proof).

Physics: the SAME composition as the full run (NOLEARN=1, CAM=0, STRUCTURAL_PLASTICITY=0,
books scroll, 2 MB RAM, MAX_ORGANISMS=512) so the =0/=1 difference is attributable to the
NE management ALONE, not to learning. Manual verification probe — deliberately NOT in the
pytest script suite (same class as remap_sandbox_probe: a kernel-driving experiment gate).
"""
import os
import sys
import json
import random
import hashlib
import numpy as np

PROBE_SEED = int(os.environ.get("PROBE_SEED", "0"))
PROBE_POP = int(os.environ.get("PROBE_POP", "24"))
PROBE_TICKS = int(os.environ.get("PROBE_TICKS", "2000"))
PROBE_REPRO = int(os.environ.get("PROBE_REPRO", "500"))

# ── physics composition (BEFORE genesis_lab import), identical across the 0/1 arms ──
os.environ["GENESIS_RAM_SIZE"] = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"] = "512"
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_LIVE_WEB"] = "0"
os.environ["GENESIS_RESUME"] = "0"
os.environ["GENESIS_AUTO_REPRO"] = "0"
os.environ["GENESIS_REMAP"] = "0"
os.environ["GENESIS_NOLEARN"] = "1"
os.environ["GENESIS_STDP3C"] = "0"
os.environ["GENESIS_STDP3"] = "0"
os.environ["GENESIS_CAM"] = "0"
os.environ["GENESIS_STRUCTURAL_PLASTICITY"] = "0"
os.environ["GENESIS_NE_POP"] = str(PROBE_POP)
os.environ["GENESIS_NE_REPRO_PERIOD"] = str(PROBE_REPRO)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import genesis_lab as gl
import neuromorphic_engine as ne

random.seed(PROBE_SEED)
np.random.seed(PROBE_SEED)
ne.seed_kernel_rng(PROBE_SEED)


def _parse_body(dna, n_c):
    """Pure-python marker walk -> (sorted nonzero synapses, hidden params, receptor params).
    Used to prove founder decode-equivalence (G2)."""
    syn = []
    hid = []
    rec = None
    i = 0
    n = len(dna)
    while i < n - 3:
        m = int(dna[i])
        if m == gl.GENE_MARKER:
            s = int(dna[i + 1]) % n_c
            d = int(dna[i + 2]) % n_c
            w = int(dna[i + 3])
            if d >= gl.N_INPUT and w != 128:   # physically expressed synapses only
                syn.append((s, d, w - 128))
            i += 4
        elif m == gl.NEURON_MARKER and i + 4 < n:
            hid.append((int(dna[i + 3]), int(dna[i + 4])))
            i += 5
        elif m == gl.RECEPTOR_MARKER and i + 9 < n:
            rec = tuple(int(dna[i + k]) for k in range(2, 10))
            i += 10
        elif m in (gl.SENSOR_MARKER, gl.ACTUATOR_MARKER, gl.MEMORY_MARKER, gl.SCRATCH_MARKER) \
                and i + 4 < n:
            i += 5
        else:
            i += 1
    return sorted(syn), hid, rec


def _world_tick(global_time):
    alive_steps = gl.g_org_lif_steps[gl.g_alive]
    dynamic_lif_steps = int(alive_steps.max()) if alive_steps.size else 1
    gl.ne_world_maintenance(global_time, dynamic_lif_steps)
    gl.world_tick_numba(
        gl.g_ram, gl.g_org_grid, gl.g_positions, gl.g_alive, gl.g_energy, gl.g_age,
        gl.g_global_v, gl.g_global_ref, gl.g_global_t_last, gl.g_global_thresh,
        gl.g_global_tau, gl.g_global_rec_id,
        gl.g_global_conn_src, gl.g_global_conn_dst, gl.g_global_conn_weight,
        gl.g_global_conn_elig, gl.g_global_conn_elig_t,
        gl.g_neuron_map, gl.g_synapse_map, gl.g_genome_map,
        gl.g_org_n_ptr, gl.g_org_n_count, gl.g_org_s_ptr, gl.g_org_s_count,
        gl.g_global_genome, gl.g_org_g_ptr, gl.g_org_g_count,
        gl.o_rec_a_plus, gl.o_rec_a_minus, gl.o_rec_tau_p, gl.o_rec_tau_m,
        gl.o_rec_v_rest, gl.o_rec_v_reset, gl.o_rec_tau_def, gl.o_rec_spk_max, gl.o_rec_tau_e,
        gl.g_viscosity, global_time, gl.g_org_lif_steps,
        gl.g_b_pos, gl.g_b_parent, gl.g_b_g_start, gl.g_b_g_count, gl.g_b_genomes, gl.g_b_energy,
        gl.g_oracle_val, gl.g_oracle_target, gl.voice_buf, gl.vocal_cords, gl.vocal_prev,
        gl.action_now, gl.action_prev, gl.g_read_log, gl.g_read_fuel, gl.g_cell_owner,
        gl.g_read_hits, gl.CANVAS_LO, gl.CANVAS_HI, gl.g_org_reward, gl.g_org_elig,
        gl.g_global_sense_type, gl.g_global_sense_meta, gl.g_global_act_drive,
        gl.g_org_delay_buf, gl.g_org_stomach_fuel, gl.g_org_scratch,
        gl.g_ram_bank_access, gl.g_ram_bank_access_next, gl.g_curriculum_delay,
        gl.g_conn_w_dna, gl.g_conn_w_slow,
        gl.g_cam_keys, gl.g_cam_vals, gl.g_cam_valid, gl.g_cam_tick,
        gl.g_clear_count, gl.g_org_run, gl.g_lump_acc,
        gl.g_race_state, gl.g_race_attempt_q,
        gl.g_reservoir_state, gl.g_reservoir_src, gl.g_reservoir_dst, gl.g_reservoir_weight,
        gl.g_readout_w,
        gl.g_ne_bytes,
    )


def main():
    failures = []
    flag = bool(ne.NEUROEVOLUTION)
    env_flag = os.environ.get("GENESIS_NEUROEVOLUTION", "0") == "1"
    import numba
    cache_dir = numba.config.CACHE_DIR

    # G1: flag mirror
    print(f"[G1] GENESIS_NEUROEVOLUTION env={env_flag} engine={flag} "
          f"cache_dir={os.path.basename(str(cache_dir))}")
    if flag != env_flag:
        failures.append("engine flag does not mirror env")

    placed = 0
    if flag:
        # G2: founder decode-equivalence — ancestor -> flat genome -> marker dna -> same body
        anc = gl.create_intelligent_ancestor(None)
        proj = gl.ne_project_byte_genome(anc)
        dna2 = ne.ne_encode_genome(proj, gl.NE_HIDDEN, gl.NE_DUP_SLOTS)
        a_syn, a_hid, a_rec = _parse_body(anc, gl.NE_N_C)
        b_syn, b_hid, b_rec = _parse_body(dna2, gl.NE_N_C)
        ok = (a_syn == b_syn) and (a_hid[:gl.NE_HIDDEN] == b_hid) and (a_rec == b_rec)
        print(f"[G2] founder decode-equivalence: synapses a={len(a_syn)} b={len(b_syn)} "
              f"equal={a_syn == b_syn} | hidden equal={a_hid[:gl.NE_HIDDEN] == b_hid} "
              f"| receptor equal={a_rec == b_rec} | genome_len={gl.NE_GENOME_LEN} "
              f"(slots={gl.NE_N_SYN_BASE}+{len(gl.NE_DUP_SLOTS)}dup params={gl.NE_N_PARAM})")
        if not ok:
            failures.append("founder projection is NOT decode-equivalent to the ancestor")

        gl._lay_library()
        rng = np.random.default_rng(PROBE_SEED)
        placed, _f = gl.ne_seed_population(rng)
    else:
        # frozen static cohort of plain ancestors (evolution OFF), same pop/seed/placement rule
        gl._lay_library()
        anc = gl.create_intelligent_ancestor(None)
        for slot in range(gl.MAX_ORGANISMS):
            if placed >= PROBE_POP:
                break
            pos = gl.ne_find_spawn_pos()
            if pos < 0:
                break
            if gl.spawn_organism(slot, pos, anc, initial_energy=gl.SEED_ENERGY):
                placed += 1
    if placed != PROBE_POP:
        failures.append(f"placement {placed} != requested pop {PROBE_POP}")
    print(f"[G3] placed {placed}/{PROBE_POP} organisms (flag={flag})")

    rng = np.random.default_rng(PROBE_SEED)
    age_mark = gl.ne_reset_generation() if flag else None
    offspring_total = 0
    bytes_total = 0.0     # accumulated per-window totals (counters reset each generation)
    evolutions = 0
    global_time = 0
    next_repro = PROBE_REPRO
    try:
        while global_time < PROBE_TICKS:
            _world_tick(global_time)
            global_time += 1
            if flag and global_time >= next_repro:
                stats = gl.ne_evolve_step(rng, age_mark)
                evolutions += 1
                offspring_total += stats["n_offspring"]
                bytes_total += stats["mean_bytes"] * stats["pop"]
                assert np.isfinite(stats["mean_fitness"]), "fitness not finite"
                print(f"  [t={global_time:>5}] pop={stats['pop']} fit={stats['mean_fitness']:.1f} "
                      f"(surv={stats['mean_survival']:.1f} bytes={stats['mean_bytes']:.1f}) "
                      f"div={stats['diversity']:.4f} off={stats['n_offspring']} "
                      f"extinct={stats['extinct']}")
                age_mark = gl.ne_reset_generation()
                next_repro += PROBE_REPRO
    except Exception as e:  # G3: any crash fails the smoke
        failures.append(f"run crashed at t={global_time}: {type(e).__name__}: {e}")

    alive = int(np.sum(gl.g_alive))
    total_bytes = int(bytes_total) if flag else int(np.sum(gl.g_ne_bytes))
    print(f"[G3] run complete: ticks={global_time} alive={alive} "
          f"evolutions={evolutions} offspring={offspring_total} ne_bytes_total={total_bytes}")

    # G4: offspring under flag 1; hooks dead under flag 0
    if flag:
        if evolutions > 0 and offspring_total <= 0:
            failures.append("no tournament offspring produced")
    else:
        if evolutions != 0:
            failures.append("evolve step ran with flag OFF")
        if total_bytes != 0:
            failures.append("g_ne_bytes nonzero with flag OFF — engine hooks NOT dead")
        print("[G4] flag OFF: g_ne_bytes stayed 0 (engine hooks dead, default path untouched)")

    # divergence fingerprints
    whash = hashlib.sha256(gl.g_global_conn_weight.tobytes()).hexdigest()[:16]
    live_genomes = sorted(
        bytes(gl.g_global_genome[gl.g_org_g_ptr[i]: gl.g_org_g_ptr[i] + gl.g_org_g_count[i]])
        for i in range(gl.MAX_ORGANISMS) if gl.g_alive[i])
    ghash = hashlib.sha256(b"".join(live_genomes)).hexdigest()[:16]
    summary = {
        "flag": flag, "seed": PROBE_SEED, "pop": PROBE_POP, "ticks": PROBE_TICKS,
        "repro": PROBE_REPRO, "alive": alive, "evolutions": evolutions,
        "offspring": offspring_total, "ne_bytes_total": total_bytes,
        "WHASH": whash, "GHASH": ghash,
        "cache_dir": str(cache_dir),
    }
    print(f"[DIV] WHASH={whash} GHASH={ghash}")
    out = os.environ.get("PROBE_JSON_OUT")
    if out:
        with open(out, "w") as f:
            json.dump(summary, f, indent=1)
        print(f"  wrote {out}")

    if failures:
        print("NEUROEVOLUTION_SMOKE_FAILED:")
        for f_ in failures:
            print("  " + f_)
        sys.exit(1)
    print("NEUROEVOLUTION_SMOKE_PASSED")


if __name__ == "__main__":
    main()
