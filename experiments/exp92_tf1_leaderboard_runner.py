"""Experiment 92-TF1 — first REAL leaderboard row: non-stationary tracking, remap sandbox.

PRE-REGISTERED (before execution, binding):

  Protocol REMAP_SANDBOX_TF1_v1. Frozen-cohort remap sandbox (tests/remap_sandbox_probe.py,
  instrument rev 2026-07-31+drift-pin), kernel run REAL (world_tick_numba), energy+position
  pinned so ONLY synaptic weights can change (in-lifetime learning, survival decoupled).

  Arms: STDP3C learner vs NOLEARN ablation (identical everything else). Crossed with
  REMAP=1 (identity <-> 2-bit swap every 4000 ticks) and REMAP=0 static control.
  Seeds: 0,1,2 (PROBE_SEED). 8000 ticks/run. STDP_DIV=1 (current default stack; the
  session-era DIV=32 is a documented secondary sensitivity axis, not this row).

  Recorded metrics per seed (mean over windows, boundary-mixed windows matched across arms):
    static_unch  = unchanged-bit accuracy, REMAP=0 (must stay high in NOLEARN => instrument sanity)
    swap_mix     = mean swap-bit accuracy in SWAP windows, REMAP=1
    unch_mix     = mean unchanged-bit accuracy in idnt windows, REMAP=1

  Certification gates (the row only publishes certified=true if ALL hold):
    G1 instrument sanity: NOLEARN static_unch >= 80% on every seed.
    G2 run completeness: every planned run produced a parseable JSON with >= 2 windows/phase.
    G3 honesty: units, seeds, fingerprints recorded verbatim; no cell is interpolated.

  Interpretive gates (reported, NOT certification conditions — a learner does not HAVE to win):
    swap_delta = mean_seeds(learner swap_mix) - mean_seeds(ablation swap_mix).
    delta > 0 would be a replicate of the Exp-34/34/91 pruning effect on the REPAIRED
    instrument; delta ~<= 0 confirms that under the current Rule-22 stack the sandbox shows
    no net in-lifetime re-tracking advantage. BOTH outcomes are publishable (Rule 16).

Output: experiments/leaderboard/latest.json (+ raw per-run JSON in experiments/leaderboard/raw/).
Run: python experiments/exp92_tf1_leaderboard_runner.py
"""
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leaderboard", "raw")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leaderboard", "latest.json")

TICKS = int(os.environ.get("EXP92_TF1_TICKS", "8000"))
SEEDS = [int(s) for s in os.environ.get("EXP92_TF1_SEEDS", "0,1,2").split(",")]
TIMEOUT = int(os.environ.get("EXP92_TF1_TIMEOUT", "600"))
PROBE = os.path.join(ROOT, "tests", "remap_sandbox_probe.py")

ARMS = {
    "stdp3c_learner": {"GENESIS_NOLEARN": "0", "GENESIS_STDP3C": "1", "GENESIS_STDP3": "0", "GENESIS_STDP": "0"},
    "nolearn_ablation": {"GENESIS_NOLEARN": "1", "GENESIS_STDP3C": "0", "GENESIS_STDP3": "0", "GENESIS_STDP": "0"},
}


def run_one(arm, remap, seed):
    os.makedirs(RAW, exist_ok=True)
    jpath = os.path.join(RAW, f"tf1_{arm}_remap{remap}_s{seed}.json")
    env = os.environ.copy()
    env.update({
        "GENESIS_LIVE_WEB": "0",
        "GENESIS_ECONOMY": "books",
        "GENESIS_REMAP": str(remap),
        "GENESIS_REMAP_PERIOD": "4000",
        "GENESIS_STDP_DIV": "1",
        "PROBE_TICKS": str(TICKS),
        "PROBE_SEED": str(seed),
        "PROBE_JSON_OUT": jpath,
        "PROBE_PIN_POS": "1",
        # DETERMINISM (Exp-93 root-cause, 2026-07-31): pool geometry in this lab floats with
        # HOST FREE MEMORY at run start (auto_capacity / engine RAM derivation). Two passes
        # with identical seeds and code then allocate different pool sizes, the address layout
        # of genomes/neurons shifts, and trajectories diverge from tick ~2000 on — visible as
        # irreproducible "seed" results. A measured row MUST pin its geometry:
        "GENESIS_MAX_ORGANISMS": "512",
        "GENESIS_RAM_SIZE": "2097152",
    })
    env.update(ARMS[arm])
    t0 = time.time()
    proc = subprocess.run([sys.executable, PROBE], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=TIMEOUT)
    wall = time.time() - t0
    ok = proc.returncode == 0 and os.path.exists(jpath)
    data = None
    if ok:
        try:
            with open(jpath) as f:
                data = json.load(f)
        except (OSError, ValueError):
            ok = False
    return {"arm": arm, "remap": remap, "seed": seed, "ok": ok,
            "wall_seconds": round(wall, 1), "json": jpath if ok else None,
            "rc": proc.returncode, "stderr_tail": (proc.stderr or "")[-600:], "data": data}


def phase_mean(windows, phase, key_correct, key_total):
    c = sum(w[key_correct] for w in windows if w["phase_label"] == phase)
    t = sum(w[key_total] for w in windows if w["phase_label"] == phase)
    return (100.0 * c / t) if t else None, t


def main():
    runs = []
    for arm in ARMS:
        for remap in (0, 1):
            for seed in SEEDS:
                r = run_one(arm, remap, seed)
                print(f"[TF1] {arm} remap={remap} seed={seed} ok={r['ok']} wall={r['wall_seconds']}s",
                      flush=True)
                runs.append(r)

    # sanity gate completeness
    completeness = all(r["ok"] and len(r["data"]["windows"]) >= 2 for r in runs)
    per = {}
    for r in runs:
        if not r["ok"]:
            continue
        w = r["data"]["windows"]
        if r["remap"] == 0:
            m, n = phase_mean(w, "idnt", "unchbit_correct", "unchbit_total")
            per[(r["arm"], 0, r["seed"])] = {"static_unch": m, "n": n}
        else:
            sm, sn = phase_mean(w, "SWAP", "swapbit_correct", "swapbit_total")
            um, un = phase_mean(w, "idnt", "unchbit_correct", "unchbit_total")
            per[(r["arm"], 1, r["seed"])] = {"swap_mix": sm, "unch_mix": um,
                                             "swap_n": sn, "unch_n": un}

    def mean(xs):
        xs = [x for x in xs if x is not None]
        return (sum(xs) / len(xs)) if xs else None

    g1 = all(per.get(("nolearn_ablation", 0, s), {}).get("static_unch") is not None
             and per[("nolearn_ablation", 0, s)]["static_unch"] >= 80.0 for s in SEEDS)
    # G2-b: a remap=1 run that measured ZERO swap-era events cannot support a delta claim
    # (caught at 2026-07-31: with TICKS=2 periods the last SWAP-era drain never fires —
    # the row must say so instead of publishing delta=None).
    g2b = all(per.get((arm, 1, s), {}).get("swap_mix") is not None
              for arm in ARMS for s in SEEDS)
    certified = bool(completeness and g1 and g2b)

    learn_swap = mean([per.get(("stdp3c_learner", 1, s), {}).get("swap_mix") for s in SEEDS])
    abl_swap = mean([per.get(("nolearn_ablation", 1, s), {}).get("swap_mix") for s in SEEDS])
    swap_delta = (learn_swap - abl_swap) if (learn_swap is not None and abl_swap is not None) else None

    fp_state = {}
    try:
        sys.path.insert(0, os.path.join(ROOT, "src"))
        import compile_fingerprint
        fp_state = compile_fingerprint.current_fingerprint()
    except Exception as e:
        fp_state = {"error": f"{type(e).__name__}: {e}"}

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    manifest_src = json.dumps({f"{k[0]}|remap{k[1]}|s{k[2]}": per[k] for k in sorted(per)},
                              sort_keys=True)
    payload = {
        "protocol_id": "REMAP_SANDBOX_TF1_v1",
        "family": "Task Family 1 — Non-stationary Tracking (remap sandbox)",
        "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": commit,
        "compile_fingerprint": fp_state,
        "instrument": "tests/remap_sandbox_probe.py @ 2026-07-31+drift-pin",
        "arms": list(ARMS.keys()),
        "config": {"ticks": TICKS, "seeds": SEEDS, "remap_period": 4000, "stdp_div": 1,
                   "probe_pin_pos": True, "economy": "books", "n_orgs": 120, "patch": 2000},
        "gates": {"G1_instrument_sanity_nolearn_static_unch>=80": g1,
                  "G2_run_completeness": completeness,
                  "G2b_swap_windows_measured": g2b},
        "certified": certified,
        "metrics": {
            "per_seed": {f"{k[0]}|remap{k[1]}|s{k[2]}": v for k, v in sorted(per.items())},
            "learner_swap_mix_mean": learn_swap,
            "ablation_swap_mix_mean": abl_swap,
            "swap_delta_learner_minus_ablation": swap_delta,
            "note": "n=3 seeds per arm; descriptive reporting only — no z-claim at this n (deep review P1-4).",
        },
        "runs_manifest_hash": hashlib.sha256(manifest_src.encode()).hexdigest(),
        "energy_basis": "cycles MEASURED natively per Rule 21.1 (see Docs/Architecture/ENERGY_ACCOUNTING.md)",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1)
    print(f"[TF1] certified={certified} (G1={g1}, G2={completeness}, G2b={g2b}) swap_delta={swap_delta}")
    print(f"[TF1] leaderboard row written to {OUT}")
    if not certified:
        print("[TF1] row stored as UNcertified — dashboard MUST keep showing measured-pending")


if __name__ == "__main__":
    main()
