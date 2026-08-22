"""Task Family 3 (TF3) — Compositional Modular Arithmetic (Algebraic Composition).

Protocol ID: TF3_COMPOSITIONAL_ARITHMETIC_v1
Task Definition:
  The agent processes arithmetic expressions of the form:
    a + b = ans (mod 10)
    a * b = ans (mod 10)
    a + b * c = ans (mod 10)
  where a, b, c in [0..9]. The target prediction is the calculation output immediately
  following the '=' token.

Cognitive Capacity:
  Tests compositional generalization, operator binding, and hierarchical algebraic computation.
"""

import os
import sys
import numpy as np

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "experiments"))

from sub4_plus_agent import Substrate4PlusAgent as SmallTransformerAgent

TOK_EQ = ord('=')
TOK_PLUS = ord('+')
TOK_MUL = ord('*')
TOK_SEP = ord(' ')

def generate_arithmetic_stream(seed, n_samples=5000):
    rng = np.random.RandomState(seed)
    stream = []
    
    for _ in range(n_samples):
        op_type = rng.choice(["add", "mul", "comp"])
        if op_type == "add":
            a = rng.randint(0, 10)
            b = rng.randint(0, 10)
            ans = (a + b) % 10
            # "a + b = ans "
            expr = [ord(str(a)), TOK_PLUS, ord(str(b)), TOK_EQ, ord(str(ans)), TOK_SEP]
        elif op_type == "mul":
            a = rng.randint(0, 10)
            b = rng.randint(0, 10)
            ans = (a * b) % 10
            # "a * b = ans "
            expr = [ord(str(a)), TOK_MUL, ord(str(b)), TOK_EQ, ord(str(ans)), TOK_SEP]
        else:
            a = rng.randint(0, 10)
            b = rng.randint(0, 10)
            c = rng.randint(0, 10)
            ans = (a + b * c) % 10
            # "a + b * c = ans "
            expr = [ord(str(a)), TOK_PLUS, ord(str(b)), TOK_MUL, ord(str(c)), TOK_EQ, ord(str(ans)), TOK_SEP]
            
        stream.extend(expr)
        
    return stream

def run_tf3_arm(seed, ticks=10000, report_every=1000, is_learn=True, n_orgs=30):
    stream = generate_arithmetic_stream(seed, n_samples=ticks // 4)
    n = len(stream)
    
    agents = [SmallTransformerAgent(seed * 300 + o) for o in range(n_orgs)]
    cursors = [rng.randint(0, n - 20) for rng in [np.random.RandomState(seed + o) for o in range(n_orgs)]]
    
    windows = []
    ans_correct = 0
    ans_total = 0
    
    for tick in range(ticks):
        for org in range(n_orgs):
            pos = cursors[org]
            in_byte = stream[pos]
            tgt_byte = stream[(pos + 1) % n]
            
            pred_byte, _ = agents[org].step(in_byte, tgt_byte, is_learn=is_learn)
            
            # If the current input is '=', the target is the answer digit
            if in_byte == TOK_EQ:
                ans_total += 1
                if pred_byte == tgt_byte:
                    ans_correct += 1
                    
            cursors[org] = (cursors[org] + 1) % (n - 1)
            
        if (tick + 1) % report_every == 0:
            acc = 100.0 * ans_correct / ans_total if ans_total > 0 else 10.0
            windows.append({"tick": tick + 1, "arithmetic_acc": round(acc, 4), "samples": ans_total})
            ans_correct = 0
            ans_total = 0
            
    early_acc = float(np.mean([w["arithmetic_acc"] for w in windows[:3]]))
    late_acc = float(np.mean([w["arithmetic_acc"] for w in windows[-3:]]))
    delta_pp = late_acc - early_acc
    
    return {
        "task": "TF3_COMPOSITIONAL_ARITHMETIC",
        "seed": seed,
        "is_learn": is_learn,
        "early_acc": early_acc,
        "late_acc": late_acc,
        "delta_pp": delta_pp,
        "windows": windows
    }
