"""
Exp 30: A/B Comparison Plot + Verdict.

Loads arm_A.json and arm_B.json, produces 3-panel figure, prints statistical verdict.

Usage:
    python plot_ablation.py
"""
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

with open("results/arm_A.json") as f: A = json.load(f)
with open("results/arm_B.json") as f: B = json.load(f)

tA, tB = np.array(A["ticks"]), np.array(B["ticks"])
popA, popB = np.array(A["population"]), np.array(B["population"])
eA, eB = np.array(A["mean_energy"]), np.array(B["mean_energy"])
crA, irA = np.array(A["correct_reads"], dtype=float), np.array(A["incorrect_reads"], dtype=float)
crB, irB = np.array(B["correct_reads"], dtype=float), np.array(B["incorrect_reads"], dtype=float)
accA = np.where(crA + irA > 0, crA / (crA + irA) * 100, np.nan)
accB = np.where(crB + irB > 0, crB / (crB + irB) * 100, np.nan)

fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
fig.suptitle("Exp 30: STDP Ablation — Is Plasticity Load-Bearing?", fontsize=16, fontweight="bold", y=0.98)
for ax, y, ylabel, title, color in [
    (axes[0], popA, "Population", "Population Survival", "#2196F3"),
]:
    axes[0].plot(tA, popA, color="#2196F3", lw=1.2, label="Arm A: STDP ON")
    axes[0].plot(tB, popB, color="#F44336", lw=1.2, label="Arm B: STDP OFF")
    axes[0].set_ylabel("Population"); axes[0].set_title("Population Survival", fontsize=13)
    axes[0].legend(); axes[0].grid(True, alpha=0.3)

axes[1].plot(tA, eA, color="#2196F3", lw=1.2, label="Arm A: STDP ON")
axes[1].plot(tB, eB, color="#F44336", lw=1.2, label="Arm B: STDP OFF")
axes[1].set_ylabel("Mean Energy / org"); axes[1].set_title("Metabolic Health", fontsize=13)
axes[1].legend(); axes[1].grid(True, alpha=0.3)

axes[2].plot(tA, accA, color="#2196F3", lw=1.2, label="Arm A: STDP ON")
axes[2].plot(tB, accB, color="#F44336", lw=1.2, label="Arm B: STDP OFF")
axes[2].set_ylabel("Read Accuracy (%)"); axes[2].set_xlabel("World Tick")
axes[2].set_title("Prediction Accuracy", fontsize=13)
axes[2].legend(); axes[2].set_ylim(0, 100); axes[2].grid(True, alpha=0.3)
axes[2].xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig("figures/ablation_comparison.png", dpi=150, bbox_inches="tight")
print("Saved: figures/ablation_comparison.png")

q = len(tA) // 4
popA_m, popB_m = np.mean(popA[-q:]), np.mean(popB[-q:])
accA_m = np.nanmean(accA[-q:]) if sum(~np.isnan(accA[-q:])) else 0
accB_m = np.nanmean(accB[-q:]) if sum(~np.isnan(accB[-q:])) else 0
pop_gap, acc_gap = (popA_m-popB_m)/max(popB_m,1)*100, accA_m-accB_m

print(f"\n{'='*70}\n  EXP 30 VERDICT (last 25%)\n{'='*70}")
print(f"  A: pop={popA_m:.0f}  acc={accA_m:.1f}%")
print(f"  B: pop={popB_m:.0f}  acc={accB_m:.1f}%")
print(f"  Gap: pop={pop_gap:+.0f}%  acc={acc_gap:+.1f} pp")
if pop_gap > 25 and acc_gap > 5:
    print("  ✅ STDP IS LOAD-BEARING")
elif abs(pop_gap) < 10 and abs(acc_gap) < 3:
    print("  ❌ SUBSTRATE FALSIFIED")
elif pop_gap < -25:
    print("  ⚠️  STDP IS HARMFUL")
else:
    print("  ⚠️  INCONCLUSIVE")
print('='*70)
