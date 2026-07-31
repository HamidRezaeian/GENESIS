"""Experiment 92-TF1 — first REAL leaderboard row: non-stationary tracking, remap sandbox.

PRE-REGISTERED (before execution, binding):

  Protocol REMAP_SANDBOX_TF1_v1. Frozen-cohort remap sandbox (tests/remap_sandbox_probe.py,
  instrument rev 2026-07-31+drift-pin), kernel run REAL (world_tick_numba), energy+position
  pinned so ONLY synaptic weights can change (in-lifetime learning, survival decoupled).

  Arms: STDP3C learner vs NOLEARN ablation (identical everything else). Crossed with
  REMAP=1 (identity <-> 2-bit swap every 4000 ticks) and REMAP=0 static control.
  Seeds: 0..7 by default (n=8 pairs, Exp 94 — upgraded from the n=3 descriptive row of
  Exp 92/93, deep-review P1-4). Exp 94b (PRE-REGISTERED 2026-07-31 in Docs/Result.md,
  committed BEFORE any seed >= 8 datum existed, binding regardless of sign) re-runs this
  exact protocol at n=24 (EXP92_TF1_SEEDS=0,1,...,23) as the single decisive confirmatory
  verdict; seeds 0-7 enter via the byte-deterministic reuse cache.
  8000 ticks/run. STDP_DIV=1 (current default stack).

  Recorded metrics per seed (mean over windows, boundary-mixed windows matched across arms):
    static_unch  = unchanged-bit accuracy, REMAP=0 (must stay high in NOLEARN => instrument sanity)
    swap_mix     = mean swap-bit accuracy in SWAP windows, REMAP=1
    unch_mix     = mean unchanged-bit accuracy in idnt windows, REMAP=1

  Certification gates (the row only publishes certified=true if ALL hold):
    G1 instrument sanity: NOLEARN static_unch >= 80% on every seed.
    G2 run completeness: every planned run produced a parseable JSON with >= 2 windows/phase.
    G3 honesty: units, seeds, fingerprints recorded verbatim; no cell is interpolated.

  INFERENCE (Exp 94, 2026-07-31, pre-registered):
    Confirmatory test = paired seed-matched deltas d_s = learner_swap_mix[s] - ablation_swap_mix[s]
    at the pre-registered operating point (DIV=1), statistic T = mean(d_s), tested against the
    exact sign-flip permutation null (within a seed pair the arm labels are exchangeable).
    TWO-SIDED tail: the sign of the effect is NOT assumed (Rule 16 — a non-positive delta is
    equally publishable). Exact enumeration over all 2^n sign assignments for n <= 20, else a
    pinned-seed Monte Carlo. Min attainable p at n=8 is 2/256 ~= 0.0078.
    Multiplicity: the single DIV=1 delta is the confirmatory test; the optional DIV sweep is
    SENSITIVITY only (unadjusted p's reported there carry an explicit note).

  Optional sensitivity axis (EXP92_TF1_DIV_SWEEP=1,8,32):
    Learner arm rerun at each STDP_DIV (remap=1, all seeds); deltas paired against the SAME
    main-ladder ablation runs. Justification: the ablation has learning disabled, so STDP_DIV
    is a no-op for it; this is not assumed but EMPIRICALLY CHECKED (one ablation run at the
    largest swept DIV on the first seed must reproduce the main ablation run bit-for-bit on
    every recorded float, else the invariance flag is false and sweep deltas are marked
    uninterpretable).

Output: experiments/leaderboard/latest.json (+ raw per-run JSON in experiments/leaderboard/raw/).
Run: python experiments/exp92_tf1_leaderboard_runner.py
     EXP92_TF1_SEEDS=0,1 (CI smoke)   EXP92_TF1_DIV_SWEEP=1,8,32 (published sensitivity block)

Cache mode (EXP92_TF1_REUSE_CACHE=1, OFF by default): raw per-run JSONs that already exist and
parse are reused instead of re-executed. This is legitimate ONLY because this instrument was
measured to be byte-deterministic across invocations at pinned geometry (Exp 93: two consecutive
full passes produced byte-identical per-seed metrics; re-verified in Exp 94 below). Every reused
run is flagged "reused_cache" in the payload's run manifest, so the row reports exactly how much
was re-measured live. Certification from a cold cache still works — it just costs the full wall
time (~5-7s per run, which at n=8+sweep exceeds the sandbox's ~300s single-call ceiling, the
only reason this mode exists).
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
SEEDS = [int(s) for s in os.environ.get("EXP92_TF1_SEEDS", "0,1,2,3,4,5,6,7").split(",")]
TIMEOUT = int(os.environ.get("EXP92_TF1_TIMEOUT", "600"))
DIV_SWEEP = [int(d) for d in os.environ.get("EXP92_TF1_DIV_SWEEP", "").split(",") if d.strip()]
REUSE = os.environ.get("EXP92_TF1_REUSE_CACHE", "0") == "1"
PROBE = os.path.join(ROOT, "tests", "remap_sandbox_probe.py")

ARMS = {
    "stdp3c_learner": {"GENESIS_NOLEARN": "0", "GENESIS_STDP3C": "1", "GENESIS_STDP3": "0", "GENESIS_STDP": "0"},
    "nolearn_ablation": {"GENESIS_NOLEARN": "1", "GENESIS_STDP3C": "0", "GENESIS_STDP3": "0", "GENESIS_STDP": "0"},
}


def run_one(arm, remap, seed, div=1, tag=None, period=4000, report=2000, extra_env=None):
    os.makedirs(RAW, exist_ok=True)
    suffix = f"_{tag}" if tag else ""
    jpath = os.path.join(RAW, f"tf1_{arm}{suffix}_remap{remap}_s{seed}.json")
    if REUSE and os.path.exists(jpath):
        try:
            with open(jpath) as f:
                data = json.load(f)
            return {"arm": arm, "remap": remap, "seed": seed, "div": div, "ok": True,
                    "wall_seconds": 0.0, "json": jpath, "rc": 0, "reused_cache": True,
                    "stderr_tail": "", "data": data}
        except (OSError, ValueError):
            pass  # corrupt/partial cache file -> fall through to a REAL run
    env = os.environ.copy()
    env.update({
        "GENESIS_LIVE_WEB": "0",
        "GENESIS_ECONOMY": "books",
        "GENESIS_REMAP": str(remap),
        "GENESIS_REMAP_PERIOD": str(period),
        "PROBE_REPORT": str(report),
        "GENESIS_STDP_DIV": str(div),
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
    if extra_env:  # Exp 98+: mechanism flags layered on top of the named arm (e.g. gate on)
        env.update(extra_env)
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
    return {"arm": arm, "remap": remap, "seed": seed, "div": div, "ok": ok,
            "period": period, "report": report,
            "wall_seconds": round(wall, 1), "json": jpath if ok else None,
            "rc": proc.returncode, "reused_cache": False,
            "stderr_tail": (proc.stderr or "")[-600:], "data": data}


def phase_mean(windows, phase, key_correct, key_total):
    c = sum(w[key_correct] for w in windows if w["phase_label"] == phase)
    t = sum(w[key_total] for w in windows if w["phase_label"] == phase)
    return (100.0 * c / t) if t else None, t


def summarize_run(r):
    """Extract the per-run metrics the pre-registered protocol records."""
    w = r["data"]["windows"]
    if r["remap"] == 0:
        m, n = phase_mean(w, "idnt", "unchbit_correct", "unchbit_total")
        return {"static_unch": m, "n": n}
    sm, sn = phase_mean(w, "SWAP", "swapbit_correct", "swapbit_total")
    um, un = phase_mean(w, "idnt", "unchbit_correct", "unchbit_total")
    return {"swap_mix": sm, "unch_mix": um, "swap_n": sn, "unch_n": un}


def paired_permutation(deltas):
    """Exact two-sided sign-flip permutation test on seed-matched paired deltas.

    Pre-registered (Exp 94): T = mean(d_s); under H0 the arm labels within a seed pair are
    exchangeable, so flipping the sign of each d_s independently is the null universe.
    Exact enumeration for n <= 20, pinned-seed Monte Carlo beyond.
    Returns None when no pair is measurable (the G2b gate then also fails).
    """
    ds = [d for d in deltas if d is not None]
    n = len(ds)
    if n == 0:
        return None
    t_obs = sum(ds) / n
    if n <= 20:
        total = 1 << n
        extreme = 0
        for mask in range(total):
            s = 0.0
            for i in range(n):
                s += ds[i] if (mask >> i) & 1 else -ds[i]
            if abs(s / n) >= abs(t_obs) - 1e-12:
                extreme += 1
        p = extreme / total
        method = f"exact enumeration over all 2^{n} = {total} sign assignments"
    else:
        import random
        rng = random.Random(0)
        trials = 100000
        extreme = 0
        for _ in range(trials):
            s = sum(d if rng.random() < 0.5 else -d for d in ds)
            if abs(s / n) >= abs(t_obs) - 1e-12:
                extreme += 1
        p = (extreme + 1) / (trials + 1)
        method = f"monte-carlo {trials} sign draws, rng pinned at seed 0"
    sd = sorted(ds)
    med = (sd[n // 2] if n % 2 else 0.5 * (sd[n // 2 - 1] + sd[n // 2]))
    return {
        "test": "paired sign-flip permutation on seed-matched deltas (learner - ablation)",
        "null_hypothesis": "within a seed pair the arm labels are exchangeable (no learning effect)",
        "tail": "two-sided (sign of the effect NOT pre-assumed; Rule 16)",
        "n_pairs": n,
        "per_seed_deltas": ds,
        "mean_delta": t_obs,
        "median_delta": med,
        "min_delta": min(ds),
        "max_delta": max(ds),
        "p_two_sided": p,
        "method": method,
        "min_attainable_p": (2.0 / (1 << n)) if n <= 20 else None,
    }


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
        per[(r["arm"], r["remap"], r["seed"])] = summarize_run(r)

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

    # ---- Exp-94 inference: paired permutation on seed-matched deltas (confirmatory, DIV=1)
    pair_deltas = []
    for s in SEEDS:
        l = per.get(("stdp3c_learner", 1, s), {}).get("swap_mix")
        a = per.get(("nolearn_ablation", 1, s), {}).get("swap_mix")
        pair_deltas.append((l - a) if (l is not None and a is not None) else None)
    stats = paired_permutation(pair_deltas)
    if stats is not None:
        stats["confirmatory"] = True
        stats["multiplicity_note"] = (
            "SINGLE confirmatory test (DIV=1 swap_mix delta). Any DIV-sweep p-values below are "
            "sensitivity/exploratory and are NOT adjusted for — treat them as hypothesis-generating.")

    # ---- Optional DIV sensitivity sweep (learner only; ablation is learning-disabled)
    div_block = None
    if DIV_SWEEP:
        # Empirical invariance check: ablation at the largest swept DIV, first seed, must
        # reproduce the main-ladder ablation run bit-for-bit (same pinned geometry+rng).
        chk_seeds = SEEDS[:1]
        invariance = {"checked": True, "equal": True, "details": {}}
        for s in chk_seeds:
            rc = run_one("nolearn_ablation", 1, s, div=max(DIV_SWEEP), tag=f"div{max(DIV_SWEEP)}invar")
            same = False
            if rc["ok"] and ("nolearn_ablation", 1, s) in per:
                same = summarize_run(rc) == per[("nolearn_ablation", 1, s)]
            invariance["details"][str(s)] = same
            invariance["equal"] = invariance["equal"] and same
            print(f"[TF1] ablation DIV-invariance check seed={s} equal={same}", flush=True)

        sweep = {}
        for div in DIV_SWEEP:
            per_div = {}
            for s in SEEDS:
                rd = run_one("stdp3c_learner", 1, s, div=div, tag=f"div{div}")
                print(f"[TF1] DIV-sweep learner div={div} seed={s} ok={rd['ok']}", flush=True)
                if rd["ok"]:
                    per_div[s] = summarize_run(rd)
            deltas = []
            for s in SEEDS:
                l = per_div.get(s, {}).get("swap_mix")
                a = per.get(("nolearn_ablation", 1, s), {}).get("swap_mix")
                deltas.append((l - a) if (l is not None and a is not None) else None)
            st = paired_permutation(deltas)
            if st is not None:
                st["exploratory_unadjusted"] = True
            sweep[str(div)] = {
                "learner_swap_mix_mean": mean([per_div.get(s, {}).get("swap_mix") for s in SEEDS]),
                "per_seed_swap_mix": {str(s): per_div.get(s, {}).get("swap_mix") for s in SEEDS},
                "stats_vs_main_ablation": st,
            }
        div_block = {
            "axis": "GENESIS_STDP_DIV (dopamine-modulated STDP divisor)",
            "pairing": "learner(div) vs the SAME main-ladder ablation runs, per seed",
            "ablation_div_invariance": invariance,
            "swept_divs": DIV_SWEEP,
            "results": sweep,
            "note": "SENSITIVITY, not confirmatory; p-values unadjusted for the multi-div look.",
        }

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
    n_pairs = (stats or {}).get("n_pairs", 0)
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
            "stats": stats if stats is not None else {
                "reason": "no measurable seed pair (see gates — G2b failed)"},
            "note": (f"n={n_pairs} seed pairs; confirmatory paired permutation (two-sided, "
                     f"exact at this n). alpha reference 0.05 — min attainable p here is "
                     f"{(stats or {}).get('min_attainable_p')!r}."),
        },
        "div_sensitivity": div_block,
        "runs_manifest_hash": hashlib.sha256(manifest_src.encode()).hexdigest(),
        "main_ladder_runs_reused_from_cache": sum(1 for r in runs if r.get("reused_cache")),
        "main_ladder_runs_executed_live": sum(1 for r in runs if not r.get("reused_cache")),
        "energy_basis": "cycles MEASURED natively per Rule 21.1 (see Docs/Architecture/ENERGY_ACCOUNTING.md)",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1)
    p_str = (stats or {}).get("p_two_sided")
    print(f"[TF1] certified={certified} (G1={g1}, G2={completeness}, G2b={g2b}) "
          f"swap_delta={swap_delta} p_two_sided={p_str} n_pairs={n_pairs}")
    print(f"[TF1] leaderboard row written to {OUT}")
    if not certified:
        print("[TF1] row stored as UNcertified — dashboard MUST keep showing measured-pending")


if __name__ == "__main__":
    main()
