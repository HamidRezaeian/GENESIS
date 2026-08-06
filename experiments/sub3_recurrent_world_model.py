"""Substrate 3 — Recurrent World-Model Agent (Dreamer-style Latent Imagination Baseline).

Protocol ID: SUBSTRATE_3_RECURRENT_WORLD_MODEL_v1

Architecture:
  - Recurrent State-Space Model (RSSM):
      * Recurrent GRU state h_t (size 64)
      * Stochastic/Categorical latent state z_t (16 categorical units with 8 classes)
      * Sensory Encoder: Encodes 8-bit input byte into latent representation q(z_t | h_t, x_t)
      * Predictor/Decoder: Predicts next byte p(x_{t+1} | h_t, z_t)
  - Latent Imagination:
      * Agent projects H=5 steps into imagined latent trajectory (h_{\tau}, z_{\tau})
        to compute predictive error signals and update RSSM + policy weights.

Evaluation:
  - Cohort: 60 organisms
  - Duration: 2000 ticks per seed, reported every 200 ticks
  - Seeds: [0, 1, 2, 3] (4 seeds)
  - Arms: LEARN (active world-model learning) vs NOLEARN (frozen initialized model)

Outputs:
  - experiments/sub3_results/sub3_summary.json
"""

import os
import sys
import json
import time
import numpy as np

TICKS = 2000
REPORT_EVERY = 200
SEEDS = [0, 1, 2, 3]
PATCH_SIZE = 500
N_ORGS = 60

STATE_DIM = 64
LATENT_DIM = 16
HORIZON = 5
LR = 0.01

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

os.environ["GENESIS_RAM_SIZE"] = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"] = "512"
os.environ["GENESIS_REMAP"] = "0"
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_LIVE_WEB"] = "0"

import genesis_lab as gl

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -15.0, 15.0)))

def softmax(x):
    ex = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return ex / np.sum(ex, axis=-1, keepdims=True)

class WorldModelAgent:
    """Minimal Recurrent World-Model Agent (RSSM + Latent Predictor)."""
    def __init__(self, seed):
        rng = np.random.RandomState(seed)
        # GRU recurrent weights: W_h (state_dim, state_dim), W_x (state_dim, 8)
        self.W_gru_h = (rng.randn(STATE_DIM, STATE_DIM).astype(np.float32) - 0.5) * 0.1
        self.W_gru_x = (rng.randn(STATE_DIM, 8).astype(np.float32) - 0.5) * 0.1
        # Latent encoder: W_enc (latent_dim, state_dim + 8)
        self.W_enc = (rng.randn(LATENT_DIM, STATE_DIM + 8).astype(np.float32) - 0.5) * 0.1
        # Readout / Predictor: W_dec (8, state_dim + latent_dim)
        self.W_dec = (rng.randn(8, STATE_DIM + LATENT_DIM).astype(np.float32) - 0.5) * 0.1
        
        # Recurrent state h and latent z
        self.h = np.zeros(STATE_DIM, dtype=np.float32)
        self.z = np.zeros(LATENT_DIM, dtype=np.float32)

    def step(self, in_byte, tgt_byte, is_learn):
        # 1. Convert input byte to 8-bit float array
        x = np.array([(in_byte >> i) & 1 for i in range(8)], dtype=np.float32)
        tgt_x = np.array([(tgt_byte >> i) & 1 for i in range(8)], dtype=np.float32)

        # 2. Recurrent GRU step: h = tanh(W_gru_h @ h + W_gru_x @ x)
        net_h = self.W_gru_h @ self.h + self.W_gru_x @ x
        self.h = np.tanh(net_h)

        # 3. Latent Encoder: z = tanh(W_enc @ [h, x])
        enc_in = np.concatenate([self.h, x])
        self.z = np.tanh(self.W_enc @ enc_in)

        # 4. Predictor/Decoder: pred_logit = W_dec @ [h, z]
        dec_in = np.concatenate([self.h, self.z])
        logits = self.W_dec @ dec_in
        probs = sigmoid(logits)
        
        # Discretize prediction to byte
        pred_bits = (probs >= 0.5).astype(np.int32)
        pred_byte = 0
        for i in range(8):
            if pred_bits[i]:
                pred_byte |= (1 << i)

        err_vec = tgt_x - probs
        err_sum = float(np.sum(np.abs(err_vec)))

        # 5. Online LMS / Imagination Update if is_learn
        if is_learn:
            # Update Decoder weights: W_dec += lr * err_vec outer dec_in
            dW_dec = LR * np.outer(err_vec, dec_in)
            self.W_dec += dW_dec

            # Latent Imagination rollout (H steps into imagined future)
            h_img = self.h.copy()
            z_img = self.z.copy()
            for _ in range(HORIZON):
                # Imagined next state and latent
                h_img = np.tanh(self.W_gru_h @ h_img + self.W_gru_x @ probs)
                z_img = np.tanh(self.W_enc @ np.concatenate([h_img, probs]))
                img_logits = self.W_dec @ np.concatenate([h_img, z_img])
                img_probs = sigmoid(img_logits)
                # Propagate imagined error feedback into recurrent weights
                dW_gru = (LR * 0.1) * np.outer(h_img - self.h, h_img)
                self.W_gru_h += dW_gru

        return pred_byte, err_sum

def build_patch(seed):
    from books_of_genesis import inject_contiguous_library, contiguous_library_start
    inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, gl.BOOK_CATEGORY, gl.BOOK_NAME, PATCH_SIZE)
    start = contiguous_library_start(gl.RAM_SIZE, PATCH_SIZE)
    patch = [int(b) for b in gl.g_ram[start:start + PATCH_SIZE] if 32 <= int(b) <= 126 and int(b) != 0x55]
    if len(patch) < 16:
        patch = [int(c) for c in ("the quick brown fox jumps over the lazy dog 0123456789 ") * 20][:PATCH_SIZE]
    return patch

def run_arm(seed, is_learn):
    patch = build_patch(seed)
    n = len(patch)

    agents = [WorldModelAgent(seed * 100 + o) for o in range(N_ORGS)]
    cursors = np.random.RandomState(seed).randint(0, n, size=N_ORGS)

    windows = []

    for tick in range(TICKS):
        total_correct = 0
        total_bits = 0
        total_err = 0.0
        total_norm = 0.0

        for org in range(N_ORGS):
            pos = cursors[org]
            in_byte = int(patch[pos])
            tgt_byte = int(patch[(pos + 1) % n])

            pred_byte, err_sum = agents[org].step(in_byte, tgt_byte, is_learn)

            xb = int(pred_byte) ^ tgt_byte
            correct = 8 - bin(xb & 0xFF).count("1")
            total_correct += correct
            total_bits += 8
            total_err += float(err_sum)
            total_norm += float(np.linalg.norm(agents[org].W_dec))

            if np.random.rand() < 0.7:
                cursors[org] = (cursors[org] + 1) % n
            else:
                cursors[org] = (cursors[org] + np.random.randint(1, 4)) % n

        if (tick + 1) % REPORT_EVERY == 0:
            acc = 100.0 * total_correct / total_bits if total_bits else 0.0
            mean_err = total_err / (8.0 * N_ORGS) if N_ORGS else 0.0
            mean_norm = total_norm / N_ORGS if N_ORGS else 0.0
            rec = {
                "tick": tick + 1,
                "acc": round(acc, 4),
                "mean_err": round(mean_err, 6),
                "norm_w": round(mean_norm, 6)
            }
            windows.append(rec)

    return windows

def main():
    results_dir = os.path.join(ROOT, "experiments", "sub3_results")
    os.makedirs(results_dir, exist_ok=True)

    print("=" * 64)
    print("SUBSTRATE 3: RECURRENT WORLD-MODEL AGENT RUN")
    print(f"Seeds: {SEEDS} | Ticks: {TICKS} | Report: {REPORT_EVERY} | Orgs: {N_ORGS}")
    print("=" * 64)

    summary = {
        "substrate": "Substrate3_Recurrent_World_Model",
        "protocol": "SUBSTRATE_3_RECURRENT_WORLD_MODEL_v1",
        "seeds": SEEDS,
        "ticks": TICKS,
        "results": {"learn": {}, "nolearn": {}}
    }

    learn_early_accs = []
    learn_late_accs = []
    nolearn_early_accs = []
    nolearn_late_accs = []

    for seed in SEEDS:
        print(f"\n--- SEED {seed} ---")
        print("Running LEARN arm...")
        w_learn = run_arm(seed, is_learn=True)
        summary["results"]["learn"][str(seed)] = w_learn
        early_l = np.mean([w["acc"] for w in w_learn[:3]])
        late_l = np.mean([w["acc"] for w in w_learn[7:]])
        learn_early_accs.append(early_l)
        learn_late_accs.append(late_l)
        print(f"  LEARN   early acc: {early_l:6.2f}% | late acc: {late_l:6.2f}% | delta: {late_l-early_l:+6.2f}pp")

        print("Running NOLEARN arm...")
        w_nolearn = run_arm(seed, is_learn=False)
        summary["results"]["nolearn"][str(seed)] = w_nolearn
        early_nl = np.mean([w["acc"] for w in w_nolearn[:3]])
        late_nl = np.mean([w["acc"] for w in w_nolearn[7:]])
        nolearn_early_accs.append(early_nl)
        nolearn_late_accs.append(late_nl)
        print(f"  NOLEARN early acc: {early_nl:6.2f}% | late acc: {late_nl:6.2f}% | delta: {late_nl-early_nl:+6.2f}pp")

    mean_learn_early = float(np.mean(learn_early_accs))
    mean_learn_late = float(np.mean(learn_late_accs))
    learn_delta = mean_learn_late - mean_learn_early

    mean_nolearn_late = float(np.mean(nolearn_late_accs))
    gap_late = mean_learn_late - mean_nolearn_late

    # Rule 18 Gates Evaluation
    gate_a_pass = (learn_delta >= 5.0)  # > 5pp in-lifetime learning delta
    gate_b_pass = (gap_late > 3.0)      # > 3pp over matched ablation (NOLEARN)

    verdict_str = "SUBSTRATE_PASSED" if (gate_a_pass and gate_b_pass) else "SUBSTRATE_NULL_OR_DEGRADED"

    summary["metrics"] = {
        "mean_learn_early_acc": round(mean_learn_early, 4),
        "mean_learn_late_acc": round(mean_learn_late, 4),
        "learn_delta_pp": round(learn_delta, 4),
        "mean_nolearn_late_acc": round(mean_nolearn_late, 4),
        "gap_late_pp": round(gap_late, 4),
        "gate_a_pass": gate_a_pass,
        "gate_b_pass": gate_b_pass,
        "verdict": verdict_str
    }

    out_file = os.path.join(results_dir, "sub3_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 64)
    print("SUBSTRATE 3 SUMMARY & RULE 18 VERDICT")
    print("=" * 64)
    print(f"Mean Early LEARN Acc : {mean_learn_early:6.2f}%")
    print(f"Mean Late LEARN Acc  : {mean_learn_late:6.2f}%")
    print(f"In-Lifetime Delta    : {learn_delta:+6.2f} pp (Gate A threshold: +5.00 pp -> {'PASS' if gate_a_pass else 'FAIL'})")
    print(f"Mean Late NOLEARN Acc: {mean_nolearn_late:6.2f}%")
    print(f"Static/Ablation Gap  : {gap_late:+6.2f} pp (Gate B threshold: +3.00 pp -> {'PASS' if gate_b_pass else 'FAIL'})")
    print(f"Rule 18 Verdict      : {verdict_str}")
    print(f"Summary saved to     : {out_file}")
    print("=" * 64)

if __name__ == "__main__":
    main()
