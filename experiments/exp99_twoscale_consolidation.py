"""Experiment 99 — CONFIRMATORY test of TWO-TIMESCALE CONSOLIDATION (substrate change).

PRE-REGISTERED (2026-08-02, committed BEFORE any seed-72..95 datum exists — binding).
This is the LAST mechanistic attempt under the triggered Rule-18 kill criterion
(Docs/Architecture/Ascent.md, recorded 2026-08-01: Exp 97 commit ad5b1f6, Exp 98 commit
1b426b5). If this experiment falsifies, the substrate hypothesis itself is falsified and
Rule 18 executes the substrate pivot — no further mechanism levers.

DIAGNOSIS CHAIN (binding record, Docs/Result.md):
  Exp 92b/94b/96: vanilla STDP3C shows ZERO re-tracking advantage over NOLEARN (replicated
      n=24) while ERODING static memory (unch_mix: NOLEARN 94.0 > every plastic arm).
  Exp 97: DIV×tempo tuning axis CLOSED (both nominated points failed, Bonferroni 0.025).
  Exp 98: surprise-GATED plasticity (when plasticity fires) mechanically reduces erosion
      (S2 +1.14, p=0.0001) but does NOT convert to advantage (primary +2.22, p=0.219) and
      does NOT reach the ≥95 static bar (93.2). Verdict: the missing advantage is NOT
      restored by controlling WHEN plasticity fires.
  Remaining registered candidate: WHERE plasticity persists. The current engine's only
      "slow" structure is the STATIC DNA birth-weight anchor g_conn_w_dna (homeostasis
      target, engine :2193) — it never consolidates. Every fast-weight change is either
      kept (churn → erosion) or pulled back to a birth prior that knows nothing learned
      in-lifetime. Two-timescale consolidation makes the anchor LEARN.

MECHANISM (implemented behind GENESIS_STDP_TWO_TIMESCALE, default OFF, documented at the
flag in src/neuromorphic_engine.py):
  New kernel state: g_conn_w_slow, (N_SYN,) float32, threaded world_tick_numba arg
  (kernel-WRITTEN state cannot be a module global — numba reads those by reference as
  read-only; the g_org_params pattern is host-written/kernel-read only and does NOT apply).
  Initialized at decode_genome to the DNA birth weight (== g_conn_w_dna at spawn).
    1. FAST weight w: unchanged STDP3C update (eligibility × per-bit credit, engine
       :2160-2202). Read path unchanged — the network reads w only.
    2. HOMEOSTASIS RETARGETED: when the flag is on, the anchor pull
       w -= p_homeo * (w - anchor) uses anchor = g_conn_w_slow[s_idx] instead of
       g_conn_w_dna[s_idx]. (Flag off: byte-identical default path, regression-guarded.)
    3. SLOW CONSOLIDATION at each REMAP-era boundary — the environment's own clock
       ((global_time % REMAP_PERIOD) < n_steps, the same boundary test the Exp-98 gate
       baseline uses, engine :2144):
           w_slow += (w - w_slow) / BITS_PER_BYTE
       Quantum = 1/8 of the gap per era: BITS_PER_BYTE is a hardware fact of the 8-bit
       substrate (Rule 17 — no new tuned constant; the consolidation rate is DERIVED, not
       searched). One era of consistent fast-weight evidence moves the slow anchor 1/8 of
       the way; noise that does not survive an era never consolidates.
  Charged like an STDP update per consolidated synapse (real work, Rule 21 honest
  accounting), activity-gated to era boundaries only.

WHY THIS OPTION (pre-registered rationale, adversarially reviewed 2026-08-02):
  (a) periodic fixed-rate consolidation — CHOSEN: fewest moving parts, smallest blast
      radius on the certified default path, easiest smoke-divergence proof, rate derived
      from hardware quantum (no knob to tune — the Exp-97 lesson: tuning axes die).
  (b) surprise-conditioned consolidation — REJECTED as primary: Exp 98 already showed
      gating by surprise reduces erosion without producing advantage; conditioning
      consolidation on the same signal confounds two mechanisms in one confirmatory row.
      Admissible ONLY as a follow-up if (a) shows signal.
  (c) dual eligibility traces from scratch — REJECTED: largest new-state surface, hardest
      to certify byte-identical default path, and the LAST mechanistic attempt must be the
      minimal decisive test, not the maximal one.

ARMS (remap=1, div=1, default tempo 4000/2000 — the certified ladder's operating point):
  twoscale = stdp3c_learner + GENESIS_STDP_TWO_TIMESCALE=1
  vanilla  = stdp3c_learner (+ flag explicitly 0; the Exp-97/98 NULL row's arm)
  nolearn  = nolearn_ablation (+ flag explicitly 0)

PRE-REGISTERED DECISION STRUCTURE — SEQUENTIAL GATE, NOT Bonferroni:
  GATE (certification, evaluated FIRST, NO alpha spent — a threshold on one arm's own
      mean, not a comparative hypothesis; same class as the G1/G2b completeness gates):
      mean twoscale unch_mix >= 95.0  (the registered erosion-kill bar, Exp 98)
      Gate FAIL => the mechanism is NOT CERTIFIED regardless of the primary statistic's
      sign or p-value; the two-timescale hypothesis is CLOSED at this locus (a stability
      mechanism that does not restore stability is nothing).
  PRIMARY (single comparative test, alpha = 0.05 two-sided, full alpha — no split, because
      the gate spends none; Exp-98 precedent: "no multiplicity correction needed" for a
      single candidate comparison):
      twoscale beats the matched NOLEARN ablation on swap-era accuracy (swap_mix).
      n=24 fresh seed pairs (72..95, NEVER used by any previous row — 48..71 burned by
      Exp 98), paired sign-flip permutation (exact n<=20, pinned-seed Monte-Carlo 10^5
      otherwise), gate G2b (swap eras measured) required.
  OUTCOMES (all binding and publishable, Rule 16):
      gate PASS + primary CONFIRMED (p<=0.05, delta>0): two-timescale consolidation is the
          first mechanism to show a certified learning advantage; advances to the
          Rule-18-A horizon question.
      gate PASS + primary NULL: stability without advantage == expensive NOLEARN; the
          two-timescale hypothesis is FALSIFIED at this locus => Rule 18 substrate pivot.
      gate FAIL: CLOSED as above => Rule 18 substrate pivot.
  SECONDARIES (recorded only, NO alpha spent — advisory):
      S1: twoscale vs vanilla swap-era delta (does consolidation itself move task
          performance?)
      S2: twoscale vs vanilla unch-era delta + per-arm mean static fidelity
      S3: weight_delta_absmax vs DNA per arm (consolidation displacement, instrument
          diagnostic via PROBE_DUMP_GATE opt-in, OFF in every measured row)

INSTRUMENTATION INHERITANCE (the Exp-98 lesson, Result.md:4520-4521 — binding BEFORE the
first measured row):
  1. GENESIS_STDP_TWO_TIMESCALE lands in src/compile_fingerprint.py KERNEL_STATE_VARS
     tuple + _mirror_values_from_env + ENV_NAME_MAP (the three-site pattern of
     STDP_SURPRISE_GATE at :88/:188/:319).
  2. Smoke-divergence proof: weight-hash trajectories of twoscale vs vanilla arms diverge
     (and flag-OFF is byte-identical to the committed certified raw JSONs) BEFORE any
     seed-72..95 run; tests/engine_defaultpath_regression_test.py gains
     env.pop("GENESIS_STDP_TWO_TIMESCALE", None) beside the Exp-98 pop (:53).
  3. New threaded arg g_conn_w_slow updates EVERY world_tick_numba call site (inventory
     2026-08-02: 40 sites — genesis_lab :1574/:1839, tests/remap_sandbox_probe.py :209,
     src/exp_stdp_target_ab_driver.py :54, exp68 :142, exp69 :194, exp78b :176/:245,
     root exp78..exp91 drivers, tests/* probes; the one stale site,
     tests/clusy/qwen/exp30_ablation/run_ablation.py :95, already predates the current
     signature and is out of scope).
  4. Instrument rev bump: tests/remap_sandbox_probe.py rev 2026-08-02+twoscale.

HYGIENE (identical discipline to Exp 97/98): no reuse cache (EXP92_TF1_REUSE_CACHE unset);
tag namespace `exp99_{arm}` (arm in tag prevents the raw-file collision that burned the
first Exp-98 pass); pinned geometry 512 organisms / 2 MiB RAM; seeded kernel+Python RNG;
8000 ticks.

Output: experiments/exp99_twoscale_results.json
Run: python experiments/exp99_twoscale_consolidation.py
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# CONFIRMATORY: no reuse, ever (see docstring)
os.environ["EXP92_TF1_REUSE_CACHE"] = "0"
# arm-level extra_env owns this flag
os.environ.pop("GENESIS_STDP_TWO_TIMESCALE", None)
# engine per-flag fingerprint pinning must stay sovereign
os.environ.pop("NUMBA_CACHE_DIR", None)
from exp92_tf1_leaderboard_runner import run_one, summarize_run, paired_permutation  # noqa: E402

SEEDS = [int(s) for s in os.environ.get("EXP99_SEEDS",
                                        ",".join(str(x) for x in range(72, 96))).split(",")]
ALPHA = float(os.environ.get("EXP99_ALPHA", "0.05"))
# registered bar, not a knob
FIDELITY_GATE = float(os.environ.get("EXP99_FIDELITY_GATE", "95.0"))
ARMS = {
    "twoscale": ("stdp3c_learner", {"GENESIS_STDP_TWO_TIMESCALE": "1"}),
    "vanilla":  ("stdp3c_learner", {"GENESIS_STDP_TWO_TIMESCALE": "0"}),
    "nolearn":  ("nolearn_ablation", {"GENESIS_STDP_TWO_TIMESCALE": "0"}),
}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "exp99_twoscale_results.json")


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
            # tag carries the arm name (Exp-98 raw-collision lesson: shared tags silently
            # OVERWRITE raws between arms sharing base "stdp3c_learner").
            r = run_one(base, 1, s, div=1, tag=f"exp99_{arm_name}", period=4000,
                        report=2000, extra_env=extra)
            ok_all = ok_all and r["ok"]
            per[(arm_name, s)] = summarize_run(r) if r["ok"] else None
            print(f"[EXP99] {arm_name} seed={s} ok={r['ok']}", flush=True)

    # SEQUENTIAL GATE FIRST (certification, no alpha spent — see docstring).
    gate_mean = (sum(per[("twoscale", s)]["unch_mix"] for s in SEEDS) / len(SEEDS)
                 if all(per.get(("twoscale", s)) for s in SEEDS) else None)
    gate_pass = bool(gate_mean is not None and gate_mean >= FIDELITY_GATE)

    primary_d = deltas(per, "twoscale", "nolearn", "swap_mix")
    st_primary = paired_permutation(primary_d)
    g2b = all(d is not None for d in primary_d)
    confirmed = bool(gate_pass and g2b and st_primary
                     and st_primary["p_two_sided"] <= ALPHA
                     and (st_primary["mean_delta"] or 0.0) > 0.0)

    if not gate_pass:
        verdict = "CLOSED_AT_GATE"          # stability not restored -> hypothesis closed
    elif confirmed:
        verdict = "CONFIRMED"               # first certified learning advantage
    else:
        verdict = "FALSIFIED_AT_LOCUS"      # stability without advantage -> Rule 18 pivot

    secondaries = {
        "S1_twoscale_minus_vanilla_swap": paired_permutation(deltas(per, "twoscale", "vanilla", "swap_mix")),
        "S2_twoscale_minus_vanilla_unch": paired_permutation(deltas(per, "twoscale", "vanilla", "unch_mix")),
        "static_fidelity_mean_unch_mix": {
            arm: (sum(per[(arm, s)]["unch_mix"] for s in SEEDS) / len(SEEDS)
                  if all(per.get((arm, s)) for s in SEEDS) else None)
            for arm in ARMS
        },
        "fidelity_gate": {"bar": FIDELITY_GATE, "twoscale_mean_unch_mix": gate_mean,
                          "PASS": gate_pass},
    }

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    payload = {
        "experiment": "Exp 99 — CONFIRMATORY two-timescale consolidation vs NOLEARN ablation",
        "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": commit,
        "instrument": "tests/remap_sandbox_probe.py @ 2026-08-02+twoscale",
        "seeds": SEEDS, "reuse_cache": False,
        "gate": {"kind": "certification_threshold_no_alpha",
                 "bar": FIDELITY_GATE, "twoscale_mean_unch_mix": gate_mean,
                 "PASS": gate_pass},
        "primary": {
            "comparison": "twoscale - nolearn on swap-era accuracy (swap_mix)",
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
        "verdict": verdict,
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
    print(
        f"[EXP99] GATE pass={gate_pass} (mean unch_mix={gate_mean} vs bar {FIDELITY_GATE})")
    print(f"[EXP99] PRIMARY mean_delta={payload['primary']['mean_delta']} "
          f"p={payload['primary']['p_two_sided']} CONFIRMED={confirmed} VERDICT={verdict}")
    print(f"[EXP99] results written to {OUT}")


if __name__ == "__main__":
    main()
