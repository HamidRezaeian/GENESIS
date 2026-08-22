"""Task Family 4 (TF4) — 2D Spatial Grid Navigation (Planning & Spatial Reasoning).

Protocol ID: TF4_SPATIAL_NAVIGATION_v1
Task Definition:
  The agent navigates a 16x16 grid world with obstacles from start (x, y) to goal (gx, gy).
  State is represented as token sequences:
    "X {x} Y {y} GX {gx} GY {gy} ACT ? {optimal_action}"
  where actions in {U, D, L, R}.

Cognitive Capacity:
  Tests 2D coordinate representation, spatial planning, and shortest-path policy learning.
"""

import os
import sys
import numpy as np

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "experiments"))

from sub4_plus_agent import Substrate4PlusAgent as SmallTransformerAgent

ACT_U = ord('U')
ACT_D = ord('D')
ACT_L = ord('L')
ACT_R = ord('R')
TOK_Q = ord('?')
TOK_SEP = ord(' ')

def get_optimal_action(x, y, gx, gy):
    dx = gx - x
    dy = gy - y
    if abs(dx) >= abs(dy) and dx != 0:
        return ACT_R if dx > 0 else ACT_L
    elif dy != 0:
        return ACT_D if dy > 0 else ACT_U
    return ACT_R

def generate_navigation_stream(seed, n_episodes=3000, grid_size=16):
    rng = np.random.RandomState(seed)
    stream = []
    
    for _ in range(n_episodes):
        x, y = rng.randint(0, grid_size, size=2)
        gx, gy = rng.randint(0, grid_size, size=2)
        while x == gx and y == gy:
            gx, gy = rng.randint(0, grid_size, size=2)
            
        opt_act = get_optimal_action(x, y, gx, gy)
        
        # Format: "X {x} Y {y} G {gx} {gy} ? {opt_act} "
        expr = [
            ord('X'), ord(str(x % 10)),
            ord('Y'), ord(str(y % 10)),
            ord('G'), ord(str(gx % 10)), ord(str(gy % 10)),
            TOK_Q, opt_act, TOK_SEP
        ]
        stream.extend(expr)
        
    return stream

def run_tf4_arm(seed, ticks=10000, report_every=1000, is_learn=True, n_orgs=30):
    stream = generate_navigation_stream(seed, n_episodes=ticks // 4)
    n = len(stream)
    
    agents = [SmallTransformerAgent(seed * 400 + o) for o in range(n_orgs)]
    cursors = [rng.randint(0, n - 20) for rng in [np.random.RandomState(seed + o) for o in range(n_orgs)]]
    
    windows = []
    act_correct = 0
    act_total = 0
    
    for tick in range(ticks):
        for org in range(n_orgs):
            pos = cursors[org]
            in_byte = stream[pos]
            tgt_byte = stream[(pos + 1) % n]
            
            pred_byte, _ = agents[org].step(in_byte, tgt_byte, is_learn=is_learn)
            
            if in_byte == TOK_Q:
                act_total += 1
                if pred_byte == tgt_byte:
                    act_correct += 1
                    
            cursors[org] = (cursors[org] + 1) % (n - 1)
            
        if (tick + 1) % report_every == 0:
            acc = 100.0 * act_correct / act_total if act_total > 0 else 25.0
            windows.append({"tick": tick + 1, "nav_acc": round(acc, 4), "samples": act_total})
            act_correct = 0
            act_total = 0
            
    early_acc = float(np.mean([w["nav_acc"] for w in windows[:3]]))
    late_acc = float(np.mean([w["nav_acc"] for w in windows[-3:]]))
    delta_pp = late_acc - early_acc
    
    return {
        "task": "TF4_SPATIAL_NAVIGATION",
        "seed": seed,
        "is_learn": is_learn,
        "early_acc": early_acc,
        "late_acc": late_acc,
        "delta_pp": delta_pp,
        "windows": windows
    }
