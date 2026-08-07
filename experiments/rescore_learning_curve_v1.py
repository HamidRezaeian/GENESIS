#!/usr/bin/env python3
"""
rescore_learning_curve_v1.py — Re-score existing substrate artifacts under the
corrected Gate A operationalization.

Protocol:  SUBSTRATE_4_LEARNING_CURVE_v1
Amendment: Docs/Architecture/SUBSTRATE_4_LEARNING_CURVE_v1.md (pre-registered,
           binding). This script implements the FROZEN definitions D1-D7 and the
           binding decision table (amendment §4). No definition here may be
           changed after re-scored values are observed (Rule 2); any change
           requires a new pre-registered amendment.

Reads existing artifacts UNMODIFIED (Rule 8 provenance) and writes NEW files:
  - experiments/<dir>/<name>_rescored_v1.json   (one per source artifact)
  - experiments/rescored_summary_v1.json        (machine-readable aggregate,
                                                 amendment §3.2 step 4)
  - experiments/RESCORE_AGGREGATE_SUMMARY_v1.md (human-readable report)

Dependencies: numpy + Python stdlib only (amendment §3.2 step 1).

Verdict-input mapping (frozen here, BEFORE first run; disclosed in every output):
  - static artifacts     : T = D3 slope CI>0 ; M = D4 rho >= 0.25 ; B = paired late gap CI>0
  - novel_switch artifact: T = D3 slope CI>0 (global; sawtooth caveat) ;
                           M = D6 rho_B under the D4 bar (amendment-explicit) ;
                           B = D6(iii) paired B-phase late gap CI>0
  - nonstationary        : T = D3 slope CI>0 (global; conservative on reset curves) ;
                           M = D4 rho (global endpoints) ; B = paired late gap CI>0.
                           D5 is the informative existence statistic for this
                           artifact and is reported alongside (amendment D5).
Decision-table precedence (frozen): (M and not T) -> INSTRUMENT_SUSPECT_F4;
  B not decisively positive with (T or M) -> INSTRUMENT_SUSPECT_F4; B not
  decisively positive with neither -> NULL (F4 audit flag recorded); otherwise
  the amendment §4 rows apply verbatim.
"""

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

PROTOCOL_ID = "SUBSTRATE_4_LEARNING_CURVE_v1"
SCRIPT_ID = "experiments/rescore_learning_curve_v1.py"
RHO_BAR = 0.25           # D4 magnitude bar (Rule 18's 25%, applied in error space)
PERM_DRAWS = 10_000      # D7 paired permutation Monte-Carlo draws
PERM_SEED = 0            # fixed RNG seed for the permutation draws (reproducibility)
FRESH_SEEDS = list(range(100, 108))   # D8 confirmatory seed range

REPO_ROOT = Path(__file__).resolve().parents[1]

# Two-sided 95% Student-t critical values, df 1..30 (stdlib-only substitute for scipy).
T_CRIT = {
    1: 12.7062, 2: 4.3027, 3: 3.1824, 4: 2.7764, 5: 2.5706,
    6: 2.4469, 7: 2.3646, 8: 2.3060, 9: 2.2622, 10: 2.2281,
    11: 2.2010, 12: 2.1788, 13: 2.1604, 14: 2.1448, 15: 2.1314,
    16: 2.1199, 17: 2.1098, 18: 2.1009, 19: 2.0930, 20: 2.0860,
    21: 2.0796, 22: 2.0739, 23: 2.0687, 24: 2.0639, 25: 2.0595,
    26: 2.0555, 27: 2.0518, 28: 2.0484, 29: 2.0452, 30: 2.0423,
}


def git_sha():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------- statistics (D7)

def mean_sd(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None, None
    m = float(np.mean(v))
    sd = float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
    return m, sd


def ci95(vals):
    """mean, sd, [lo, hi] 95% Student-t CI."""
    m, sd = mean_sd(vals)
    if m is None:
        return None, None, [None, None]
    n = len([x for x in vals if x is not None])
    if n < 2:
        return m, sd, [m, m]
    tcrit = T_CRIT.get(n - 1, 1.96)
    half = tcrit * sd / math.sqrt(n)
    return m, sd, [m - half, m + half]


def paired_t(vals):
    m, sd = mean_sd(vals)
    if m is None:
        return None
    n = len([x for x in vals if x is not None])
    if n < 2 or sd == 0.0:
        return math.inf if m > 0 else (-math.inf if m < 0 else 0.0)
    return m / (sd / math.sqrt(n))


def perm_p(vals, draws=PERM_DRAWS, seed=PERM_SEED):
    """Paired sign-flip permutation p (two-sided), Monte-Carlo estimate.

    Reported as an MC estimate, never as an 'exact' enumeration
    (Docs/RESUME_NEXT_SESSION.md Session 18 wording correction).
    """
    v = np.array([x for x in vals if x is not None], dtype=float)
    if v.size < 2:
        return None
    obs = abs(float(v.mean()))
    if obs == 0.0:
        return 1.0
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(draws, v.size))
    sims = np.abs((signs * v).mean(axis=1))
    return float((1 + np.count_nonzero(sims >= obs - 1e-12)) / (1 + draws))


def stats_block(vals):
    m, sd, (lo, hi) = ci95(vals)
    n = len([x for x in vals if x is not None])
    return {
        "n": n,
        "mean": m,
        "sd": sd,
        "ci95": [lo, hi],
        "t_vs_0": paired_t(vals),
        "df": (n - 1) if n >= 2 else None,
        "perm_p_mc": perm_p(vals),
        "perm_note": ("paired sign-flip Monte-Carlo, "
                      f"{PERM_DRAWS} draws, rng seed {PERM_SEED}; MC estimate, not exact"),
    }


def ols_slope(y):
    """OLS slope of y on window index x = 0..W-1 (D3)."""
    x = np.arange(len(y), dtype=float)
    xm = x.mean()
    ym = float(np.mean(y))
    denom = float(((x - xm) ** 2).sum())
    if denom == 0.0:
        return 0.0
    return float(((x - xm) * (np.asarray(y, dtype=float) - ym)).sum() / denom)


# ---------------------------------------------------------------- artifact loading

def load_summary_artifact(path):
    """sub*-style summary: results.learn[seed][i].acc / results.nolearn[seed][i].acc (D1)."""
    d = json.loads(path.read_text())
    learn = {int(s): [r["acc"] for r in recs] for s, recs in d["results"]["learn"].items()}
    nolearn = {int(s): [r["acc"] for r in recs] for s, recs in d["results"]["nolearn"].items()}
    raw = d["results"]["learn"]
    patterns = None
    first_recs = raw[sorted(raw, key=int)[0]]
    if "pattern" in first_recs[0]:
        patterns = {int(s): [r["pattern"] for r in recs] for s, recs in raw.items()}
    meta = {
        "substrate": d.get("substrate"),
        "source_protocol": d.get("protocol"),
        "ticks": d.get("ticks"),
        "seeds": [int(s) for s in d.get("seeds", sorted(learn))],
        "metrics": d.get("metrics", {}),
        "switch_every": d.get("switch_every"),
        "switch_tick": d.get("switch_tick"),
    }
    return learn, nolearn, patterns, meta


def load_perseed_artifact(dirpath, summary_name):
    """exp103-style: one JSON per arm per seed with a `samples` window log."""
    learn, nolearn = {}, {}
    files = sorted(p for p in dirpath.glob("*.json") if not p.name.endswith("_summary.json")
                   and "_rescored_" not in p.name)
    for p in files:
        d = json.loads(p.read_text())
        arm = str(d.get("arm", "")).lower()
        seed = int(d["seed"])
        series = [s["acc"] for s in d["samples"]]
        if arm in ("learner", "perorg", "learn"):
            learn[seed] = series
        elif arm == "nolearn":
            nolearn[seed] = series
    summary = json.loads((dirpath / summary_name).read_text())
    meta = {
        "substrate": summary.get("protocol"),
        "source_protocol": summary.get("protocol"),
        "ticks": summary.get("ticks"),
        "seeds": sorted(learn),
        "metrics": {
            "mean_learn_early_acc": summary.get("mean_learner_early_acc"),
            "mean_learn_late_acc": summary.get("mean_learner_late_acc"),
            "learn_delta_pp": summary.get("mean_learner_delta_pp"),
            "mean_nolearn_late_acc": summary.get("mean_nolearn_late_acc"),
            "gap_late_pp": summary.get("gap_late_pp"),
            "verdict": summary.get("verdict"),
        },
        "switch_every": None,
        "switch_tick": None,
    }
    return learn, nolearn, None, meta, [p.name for p in files] + [summary_name]


# ------------------------------------------------------------- core computations

def endpoints(series):
    """D2: C0 = mean first 3 windows, C1 = mean last 3 windows; E = 100 - C."""
    c0 = float(np.mean(series[:3]))
    c1 = float(np.mean(series[-3:]))
    return c0, c1, 100.0 - c0, 100.0 - c1


def safe_rho(e0, e1):
    """D4: rho = (E0 - E1)/E0 ; undefined (None) if E0 <= 0."""
    if e0 is None or e0 <= 0.0:
        return None
    return (e0 - e1) / e0


def rho_trajectory(series, c0, e0):
    """Per-window error-space reduction rho_w = (E0 - E(w))/E0 (descriptive curve)."""
    if e0 <= 0.0:
        return [None] * len(series)
    return [((e0 - (100.0 - a)) / e0) for a in series]


def detect_task(meta, patterns):
    if patterns is None:
        return "static"
    seed0 = sorted(patterns)[0]
    vals = patterns[seed0]
    if all(isinstance(v, str) for v in vals):
        return "novel_switch"
    return "nonstationary"


def phases_from_patterns(patterns_one_seed):
    """Consecutive same-pattern chunks -> list of (start, end) window index spans."""
    spans = []
    start = 0
    for i in range(1, len(patterns_one_seed)):
        if patterns_one_seed[i] != patterns_one_seed[start]:
            spans.append((start, i))
            start = i
    spans.append((start, len(patterns_one_seed)))
    return spans


def d5_relearning(learn, nolearn, patterns):
    """D5: within-phase re-learning on post-switch phases.

    Per phase p (post-switch only, primary): delta_p = mean(last 2 windows of p)
    - first window of p. Per-seed mean over phases; across-seed D7 stats.
    Robustness (pre-registered): all-phase variant; last-window-only variant.
    NOLEARM paired phases provide the ablation reference.
    """
    def per_seed(series_map, use_all_phases=False, last_only=False):
        out = {}
        for s, series in series_map.items():
            spans = phases_from_patterns(patterns[s])
            use = spans if use_all_phases else spans[1:]
            ds = []
            for (a, b) in use:
                onset = series[a]
                achieved = series[b - 1] if last_only else float(np.mean(series[max(a, b - 2):b]))
                ds.append(achieved - onset)
            out[s] = float(np.mean(ds)) if ds else None
        return out

    primary_l = per_seed(learn)
    allphase_l = per_seed(learn, use_all_phases=True)
    lastonly_l = per_seed(learn, last_only=True)
    primary_n = per_seed(nolearn)
    return {
        "definition": ("post-switch phases only; delta_p = mean(last 2 windows of phase) "
                       "- first window of phase; per-seed mean over phases"),
        "learn_per_seed": primary_l,
        "learn_across_seeds": stats_block(list(primary_l.values())),
        "nolearn_per_seed": primary_n,
        "nolearn_across_seeds": stats_block(list(primary_n.values())),
        "robustness_all_phases": stats_block(list(allphase_l.values())),
        "robustness_last_window_only": stats_block(list(lastonly_l.values())),
    }


def d6_transfer(learn, nolearn, patterns):
    """D6: A->B transfer. retention = B0 - A_late ; rho_B = (E(B0)-E(B_late))/E(B0)
    under the D4 bar ; gap_B = B_late - NOLEARN B_late (paired)."""
    per_seed = {}
    for s in learn:
        a_idx = [i for i, p in enumerate(patterns[s]) if p == "A"]
        b_idx = [i for i, p in enumerate(patterns[s]) if p == "B"]
        series, nseries = learn[s], nolearn[s]
        a_late = float(np.mean([series[i] for i in a_idx[-3:]]))
        b0 = series[b_idx[0]]
        b_late = float(np.mean([series[i] for i in b_idx[-3:]]))
        nb_late = float(np.mean([nseries[i] for i in b_idx[-3:]]))
        per_seed[s] = {
            "A_late": a_late,
            "B0_first_window": b0,
            "B_late": b_late,
            "retention_pp": b0 - a_late,
            "rho_B": safe_rho(100.0 - b0, 100.0 - b_late),
            "gap_B_pp": b_late - nb_late,
        }
    return {
        "definition": ("A_late = mean last 3 A-windows; B0 = first B window; "
                       "B_late = mean last 3 B-windows; rho_B under the D4 bar"),
        "per_seed": per_seed,
        "retention_across_seeds": stats_block([v["retention_pp"] for v in per_seed.values()]),
        "rho_B_across_seeds": stats_block([v["rho_B"] for v in per_seed.values()]),
        "gap_B_across_seeds": stats_block([v["gap_B_pp"] for v in per_seed.values()]),
    }


# ----------------------------------------------------------------- rescore driver

def rescore_artifact(name, source_files, learn, nolearn, patterns, meta):
    task = detect_task(meta, patterns)
    seeds = sorted(learn)
    ticks = meta.get("ticks") or 0
    n_win = len(learn[seeds[0]])
    window_ticks = ticks // n_win if n_win else None

    per_seed = []
    for s in seeds:
        series = learn[s]
        c0, c1, e0, e1 = endpoints(series)
        slope_w = ols_slope(series)
        nl_c1 = float(np.mean(nolearn[s][-3:]))
        rec = {
            "seed": s,
            "C0_first3": c0, "C1_last3": c1,
            "E0": e0, "E1": e1,
            "delta_pp": c1 - c0,                                   # D3 secondary
            "rho": safe_rho(e0, e1),                               # D4
            "slope_pp_per_window": slope_w,                        # D3 primary
            "slope_pp_per_1000ticks": (slope_w * 1000.0 / window_ticks
                                       if window_ticks else None),
            "rho_trajectory_per_window": rho_trajectory(series, c0, e0),
            "nolearn_C1_last3": nl_c1,
            "paired_gap_late_pp": c1 - nl_c1,                      # B (paired)
        }
        per_seed.append(rec)

    deltas = [r["delta_pp"] for r in per_seed]
    rhos = [r["rho"] for r in per_seed]
    slopes = [r["slope_pp_per_window"] for r in per_seed]
    gaps = [r["paired_gap_late_pp"] for r in per_seed]

    across = {
        "delta_pp": stats_block(deltas),
        "rho": stats_block(rhos),
        "slope_pp_per_window": stats_block(slopes),
        "gate_b_gap_pp": stats_block(gaps),
    }

    d5 = d5_relearning(learn, nolearn, patterns) if task == "nonstationary" else None
    d6 = d6_transfer(learn, nolearn, patterns) if task == "novel_switch" else None

    # ---- Gate tests (amendment §4; verdict-input mapping frozen in module docstring)
    slope_b = across["slope_pp_per_window"]
    T = bool(slope_b["ci95"][0] is not None and slope_b["ci95"][0] > 0.0)

    if task == "novel_switch":
        m_stats = d6["rho_B_across_seeds"]
        m_used = "D6 rho_B under D4 bar"
    else:
        m_stats = across["rho"]
        m_used = "D4 rho (global endpoints)"
    M = bool(m_stats["mean"] is not None and m_stats["mean"] >= RHO_BAR
             and m_stats["ci95"][0] is not None and m_stats["ci95"][0] > 0.0)

    if task == "novel_switch":
        b_stats = d6["gap_B_across_seeds"]
    else:
        b_stats = across["gate_b_gap_pp"]
    blo, bhi = b_stats["ci95"]
    B = bool(blo is not None and blo > 0.0)
    B_state = "pass" if B else ("negative" if (bhi is not None and bhi < 0.0)
                                else "indeterminate")

    d_lo, d_hi = across["delta_pp"]["ci95"]
    F1 = bool(not T and d_lo is not None and d_lo <= 0.0 <= d_hi)
    rho_hi = m_stats["ci95"][1]
    F2 = bool(rho_hi is not None and rho_hi < RHO_BAR)
    F3 = bool((not T) and B_state == "pass")
    F4 = bool((M and not T) or B_state != "pass")

    # ---- decision table (precedence frozen in module docstring)
    if M and not T:
        verdict = "INSTRUMENT_SUSPECT_F4"
    elif B_state != "pass":
        verdict = "INSTRUMENT_SUSPECT_F4" if (T or M) else "NULL"
    elif T and M:
        verdict = "GATE_A_SCREEN_PASS_CORRECTED"
    elif T and not M:
        verdict = "REAL_BUT_NEGLIGIBLE_F2"
    else:
        verdict = "STATIC_ONLY_F3"
    confirmatory = verdict == "GATE_A_SCREEN_PASS_CORRECTED"

    # ---- aggregate cross-check against already-published metrics (amendment §3.3)
    pm = meta.get("metrics", {})
    xcheck = None
    pe, pl = pm.get("mean_learn_early_acc"), pm.get("mean_learn_late_acc")
    if pe is not None and pl is not None and (100.0 - pe) > 0:
        rho_agg = ((100.0 - pe) - (100.0 - pl)) / (100.0 - pe)
        rho_seed_mean = across["rho"]["mean"]
        xcheck = {
            "published_early": pe, "published_late": pl,
            "rho_from_published_aggregates": rho_agg,
            "rho_per_seed_mean": rho_seed_mean,
            "abs_discrepancy": (abs(rho_agg - rho_seed_mean)
                                if rho_seed_mean is not None else None),
            "note": ("aggregate rho is arithmetic on already-published metrics; "
                     "per-seed mean is the binding D7 quantity"),
        }

    notes = []
    if task in ("nonstationary", "novel_switch"):
        notes.append("global slope/rho on a reset curve are conservative; see "
                     + ("D5 within-phase re-learning" if task == "nonstationary"
                        else "D6 transfer statistics"))
    if B_state != "pass":
        notes.append("F4: Gate B paired gap CI not decisively positive -> Rule 20 audit "
                     "before any claim (see amendment §4)")
    notes.append("re-analysis of n=4 existing seeds; confirmatory claims require "
                 "fresh seeds 100-107 to n>=8 (amendment D8)")

    return {
        "protocol": PROTOCOL_ID,
        "rescored_by": SCRIPT_ID,
        "git_sha": GIT_SHA,
        "artifact": name,
        "source_files": source_files,
        "originals_untouched": True,
        "task_type": task,
        "substrate": meta.get("substrate"),
        "source_protocol": meta.get("source_protocol"),
        "ticks": ticks,
        "n_windows": n_win,
        "window_ticks": window_ticks,
        "seeds": seeds,
        "historical_verdict_fields": {
            k: pm.get(k) for k in ("gate_a_pass", "gate_b_pass", "verdict")
            if k in pm
        },
        "per_seed": per_seed,
        "across_seeds": across,
        "D5_within_phase_relearning": d5,
        "D6_transfer": d6,
        "gate_tests": {
            "T_slope_positive": T,
            "M_magnitude": M,
            "M_statistic_used": m_used,
            "B_gate_gap": B,
            "B_state": B_state,
            "F1_learning_real_falsified": F1,
            "F2_nonnegligible_falsified": F2,
            "F3_static_only": F3,
            "F4_instrument_alarm": F4,
        },
        "verdict": verdict,
        "confirmatory_run_required": confirmatory,
        "confirmatory_protocol": ({
            "fresh_seeds": FRESH_SEEDS, "min_total_n": 8,
            "driver": "original protocol ID, unchanged",
            "reference": "amendment D8; Exp 96->97 anti-winner's-curse precedent",
        } if confirmatory else None),
        "aggregate_crosscheck": xcheck,
        "notes": notes,
    }


# -------------------------------------------------------------------- sanitizing

def sanitize(o):
    if isinstance(o, dict):
        return {k: sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [sanitize(v) for v in o]
    if isinstance(o, float):
        if math.isnan(o) or math.isinf(o):
            return None if math.isnan(o) else (1e308 if o > 0 else -1e308)
        return round(o, 4)
    return o


def dump(obj, path):
    path.write_text(json.dumps(sanitize(obj), indent=2, allow_nan=False) + "\n")


# ------------------------------------------------------------------ MD report

def fmt_ci(b, scale=1.0, unit=""):
    if b["mean"] is None:
        return "n/a"
    lo, hi = b["ci95"]
    return f"{b['mean']*scale:+.3f} [{lo*scale:+.3f}, {hi*scale:+.3f}]{unit}"


def build_md(rows, sha):
    L = []
    L.append("# Re-Score Aggregate Summary — Corrected Gate A (Amendment v1)")
    L.append("")
    L.append(f"**Protocol:** `{PROTOCOL_ID}`  ")
    L.append(f"**Script:** `{SCRIPT_ID}`  ")
    L.append(f"**Git SHA at re-score:** `{sha}`  ")
    L.append("**Status:** RE-ANALYSIS of existing artifacts under the pre-registered amendment "
             "`Docs/Architecture/SUBSTRATE_4_LEARNING_CURVE_v1.md`. Originals untouched (Rule 8); "
             "all outputs are NEW files. n=4 existing seeds per artifact — diagnostic only; "
             "confirmatory claims require fresh seeds 100–107 to n ≥ 8 (amendment D8).")
    L.append("")
    L.append("Corrected Gate A screen (frozen): **T** = OLS slope of window accuracy, 95% CI > 0 "
             "(D3); **M** = error-space relative reduction ρ = (E0−E1)/E0 ≥ 0.25 with CI > 0 "
             "(D4; for the novel-switch artifact M uses ρ_B per D6); **B** = LEARN−NOLEARN "
             "paired late gap, 95% CI > 0 (D7). Decision table: amendment §4.")
    L.append("")
    L.append("## 1. Decision table — one row per artifact (binding)")
    L.append("")
    L.append("| Artifact | Task | Ticks | Δ (late−early), pp [95% CI] | Slope, pp/1k ticks [95% CI] "
             "| ρ (M stat) [95% CI] | Gate B gap, pp [95% CI] | T | M | B | F flags | Verdict "
             "| Confirmatory |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        a = r["across_seeds"]
        wtick = r["window_ticks"] or 1000
        slope1k = dict(a["slope_pp_per_window"])
        scale = 1000.0 / wtick
        slope1k = {"mean": a["slope_pp_per_window"]["mean"] and a["slope_pp_per_window"]["mean"]*scale,
                   "ci95": [c and c*scale for c in a["slope_pp_per_window"]["ci95"]]}
        if r["task_type"] == "novel_switch":
            mstat = r["D6_transfer"]["rho_B_across_seeds"]
            bstat = r["D6_transfer"]["gap_B_across_seeds"]
        else:
            mstat = a["rho"]
            bstat = a["gate_b_gap_pp"]
        g = r["gate_tests"]
        flags = "".join(k for k, v in (("F1", g["F1_learning_real_falsified"]),
                                       ("F2", g["F2_nonnegligible_falsified"]),
                                       ("F3", g["F3_static_only"]),
                                       ("F4", g["F4_instrument_alarm"])) if v) or "—"
        confirm = "**YES — fresh seeds 100–107**" if r["confirmatory_run_required"] else "no"
        L.append(f"| {r['artifact']} | {r['task_type']} | {r['ticks']} "
                 f"| {fmt_ci(a['delta_pp'])} | {fmt_ci(slope1k)} "
                 f"| {fmt_ci(mstat)} | {fmt_ci(bstat)} "
                 f"| {'✓' if g['T_slope_positive'] else '✗'} | {'✓' if g['M_magnitude'] else '✗'} "
                 f"| {'✓' if g['B_gate_gap'] else '✗'} | {flags} | **{r['verdict']}** | {confirm} |")
    L.append("")
    L.append("Verdict legend (amendment §4): `GATE_A_SCREEN_PASS_CORRECTED` → substrate viability "
             "re-opened, confirmatory run required; `REAL_BUT_NEGLIGIBLE_F2` → rise real but ρ < 25%, "
             "Paper v2 conclusion stands; `STATIC_ONLY_F3` → in-lifetime-learning claim withdrawn "
             "for the artifact (Exp 103 pattern); `NULL` → remains Gate-A-negative; "
             "`INSTRUMENT_SUSPECT_F4` → Rule 20 audit before any claim.")
    L.append("")
    # D5 section
    d5_rows = [r for r in rows if r["D5_within_phase_relearning"]]
    if d5_rows:
        L.append("## 2. D5 — within-phase re-learning (non-stationary artifact)")
        L.append("")
        for r in d5_rows:
            d5 = r["D5_within_phase_relearning"]
            L.append(f"**{r['artifact']}** — {d5['definition']}:")
            L.append("")
            L.append("| seed | LEARN re-learning Δ, pp | NOLEARN Δ, pp |")
            L.append("|---|---|---|")
            for s in r["seeds"]:
                L.append(f"| {s} | {d5['learn_per_seed'][s]:+.3f} "
                         f"| {d5['nolearn_per_seed'][s]:+.3f} |")
            L.append("")
            L.append(f"- LEARN across seeds: {fmt_ci(d5['learn_across_seeds'])} pp, "
                     f"t = {d5['learn_across_seeds']['t_vs_0']:.2f}, "
                     f"permutation p ≈ {d5['learn_across_seeds']['perm_p_mc']:.4f} (MC)")
            L.append(f"- NOLEARN across seeds: {fmt_ci(d5['nolearn_across_seeds'])} pp")
            L.append(f"- Robustness (pre-registered): all-phases "
                     f"{fmt_ci(d5['robustness_all_phases'])} pp; last-window-only "
                     f"{fmt_ci(d5['robustness_last_window_only'])} pp")
            L.append("")
    # D6 section
    d6_rows = [r for r in rows if r["D6_transfer"]]
    if d6_rows:
        L.append("## 3. D6 — novel-sequence transfer (A→B)")
        L.append("")
        for r in d6_rows:
            d6 = r["D6_transfer"]
            L.append(f"**{r['artifact']}** — {d6['definition']}:")
            L.append("")
            L.append("| seed | A_late | B0 | B_late | retention, pp | ρ_B | gap_B, pp |")
            L.append("|---|---|---|---|---|---|---|")
            for s, v in d6["per_seed"].items():
                L.append(f"| {s} | {v['A_late']:.2f} | {v['B0_first_window']:.2f} "
                         f"| {v['B_late']:.2f} | {v['retention_pp']:+.3f} "
                         f"| {v['rho_B'] if v['rho_B'] is not None else float('nan'):.4f} "
                         f"| {v['gap_B_pp']:+.3f} |")
            L.append("")
            L.append(f"- retention: {fmt_ci(d6['retention_across_seeds'])} pp "
                     "(≤ 0 expected; catastrophic-interference reference)")
            L.append(f"- ρ_B: {fmt_ci(d6['rho_B_across_seeds'])} (bar: ≥ 0.25)")
            L.append(f"- gap_B (paired, Gate B continuity): {fmt_ci(d6['gap_B_across_seeds'])} pp")
            L.append("")
    # Cross-check
    L.append("## 4. Worked-example validation & aggregate cross-check")
    L.append("")
    L.append("Amendment §3.3 worked example: sub4-20k ρ from published aggregates = 26.79% "
             "(E0 = 13.8021, E1 = 10.1042). Binding per-seed recomputation below; discrepancies "
             "are the expected Jensen gap between an aggregate-of-means and a mean-of-ratios and "
             "are documented, not smoothed over.")
    L.append("")
    L.append("| Artifact | ρ from published aggregates | ρ per-seed mean (binding) "
             "| abs discrepancy |")
    L.append("|---|---|---|---|")
    for r in rows:
        xc = r.get("aggregate_crosscheck")
        if xc:
            L.append(f"| {r['artifact']} | {xc['rho_from_published_aggregates']*100:.2f}% "
                     f"| {xc['rho_per_seed_mean']*100:.2f}% "
                     f"| {xc['abs_discrepancy']*100:.2f}pp |")
    L.append("")
    # Confirmatory + scope
    passes = [r["artifact"] for r in rows if r["confirmatory_run_required"]]
    L.append("## 5. Confirmatory-run requirements (amendment D8)")
    L.append("")
    if passes:
        L.append(f"Artifacts passing the corrected Gate A screen: **{', '.join(passes)}**.")
        L.append("Per D8, a confirmatory run is REQUIRED before any viability claim: fresh seeds "
                 "100–107 (as many as needed for n ≥ 8 total, minimum 4), original driver protocol "
                 "IDs unchanged, NOLEARN arm re-run on the same fresh seeds for pairing, result-cache "
                 "reuse disabled (Exp 96→97 anti-winner's-curse precedent).")
    else:
        L.append("No artifact passed the corrected Gate A screen; no confirmatory runs triggered.")
    L.append("")
    L.append("## 6. What this re-scoring does NOT change")
    L.append("")
    L.append("- Exp 99's SNN-on-RAM substrate falsification stands (independent, executed "
             "kill criterion).")
    L.append("- `Ascent.md` §2 / Rule 18 finish line unchanged; the staged pilot "
             "(`SUBSTRATE_4_STAGED_PILOT_v1`) remains the only instrument for the 5M question.")
    L.append("- All verdicts here are re-analysis of n=4 seeds — diagnostic, not confirmatory "
             "(Rule 3). Historical `gate_a_pass`/`verdict` fields in the source artifacts remain "
             "as recorded under the retired proxy.")
    L.append("")
    return "\n".join(L)


# ------------------------------------------------------------------------ main

GIT_SHA = git_sha()


def main():
    exp = REPO_ROOT / "experiments"
    jobs = [
        # (artifact name, kind, path, summary_name_for_perseed)
        ("sub3_summary", "summary", exp / "sub3_results" / "sub3_summary.json", None),
        ("sub4_summary", "summary", exp / "sub4_results" / "sub4_summary.json", None),
        ("sub4_20k_summary", "summary", exp / "sub4_results" / "sub4_20k_summary.json", None),
        ("sub4_nonstationary_summary", "summary",
         exp / "sub4_results" / "sub4_nonstationary_summary.json", None),
        ("sub4_novel_summary", "summary", exp / "sub4_results" / "sub4_novel_summary.json", None),
        ("sub5_summary", "summary", exp / "sub5_results" / "sub5_summary.json", None),
        ("exp103_full", "perseed", exp / "exp103_results", "exp103_full_summary.json"),
        ("exp103b_full", "perseed", exp / "exp103b_results", "exp103b_full_summary.json"),
    ]

    rows = []
    for name, kind, path, summ in jobs:
        if kind == "summary":
            learn, nolearn, patterns, meta = load_summary_artifact(path)
            sources = [str(path.relative_to(REPO_ROOT))]
        else:
            learn, nolearn, patterns, meta, srcs = load_perseed_artifact(path, summ)
            sources = [str((path / s).relative_to(REPO_ROOT)) for s in srcs]
        row = rescore_artifact(name, sources, learn, nolearn, patterns, meta)
        rows.append(row)
        out_path = (path if kind == "perseed" else path.parent) / f"{name}_rescored_v1.json"
        dump(row, out_path)
        g = row["gate_tests"]
        print(f"{name:32s} T={int(g['T_slope_positive'])} M={int(g['M_magnitude'])} "
              f"B={int(g['B_gate_gap'])} -> {row['verdict']}"
              + ("  [CONFIRMATORY REQUIRED]" if row["confirmatory_run_required"] else ""))
        print(f"  wrote {out_path.relative_to(REPO_ROOT)}")

    aggregate = {
        "protocol": PROTOCOL_ID,
        "rescored_by": SCRIPT_ID,
        "git_sha": GIT_SHA,
        "originals_untouched": True,
        "rho_bar": RHO_BAR,
        "perm_draws": PERM_DRAWS,
        "perm_seed": PERM_SEED,
        "artifacts": rows,
        "decision_table_reference": "Docs/Architecture/SUBSTRATE_4_LEARNING_CURVE_v1.md §4",
        "confirmatory_seed_rule": "amendment D8: fresh seeds 100-107, n>=8, reuse disabled",
    }
    dump(aggregate, exp / "rescored_summary_v1.json")
    print("  wrote experiments/rescored_summary_v1.json")

    md = build_md(rows, GIT_SHA)
    (exp / "RESCORE_AGGREGATE_SUMMARY_v1.md").write_text(md)
    print("  wrote experiments/RESCORE_AGGREGATE_SUMMARY_v1.md")


if __name__ == "__main__":
    sys.exit(main())
