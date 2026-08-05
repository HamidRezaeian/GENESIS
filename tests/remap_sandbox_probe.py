"""Exp 34 — WITHIN-LIFETIME REMAP, held-out sandbox probe (Ascent.md §4 step 2, Rules 9<->6/14).

The decisive, survival-DECOUPLED test of Rule-6 in-lifetime LEARNING. Every prior "does it learn?"
result was confounded by the survival economy: making reading harder pushes the colony to the refuge
floor (pop=12), so a learner's re-tracking can't be separated from the economy collapsing. This probe
removes the economy entirely and measures learning in isolation, on the REAL world_tick_numba kernel
(no reimplemented physics — the Live-Loop-Test-Gap rule):

  - A fixed cohort of REMAP-ancestor clones stands on a fixed contiguous text patch.
  - Energy is PINNED high every tick -> nobody dies, nobody reproduces (births zeroed) -> the cohort
    is frozen; only SYNAPTIC WEIGHTS (STDP) change. So any change in accuracy is IN-LIFETIME LEARNING,
    nothing else.
  - The remap phase alternates on the REMAP_PERIOD clock (identity <-> 2-bit swap). The kernel reads
    the phase from global_time, exactly as in the live loop.
  - Observation-only per-bit accuracy is computed from the read_log (type-1 solves + type-2 misses
    carry target byte + emission), split into: the 2 SWAPPED bits (SB0/SB1) vs the 6 UNCHANGED bits.

THE PRE-REGISTERED PREDICTION (from the kernel analysis): STDP3C's credit is OUTPUT-GATED — it can
only reinforce/suppress vocal neurons that ACTUALLY FIRED. In a swapped phase the echo diagonal makes
vocal-SB0 fire (now WRONG) and leaves vocal-SB1 SILENT (should fire). STDP3C can LTD-suppress the wrong
firing route, but to make SB1 fire it must potentiate a synapse onto a SILENT neuron — no post-spike,
no eligibility, so Hebbian-family STDP can never RECRUIT it. Prediction: the learner PRUNES wrong
pathways (swap-bit acc may rise above the echo floor by suppression) but cannot RECRUIT the new one
(swap-bit acc stays well below the unchanged-bit acc), while NOLEARN stays pinned at the echo floor
(~correct only when the swap happens to be a no-op for that byte). If the learner CANNOT recruit, the
missing substrate capability is localised: a true ERROR/teaching signal that reaches silent-but-wanted
neurons — the next SUBSTRATE change, not another economy lever.

Run:
  GENESIS_ECONOMY=books GENESIS_REMAP=1 GENESIS_STDP3C=1 GENESIS_STDP_DIV=32 python tests/remap_sandbox_probe.py
  GENESIS_ECONOMY=books GENESIS_REMAP=1 GENESIS_NOLEARN=1               python tests/remap_sandbox_probe.py
"""
import os, sys
os.environ.setdefault("GENESIS_ECONOMY", "books")
# Measurement-window integrity (2026-07-31 audit): this probe attributes accuracy to a remap
# PHASE, so the report window (PROBE_REPORT, default 2000) must fit INSIDE one remap phase and
# alternate idnt/SWAP between samples — i.e. REMAP_PERIOD == 2*REPORT, the era the probe was
# designed for. Rule 22 later set genesis_lab's fallback default to 500, which (a) aliases every
# 2000-tick sample onto the identity phase and (b) mixes both phases inside each window, silently
# voiding per-phase attribution. Pin the documented default HERE (a user-explicit env still wins,
# and a startup check below refuses to emit phase-attributed numbers if the window/period
# relationship is broken).
os.environ.setdefault("GENESIS_REMAP_PERIOD", "4000")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

# Multi-seed replication (Rule 3): seed BOTH RNG families BEFORE importing the lab/engine —
# the ancestor fabricator uses Python's `random` module (create_intelligent_ancestor and the
# lib's roll functions), numpy RNG drives placement/injectors, and module-level draws happen
# at import time. Seeding only np.random AFTER import (the earlier hook) left per-run entropy
# from the OS in the ancestor bytes: two "identical" leaderboard passes differed seed-for-seed
# (caught by the 2026-07-31 reproducibility audit of Exp 92-TF1).
import random as _pyrandom
_EARLY_SEED = int(os.environ.get("PROBE_SEED", "0"))
_pyrandom.seed(_EARLY_SEED)
import numpy as np
np.random.seed(_EARLY_SEED)

import genesis_lab as gl
import neuromorphic_engine as ne

# Pin the KERNEL's internal RNG (numba in-JIT `random` draws — mutation/viscosity/sensing).
# Python-level seeds alone were proven insufficient by the Exp-92 reproducibility audit.
ne.seed_kernel_rng(_EARLY_SEED)

N_ORG    = int(os.environ.get("PROBE_N", "120"))
TICKS    = int(os.environ.get("PROBE_TICKS", "60000"))
PATCH    = int(os.environ.get("PROBE_PATCH", "2000"))     # contiguous text patch width
REPORT   = int(os.environ.get("PROBE_REPORT", "2000"))    # print cadence (global_time units)
SB0, SB1 = int(os.environ.get("GENESIS_REMAP_SB0", "0")), int(os.environ.get("GENESIS_REMAP_SB1", "1"))


def build_patch():
    """Lay a fixed contiguous text scroll and stand the cohort on it, one org per cell.

    Returns (placed_count, patch_start). The initial placement slots are remembered in
    _PIN for the drift-pinning below."""
    from books_of_genesis import inject_contiguous_library
    inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, gl.BOOK_CATEGORY, gl.BOOK_NAME, PATCH)
    start = gl.contiguous_library_start(gl.RAM_SIZE, PATCH)
    dna = gl.create_intelligent_ancestor(None)
    placed = 0
    p = start
    while placed < N_ORG and p < start + PATCH:
        if gl.g_org_grid[p] == -1:
            if gl.spawn_organism(placed, p, dna, initial_energy=gl.SEED_ENERGY):
                placed += 1
        p += 3   # space them out so they don't collide-block on the saccade
    return placed, start


_PIN = {"start": 0, "enabled": os.environ.get("PROBE_PIN_POS", "1") == "1"}

def pin_positions_to_patch():
    """Drift-pin the frozen cohort onto the patch (Exp-92b instrument repair, 2026-07-31).

    The probe pins ENERGY high (nobody dies) but never pinned POSITIONS, and its own comment
    claimed re-pinning was "unnecessary because the scroll is contiguous and long". That
    assumption is FALSE: saccades carry the cohort off the patch within ~2k ticks, after which
    per-window "accuracy" collapses arm-independently (STDP3C hits n=0 reads by t=6000 with
    REMAP=0!) and any phase attribution is void — the very diagnosis class the deep review
    warns about. Fix: at the top of every tick, wrap each placed organism's position MODULO
    the patch (start + ((pos - start) % PATCH)) and repair the occupancy grid for the moved
    ones. Organisms still move/saccade physically every tick (real kernel, real physics); they
    just cannot LEAVE the measured text — the minimal bounded intervention that preserves the
    frozen-cohort abstraction, same class as the energy pin. Disable with PROBE_PIN_POS=0 to
    reproduce the broken historical geometry."""
    if not _PIN["enabled"]:
        return
    start = _PIN["start"]
    alive_ids = np.nonzero(gl.g_alive)[0]
    if alive_ids.size == 0:
        return
    pos = gl.g_positions[alive_ids]
    newpos = start + ((pos - start) % PATCH)
    for oid, old, new in zip(alive_ids, pos, newpos):
        if old == new:
            continue
        if gl.g_org_grid[new] != -1:
            continue  # occupied this tick; defer (rare — 120 orgs on a 2000-cell patch)
        if gl.g_org_grid[old] == oid:
            gl.g_org_grid[old] = -1
        gl.g_org_grid[new] = oid
        gl.g_positions[oid] = new


def remap_target(nb, swapped):
    if not swapped:
        return nb & 0xFF
    b0 = (nb >> SB0) & 1
    b1 = (nb >> SB1) & 1
    nb2 = nb & ~((1 << SB0) | (1 << SB1))
    nb2 |= (b1 << SB0) | (b0 << SB1)
    return nb2 & 0xFF


def measure_window(swapped):
    """Drain read_log; for every logged read, compare emission bits to the remapped target bits.
    type1 (solve) => emission == remapped target on all 8 bits. type2 (miss) => explicit emission."""
    rl = gl.g_read_log
    sc = st = uc = ut = 0
    idx = 1
    n = int(rl[0])
    while idx < n:
        t = int(rl[idx])
        if t == 1:
            tgt = remap_target(int(rl[idx + 2]), swapped)
            emit = tgt  # a full solve matched every bit by definition
            idx += 3
        elif t == 2:
            tgt = remap_target(int(rl[idx + 2]), swapped)
            emit = int(rl[idx + 3])
            idx += 4
        elif t == 3:
            idx += 3; continue
        elif t == 4:
            idx += 3; continue
        elif t == 5:
            idx += 3; continue
        else:
            break
        for b in range(8):
            ok = ((emit >> b) & 1) == ((tgt >> b) & 1)
            if b == SB0 or b == SB1:
                st += 1; sc += 1 if ok else 0
            else:
                ut += 1; uc += 1 if ok else 0
    rl[0] = 1
    return sc, st, uc, ut


def main():
    # Seeding is done at import time above (BEFORE the lab/engine modules hydrate), since
    # module-level draws happen during import; re-read it here only for the manifest fields.
    seed = _EARLY_SEED
    mode = ("NOLEARN" if ne.NOLEARN else ("STDP3C" if ne.STDP3C else ("STDP3" if ne.STDP3 else "STDP")))
    # Startup integrity check: refuse to emit phase-attributed measurements if the report
    # window would span or alias remap phases (see the env pin at the top of this file).
    _period = int(ne.REMAP_PERIOD)
    if ne.REMAP and (2 * REPORT > _period or _period % (2 * REPORT) != 0):
        raise SystemExit(
            f"[SANDBOX] INVALID MEASUREMENT GEOMETRY: REPORT={REPORT} vs REMAP_PERIOD={_period}. "
            f"Per-phase attribution requires REMAP_PERIOD == 2*REPORT*k (k>=1); fix PROBE_REPORT or "
            f"GENESIS_REMAP_PERIOD before trusting any output.")
    print(f"[SANDBOX] mode={mode} REMAP={ne.REMAP} period={int(ne.REMAP_PERIOD)} states={int(ne.REMAP_STATES)} "
          f"swapbits=({SB0},{SB1}) DIV={float(ne.STDP_DIV):.0f} N={N_ORG} ticks={TICKS} patch={PATCH} pin_pos={_PIN['enabled']}")
    # JIT warmup on a throwaway single org handled by first real tick.
    placed, patch_start = build_patch()
    _PIN["start"] = patch_start
    print(f"[SANDBOX] placed {placed} clones on a {PATCH}-byte patch; energy pinned (no death/birth)")

    windows = []   # per-window metrics (exported to PROBE_JSON_OUT if set)
    global_time = 0
    HI = float(gl.ATP_MAX) * 0.5
    dummy_births = None
    while global_time < TICKS:
        pin_positions_to_patch()

        if os.environ.get("PROBE_DEBUG_HASH") == "1" and global_time % 500 == 0:
            import hashlib as _hl
            def hh(a): return _hl.sha256(a.tobytes()).hexdigest()[:8]
            print(f"    [HASH t={global_time}] pos={hh(gl.g_positions)} en={hh(gl.g_energy)} "
                  f"age={hh(gl.g_age)} v={hh(gl.g_global_v)} w={hh(gl.g_global_conn_weight)} "
                  f"log={hh(gl.g_read_log[:64])} ram={hh(gl.g_ram[:8192])}")
# PIN energy high every tick so nobody dies and the reproduce threshold is moot; we also zero
        # the birth buffer return so the cohort stays frozen (only weights move).
        gl.g_energy[gl.g_alive] = np.float32(HI)

        n_alive, n_births = gl.world_tick_numba(
            gl.g_ram, gl.g_org_grid, gl.g_positions, gl.g_alive, gl.g_energy, gl.g_age,
            gl.g_global_v, gl.g_global_ref, gl.g_global_t_last, gl.g_global_thresh, gl.g_global_tau, gl.g_global_rec_id,
            gl.g_global_conn_src, gl.g_global_conn_dst, gl.g_global_conn_weight, gl.g_global_conn_elig, gl.g_global_conn_elig_t,
            gl.g_neuron_map, gl.g_synapse_map, gl.g_genome_map,
            gl.g_org_n_ptr, gl.g_org_n_count, gl.g_org_s_ptr, gl.g_org_s_count,
            gl.g_global_genome, gl.g_org_g_ptr, gl.g_org_g_count,
            gl.o_rec_a_plus, gl.o_rec_a_minus, gl.o_rec_tau_p, gl.o_rec_tau_m,
            gl.o_rec_v_rest, gl.o_rec_v_reset, gl.o_rec_tau_def, gl.o_rec_spk_max, gl.o_rec_tau_e,
            gl.g_viscosity, global_time, gl.g_org_lif_steps,
            gl.g_b_pos, gl.g_b_parent, gl.g_b_g_start, gl.g_b_g_count, gl.g_b_genomes, gl.g_b_energy,
            gl.g_oracle_val, gl.g_oracle_target, gl.voice_buf, gl.vocal_cords, gl.vocal_prev,
            gl.action_now, gl.action_prev, gl.g_read_log, gl.g_read_fuel, gl.g_cell_owner, gl.g_read_hits,
            gl.CANVAS_LO, gl.CANVAS_HI, gl.g_org_reward, gl.g_org_elig,
            gl.g_global_sense_type, gl.g_global_sense_meta, gl.g_global_act_drive,
            gl.g_org_delay_buf, gl.g_org_stomach_fuel, gl.g_org_scratch, gl.g_ram_bank_access, gl.g_ram_bank_access_next,
            gl.g_curriculum_delay, gl.g_conn_w_dna, gl.g_conn_w_slow,
            gl.g_cam_keys, gl.g_cam_vals, gl.g_cam_valid, gl.g_cam_tick,
            gl.g_clear_count, gl.g_org_run, gl.g_lump_acc, gl.g_race_state, gl.g_race_attempt_q,

            gl.g_eligibility, gl.g_baseline_acc, gl.g_spikes_used,
            gl.g_reservoir_state, gl.g_readout_w)

        # Ignore births entirely (frozen cohort): free any birth-buffer bodies were NOT allocated (the
        # kernel only fills b_* arrays; spawning happens in sim_loop which we don't call), so nothing to
        # undo. Drift off the patch is handled by pin_positions_to_patch() at the top of each tick
        # (the old "re-pinning is unnecessary" assumption was falsified by the Exp-92b instrument
        # audit: reads collapsed to n≈0 long before the run ended).

        period = int(ne.REMAP_PERIOD); states = int(ne.REMAP_STATES)
        # Era attribution (Exp-93 instrument fix, 2026-07-31): the window just drained spans
        # ticks [global_time-REPORT, global_time). With REMAP_PERIOD == 2*REPORT*k each report
        # window lies FULLY inside one physical era, so its label must come from the era of its
        # FIRST tick — labeling by `global_time` at drain time shifted every era attribution by
        # exactly one window (identity data reported as "SWAP" and vice versa), corrupting the
        # pre-pinning era readings of the session-era experiments on this probe.
        era_start = (global_time - REPORT) if global_time >= REPORT else max(global_time - REPORT, 0)
        swapped = (states > 1) and (((era_start // period) % states) != 0)

        if global_time % REPORT == 0 and global_time > 0:
            sc, st, uc, ut = measure_window(swapped)
            swap_acc = (100.0 * sc / st) if st else float("nan")
            unch_acc = (100.0 * uc / ut) if ut else float("nan")
            phase = "SWAP" if swapped else "idnt"
            windows.append({"t": int(global_time), "remap_active": bool(ne.REMAP),
                            "phase_label": phase,
                            "swapbit_correct": int(sc), "swapbit_total": int(st),
                            "unchbit_correct": int(uc), "unchbit_total": int(ut),
                            "alive": int(n_alive)})
            print(f"  t={global_time:>6} phase={phase} | swapbit_acc={swap_acc:5.1f}% (n={st:4d}) "
                  f"| unchbit_acc={unch_acc:5.1f}% (n={ut:5d}) | alive={int(n_alive)}")

        global_time += 1

    # Machine-readable export for the leaderboard driver (Experiment 92 series).
    out = os.environ.get("PROBE_JSON_OUT")
    if out:
        import json
        payload = {
            "instrument": "remap_sandbox_probe",
            "instrument_rev": "2026-08-02+twoscale",
            "seed": seed,
            "mode": mode, "remap": bool(ne.REMAP), "period": int(ne.REMAP_PERIOD),
            "states": int(ne.REMAP_STATES), "swapbits": [SB0, SB1],
            "stdp_div": float(ne.STDP_DIV), "n_orgs": N_ORG, "ticks": TICKS,
            "patch": PATCH, "report": REPORT, "pin_pos": bool(_PIN["enabled"]),
            "windows": windows,
        }
        if os.environ.get("PROBE_DUMP_GATE") == "1":
            # Exp-98 build-time diagnostic (off by default; never part of certified rows):
            # dump the gate accumulator columns so mechanism development can VERIFY that the
            # gated branch actually executed (cols 8/9 = scalar SUM/CNT; 10-17 per-bit SUM).
            e = gl.g_org_elig
            payload["gate_diag"] = {
                "col8_sum_nonzero": int(np.count_nonzero(e[:, 8])),
                "col9_cnt_max": float(e[:, 9].max()),
                "col9_cnt_mean": float(e[:, 9].mean()),
                "col10_16_absmax": float(np.abs(e[:, 10:18]).max()),
                "gate_flag_in_engine": bool(getattr(ne, "STDP_SURPRISE_GATE", False)),
                # plasticity-health forensics: is the eligibility TRACE itself alive?
                "conn_elig_absmax": float(np.abs(gl.g_global_conn_elig).max()),
                "conn_elig_mean_abs": float(np.abs(gl.g_global_conn_elig).mean()),
                "homeo_lambda": float(os.environ.get("GENESIS_HOMEOSTATIC_LAMBDA", "0.01")),
                "weight_delta_absmax_vs_dna": float(np.abs(
                    gl.g_global_conn_weight - gl.g_conn_w_dna).max()) if hasattr(gl, "g_conn_w_dna") else None,
            }
        with open(out, "w") as f:
            json.dump(payload, f, indent=1)
        print(f"[SANDBOX] JSON written to {out}")


if __name__ == "__main__":
    main()
