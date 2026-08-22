"""Substrate 4 — Staged Multi-Book Deep-Time 500,000-Tick Marathon.

Protocol ID: SUBSTRATE_4_DEEP_TIME_500K_MULTIBOOK_v1
Rule Reference: Rule 6 (Prime Directive), Rule 18 (Finish Line), Rule 24 (Deep-Time Stability)

Scope:
  Evaluates continual in-lifetime learning, non-interference, and asymptotic weight stability
  across 500,000 continuous world-ticks with 4 dynamic curriculum eras:
    - Era 1 (0k   .. 125k ticks): 00_Ascent (Cognitive Ramp: Bootstrap -> Successor -> Arithmetic)
    - Era 2 (125k .. 250k ticks): 01_Digits & 02_Addition (Compositional Arithmetic)
    - Era 3 (250k .. 375k ticks): 02_Basic_Words (Lexical Memory)
    - Era 4 (375k .. 500k ticks): 03_Phrases (Complex Syntax)

Telemetry:
  Reports progress and timing metrics every 25,000 ticks per worker.

Outputs:
  - experiments/sub4_results/sub4_500k_progress.json (live checkpoint)
  - experiments/sub4_results/sub4_500k_summary.json (final synthesis)
"""

import os
import sys
import json
import time
import math
import argparse
import numpy as np
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

TICKS = 500000
CHECKPOINT_INTERVAL = 25000
REPORT_EVERY = 2500
SEEDS = [100, 101, 102, 103]
N_ORGS = 20
PATCH_SIZE = 500

D_MODEL = 32
CONTEXT_LEN = 16
VOCAB = 256
LR = 0.005

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, _DIR)

from sub4_small_transformer import SmallTransformerAgent
from books_of_genesis import _load_glyphs

ERAS = [
    (0,      125000, "Era 1: 00_Ascent (Cognitive Ramp)",      ("English", "00_Ascent")),
    (125000, 250000, "Era 2: Math (Digits & Addition)",       ("Math", "02_Addition")),
    (250000, 375000, "Era 3: English (Basic Words)",          ("English", "02_Basic_Words")),
    (375000, 500000, "Era 4: English (Phrases & Syntax)",     ("English", "03_Phrases")),
]

def load_era_patch(category, book_name):
    glyphs = _load_glyphs(category, book_name)
    if len(glyphs) < PATCH_SIZE:
        glyphs = _load_glyphs("English", "00_Graded") + glyphs
    if len(glyphs) < 16:
        glyphs = [ord(c) for c in ("the quick brown fox jumps over the lazy dog 0123456789 ") * 20]
    return glyphs[:PATCH_SIZE]

T_CRIT = {
    1: 12.7062, 2: 4.3027, 3: 3.1824, 4: 2.7764, 5: 2.5706,
    6: 2.4469, 7: 2.3646, 8: 2.3060, 9: 2.2622, 10: 2.2281,
}

def ci95(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None, None, [None, None]
    m = float(np.mean(v))
    sd = float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
    n = len(v)
    if n < 2:
        return m, sd, [m, m]
    tcrit = T_CRIT.get(n - 1, 1.96)
    half = tcrit * sd / math.sqrt(n)
    return m, sd, [m - half, m + half]

def run_single_500k_arm(args):
    seed, is_learn, ticks, report_every, chk_interval, n_orgs = args
    arm_str = "LEARN" if is_learn else "NOLEARN"
    t_start = time.time()
    t_last_chk = t_start
    
    # Preload patches for all eras
    era_patches = [load_era_patch(cat, bname) for _, _, _, (cat, bname) in ERAS]
    
    agents = [SmallTransformerAgent(seed * 100 + o) for o in range(n_orgs)]
    cursors = [rng.randint(0, len(era_patches[0]) - 20) for rng in [np.random.RandomState(seed + o) for o in range(n_orgs)]]

    windows = []
    checkpoints = []
    
    initial_w_head_norm = float(np.mean([np.linalg.norm(a.W_head) for a in agents]))
    prev_w_head = [np.copy(a.W_head) for a in agents]

    current_era_idx = 0
    patch = era_patches[current_era_idx]
    n_patch = len(patch)

    total_correct = 0
    total_bits = 0
    total_err = 0.0

    print(f"[{datetime.now().strftime('%H:%M:%S')}] START [{arm_str} Seed={seed}] Total Ticks={ticks} | Cohort={n_orgs}", flush=True)

    for tick in range(ticks):
        # Check era transition
        if current_era_idx < len(ERAS) - 1 and tick >= ERAS[current_era_idx + 1][0]:
            current_era_idx += 1
            patch = era_patches[current_era_idx]
            n_patch = len(patch)
            for o in range(n_orgs):
                cursors[o] = cursors[o] % (n_patch - 1)

        for org in range(n_orgs):
            pos = cursors[org]
            in_byte = int(patch[pos])
            tgt_byte = int(patch[(pos + 1) % n_patch])

            pred_byte, err_sum = agents[org].step(in_byte, tgt_byte, is_learn)

            xb = int(pred_byte) ^ tgt_byte
            correct = 8 - bin(xb & 0xFF).count("1")
            total_correct += correct
            total_bits += 8
            total_err += float(err_sum)

            if np.random.rand() < 0.7:
                cursors[org] = (cursors[org] + 1) % n_patch
            else:
                cursors[org] = (cursors[org] + np.random.randint(1, 4)) % n_patch

        # Sample window
        if (tick + 1) % report_every == 0:
            acc = 100.0 * total_correct / total_bits if total_bits else 0.0
            mean_loss = total_err / float(n_orgs) if n_orgs else 0.0
            curr_w_norm = float(np.mean([np.linalg.norm(a.W_head) for a in agents]))
            displacement = float(np.mean([np.linalg.norm(a.W_head - prev_w_head[i]) for i, a in enumerate(agents)]))
            prev_w_head = [np.copy(a.W_head) for a in agents]

            rec = {
                "tick": tick + 1,
                "era": ERAS[current_era_idx][2],
                "acc": round(acc, 4),
                "loss": round(mean_loss, 4),
                "w_head_norm": round(curr_w_norm, 4),
                "w_displacement": round(displacement, 4)
            }
            windows.append(rec)
            total_correct = 0
            total_bits = 0
            total_err = 0.0

        # Milestone Checkpoint every 25,000 ticks
        if (tick + 1) % chk_interval == 0:
            now = time.time()
            elapsed_total = now - t_start
            elapsed_interval = now - t_last_chk
            t_last_chk = now
            
            rate = chk_interval / max(elapsed_interval, 1e-6)
            remaining_ticks = ticks - (tick + 1)
            eta_seconds = remaining_ticks / max(rate, 1e-6)
            
            recent_acc = np.mean([w["acc"] for w in windows[-max(1, chk_interval // report_every):]])
            recent_loss = np.mean([w["loss"] for w in windows[-max(1, chk_interval // report_every):]])
            curr_w_norm = float(np.mean([np.linalg.norm(a.W_head) for a in agents]))
            
            chk_record = {
                "tick": tick + 1,
                "era": ERAS[current_era_idx][2],
                "acc": round(float(recent_acc), 2),
                "loss": round(float(recent_loss), 3),
                "w_norm": round(curr_w_norm, 2),
                "elapsed_total_s": round(elapsed_total, 1),
                "interval_time_s": round(elapsed_interval, 1),
                "rate_ticks_per_s": round(rate, 1),
                "eta_s": round(eta_seconds, 1)
            }
            checkpoints.append(chk_record)
            
            # Print prominent progress line requested by user
            timestamp_str = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp_str}] [CHECKPOINT {tick+1:6d}/{ticks} ticks] [{arm_str} s={seed}] | "
                  f"Era: {ERAS[current_era_idx][2]} | Acc: {recent_acc:6.2f}% | Loss: {recent_loss:5.3f} | "
                  f"||W||: {curr_w_norm:5.2f} | Interval: {elapsed_interval:5.1f}s | "
                  f"Rate: {rate:6.1f} t/s | Total Elapsed: {elapsed_total/60.0:4.1f} min | ETA: {eta_seconds/60.0:4.1f} min",
                  flush=True)

    elapsed_total = time.time() - t_start
    early_acc = float(np.mean([w["acc"] for w in windows[:5]]))
    late_acc = float(np.mean([w["acc"] for w in windows[-5:]]))
    delta_pp = late_acc - early_acc
    final_w_norm = float(np.mean([np.linalg.norm(a.W_head) for a in agents]))

    print(f"[{datetime.now().strftime('%H:%M:%S')}] FINISHED [{arm_str} Seed={seed}] in {elapsed_total/60.0:.2f} min | Early={early_acc:.2f}% | Late={late_acc:.2f}% | Delta={delta_pp:+.2f}pp | ||W||={final_w_norm:.2f}", flush=True)

    return {
        "seed": seed,
        "is_learn": is_learn,
        "ticks": ticks,
        "elapsed_s": round(elapsed_total, 2),
        "early_acc": round(early_acc, 4),
        "late_acc": round(late_acc, 4),
        "delta_pp": round(delta_pp, 4),
        "initial_head_norm": round(initial_w_head_norm, 4),
        "final_head_norm": round(final_w_norm, 4),
        "checkpoints": checkpoints,
        "windows": windows
    }

def main():
    parser = argparse.ArgumentParser(description="Substrate 4 500,000-Tick Multi-Book Marathon Runner")
    parser.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    parser.add_argument("--ticks", type=int, default=TICKS)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    out_dir = os.path.join(ROOT, "experiments", "sub4_results")
    os.makedirs(out_dir, exist_ok=True)

    print("=" * 80, flush=True)
    print("GENESIS SUBSTRATE 4 — MULTI-BOOK DEEP-TIME 500,000-TICK MARATHON (Rule 18 / Rule 24)", flush=True)
    print(f"Seeds: {args.seeds} | Ticks: {args.ticks} | Workers: {args.workers} | Checkpoint: Every {CHECKPOINT_INTERVAL} ticks", flush=True)
    print(f"Eras: {[e[2] for e in ERAS]}", flush=True)
    print("=" * 80, flush=True)

    work_items = []
    for s in args.seeds:
        work_items.append((s, True, args.ticks, REPORT_EVERY, CHECKPOINT_INTERVAL, N_ORGS))   # LEARN
        work_items.append((s, False, args.ticks, REPORT_EVERY, CHECKPOINT_INTERVAL, N_ORGS))  # NOLEARN

    t_start = time.time()
    results = {"learn": {}, "nolearn": {}}

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_single_500k_arm, w): w for w in work_items}
        for fut in as_completed(futures):
            r = fut.result()
            arm_key = "learn" if r["is_learn"] else "nolearn"
            results[arm_key][r["seed"]] = r
            
            # Save intermediate summary after every completed arm
            temp_file = os.path.join(out_dir, "sub4_500k_progress.json")
            with open(temp_file, "w") as f:
                json.dump(results, f, indent=2)

    total_time = time.time() - t_start

    learn_res = [results["learn"][s] for s in args.seeds]
    nolearn_res = [results["nolearn"][s] for s in args.seeds]

    learn_lates = [r["late_acc"] for r in learn_res]
    nolearn_lates = [r["late_acc"] for r in nolearn_res]
    learn_deltas = [r["delta_pp"] for r in learn_res]
    ablation_gaps = [learn_lates[i] - nolearn_lates[i] for i in range(len(args.seeds))]

    m_gap, _, ci_gap = ci95(ablation_gaps)
    m_delta, _, ci_delta = ci95(learn_deltas)

    final_norms = [r["final_head_norm"] for r in learn_res]
    norm_pass = all(n < 100.0 for n in final_norms)
    b_pass = (m_gap >= 20.0 and ci_gap[0] > 0)

    all_passed = b_pass and norm_pass

    print("\n" + "=" * 80, flush=True)
    print("500,000-TICK MARATHON SYNTHESIS SCORECARD (Rule 18 Milestone)", flush=True)
    print("=" * 80, flush=True)
    print(f"  Mean LEARN Late Acc:      {np.mean(learn_lates):6.2f}%", flush=True)
    print(f"  Mean NOLEARN Late Acc:    {np.mean(nolearn_lates):6.2f}%", flush=True)
    print(f"  Ablation Gap (B-Screen):  {m_gap:+6.2f} pp [95% CI: {ci_gap[0]:+.2f}, {ci_gap[1]:+.2f}] -> {'PASS' if b_pass else 'FAIL'}", flush=True)
    print(f"  In-Run Delta (A-Screen):  {m_delta:+6.2f} pp [95% CI: {ci_delta[0]:+.2f}, {ci_delta[1]:+.2f}]", flush=True)
    print(f"  Weight Norm Stability:    mean={np.mean(final_norms):.2f} (max={max(final_norms):.2f}) -> {'PASS' if norm_pass else 'FAIL'}", flush=True)
    print("=" * 80, flush=True)
    print(f"Overall 500k Marathon:      {'CERTIFIED_500K_DEEP_TIME_PASS' if all_passed else 'DEEP_TIME_WARNING'}", flush=True)
    print(f"Total Execution Time:       {total_time/60.0:.2f} minutes ({total_time:.1f}s)", flush=True)
    print("=" * 80, flush=True)

    summary_data = {
        "protocol": "SUBSTRATE_4_DEEP_TIME_500K_MULTIBOOK_v1",
        "seeds": args.seeds,
        "ticks": args.ticks,
        "cohort_size": N_ORGS,
        "total_wall_time_s": round(total_time, 2),
        "mean_learn_late": round(float(np.mean(learn_lates)), 4),
        "mean_nolearn_late": round(float(np.mean(nolearn_lates)), 4),
        "ablation_gap": {
            "mean": round(m_gap, 4),
            "ci95": [round(ci_gap[0], 4), round(ci_gap[1], 4)],
            "pass": b_pass
        },
        "weight_norm_stability": {
            "mean_final_norm": round(float(np.mean(final_norms)), 4),
            "max_final_norm": round(float(max(final_norms)), 4),
            "pass": norm_pass
        },
        "overall_marathon_pass": all_passed,
        "learn_runs": {str(s): results["learn"][s] for s in args.seeds},
        "nolearn_runs": {str(s): results["nolearn"][s] for s in args.seeds}
    }

    out_file = os.path.join(out_dir, "sub4_500k_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"\nFull 500k synthesis saved -> {out_file}", flush=True)

if __name__ == "__main__":
    main()
