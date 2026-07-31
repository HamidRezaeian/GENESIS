"""Experiment 98 — CONFIRMATORY test of SURPRISE-GATED plasticity (mechanism change).

PRE-REGISTERED (2026-07-31, committed BEFORE any seed-48..71 datum exists — binding).
The mechanism-change clause of Exp 97's verdict (Docs/Result.md): with the DIV×tempo tuning
axis CLOSED (both nominated points failed confirmation, n=24, fresh seeds), the next test
must change the MECHANISM, not the knobs. This is that test.

MECHANISM (implemented behind GENESIS_STDP_SURPRISE_GATE, default OFF, documented at the
flag in src/neuromorphic_engine.py):
    dopamine_gated = net - era_local_baseline(net)
where the baseline is the organism's own cumulative mean of read-correctness `net` since the
last REMAP-era boundary (horizon = the environment's own REMAP_PERIOD clock; no new constant,
Rule 17). The per-vocal-bit credit channel (org_elig) is advantage-gated the same way
(v2 — gating only the scalar dopamine left the dominant per-bit channel vanilla; smoke-verified
byte-divergent 2026-07-31). Rationale: on mastered input net ≈ baseline → update ≈ 0 → the
measured static-memory erosion dies; on an era switch, performance drops below the collapsed
baseline → depression of the stale mapping, then re-acquisition rises above it → potentiation
of the new mapping. Plasticity fades IN during transients (where credit matters) and OFF at
steady state.

ARMS (remap=1, div=1, default tempo 4000/2000 — the certified ladder's operating point):
  gated   = stdp3c_learner + GENESIS_STDP_SURPRISE_GATE=1
  vanilla = stdp3c_learner (+ flag explicitly 0; the Exp-97 NULL row's arm)
  nolearn = nolearn_ablation (+ flag explicitly 0)

PRE-REGISTERED DECISION STRUCTURE:
  PRIMARY test (single, alpha = 0.05 two-sided — no multiplicity correction needed):
      gated beats the matched NOLEARN ablation on swap-era accuracy (Rule-18 Ascent-B shape:
      a plasticity mechanism must beat its matched ablation to count as learning-advantage).
      n=24 fresh seed pairs (48..71, NEVER used by any previous row), paired sign-flip
      permutation (branch per code: exact n<=20, pinned-seed Monte-Carlo 10^5 draws otherwise),
      CONFIRMED iff completeness + G2b (swap eras measured) + p_two_sided <= 0.05.
  SECONDARY (recorded only, NO alpha spent — advisory for the next design):
      S1: gated vs vanilla swap-era delta (does the gate itself change task performance?)
      S2: gated vs vanilla unch-era delta + per-arm mean static fidelity unch_mix
          (the erosion-kill endpoint; certified G1/G4 static band reference is the
          REMAP=0 ladder — mean unch_mix >= 95% is the registered erosion-kill bar)
  All outcomes binding and publishable (Rule 16): CONFIRMED advances the mechanism to the
  Rule-18-A horizon question; NOT confirmed closes the gating hypothesis at THIS locus and
  forces the next substrate-hypothesis change per Rule 18's clause.

HYGIENE (identical discipline to Exp 97): no reuse cache (EXP92_TF1_REUSE_CACHE unset;
tag namespace `exp98_` cannot collide); pinned geometry 512 organisms / 2 MiB RAM; seeded
kernel+Python RNG; 8000 ticks. Instrument: tests/remap_sandbox_probe.py rev
2026-07-31+drift-pin+gate-diag (the gate_diag block is opt-in via PROBE_DUMP_GATE and OFF in
every measured row; tests/engine_defaultpath_regression_test.py certifies byte-identity of
the default path against the committed certified raw JSONs).

Output: experiments/exp98_gated_results.json
Run: python experiments/exp98_gated_plasticity.py
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["EXP92_TF1_REUSE_CACHE"] = "0"  # CONFIRMATORY: no reuse, ever (see docstring)
os.environ.pop("GENESIS_STDP_SURPRISE_GATE", None)  # arm-level extra_env owns this flag
os.environ.pop("NUMBA_CACHE_DIR", None)  # engine per-flag fingerprint pinning must stay sovereign
from exp92_tf1_leaderboard_runner import run_one, summarize_run, paired_permutation  # noqa: E402

SEEDS = [int(s) for s in os.environ.get("EXP98_SEEDS",
        ",".join(str(x) for x in range(48, 72))).split(",")]
ALPHA = float(os.environ.get("EXP98_ALPHA", "0.05"))
ARMS = {
    "gated":   ("stdp3c_learner", {"GENESIS_STDP_SURPRISE_GATE": "1"}),
    "vanilla": ("stdp3c_learner", {"GENESIS_STDP_SURPRISE_GATE": "0"}),
    "nolearn": ("nolearn_ablation", {"GENESIS_STDP_SURPRISE_GATE": "0"}),
}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp98_gated_results.json")


def deltas(per, arm_a, arm_b, key):
    """Per-seed paired endpoint deltas arm_a - arm_b on metric key (None if either missing)."""
    out = []
    for s in SEEDS:
        a = (per.get((arm_a, s)) or {}).get(key)
        b = (per.get((arm_b, s)) or {}).get(key)
        out.append((a - b) if (a is not None and b is not None) else None)
    return out


def main():
    t0 = time.time()
    per = {}
    ok_all = True
    for arm_name, (base, extra) in ARMS.items():
        for s in SEEDS:
            r = run_one(base, 1, s, div=1, tag="exp98", period=4000, report=2000,
                        extra_env=extra)
            ok_all = ok_all and r["ok"]
            per[(arm_name, s)] = summarize_run(r) if r["ok"] else None
            print(f"[EXP98] {arm_name} seed={s} ok={r['ok']}", flush=True)

    primary_d = deltas(per, "gated", "nolearn", "swap_mix")
    st_primary = paired_permutation(primary_d)
    g2b = all(d is not None for d in primary_d)
    confirmed = bool(g2b and st_primary and st_primary["p_two_sided"] <= ALPHA)

    secondaries = {
        "S1_gated_minus_vanilla_swap": paired_permutation(deltas(per, "gated", "vanilla", "swap_mix")),
        "S2_gated_minus_vanilla_unch": paired_permutation(deltas(per, "gated", "vanilla", "unch_mix")),
        "static_fidelity_mean_unch_mix": {
            arm: (sum(per[(arm, s)]["unch_mix"] for s in SEEDS) / len(SEEDS)
                  if all(per.get((arm, s)) for s in SEEDS) else None)
            for arm in ARMS
        },
        "erosion_kill_bar": "mean gated unch_mix >= 95.0 (registered, advisory only)",
    }

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    payload = {
        "experiment": "Exp 98 — CONFIRMATORY surprise-gated plasticity vs NOLEARN ablation",
        "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": commit,
        "instrument": "tests/remap_sandbox_probe.py @ 2026-07-31+drift-pin+gate-diag",
        "seeds": SEEDS, "reuse_cache": False,
        "primary": {
            "comparison": "gated - nolearn on swap-era accuracy (swap_mix)",
            "alpha_two_sided": ALPHA,
            "n_pairs": (st_primary or {}).get("n_pairs"),
            "mean_delta": (st_primary or {}).get("mean_delta"),
            "median_delta": (st_primary or {}).get("median_delta"),
            "per_seed_deltas": (st_primary or {}).get("per_seed_deltas"),
            "p_two_sided": (st_primary or {}).get("p_two_sided"),
            "method": (st_primary or {}).get("method"),
            "gate_G2b_swap_measured": g2b,
            "CONFIRMED": confirmed,
        },
        "secondaries_recorded_only_no_alpha": secondaries,
        "per_arm_per_seed_metrics": {
            f"{arm}|seed{s}": per.get((arm, s)) for arm in ARMS for s in SEEDS
        },
        "gates": {"completeness_all_runs_ok": ok_all},
        "wall_seconds": round(time.time() - t0, 1),
        "energy_basis": "cycles MEASURED natively per Rule 21.1 (Docs/Architecture/ENERGY_ACCOUNTING.md)",
    }
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1)
    print(f"[EXP98] PRIMARY mean_delta={payload['primary']['mean_delta']} "
          f"p={payload['primary']['p_two_sided']} CONFIRMED={confirmed}")
    print(f"[EXP98] results written to {OUT}")


if __name__ == "__main__":
    main()
