"""Offline checkpoint inspector: per-world alive distribution (no GPU, no server lock)."""
import sys
import os

REPO = r"c:\Users\Hamid\source\repos\GENESIS"
sys.path.insert(0, os.path.join(REPO, "src"))
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # keep the live server's GPU untouched

import torch

CKPT = os.path.join(REPO, "Brain", "phase_e_state.pt")
OUT = os.path.join(REPO, "scratch", "world_alive_report.txt")
# CPPNGenome lives in phase_e_substrate: import it so unpickling can resolve classes.
import genesis.server.phase_e_substrate  # noqa: F401

try:
    state = torch.load(CKPT, map_location="cpu", weights_only=False)
    pop_state = state["pop_state"]
    alive = pop_state["alive_mask"]
    per_world = alive.sum(dim=1).tolist()
    lines = [
        f"server tick: {state['tick_count']}",
        f"llm queries: {state.get('llm_query_count', 'MISSING')}",
        f"per-world alive: {per_world}",
        f"total alive: {int(alive.sum())} / {alive.numel()}",
        f"mean energy (all): {float(pop_state['energy'].mean()):.1f}",
        f"mean energy (alive): {float(pop_state['energy'][alive].mean()):.1f}",
    ]
except Exception as exc:  # write errors to the report too, never hang
    lines = [f"INSPECT ERROR: {type(exc).__name__}: {exc}"]

report = "\n".join(lines)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(report + "\n")
print(report)
