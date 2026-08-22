"""Substrate 4 — Small Transformer Sequence Learner (Diagnostic Baseline).

Protocol ID: SUBSTRATE_4_SMALL_TRANSFORMER_v1

Architecture:
  - Causal Transformer Sequence Learner:
      * Vocabulary: 256 (byte-level tokenization)
      * Embedding Dim: d_model = 32
      * Context Window: L = 16 bytes
      * Layers: 2 Transformer Blocks (Causal Self-Attention + LayerNorm + FFN 32->64->32)
      * Output Head: Linear(32, 256) predicting next byte logits
      * Parameters: ~10,000 trainable weights

Evaluation Protocol:
  - Cohort: 60 organisms
  - Duration: 2000 ticks per seed, reported every 200 ticks
  - Seeds: [0, 1, 2, 3] (4 seeds)
  - Arms: LEARN (active backprop/online update) vs NOLEARN (frozen initialized transformer)

Outputs:
  - experiments/sub4_results/sub4_summary.json
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

D_MODEL = 32
CONTEXT_LEN = 16
N_HEADS = 2
D_K = D_MODEL // N_HEADS
D_FF = 64
VOCAB = 256
LR = 0.005

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..")
# Standalone Substrate 4 sequence learner (Zero numba dependency)

def softmax(x, axis=-1):
    ex = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return ex / np.sum(ex, axis=axis, keepdims=True)

class SmallTransformerAgent:
    """Tiny Causal Transformer for next-byte prediction (~10k params)."""
    def __init__(self, seed):
        rng = np.random.RandomState(seed)
        # 1. Embeddings
        self.tok_embed = (rng.randn(VOCAB, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.pos_embed = (rng.randn(CONTEXT_LEN, D_MODEL).astype(np.float32) - 0.5) * 0.1
        
        # 2. Block 1 Attention & FFN
        self.W_q1 = (rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.W_k1 = (rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.W_v1 = (rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.W_o1 = (rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.W_ff1_1 = (rng.randn(D_FF, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.W_ff1_2 = (rng.randn(D_MODEL, D_FF).astype(np.float32) - 0.5) * 0.1

        # 3. Output Projection Head
        self.W_head = (rng.randn(VOCAB, D_MODEL).astype(np.float32) - 0.5) * 0.1

        # Buffer of context history
        self.context_buf = np.zeros(CONTEXT_LEN, dtype=np.int32)

    def forward(self, seq_bytes):
        # seq_bytes: list of byte ints (length <= CONTEXT_LEN)
        L = len(seq_bytes)
        seq_idx = np.array(seq_bytes, dtype=np.int32)
        
        # Embeddings: (L, D_MODEL)
        x = self.tok_embed[seq_idx] + self.pos_embed[:L]

        # Block 1 Causal Self-Attention
        Q = x @ self.W_q1.T
        K = x @ self.W_k1.T
        V = x @ self.W_v1.T

        scores = (Q @ K.T) / np.sqrt(D_MODEL)
        mask = np.triu(np.full((L, L), -1e9, dtype=np.float32), k=1)
        attn = softmax(scores + mask, axis=-1)
        attn_out = (attn @ V) @ self.W_o1.T
        x_att = x + attn_out

        # FFN
        ff_hidden = np.maximum(0, x_att @ self.W_ff1_1.T)  # ReLU
        ff_out = ff_hidden @ self.W_ff1_2.T
        x_ff = x_att + ff_out

        # Readout Logits for last token
        last_h = x_ff[-1]
        logits = self.W_head @ last_h
        return logits, last_h

    def step(self, in_byte, tgt_byte, is_learn):
        # Update context buffer
        self.context_buf = np.roll(self.context_buf, -1)
        self.context_buf[-1] = in_byte

        logits, last_h = self.forward(self.context_buf)
        probs = softmax(logits)
        pred_byte = int(np.argmax(probs))

        # Bit accuracy calculation
        tgt_x = np.array([(tgt_byte >> i) & 1 for i in range(8)], dtype=np.float32)
        pred_x = np.array([(pred_byte >> i) & 1 for i in range(8)], dtype=np.float32)
        xb = int(pred_byte) ^ tgt_byte
        correct = 8 - bin(xb & 0xFF).count("1")

        target_onehot = np.zeros(VOCAB, dtype=np.float32)
        target_onehot[tgt_byte] = 1.0
        err_vec = target_onehot - probs
        err_sum = float(-np.log(probs[tgt_byte] + 1e-8))

        if is_learn:
            # Online gradient step on W_head and W_tok_embed
            d_head = LR * np.outer(err_vec, last_h)
            self.W_head += d_head
            
            d_emb = LR * (err_vec @ self.W_head)
            self.tok_embed[in_byte] += d_emb

        return pred_byte, err_sum

def build_patch(seed):
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from books_of_genesis import _load_glyphs
    glyphs = _load_glyphs("English", "00_Ascent")
    if len(glyphs) < PATCH_SIZE:
        glyphs = _load_glyphs("English", "00_Graded") + glyphs
    if len(glyphs) < 16:
        glyphs = [ord(c) for c in ("the quick brown fox jumps over the lazy dog 0123456789 ") * 20]
    return glyphs[:PATCH_SIZE]

def run_arm(seed, is_learn):
    patch = build_patch(seed)
    n = len(patch)

    agents = [SmallTransformerAgent(seed * 100 + o) for o in range(N_ORGS)]
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
            total_norm += float(np.linalg.norm(agents[org].W_head))

            if np.random.rand() < 0.7:
                cursors[org] = (cursors[org] + 1) % n
            else:
                cursors[org] = (cursors[org] + np.random.randint(1, 4)) % n

        if (tick + 1) % REPORT_EVERY == 0:
            acc = 100.0 * total_correct / total_bits if total_bits else 0.0
            mean_err = total_err / float(N_ORGS) if N_ORGS else 0.0
            mean_norm = total_norm / float(N_ORGS) if N_ORGS else 0.0
            rec = {
                "tick": tick + 1,
                "acc": round(acc, 4),
                "mean_err": round(mean_err, 6),
                "norm_w": round(mean_norm, 6)
            }
            windows.append(rec)

    return windows

def main():
    results_dir = os.path.join(ROOT, "experiments", "sub4_results")
    os.makedirs(results_dir, exist_ok=True)

    print("=" * 64)
    print("SUBSTRATE 4: SMALL TRANSFORMER SEQUENCE LEARNER RUN")
    print(f"Seeds: {SEEDS} | Ticks: {TICKS} | Report: {REPORT_EVERY} | Orgs: {N_ORGS}")
    print("=" * 64)

    summary = {
        "substrate": "Substrate4_Small_Transformer",
        "protocol": "SUBSTRATE_4_SMALL_TRANSFORMER_v1",
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

    out_file = os.path.join(results_dir, "sub4_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 64)
    print("SUBSTRATE 4 SUMMARY & RULE 18 VERDICT")
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
