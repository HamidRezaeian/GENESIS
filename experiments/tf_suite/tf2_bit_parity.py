"""Task Family 2 (TF2) — Dynamic Bit Parity (Logical / XOR Reasoning).

Protocol ID: TF2_BIT_PARITY_v1
Task Definition:
  The agent is presented with sequences of binary digits b_1, b_2, ..., b_K (K in [4, 16])
  followed by a query token '?'. The target next token is the exact parity bit:
    y = sum(b_i) mod 2  in {0, 1}

Cognitive Capacity:
  Tests temporal non-linear XOR computation and working-memory integration across
  variable-length contextual tokens.
"""

import os
import sys
import numpy as np

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "experiments"))

from sub4_plus_agent import Substrate4PlusAgent as SmallTransformerAgent

TOK_0 = 48    # ASCII '0'
TOK_1 = 49    # ASCII '1'
TOK_Q = 63    # ASCII '?'
TOK_SEP = 32  # ASCII ' '

def generate_parity_stream(seed, n_samples=5000, min_len=4, max_len=16):
    rng = np.random.RandomState(seed)
    stream = []
    query_positions = []
    
    for _ in range(n_samples):
        k = rng.randint(min_len, max_len + 1)
        bits = rng.randint(0, 2, size=k)
        parity = int(np.sum(bits) % 2)
        
        # Sequence format: b0 b1 ... bK ? parity [SEP]
        for b in bits:
            stream.append(TOK_0 if b == 0 else TOK_1)
        stream.append(TOK_Q)
        query_positions.append(len(stream) - 1)
        stream.append(TOK_0 if parity == 0 else TOK_1)
        stream.append(TOK_SEP)
        
    return stream, set(query_positions)

def run_tf2_arm(seed, ticks=10000, report_every=1000, is_learn=True, n_orgs=30):
    stream, query_set = generate_parity_stream(seed, n_samples=ticks // 4)
    n = len(stream)
    
    agents = [SmallTransformerAgent(seed * 200 + o) for o in range(n_orgs)]
    cursors = [rng.randint(0, n - 20) for rng in [np.random.RandomState(seed + o) for o in range(n_orgs)]]
    
    windows = []
    q_correct = 0
    q_total = 0
    
    for tick in range(ticks):
        for org in range(n_orgs):
            pos = cursors[org]
            in_byte = stream[pos]
            tgt_byte = stream[(pos + 1) % n]
            
            pred_byte, _ = agents[org].step(in_byte, tgt_byte, is_learn=is_learn)
            
            # Check if this step was predicting after a query token '?'
            if in_byte == TOK_Q:
                q_total += 1
                if pred_byte == tgt_byte:
                    q_correct += 1
                    
            cursors[org] = (cursors[org] + 1) % (n - 1)
            
        if (tick + 1) % report_every == 0:
            acc = 100.0 * q_correct / q_total if q_total > 0 else 50.0
            windows.append({"tick": tick + 1, "query_acc": round(acc, 4), "samples": q_total})
            q_correct = 0
            q_total = 0
            
    early_acc = float(np.mean([w["query_acc"] for w in windows[:3]]))
    late_acc = float(np.mean([w["query_acc"] for w in windows[-3:]]))
    delta_pp = late_acc - early_acc
    
    return {
        "task": "TF2_BIT_PARITY",
        "seed": seed,
        "is_learn": is_learn,
        "early_acc": early_acc,
        "late_acc": late_acc,
        "delta_pp": delta_pp,
        "windows": windows
    }
