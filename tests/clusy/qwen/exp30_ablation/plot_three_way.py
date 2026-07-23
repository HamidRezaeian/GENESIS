"""
Exp 30: Three-Way Comparison Plot (A/B/C) + Verdict.

Loads arm_A.json, arm_B.json, arm_C.json. Produces 2×2 figure with
population, accuracy, mean energy, and steady-state bar chart.

Usage:
    python plot_three_way.py
"""
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

arms = {}
for label, path in [("A","results/arm_A.json"), ("B","results/arm_B.json"), ("C","results/arm_C.json")]:
    with open(path) as f: arms[label] = json.load(f)

for k in arms:
    cr, ir = np.array(arms[k]["correct_reads"], dtype=float), np.array(arms[k]["incorrect_reads"], dtype=float)
    total = cr + ir
    arms[k]["accuracy"] = np.where(total > 0, cr / total * 100, 0.0)

ss = {}
for k in arms:
    n = len(arms[k]["ticks"])
    s = int(n * 0.75)
    ss[k] = {"pop": np.mean(arms[k]["population"][s:]),
             "acc": np.mean(arms[k]["accuracy"][s:]),
             "energy": np.mean(arms[k]["mean_energy"][s:])}

fig, axes = plt.subplots(2, 2, figsize=(16, 11))
colors = {"A":"#2196F3","B":"#F44336","C":"#FF9800"}
labels = {"A":"A: STDP ON","B":"B: STDP OFF","C":"C: COSTONLY"}

for ax, metric, ylabel, title in [
    (axes[0,0],"population","Population","Population Dynamics"),
    (axes[0,1],lambda k:arms[k]["accuracy"],"Read Accuracy (%)","Prediction Accuracy"),
    (axes[1,0],"mean_energy","Mean Energy / Organism","Energy per Organism"),
]:
    for k in ["A","B","C"]:
        y = arms[k][metric] if isinstance(metric,str) else metric(k)
        ax.plot(arms[k]["ticks"], y, color=colors[k], label=labels[k], lw=1.2, alpha=0.85)
    ax.set_ylabel(ylabel); ax.set_title(title, fontweight="bold")
    ax.legend(); ax.grid(True, alpha=0.3); ax.set_xlim(0, 200_000)

# Bar chart
ax = axes[1,1]
x = np.arange(3); w = 0.35
pops = [ss[k]["pop"] for k in ["A","B","C"]]
accs = [ss[k]["acc"] for k in ["A","B","C"]]
ax.bar(x-w/2, pops, w, color=[colors[k] for k in ["A","B","C"]], alpha=0.7, edgecolor="black")
ax2 = ax.twinx()
ax2.bar(x+w/2, accs, w, color=[colors[k] for k in ["A","B","C"]], alpha=0.35, edgecolor="black", hatch="//")
ax.set_xticks(x); ax.set_xticklabels(["A: STDP ON","B: STDP OFF","C: COSTONLY"])
ax.set_ylabel("Population"); ax2.set_ylabel("Accuracy (%)")
ax.set_title("Steady-State Summary (last 25%)", fontweight="bold")
ax.set_ylim(0, 700); ax2.set_ylim(0, 100)
for i,(p,a) in enumerate(zip(pops,accs)):
    ax.text(i-w/2, p+10, f"{p:.0f}", ha="center", va="bottom", fontweight="bold")
    ax2.text(i+w/2, a+2, f"{a:.1f}%", ha="center", va="bottom", fontweight="bold")

plt.tight_layout(rect=[0,0,1,0.95])
plt.savefig("figures/three_way_comparison.png", dpi=150, bbox_inches="tight")
print("Saved: figures/three_way_comparison.png")

print(f"\n{'='*70}")
print(f"  THREE-WAY VERDICT (last 25%)\n{'='*70}")
for k in ["A","B","C"]:
    print(f"  Arm {k}: pop={ss[k]['pop']:6.0f}  acc={ss[k]['acc']:5.1f}%  energy={ss[k]['energy']:10.0f}")
pop_AC = (ss["A"]["pop"]-ss["C"]["pop"])/ss["C"]["pop"]*100
pop_BC = (ss["B"]["pop"]-ss["C"]["pop"])/ss["C"]["pop"]*100
print(f"  A vs C pop: {pop_AC:+.0f}%  B vs C pop: {pop_BC:+.0f}%")
if abs(pop_BC) < 5:
    print("  → Energy cost is NEGLIGIBLE")
if ss["C"]["acc"] > ss["A"]["acc"]:
    print("  → STDP is HARMFUL (frozen weights predict better)")
print(f"{'='*70}")
