import numpy as np
from numba import njit
import random

# ═══════════════════════════════════════════════════════════════════════════════
#  جهان — World Geometry
# ═══════════════════════════════════════════════════════════════════════════════
WORLD_W  = 64
WORLD_H  = 64
WORLD_SZ = WORLD_W * WORLD_H   # 4096 سلول

# ═══════════════════════════════════════════════════════════════════════════════
#  توپولوژی شبکه — fixed در فاز ۱، در فاز ۲ با NEAT تکامل مییابد
# ═══════════════════════════════════════════════════════════════════════════════
N_INPUT  = 7    # نورونهای حسی
N_HIDDEN = 16   # نورونهای پنهان (genome-encoded)
N_OUTPUT = 6    # نورونهای حرکتی
N_ALL    = N_INPUT + N_HIDDEN + N_OUTPUT  # 29 نورون کل

# آفست لایهها
H_OFF = N_INPUT                 # نورونهای پنهان از ۷ شروع میشوند
O_OFF = N_INPUT + N_HIDDEN      # نورونهای خروجی از ۲۳ شروع میشوند

# نورونهای خروجی — اکشنها
OUT_N        = 0   # حرکت شمال
OUT_S        = 1   # حرکت جنوب
OUT_E        = 2   # حرکت شرق
OUT_W        = 3   # حرکت غرب
OUT_EAT      = 4   # خوردن غذا
OUT_REPRODUCE= 5   # تولیدمثل

# ═══════════════════════════════════════════════════════════════════════════════
#  ژنوم — Genome Layout (256 بایت)
# ═══════════════════════════════════════════════════════════════════════════════
# [  0..111] : w_ih  — وزنهای ورودی→پنهان   (7×16 = 112 بایت)
# [112..207] : w_ho  — وزنهای پنهان→خروجی  (16×6 = 96 بایت)
# [208..223] : thresh — آستانه نورونهای پنهان (16 بایت)
# [224..239] : tau   — ثابتزمانی نورونهای پنهان (16 بایت)
# [240..255] : reserved
GENOME_SZ    = 256
G_WIH_START  = 0
G_WIH_LEN    = N_INPUT * N_HIDDEN        # 112
G_WHO_START  = G_WIH_START + G_WIH_LEN  # 112
G_WHO_LEN    = N_HIDDEN * N_OUTPUT       # 96
G_THR_START  = G_WHO_START + G_WHO_LEN  # 208
G_TAU_START  = G_THR_START + N_HIDDEN   # 224

# ═══════════════════════════════════════════════════════════════════════════════
#  ثابتهای بیوفیزیکی — Biophysical Constants
# ═══════════════════════════════════════════════════════════════════════════════
V_REST       = np.float32(-65.0)   # پتانسیل استراحت (mV)
V_RESET      = np.float32(-70.0)   # ریست بعد از اسپایک (mV)
V_THRESH_IO  = np.float32(-50.0)   # آستانه ثابت برای لایه ورودی/خروجی (mV)
DT           = np.float32(0.5)     # گام زمانی LIF (ms)
TAU_DEFAULT  = np.float32(20.0)    # ثابتزمانی پیشفرض (ms)
TAU_REF      = 4                   # دوره تناوب (تیک)

# STDP — Spike-Timing Dependent Plasticity
A_PLUS  = np.float32(0.04)    # دامنه LTP
A_MINUS = np.float32(0.044)   # دامنه LTD
TAU_P   = np.float32(20.0)    # پنجره LTP (ms)
TAU_M   = np.float32(20.0)    # پنجره LTD (ms)
W_MIN   = np.float32(-15.0)
W_MAX   = np.float32(15.0)

# ATP — انرژی
ATP_SPIKE      = np.float32(2.5)   # هزینه هر اسپایک
ATP_LEAK       = np.float32(0.04)  # نشت غیرفعال: هر نورون هر تیک
ATP_MOVE       = np.float32(6.0)   # حرکت
ATP_EAT_GAIN   = np.float32(3.0)   # سود خوردن: به ازای هر واحد غذا
ATP_REPR_COST  = np.float32(120.0) # آستانه + هزینه تولیدمثل
ATP_CHILD_INIT = np.float32(80.0)  # انرژی اولیه نوزاد
ATP_INIT       = np.float32(250.0) # انرژی اولیه موجود تازه-seed
ATP_MAX        = np.float32(500.0)

# ═══════════════════════════════════════════════════════════════════════════════
#  ثابتهای جهان
# ═══════════════════════════════════════════════════════════════════════════════
FOOD_DECAY        = np.float32(0.993)  # فساد غذا هر تیک
FOOD_INFLUX       = np.float32(1800.0) # کل غذا اضافهشده هر world-tick
SUN_FRAC          = 0.15              # ۱۵٪ جهان = منطقه خورشید
SPIKE_RATE_MAX    = np.float32(0.55)   # ماکزیمم احتمال شلیک ورودی در هر تیک

MAX_ORGANISMS = 600
BIRTH_BUF_SZ  = 150


# ═══════════════════════════════════════════════════════════════════════════════
#  ژنوم ↔ پارامترهای شبکه
# ═══════════════════════════════════════════════════════════════════════════════

@njit(cache=True)
def decode_genome(genome, w_ih, w_ho, thresh_h, tau_h):
    for i in range(N_INPUT):
        for h in range(N_HIDDEN):
            w_ih[i, h] = (np.float32(genome[G_WIH_START + i * N_HIDDEN + h]) - 128.0) / 8.0

    for h in range(N_HIDDEN):
        for o in range(N_OUTPUT):
            w_ho[h, o] = (np.float32(genome[G_WHO_START + h * N_OUTPUT + o]) - 128.0) / 8.0

    for h in range(N_HIDDEN):
        thresh_h[h] = np.float32(-58.0) + (np.float32(genome[G_THR_START + h]) / np.float32(255.0)) * np.float32(16.0)

    for h in range(N_HIDDEN):
        tau_h[h] = np.float32(10.0) + (np.float32(genome[G_TAU_START + h]) / np.float32(255.0)) * np.float32(30.0)


@njit(cache=True)
def encode_weights_to_genome(genome, w_ih, w_ho, thresh_h, tau_h):
    for i in range(N_INPUT):
        for h in range(N_HIDDEN):
            val = w_ih[i, h] * 8.0 + 128.0
            if val < 0.0: val = 0.0
            if val > 255.0: val = 255.0
            genome[G_WIH_START + i * N_HIDDEN + h] = np.uint8(val)

    for h in range(N_HIDDEN):
        for o in range(N_OUTPUT):
            val = w_ho[h, o] * 8.0 + 128.0
            if val < 0.0: val = 0.0
            if val > 255.0: val = 255.0
            genome[G_WHO_START + h * N_OUTPUT + o] = np.uint8(val)

    for h in range(N_HIDDEN):
        val = int((thresh_h[h] - (-58.0)) / 16.0 * 255.0)
        if val < 0:   val = 0
        if val > 255: val = 255
        genome[G_THR_START + h] = np.uint8(val)

    for h in range(N_HIDDEN):
        val = int((tau_h[h] - 10.0) / 30.0 * 255.0)
        if val < 0:   val = 0
        if val > 255: val = 255
        genome[G_TAU_START + h] = np.uint8(val)


# ═══════════════════════════════════════════════════════════════════════════════
#  هندسه جهان
# ═══════════════════════════════════════════════════════════════════════════════

@njit(cache=True)
def cell(x, y):
    return ((y + WORLD_H) % WORLD_H) * WORLD_W + ((x + WORLD_W) % WORLD_W)


# ═══════════════════════════════════════════════════════════════════════════════
#  رمزگذاری حسی — Rate Coding
# ═══════════════════════════════════════════════════════════════════════════════

@njit(cache=True)
def sense(pos, food_grid, org_grid, energy, out):
    x = pos % WORLD_W
    y = pos // WORLD_W

    v = food_grid[pos] / np.float32(128.0)
    out[0] = v if v < np.float32(1.0) else np.float32(1.0)

    v = food_grid[cell(x, y - 1)] / np.float32(128.0)
    out[1] = v if v < np.float32(1.0) else np.float32(1.0)

    v = food_grid[cell(x, y + 1)] / np.float32(128.0)
    out[2] = v if v < np.float32(1.0) else np.float32(1.0)

    v = food_grid[cell(x + 1, y)] / np.float32(128.0)
    out[3] = v if v < np.float32(1.0) else np.float32(1.0)

    v = food_grid[cell(x - 1, y)] / np.float32(128.0)
    out[4] = v if v < np.float32(1.0) else np.float32(1.0)

    v = energy / ATP_MAX
    out[5] = v if v < np.float32(1.0) else np.float32(1.0)

    n = 0
    if org_grid[cell(x, y - 1)] >= 0: n += 1
    if org_grid[cell(x, y + 1)] >= 0: n += 1
    if org_grid[cell(x + 1, y)] >= 0: n += 1
    if org_grid[cell(x - 1, y)] >= 0: n += 1
    out[6] = np.float32(n) / np.float32(4.0)


# ═══════════════════════════════════════════════════════════════════════════════
#  دینامیک LIF — Leaky Integrate-and-Fire
# ═══════════════════════════════════════════════════════════════════════════════

@njit(cache=True)
def lif_step(v, ref, t_last,
             thresh_h, tau_h,
             w_ih, w_ho,
             sense_rates, t,
             out_spikes, atp_out):
    in_spk  = np.zeros(N_INPUT,  dtype=np.bool_)
    hid_spk = np.zeros(N_HIDDEN, dtype=np.bool_)
    I_h     = np.zeros(N_HIDDEN, dtype=np.float32)
    I_o     = np.zeros(N_OUTPUT, dtype=np.float32)

    for i in range(N_INPUT):
        if ref[i] > 0:
            ref[i] -= 1
        else:
            if random.random() < sense_rates[i] * SPIKE_RATE_MAX:
                in_spk[i]  = True
                v[i]        = V_RESET
                ref[i]      = TAU_REF
                t_last[i]   = t

    for i in range(N_INPUT):
        if in_spk[i]:
            for h in range(N_HIDDEN):
                I_h[h] += w_ih[i, h]

    for h in range(N_HIDDEN):
        hi = H_OFF + h
        if ref[hi] > 0:
            ref[hi] -= 1
            v[hi] = V_REST
        else:
            v[hi] += I_h[h]
            dv = -(v[hi] - V_REST) * DT / tau_h[h]
            v[hi] += dv
            if v[hi] >= thresh_h[h]:
                hid_spk[h]   = True
                v[hi]        = V_RESET
                ref[hi]      = TAU_REF
                t_last[hi]   = t

    for h in range(N_HIDDEN):
        if hid_spk[h]:
            for o in range(N_OUTPUT):
                I_o[o] += w_ho[h, o]

    for o in range(N_OUTPUT):
        oi = O_OFF + o
        out_spikes[o] = False
        if ref[oi] > 0:
            ref[oi] -= 1
            v[oi] = V_REST
        else:
            v[oi] += I_o[o]
            dv = -(v[oi] - V_REST) * DT / TAU_DEFAULT
            v[oi] += dv
            if v[oi] >= V_THRESH_IO:
                out_spikes[o]  = True
                v[oi]          = V_RESET
                ref[oi]        = TAU_REF
                t_last[oi]     = t

    cost = ATP_LEAK * np.float32(N_ALL)

    for i in range(N_INPUT):
        if in_spk[i]:  cost += ATP_SPIKE
    for h in range(N_HIDDEN):
        if hid_spk[h]: cost += ATP_SPIKE
    for o in range(N_OUTPUT):
        if out_spikes[o]: cost += ATP_SPIKE

    atp_out[0] = cost


# ═══════════════════════════════════════════════════════════════════════════════
#  STDP — قانون یادگیری هبی
# ═══════════════════════════════════════════════════════════════════════════════

@njit(cache=True)
def apply_stdp(w_ih, w_ho, t_last, t):
    for i in range(N_INPUT):
        t_pre = t_last[i]
        if t_pre < 0:
            continue
        for h in range(N_HIDDEN):
            t_post = t_last[H_OFF + h]
            if t_post < 0:
                continue
            dt = np.float32(t_post - t_pre) * DT
            if dt > np.float32(0.1):
                dw = A_PLUS * np.exp(-dt / TAU_P)
            elif dt < np.float32(-0.1):
                dw = -A_MINUS * np.exp(dt / TAU_M)
            else:
                continue
            w = w_ih[i, h] + dw
            if w < W_MIN: w = W_MIN
            if w > W_MAX: w = W_MAX
            w_ih[i, h] = w

    for h in range(N_HIDDEN):
        t_pre = t_last[H_OFF + h]
        if t_pre < 0:
            continue
        for o in range(N_OUTPUT):
            t_post = t_last[O_OFF + o]
            if t_post < 0:
                continue
            dt = np.float32(t_post - t_pre) * DT
            if dt > np.float32(0.1):
                dw = A_PLUS * np.exp(-dt / TAU_P)
            elif dt < np.float32(-0.1):
                dw = -A_MINUS * np.exp(dt / TAU_M)
            else:
                continue
            w = w_ho[h, o] + dw
            if w < W_MIN: w = W_MIN
            if w > W_MAX: w = W_MAX
            w_ho[h, o] = w


# ═══════════════════════════════════════════════════════════════════════════════
#  حلقه اصلی — World Tick (Numba JIT)
# ═══════════════════════════════════════════════════════════════════════════════

@njit(nogil=True, cache=True)
def world_tick_numba(
    food_grid, org_grid,
    positions, alive, energy, age,
    v_mem, ref, t_last,
    thresh_h, tau_h, w_ih, w_ho, genomes,
    t_lif, n_lif_steps,
    b_pos, b_parent,
    b_w_ih, b_w_ho, b_thresh, b_tau, b_genome
):
    max_org = positions.shape[0]

    for i in range(WORLD_SZ):
        food_grid[i] *= FOOD_DECAY

    sun_center = (t_lif // 200) % WORLD_SZ
    sun_w      = int(WORLD_W * SUN_FRAC)
    n_drops    = int(FOOD_INFLUX / 64.0)
    if n_drops < 8: n_drops = 8

    for _ in range(n_drops):
        offset = int(random.gauss(0.0, float(sun_w) / 3.0))
        idx = (sun_center + offset) % WORLD_SZ
        if idx < 0: idx += WORLD_SZ
        food_grid[idx] += np.float32(64.0)
        if food_grid[idx] > np.float32(255.0):
            food_grid[idx] = np.float32(255.0)

    n_births   = np.int32(0)
    sense_buf  = np.zeros(N_INPUT,  dtype=np.float32)
    out_spikes = np.zeros(N_OUTPUT, dtype=np.bool_)
    atp_buf    = np.zeros(1,        dtype=np.float32)
    out_accum  = np.zeros(N_OUTPUT, dtype=np.int32)

    for org in range(max_org):
        if not alive[org]:
            continue

        pos = positions[org]
        x   = pos % WORLD_W
        y   = pos // WORLD_W

        for o in range(N_OUTPUT):
            out_accum[o] = 0
        total_atp = np.float32(0.0)

        for step in range(n_lif_steps):
            sense(pos, food_grid, org_grid, energy[org], sense_buf)
            lif_step(
                v_mem[org], ref[org], t_last[org],
                thresh_h[org], tau_h[org],
                w_ih[org], w_ho[org],
                sense_buf, t_lif + step,
                out_spikes, atp_buf
            )
            for o in range(N_OUTPUT):
                if out_spikes[o]:
                    out_accum[o] += 1
            total_atp += atp_buf[0]
            apply_stdp(w_ih[org], w_ho[org], t_last[org], t_lif + step)

        energy[org] -= total_atp

        best_a = -1
        best_n = 0
        for o in range(N_OUTPUT):
            if out_accum[o] > best_n:
                best_n = out_accum[o]
                best_a = o

        if best_a >= 0 and best_n > 0:
            if best_a == OUT_N:
                npos = cell(x, y - 1)
                org_grid[pos] = -1
                positions[org] = npos; org_grid[npos] = org
                energy[org] -= ATP_MOVE
                pos = npos; x = pos % WORLD_W; y = pos // WORLD_W

            elif best_a == OUT_S:
                npos = cell(x, y + 1)
                org_grid[pos] = -1
                positions[org] = npos; org_grid[npos] = org
                energy[org] -= ATP_MOVE
                pos = npos; x = pos % WORLD_W; y = pos // WORLD_W

            elif best_a == OUT_E:
                npos = cell(x + 1, y)
                org_grid[pos] = -1
                positions[org] = npos; org_grid[npos] = org
                energy[org] -= ATP_MOVE
                pos = npos; x = pos % WORLD_W; y = pos // WORLD_W

            elif best_a == OUT_W:
                npos = cell(x - 1, y)
                org_grid[pos] = -1
                positions[org] = npos; org_grid[npos] = org
                energy[org] -= ATP_MOVE
                pos = npos; x = pos % WORLD_W; y = pos // WORLD_W

            elif best_a == OUT_EAT:
                food = food_grid[pos]
                if food > np.float32(1.0):
                    bite = food if food < np.float32(24.0) else np.float32(24.0)
                    food_grid[pos] -= bite
                    gain = bite * ATP_EAT_GAIN
                    energy[org] += gain
                    if energy[org] > ATP_MAX:
                        energy[org] = ATP_MAX

            elif best_a == OUT_REPRODUCE:
                if energy[org] >= ATP_REPR_COST and n_births < b_pos.shape[0]:
                    energy[org] -= ATP_REPR_COST
                    encode_weights_to_genome(
                        genomes[org],
                        w_ih[org], w_ho[org],
                        thresh_h[org], tau_h[org]
                    )
                    b_pos[n_births]    = pos
                    b_parent[n_births] = org
                    for i2 in range(N_INPUT):
                        for h2 in range(N_HIDDEN):
                            b_w_ih[n_births, i2, h2] = w_ih[org, i2, h2]
                    for h2 in range(N_HIDDEN):
                        for o2 in range(N_OUTPUT):
                            b_w_ho[n_births, h2, o2] = w_ho[org, h2, o2]
                    for h2 in range(N_HIDDEN):
                        b_thresh[n_births, h2] = thresh_h[org, h2]
                        b_tau[n_births, h2]    = tau_h[org, h2]
                    for g in range(GENOME_SZ):
                        b_genome[n_births, g] = genomes[org, g]
                    n_births += 1

        age[org] += n_lif_steps

        if energy[org] <= np.float32(0.0):
            alive[org] = False
            org_grid[positions[org]] = -1

    n_alive_new = np.int32(0)
    for i in range(max_org):
        if alive[i]:
            n_alive_new += 1

    return n_alive_new, n_births
