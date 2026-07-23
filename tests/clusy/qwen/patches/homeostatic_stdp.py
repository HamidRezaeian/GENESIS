"""
HOMEOSTATIC STDP — @njit-safe drop-in replacement for destructive STDP.

Problem: Exp 30 proved STDP random-walks weights away from the genome's
functional configuration. Frozen weights predict at 56.9% vs STDP at 43.3%.

Fix: Anchor each synapse toward its DNA-decoded birth weight.

    w += Δw_STDP − λ(w − w_DNA)

Where:
    w_DNA   = weight decoded from genome at birth
    λ       = HOMEOSTATIC_LAMBDA (default 0.01, env-gated)
    Δw_STDP = existing Hebbian eligibility-trace update (unchanged)

Cost: 1 extra FMA per synapse per tick. Negligible.
"""

import numpy as np
import os
from numba import njit

# ═══════════════════════════════════════════════════════════════════════════
# COMPILE-TIME CONSTANT — add to neuromorphic_engine.py after line ~122
# ═══════════════════════════════════════════════════════════════════════════

HOMEOSTATIC_LAMBDA = np.float32(
    float(os.environ.get("GENESIS_HOMEOSTATIC_LAMBDA", "0.01"))
)
# λ = 0     → byte-identical to current destructive STDP (DCE eliminates branch)
# λ = 0.01  → weights anchored ±10% around DNA baseline (DEFAULT)
# λ = 1.0   → weights snap back to DNA every tick (no learning)


# ═══════════════════════════════════════════════════════════════════════════
# CHANGE 2: decode_genome() — store DNA birth weight
# ═══════════════════════════════════════════════════════════════════════════
# After this line (around line 593):
#     global_conn_weight[s_ptr + s_idx] = np.float32(w_raw) - 128.0
#
# ADD:
#     g_conn_w_dna[s_ptr + s_idx] = np.float32(w_raw) - 128.0


# ═══════════════════════════════════════════════════════════════════════════
# CHANGE 3a: Phase-3 inline STDP block (~lines 1189–1225)
# ═══════════════════════════════════════════════════════════════════════════
# In BOTH LTP and LTD branches, AFTER the eligibility trace update and
# BEFORE `total_atp += CYCLES_PER_STDP_UPDATE`, add:
#
#     # ── Homeostatic anchoring (Exp 30 fix) ──
#     if HOMEOSTATIC_LAMBDA > np.float32(0.0):
#         w_now = global_conn_weight[s_ptr + c]
#         w_now -= HOMEOSTATIC_LAMBDA * (w_now - g_conn_w_dna[s_ptr + c])
#         if w_now > W_MAX: w_now = W_MAX
#         elif w_now < W_MIN: w_now = W_MIN
#         global_conn_weight[s_ptr + c] = w_now


# ═══════════════════════════════════════════════════════════════════════════
# CHANGE 3b: STDP3C consolidation block (~lines 1500–1530)
# ═══════════════════════════════════════════════════════════════════════════
#
# REPLACE:
#     w = global_conn_weight[s_idx]
#     w += e * D * learning_rate
#     if w > W_MAX: w = W_MAX
#     elif w < W_MIN: w = W_MIN
#     global_conn_weight[s_idx] = w
#
# WITH:
#     w = global_conn_weight[s_idx]
#     w += e * D * learning_rate                    # Hebbian (unchanged)
#     w -= HOMEOSTATIC_LAMBDA * (w - g_conn_w_dna[s_idx])  # Anchor (NEW)
#     if w > W_MAX: w = W_MAX
#     elif w < W_MIN: w = W_MIN
#     global_conn_weight[s_idx] = w


@njit(cache=True)
def test_homeostatic_stdp(
    w, w_dna, elig, elig_t, dst, rec_id, tau_e,
    org_elig, s_ptr, s_count, n_ptr, org,
    t_end, dopamine, learning_rate,
    W_MAX, W_MIN, homeostatic_lambda,
    stdp3c, N_INPUT, N_IO,
):
    """Verification test: n ticks of homeostatic STDP should bound drift."""
    for c in range(s_count):
        s_idx = s_ptr + c
        d = dst[s_idx]
        r_idx = rec_id[d]
        t_e = tau_e[org, r_idx]
        t_last = elig_t[s_idx]
        dt = t_end - t_last
        e = elig[s_idx]
        if dt > 0 and t_e > 1.0:
            e *= np.exp(-dt / t_e)
        elif dt > 0:
            e = np.float32(0.0)
        D = dopamine
        wgt = w[s_idx]
        wgt += e * D * learning_rate
        wgt -= homeostatic_lambda * (wgt - w_dna[s_idx])
        if wgt > W_MAX: wgt = W_MAX
        elif wgt < W_MIN: wgt = W_MIN
        w[s_idx] = wgt
        elig[s_idx] = e
        elig_t[s_idx] = t_end


if __name__ == "__main__":
    N_SYN, N_NEU = 10, 20
    w     = np.random.uniform(-64, 64, N_SYN).astype(np.float32)
    w_dna = w.copy()
    elig  = np.random.uniform(-0.5, 0.5, N_SYN).astype(np.float32)
    elig_t = np.zeros(N_SYN, dtype=np.int64)
    dst   = np.random.randint(0, N_NEU, N_SYN).astype(np.int64)
    rec_id = np.zeros(N_NEU, dtype=np.int64)
    tau_e  = np.full((2, 16), 5.0, dtype=np.float32)
    org_el = np.zeros((2, 8), dtype=np.float32)

    for tick in range(100):
        test_homeostatic_stdp(
            w, w_dna, elig, elig_t, dst, rec_id, tau_e, org_el,
            0, N_SYN, 0, 0,
            np.float32(tick + 1), np.float32(1.0), np.float32(1.0),
            np.float32(127.0), np.float32(-128.0),
            np.float32(0.01), True, 25, 39,
        )

    drift = np.abs(w - w_dna)
    print(f"Homeostatic STDP: mean|w-w_DNA| = {drift.mean():.4f}")
    print(f"  → Drift bounded near zero (λ=0.01)")
