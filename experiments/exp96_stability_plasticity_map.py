"""Experiment 96 — Stability/Plasticity map: where (if anywhere) learning beats ablation.

PRE-REGISTERED (2026-07-31, BEFORE execution — binding for interpretation):

  Instrument: the SAME certified remap sandbox as TF1 (tests/remap_sandbox_probe.py
  @ 2026-07-31+drift-pin; pinned geometry 512 organisms / 2 MiB RAM; energy+position pinned;
  kernel RNG + Python RNG seeded per-run). Reuses `run_one`/`summarize_run`/
  `paired_permutation` from experiments/exp92_tf1_leaderboard_runner.py — no copied logic.

  Question. Exp 94b showed learning has no detectable re-tracking advantage at DIV=1 on the
  default tempo (n=24, p~0.61), while Exp 92b showed strong plasticity actively ERODES static
  memory. Both point at a stability/plasticity trade-off: net advantage should rise as
  plasticity weakens (less erosion) UP TO the point where re-tracking becomes too slow.
  This map locates the peak of that curve before any confirmatory bet is placed.

  Grid (exploratory; 14 learner combos + tempo-matched ablations):
    DIV  in {1, 2, 4, 8, 16, 32, 64}        (GENESIS_STDP_DIV)
    tempo: default  = REMAP_PERIOD 4000, PROBE_REPORT 2000 (k=1)
           fast     = REMAP_PERIOD 2000, PROBE_REPORT 1000 (k=1)
    seeds 0..7 (PROBE_SEED), 8000 ticks. ablation pairing: per-tempo matched runs
    (ablation DIV-invariance was verified on recorded metrics in Exp 94; re-checked per tempo
    here with one run at DIV=64 seed 0 vs the DIV=1 ablation — recorded, not assumed).

  Hypotheses (directional where stated):
    H1: mean paired delta rises with DIV above 1 and shows an INTERIOR optimum or a plateau —
        i.e. DIV=1 is not the peak.
    H2: the location of the peak differs between the two tempos (tempo x DIV interaction);
        the DIRECTION of any shift is left exploratory (no sign pre-registered for H2).
    Multiplicity: ALL 14 combos are EXPLORATORY, p-values unadjusted. Nothing in this map is
    a confirmatory claim by itself. A combo "nominating" itself for confirmation must show
    the largest mean paired delta within its tempo (tie-break: smaller two-sided p).
    The single nominated (DIV, tempo) pair becomes Exp 97's pre-registered confirmatory target
    at n=24 (seeds 0..23; seeds 0..7 enter via the byte-deterministic reuse cache), run
    under the SAME gates and permutation protocol as Exp 94b. If NO combo shows a positive
    mean delta, no confirmatory run is nominated and the report says so (negative map is a
    publishable outcome, Rule 16; next lever then = plasticity gating / consolidation, i.e. a
    mechanism change, not more sweeping).

  Output: experiments/exp96_map_results.json (+ raw per-run probe JSONs alongside TF1's raw/).
  Run: python experiments/exp96_stability_plasticity_map.py
"""
import json
import os
import sys
import time

# The runner reads tick budget at IMPORT time (module-level EXP92_TF1_TICKS env); forward the
# exp96 knob BEFORE importing it so both always agree.
if "EXP96_TICKS" in os.environ:
    os.environ["EXP92_TF1_TICKS"] = os.environ["EXP96_TICKS"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp92_tf1_leaderboard_runner import run_one, summarize_run, paired_permutation  # noqa: E402

DIVS = [int(d) for d in os.environ.get("EXP96_DIVS", "1,2,4,8,16,32,64").split(",")]
SEEDS = [int(s) for s in os.environ.get("EXP96_SEEDS", "0,1,2,3,4,5,6,7").split(",")]
TICKS = int(os.environ.get("EXP96_TICKS", "8000"))
TEMPOS = {
    "default": {"period": 4000, "report": 2000},
    "fast": {"period": 2000, "report": 1000},
}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp96_map_results.json")


def mean(xs):
    xs = [x for x in xs if x is not None]
    return (sum(xs) / len(xs)) if xs else None


def main():
    os.environ.setdefault("EXP92_TF1_REUSE_CACHE", "1")  # byte-deterministic; flagged per-run
    os.environ["PROBE_TICKS"] = str(TICKS)
    grid = {"learner": {}, "ablation": {}}
    t_start = time.time()

    # tempo-matched ablations (one 8000-tick run per seed per tempo)
    for tempo, tp in TEMPOS.items():
        for s in SEEDS:
            r = run_one("nolearn_ablation", 1, s, div=1,
                        tag=f"exp96_{tempo}" if tempo != "default" else None,
                        period=tp["period"], report=tp["report"])
            grid["ablation"][(tempo, s)] = summarize_run(r) if r["ok"] else None
            print(f"[EXP96] ablation tempo={tempo} seed={s} ok={r['ok']}", flush=True)

    # learner grid: DIV x tempo x seeds
    for tempo, tp in TEMPOS.items():
        for div in DIVS:
            for s in SEEDS:
                # default-tempo DIV runs reuse the certified TF1 ladder/sweep naming so the
                # byte-deterministic cache from Exp 94/94b applies
                if tempo == "default":
                    tag = None if div == 1 else f"div{div}"
                else:
                    tag = f"exp96_{tempo}_div{div}"
                r = run_one("stdp3c_learner", 1, s, div=div, tag=tag,
                            period=tp["period"], report=tp["report"])
                grid["learner"][(tempo, div, s)] = summarize_run(r) if r["ok"] else None
                print(f"[EXP96] learner tempo={tempo} div={div} seed={s} ok={r['ok']}", flush=True)

    # per-tempo DIV-invariance re-check for the ablation (recorded, not assumed)
    invariance = {}
    for tempo, tp in TEMPOS.items():
        rc = run_one("nolearn_ablation", 1, SEEDS[0], div=64,
                     tag=f"exp96_{tempo}_div64invar" if tempo != "default" else "div32invar",
                     period=tp["period"] if tempo != "default" else 4000,
                     report=tp["report"])
        if tempo == "default":
            invariance[tempo] = "previously verified in Exp 94/94b (equal on recorded metrics)"
        else:
            invariance[tempo] = (summarize_run(rc) == grid["ablation"][(tempo, SEEDS[0])]) if rc["ok"] else None

    # assemble the map
    results = {}
    for tempo in TEMPOS:
        for div in DIVS:
            deltas = []
            for s in SEEDS:
                l = (grid["learner"].get((tempo, div, s)) or {}).get("swap_mix")
                a = (grid["ablation"].get((tempo, s)) or {}).get("swap_mix")
                deltas.append((l - a) if (l is not None and a is not None) else None)
            st = paired_permutation(deltas)
            abl = mean([(grid["ablation"].get((tempo, s)) or {}).get("swap_mix") for s in SEEDS])
            lrn = mean([(grid["learner"].get((tempo, div, s)) or {}).get("swap_mix") for s in SEEDS])
            results[f"{tempo}|div{div}"] = {
                "tempo": tempo, "div": div,
                "learner_swap_mix_mean": lrn,
                "ablation_swap_mix_mean": abl,
                "stats": st,
            }

    # nomination per pre-registered rule: largest mean delta within each tempo
    nomination = {}
    for tempo in TEMPOS:
        cands = [(k, v) for k, v in results.items() if v["tempo"] == tempo and v["stats"]]
        if not cands:
            nomination[tempo] = None
            continue
        cands.sort(key=lambda kv: (-(kv[1]["stats"]["mean_delta"]), kv[1]["stats"]["p_two_sided"]))
        best = cands[0]
        nomination[tempo] = {
            "combo": best[0],
            "mean_delta": best[1]["stats"]["mean_delta"],
            "p_two_sided": best[1]["stats"]["p_two_sided"],
            "all_combos_positive": all(v["stats"]["mean_delta"] > 0 for _, v in cands),
        }

    commit = None
    import subprocess
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    payload = {
        "experiment": "Exp 96 — Stability/Plasticity map (EXPLORATORY)",
        "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": commit,
        "instrument": "tests/remap_sandbox_probe.py @ 2026-07-31+drift-pin (TF1-certified)",
        "grid": {"divs": DIVS, "seeds": SEEDS, "ticks": TICKS,
                 "tempos": {k: v for k, v in TEMPOS.items()}},
        "ablation_div_invariance_per_tempo": invariance,
        "multiplicity": "EXPLORATORY — all p-values unadjusted; confirmatory target = Exp 97 "
                        "pre-registered nomination rule (largest mean delta per tempo).",
        "results": results,
        "nomination_per_tempo": nomination,
        "wall_seconds": round(time.time() - t_start, 1),
        "energy_basis": "cycles MEASURED natively per Rule 21.1 (Docs/Architecture/ENERGY_ACCOUNTING.md)",
    }
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1)
    print(f"[EXP96] map written to {OUT}")
    for tempo, nom in nomination.items():
        print(f"[EXP96] nomination tempo={tempo}: {nom}")


if __name__ == "__main__":
    main()
