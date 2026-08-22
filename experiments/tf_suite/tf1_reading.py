"""Task Family 1 (TF1) — Continuous Sequence Reading & Delayed Match-to-Sample.

Protocol ID: TF1_SEQUENCE_READING_v1
Scope: Tests continuous sequence reading, context buffering, and next-byte prediction on RAM library text.
"""

import os
import sys
import numpy as np

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "experiments"))

from sub4_plus_agent import Substrate4PlusAgent
from sub4_small_transformer import build_patch

def run_tf1_arm(seed, ticks=10000, report_every=1000, is_learn=True, n_orgs=30):
    patch = build_patch(seed)
    n = len(patch)
    
    agents = [Substrate4PlusAgent(seed * 100 + o) for o in range(n_orgs)]
    cursors = [rng.randint(0, n - 20) for rng in [np.random.RandomState(seed + o) for o in range(n_orgs)]]
    
    windows = []
    
    for tick in range(ticks):
        total_correct = 0
        total_bits = 0
        
        for org in range(n_orgs):
            pos = cursors[org]
            in_byte = int(patch[pos])
            tgt_byte = int(patch[(pos + 1) % n])
            
            pred_byte, _ = agents[org].step(in_byte, tgt_byte, is_learn=is_learn)
            
            xb = int(pred_byte) ^ tgt_byte
            correct = 8 - bin(xb & 0xFF).count("1")
            total_correct += correct
            total_bits += 8
            
            if np.random.rand() < 0.7:
                cursors[org] = (cursors[org] + 1) % n
            else:
                cursors[org] = (cursors[org] + np.random.randint(1, 4)) % n
                
        if (tick + 1) % report_every == 0:
            acc = 100.0 * total_correct / total_bits if total_bits else 0.0
            windows.append({"tick": tick + 1, "acc": round(acc, 4)})
            
    early_acc = float(np.mean([w["acc"] for w in windows[:3]]))
    late_acc = float(np.mean([w["acc"] for w in windows[-3:]]))
    delta_pp = late_acc - early_acc
    
    return {
        "task": "TF1_SEQUENCE_READING",
        "seed": seed,
        "is_learn": is_learn,
        "early_acc": early_acc,
        "late_acc": late_acc,
        "delta_pp": delta_pp,
        "windows": windows
    }
