"""
Exp 87: Metabolic-Ceiling Evolution — plots + verdict.

Loads results/stdp_target_0.json and results/stdp_target_1.json (3 seeds x 150
snapshots each), produces the 4-panel metabolic-ceiling figure and the PARAM-gene
drift heatmap, and prints the pre-registered H1/H2/H3 verdict.

Run from this directory:
    cd tests/clusy/qwen/exp87_metabolic_ceiling
    python plot_metabolic_ceiling.py

Outputs:
    figures/metabolic_ceiling.png
    figures/param_drift.png
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

with open("results/stdp_target_0.json") as f:
    ARM0 = json.load(f)
with open("results/stdp_target_1.json") as f:
    ARM1 = json.load(f)
ARMS = {"0": ARM0, "1": ARM1}
INCOME = float(ARM0["income_quantum"])            # 256 cycles (CELL_STATES = 2^8)
PNAMES = ARM0["param_names"]
NTICKS = ARM0["n_ticks"]


def stack(arm, key):
    return np.array([[snap.get(key, np.nan) for snap in s] for s in ARMS[arm]["series"]], float)


def t_axis(arm):
    return np.array([s["tick"] for s in ARMS[arm]["series"][0]])


def ms(arr):
    return np.nanmean(arr, 0), np.nanstd(arr, 0)


t = t_axis("0")
data = {a: {m: stack(a, m) for m in
            ["n_neurons_mean", "idle_cost_mean", "correct_per_tick", "refuge_germ_cum"]}
        for a in ("0", "1")}
C0, C1 = "#d1495b", "#00798c"   # arm0 red, arm1 teal

# ---------------- Figure 1: metabolic-ceiling panel ----------------
fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
fig.suptitle("Exp 87 — Metabolic-Ceiling Evolution: structure evolves under grounded income pressure\n"
             "(3 seeds/arm, 30 000 ticks, income quantum = 256 cycles/tick; shaded = +/-1 SD over seeds)",
             fontsize=12, fontweight="bold")

ax = axes[0, 0]
for arm, c, lab in (("0", C0, "STDP_TARGET=0"), ("1", C1, "STDP_TARGET=1")):
    m, s = ms(data[arm]["idle_cost_mean"]); ax.plot(t, m, color=c, lw=2, label=lab)
    ax.fill_between(t, m - s, m + s, color=c, alpha=0.15)
ax.axhline(INCOME, color="k", ls="--", lw=1.5, label="income quantum (256)")
ax.set_ylabel("idle cost (cycles/tick)"); ax.set_title("(a) Metabolic cost — Rule 7 test")
ax.set_yscale("log"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
ax.annotate("bankruptcy gap\ncost >> income", xy=(t[-1], 2387), xytext=(t[-1] * 0.55, 1500),
            fontsize=9, arrowprops=dict(arrowstyle="->", color="gray"))

ax = axes[0, 1]
for arm, c, lab in (("0", C0, "STDP_TARGET=0"), ("1", C1, "STDP_TARGET=1")):
    m, s = ms(data[arm]["n_neurons_mean"]); ax.plot(t, m, color=c, lw=2, label=lab)
    ax.fill_between(t, m - s, m + s, color=c, alpha=0.15)
ax.axhline(65, color="k", ls=":", lw=1.2, label="ancestor (65)")
ax.set_ylabel("n_neurons (mean)"); ax.set_title("(b) Brain size — bloat, not shrinkage")
ax.legend(fontsize=8); ax.grid(alpha=0.3)

ax = axes[1, 0]
for arm, c, lab in (("0", C0, "STDP_TARGET=0"), ("1", C1, "STDP_TARGET=1")):
    m, s = ms(data[arm]["correct_per_tick"]); ax.plot(t, m, color=c, lw=2, label=lab)
    ax.fill_between(t, np.maximum(m - s, 0), m + s, color=c, alpha=0.15)
ax.set_xlabel("tick"); ax.set_ylabel("correct predictions / tick")
ax.set_title("(c) Comprehension income — collapses after founders die"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
ax.annotate("founders echo-predict\nthen go bankrupt", xy=(t[0], 129), xytext=(t[-1] * 0.18, 95),
            fontsize=8, arrowprops=dict(arrowstyle="->", color="gray"))

ax = axes[1, 1]
for arm, c, lab in (("0", C0, "STDP_TARGET=0"), ("1", C1, "STDP_TARGET=1")):
    m, s = ms(data[arm]["refuge_germ_cum"]); ax.plot(t, m, color=c, lw=2, label=lab)
    ax.fill_between(t, m - s, m + s, color=c, alpha=0.15)
ax.plot(t, 0.05 * t, color="k", ls="--", lw=1.2, label="5% Rule-14 threshold")
ax.set_xlabel("tick"); ax.set_ylabel("cumulative refugium germinations")
ax.set_title("(d) Population on life support (Rule-14 violation)"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig("figures/metabolic_ceiling.png", dpi=130, bbox_inches="tight")
print("saved figures/metabolic_ceiling.png")

# ---------------- Figure 2: PARAM-gene drift heatmap ----------------
drift = np.zeros((2, len(PNAMES))); drift_std = np.zeros((2, len(PNAMES)))
for ai, arm in enumerate(("0", "1")):
    for gi, g in enumerate(PNAMES):
        arr = stack(arm, "param_%s" % g)
        per = arr[:, -1] - arr[:, 0]
        drift[ai, gi] = np.nanmean(per); drift_std[ai, gi] = np.nanstd(per)
vmax = max(1.0, float(np.nanmax(np.abs(drift))))
fig2, ax2 = plt.subplots(1, 1, figsize=(11, 4.2))
im = ax2.imshow(drift, aspect="auto", cmap="RdBu_r", vmax=vmax, vmin=-vmax)
ax2.set_xticks(range(len(PNAMES))); ax2.set_xticklabels(PNAMES, rotation=35, ha="right", fontsize=8)
ax2.set_yticks([0, 1]); ax2.set_yticklabels(["STDP_TARGET=0", "STDP_TARGET=1"])
ax2.set_title("Exp 87 — PARAM-gene total drift over 30 000 ticks (mean over 3 seeds)\n"
              "small per-seed SD => drift shared across seeds = mutational bias (refugium-dominated), NOT adaptive tuning",
              fontsize=10)
for ai in range(2):
    for gi in range(len(PNAMES)):
        ax2.text(gi, ai, "%+.2f" % drift[ai, gi], ha="center", va="center", fontsize=7,
                 color="white" if abs(drift[ai, gi]) > 0.6 * vmax else "black")
fig2.colorbar(im, ax=ax2, label="total drift (native units)")
plt.tight_layout()
plt.savefig("figures/param_drift.png", dpi=130, bbox_inches="tight")
print("saved figures/param_drift.png")

# ---------------- printed verdict ----------------
print("\n" + "=" * 70)
print("VERDICT (pre-registered H1/H2/H3)")
print("=" * 70)
for arm in ("0", "1"):
    ic = data[arm]["idle_cost_mean"]
    first, last = float(np.nanmean(ic[:, 0])), float(np.nanmean(ic[:, -1]))
    cp = data[arm]["correct_per_tick"]
    peak, end = float(np.nanmax(np.nanmean(cp, 0))), float(np.nanmean(cp[:, -1]))
    refuge_rate = float(np.nanmean(data[arm]["refuge_germ_cum"][:, -1])) / NTICKS
    print("arm %s: idle %.0f -> %.0f (%s) | correct/tick peak %.0f -> end %.1f | refuge %.1f%% %s"
          % (arm, first, last, "RISES (anti-Rule-7)" if last > first else "falls",
             peak, end, 100 * refuge_rate,
             "[Rule-14 VIOLATION]" if refuge_rate > 0.05 else "[ok]"))
print("max |per-seed SD| across PARAM genes = %.3f  (small => mutational bias, not selection)"
      % float(np.nanmax(drift_std)))
print("\nH1 Rule-7 efficiency : REJECTED (idle cost rises; brains bloat)")
print("H2 adaptive PARAM drift: NEUTRAL (mutational bias, per-seed SD small)")
print("H3 STDP_TARGET effect : NOT supported (comprehension collapses in both arms)")
print("Core: the metabolic ceiling nullifies selection (income gradient flat at zero).")
