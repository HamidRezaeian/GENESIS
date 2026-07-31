"""Experiment 97 — CONFIRMATORY test at the two Exp-96-nominated operating points.

PRE-REGISTERED (2026-07-31, committed BEFORE any seed-24..47 datum exists — binding):

  Targets (nominated by Exp 96's registered rule, largest mean paired delta per tempo):
    T1: (GENESIS_STDP_DIV=32, default tempo: REMAP_PERIOD 4000 / PROBE_REPORT 2000)
    T2: (GENESIS_STDP_DIV=1,  fast tempo:    REMAP_PERIOD 2000 / PROBE_REPORT 1000)

  Confirmatory-hygiene override (supersedes the reuse clause in Exp 96's docstring, recorded
  in Docs/Result.md Exp 96): Exp 96's nominations DEPENDED on seeds 0-7, so those seeds are
  election data, not confirmation data. This test uses ENTIRELY FRESH seeds 24..47
  (EXP97_SEEDS), n=24 pairs per target; nothing is reused from any previous row (the reuse
  cache is disabled here: EXP97 never sets EXP92_TF1_REUSE_CACHE; a stale file with these
  tags cannot exist by construction — tag namespace `exp97_`).

  Per target: learner (STDP3C) vs matched NOLEARN ablation, both run per seed — matched
  pairing, no cross-DIV ablation sharing, so the DIV-invariance question does not arise in
  the confirmatory comparison itself (one invariance check per tempo is still run and
  RECORDED for the file). 8000 ticks, pinned geometry (512 organisms / 2 MiB RAM), seeded
  kernel+Python RNG, energy+position pinned. Endpoint: swap-era accuracy delta per seed pair;
  test: paired sign-flip permutation (code branch: exact enumeration n<=20, pinned-seed
  Monte-Carlo 10^5 draws otherwise — the method string is recorded verbatim after the
  Exp-94b wording audit).

  Multiplicity: TWO confirmatory tests -> Bonferroni: a target CONFIRMS iff
  p_two_sided <= 0.025. Gates: completeness (all 96 planned runs ok) and G2b (swap eras
  measured) and static-sanity note (G1 static band is tempo- and DIV-independent; refer to
  the certified n=24 REMAP=0 ladder). Outcomes bound regardless of sign (Rule 16).

Output: experiments/exp97_confirmatory_results.json
Run: python experiments/exp97_confirmatory.py
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["EXP92_TF1_REUSE_CACHE"] = "0"  # CONFIRMATORY: no reuse, ever (see docstring)
from exp92_tf1_leaderboard_runner import run_one, summarize_run, paired_permutation  # noqa: E402

SEEDS = [int(s) for s in os.environ.get("EXP97_SEEDS",
        ",".join(str(x) for x in range(24, 48))).split(",")]
ALPHA = float(os.environ.get("EXP97_ALPHA_BONFERRONI", "0.025"))
TARGETS = {
    "default_div32": {"div": 32, "period": 4000, "report": 2000, "tempo": "default"},
    "fast_div1": {"div": 1, "period": 2000, "report": 1000, "tempo": "fast"},
}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp97_confirmatory_results.json")


def main():
    t0 = time.time()
    per = {}
    ok_all = True
    for name, t in TARGETS.items():
        for arm in ("stdp3c_learner", "nolearn_ablation"):
            for s in SEEDS:
                r = run_one(arm, 1, s, div=t["div"], tag=f"exp97_{name}",
                            period=t["period"], report=t["report"])
                ok_all = ok_all and r["ok"]
                per[(name, arm, s)] = summarize_run(r) if r["ok"] else None
                print(f"[EXP97] {name} {arm} seed={s} ok={r['ok']}", flush=True)

    # recorded-only invariance checks (not part of the confirmatory pairing)
    invariance = {}
    for name, t in TARGETS.items():
        rc = run_one("nolearn_ablation", 1, SEEDS[0], div=64, tag=f"exp97_{name}_invar64",
                     period=t["period"], report=t["report"])
        invariance[name] = (summarize_run(rc) == per[(name, "nolearn_ablation", SEEDS[0])]) if rc["ok"] else None

    targets_out = {}
    for name in TARGETS:
        deltas = []
        for s in SEEDS:
            l = (per.get((name, "stdp3c_learner", s)) or {}).get("swap_mix")
            a = (per.get((name, "nolearn_ablation", s)) or {}).get("swap_mix")
            deltas.append((l - a) if (l is not None and a is not None) else None)
        st = paired_permutation(deltas)
        g2b = all(d is not None for d in deltas)
        confirmed = bool(g2b and st and st["p_two_sided"] <= ALPHA)
        targets_out[name] = {
            "config": TARGETS[name],
            "n_pairs": (st or {}).get("n_pairs"),
            "mean_delta": (st or {}).get("mean_delta"),
            "median_delta": (st or {}).get("median_delta"),
            "per_seed_deltas": (st or {}).get("per_seed_deltas"),
            "p_two_sided": (st or {}).get("p_two_sided"),
            "method": (st or {}).get("method"),
            "gate_G2b_swap_measured": g2b,
            "bonferroni_alpha": ALPHA,
            "CONFIRMED": confirmed,
        }
        print(f"[EXP97] {name}: delta={targets_out[name]['mean_delta']} "
              f"p={targets_out[name]['p_two_sided']} CONFIRMED={confirmed}", flush=True)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    payload = {
        "experiment": "Exp 97 — CONFIRMATORY at Exp-96-nominated operating points",
        "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": commit,
        "instrument": "tests/remap_sandbox_probe.py @ 2026-07-31+drift-pin",
        "seeds": SEEDS, "reuse_cache": False,
        "multiplicity": "two confirmatory tests, Bonferroni alpha=0.025 each, two-sided",
        "gates": {"completeness_all_runs_ok": ok_all},
        "ablation_div_invariance_recorded_only": invariance,
        "targets": targets_out,
        "wall_seconds": round(time.time() - t0, 1),
        "energy_basis": "cycles MEASURED natively per Rule 21.1 (Docs/Architecture/ENERGY_ACCOUNTING.md)",
    }
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1)
    print(f"[EXP97] results written to {OUT}")


if __name__ == "__main__":
    main()
