"""Task Family 5 (TF5) — Causal Intervention & Graph Discovery (Causal Reasoning).

Protocol ID: TF5_CAUSAL_INTERVENTION_v1
Task Definition:
  Structural Causal Model (SCM):
    X1 in [0..9]
    X2 := (X1 + 3) mod 10
    X3 := (2 * X2 + 1) mod 10
  Under observational mode:
    "OBS X1 {x1} X2 {x2} ? {x3} "
  Under interventional mode do(X2 = v):
    "DO X2 {v} ? {x3_do} "  (where x3_do = (2 * v + 1) mod 10, decoupled from X1)

Cognitive Capacity:
  Tests causal graph induction, counterfactual reasoning, and Do-Calculus invariance.
"""

import os
import sys
import numpy as np

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "experiments"))

from sub4_plus_agent import Substrate4PlusAgent as SmallTransformerAgent

TOK_Q = ord('?')
TOK_SEP = ord(' ')

def generate_causal_stream(seed, n_samples=3000):
    rng = np.random.RandomState(seed)
    stream = []
    
    for _ in range(n_samples):
        is_intervene = (rng.rand() < 0.5)
        if not is_intervene:
            # Observational sample
            x1 = rng.randint(0, 10)
            x2 = (x1 + 3) % 10
            x3 = (2 * x2 + 1) % 10
            # "O X1 {x1} X2 {x2} ? {x3} "
            expr = [
                ord('O'), ord('1'), ord(str(x1)),
                ord('2'), ord(str(x2)),
                TOK_Q, ord(str(x3)), TOK_SEP
            ]
        else:
            # Interventional sample: do(X2 = v)
            v = rng.randint(0, 10)
            x3 = (2 * v + 1) % 10
            # "D 2 {v} ? {x3} "
            expr = [
                ord('D'), ord('2'), ord(str(v)),
                TOK_Q, ord(str(x3)), TOK_SEP
            ]
        stream.extend(expr)
        
    return stream

def run_tf5_arm(seed, ticks=10000, report_every=1000, is_learn=True, n_orgs=30):
    stream = generate_causal_stream(seed, n_samples=ticks // 4)
    n = len(stream)
    
    agents = [SmallTransformerAgent(seed * 500 + o) for o in range(n_orgs)]
    cursors = [rng.randint(0, n - 20) for rng in [np.random.RandomState(seed + o) for o in range(n_orgs)]]
    
    windows = []
    causal_correct = 0
    causal_total = 0
    
    for tick in range(ticks):
        for org in range(n_orgs):
            pos = cursors[org]
            in_byte = stream[pos]
            tgt_byte = stream[(pos + 1) % n]
            
            pred_byte, _ = agents[org].step(in_byte, tgt_byte, is_learn=is_learn)
            
            if in_byte == TOK_Q:
                causal_total += 1
                if pred_byte == tgt_byte:
                    causal_correct += 1
                    
            cursors[org] = (cursors[org] + 1) % (n - 1)
            
        if (tick + 1) % report_every == 0:
            acc = 100.0 * causal_correct / causal_total if causal_total > 0 else 10.0
            windows.append({"tick": tick + 1, "causal_acc": round(acc, 4), "samples": causal_total})
            causal_correct = 0
            causal_total = 0
            
    early_acc = float(np.mean([w["causal_acc"] for w in windows[:3]]))
    late_acc = float(np.mean([w["causal_acc"] for w in windows[-3:]]))
    delta_pp = late_acc - early_acc
    
    return {
        "task": "TF5_CAUSAL_INTERVENTION",
        "seed": seed,
        "is_learn": is_learn,
        "early_acc": early_acc,
        "late_acc": late_acc,
        "delta_pp": delta_pp,
        "windows": windows
    }
