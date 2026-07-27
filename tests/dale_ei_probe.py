#!/usr/bin/env python3
"""
Dale's-law E/I balance — controlled demonstration (Session 14)
==============================================================

WHAT THIS SHOWS
---------------
The engine now implements Dale's law: every neuron is excitatory (+1) or
inhibitory (-1), and a spike delivers |w|*sign[src] to each target. This probe
demonstrates, on a dense recurrent network that uses the SAME event-driven LIF +
Dale's-law update as the engine kernel, why inhibitory neurons are essential:

  A) ALL-EXCITATORY ("no brakes"): recurrent excitation is unchecked positive
     feedback -> the network is OVERACTIVE (high firing) and UNSTABLE (synchronous
     bursts; epileptiform).
  B) 80/20 E/I ("with brakes"): ~20% inhibitory neurons provide negative feedback
     -> activity is CONTROLLED (lower firing) and STABLE (steady, asynchronous).

DESIGN NOTES (why the parameters are biologically faithful)
-----------------------------------------------------------
* Heterogeneous neurons (threshold & time constant drawn from a distribution):
  real cortical neurons are not identical; homogeneity artefactually synchronises
  a purely excitatory network.
* Inhibitory synapses are G_INHIB=4x stronger per-synapse than excitatory ones.
  This is how cortex reconciles the 80/20 *neuron* ratio with a *balanced* net
  drive (0.8*W - 0.2*4*W ~ 0): inhibition is several times stronger per connection.
  The engine supports this directly — Dale's law fixes the SIGN, while the weight
  MAGNITUDE is evolvable, so inhibitory synapses can carry larger |w|.
* A sustained external drive steps on at t=STEP (a sensory stimulus). Excitation
  amplifies it (runaway); inhibition stabilises the response.

Run:  cd <repo> && python3 tests/dale_ei_probe.py
Exit: 0 iff the all-excitatory network is BOTH more active AND less stable.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np

# ---- network + LIF parameters (same event-driven LIF as the engine) ----
N        = 500
P_CONN   = 0.10      # connection probability (~50 inputs/neuron)
REFRACT  = 3
V_REST   = 0.0
V_RESET  = 0.0
T        = 700       # time steps
STEP     = 150       # external drive switches on here (the "stimulus")
W        = 0.30      # excitatory synapse magnitude |w|
G_INHIB  = 4.0       # inhibitory synapses are 4x stronger (cortical E/I balance)
EXT_ON   = 0.25      # external drive probability/step (after STEP)
EXT_W    = 0.20      # external input magnitude
SEED     = 7

rng = np.random.default_rng(SEED)
A = (rng.random((N, N)) < P_CONN).astype(np.float32)   # A[i,j]=1 if j -> i
np.fill_diagonal(A, 0)
# realistic heterogeneity
THRESH = rng.normal(1.0, 0.12, N).astype(np.float32)
TAU    = rng.normal(10.0, 2.0, N).astype(np.float32)


def simulate(inhib_frac, seed=SEED):
    """LIF network with a given fraction of inhibitory neurons; returns per-step rate."""
    r = np.random.default_rng(seed)
    sign = np.ones(N, np.float32)
    n_inhib = int(N * inhib_frac)
    if n_inhib > 0:
        sign[r.choice(N, n_inhib, replace=False)] = -1.0
    # Dale's law: sign sets direction; inhibitory synapses carry larger magnitude
    mag = np.where(sign < 0, W * G_INHIB, W).astype(np.float32)

    v = np.full(N, V_REST, np.float32)
    ref = np.zeros(N, np.int32)
    sp = np.zeros(N, np.float32)
    rates = np.zeros(T, np.float32)
    for t in range(T):
        rec = A @ (mag * sign * sp)                       # Dale's-law signed input
        ext_rate = EXT_ON if t >= STEP else 0.0           # stimulus step
        ext = (r.random(N) < ext_rate).astype(np.float32) * EXT_W
        I = rec + ext
        active = ref == 0
        v[active] += (V_REST - v[active]) / TAU[active] + I[active]
        fired = (v >= THRESH) & active
        v[fired] = V_RESET
        ref[fired] = REFRACT
        ref[ref > 0] -= 1
        rates[t] = fired.sum() / N
        sp = fired.astype(np.float32)
    return rates, sign


print("=" * 68)
print("DALE'S-LAW E/I BALANCE  (dense recurrent LIF, same update as engine)")
print("N=%d  fan-in~%d  |w|=%.2f  inhib x%.0f  hetero thresh/tau" %
      (N, int(A.sum(1).mean()), W, G_INHIB))
print("=" * 68)

rates_A, sign_A = simulate(0.0)        # all excitatory
rates_B, sign_B = simulate(0.20)       # 80/20 E/I

post = slice(STEP + 50, T)             # steady response after the stimulus
base_A = float(rates_A[:STEP].mean());  base_B = float(rates_B[:STEP].mean())
mean_A = float(rates_A[post].mean());   mean_B = float(rates_B[post].mean())
std_A  = float(rates_A[post].std());    std_B  = float(rates_B[post].std())

print("\n[A] ALL-EXCITATORY (no brakes):   inhibitory=%d/%d" % (int((sign_A < 0).sum()), N))
print("    baseline=%.4f  ->  stimulus response: mean=%.4f  std=%.4f" % (base_A, mean_A, std_A))
print("\n[B] 80/20 E/I (with brakes):      inhibitory=%d/%d (%.0f%%)" %
      (int((sign_B < 0).sum()), N, 100 * (sign_B < 0).mean()))
print("    baseline=%.4f  ->  stimulus response: mean=%.4f  std=%.4f" % (base_B, mean_B, std_B))

print("\n" + "-" * 68)
print("RESULT (response to the same stimulus):")
print("   activity :  %.4f (no brakes)  vs  %.4f (with brakes)  -> %.2fx" %
      (mean_A, mean_B, mean_A / mean_B if mean_B > 0 else float('inf')))
print("   stability:  std %.4f (no brakes)  vs  std %.4f (with brakes)  -> %.1fx steadier" %
      (std_A, std_B, std_A / std_B if std_B > 0 else float('inf')))
overactive = mean_A > mean_B
stable = std_A > std_B
print("   no-brakes network is OVERACTIVE: %s ; UNSTABLE/bursty: %s" % (overactive, stable))
print("-" * 68)

# ---- plot ----
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=110)
    t = np.arange(T)
    w = 8
    sm = lambda x: np.convolve(x, np.ones(w) / w, mode="same")
    ax.plot(t, sm(rates_A), color="#c0392b", lw=1.5, label="All-excitatory (no brakes)")
    ax.plot(t, sm(rates_B), color="#2980b9", lw=1.5, label="80/20 E/I (with brakes)")
    ax.axvline(STEP, color="gray", ls=":", lw=1.2)
    ax.text(STEP + 6, ax.get_ylim()[1] * 0.92, "stimulus on", color="gray", fontsize=9)
    ax.set_xlabel("time step")
    ax.set_ylabel("population firing rate")
    ax.set_title("Dale's law: inhibitory neurons stabilise recurrent activity")
    ax.legend(frameon=False, loc="upper left")
    ax.set_xlim(0, T)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    out = os.path.join(os.path.dirname(__file__), "dale_ei_balance.png")
    fig.savefig(out)
    print("saved plot:", out)
except Exception as e:
    print("plot skipped:", e)

sys.exit(0 if (overactive and stable) else 1)
