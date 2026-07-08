import numpy as np
from numba import njit
import random

RAM_SIZE = 65536

N_INPUT  = 15
N_OUTPUT = 14
N_IO     = N_INPUT + N_OUTPUT

OUT_JMP_FWD    = 0
OUT_JMP_BCK    = 1
OUT_JMP_FWD_10 = 2
OUT_JMP_BCK_10 = 3
OUT_CONSUME    = 4
OUT_REPRODUCE  = 5

GENE_MARKER  = 161
NEURON_MARKER = 162
RECEPTOR_MARKER = 195
MAX_RECEPTORS_PER_ORG = 16

V_THRESH_IO  = np.float32(-50.0)
DT           = np.float32(0.5)
TAU_REF      = 4
W_MIN   = np.float32(-15.0)
W_MAX   = np.float32(15.0)

# THERMODYNAMICS = RAW EXECUTION CYCLES
CYCLES_PER_SPIKE_CHECK = np.float32(1.0)
CYCLES_PER_SYNAPSE_READ = np.float32(1.0)
CYCLES_PER_MOVE = np.float32(3.0) 
CYCLES_PER_EAT_GAIN = np.float32(1024.0) 
CYCLES_PER_BYTE_COPY = np.float32(1.0)
ATP_MAX = np.float32(1000000.0)

MAX_ORGANISMS = 600
BIRTH_BUF_SZ  = 150

# UNIVERSE PHYSICAL LIMITS
UNIVERSE_MAX_NEURONS = 500000
UNIVERSE_MAX_SYNAPSES = 2000000
UNIVERSE_MAX_DNA = 5000000
MAX_DNA_PER_ORG = 8192

@njit(cache=True)
def malloc_block(count, g_map):
    if count <= 0: return 0
    consecutive = 0
    start = -1
    for i in range(len(g_map)):
        if not g_map[i]:
            if consecutive == 0:
                start = i
            consecutive += 1
            if consecutive == count:
                for j in range(start, start + count):
                    g_map[j] = True
                return start
        else:
            consecutive = 0
    return -1

@njit(cache=True)
def free_block(start, count, g_map):
    if start >= 0 and count > 0:
        for i in range(start, start + count):
            g_map[i] = False

@njit(cache=True)
def parse_receptors(
    g_ptr, g_count, global_genome, org_id,
    o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m,
    o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max
):
    for i in range(MAX_RECEPTORS_PER_ORG):
        o_rec_a_plus[org_id, i] = 0.0
        o_rec_a_minus[org_id, i] = 0.0
        o_rec_tau_p[org_id, i] = 20.0
        o_rec_tau_m[org_id, i] = 20.0
        o_rec_v_rest[org_id, i] = -65.0
        o_rec_v_reset[org_id, i] = -70.0
        o_rec_tau_def[org_id, i] = 20.0
        o_rec_spk_max[org_id, i] = 0.5
        
    i = 0
    rec_found = 0
    while i < g_count - 9:
        marker = global_genome[g_ptr + i]
        if marker == RECEPTOR_MARKER:
            r_idx = global_genome[g_ptr + i + 1] % MAX_RECEPTORS_PER_ORG
            o_rec_a_plus[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 2]) / 255.0 * 0.1
            o_rec_a_minus[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 3]) / 255.0 * 0.1
            o_rec_tau_p[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 4]) / 255.0 * 60.0 + 1.0
            o_rec_tau_m[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 5]) / 255.0 * 60.0 + 1.0
            o_rec_v_rest[org_id, r_idx] = (np.float32(global_genome[g_ptr + i + 6]) / 255.0 * 100.0) - 100.0
            o_rec_v_reset[org_id, r_idx] = (np.float32(global_genome[g_ptr + i + 7]) / 255.0 * 100.0) - 100.0
            o_rec_tau_def[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 8]) / 255.0 * 60.0 + 1.0
            o_rec_spk_max[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 9]) / 255.0 * 1.0 + 0.1
            rec_found += 1
            i += 10
        elif marker == GENE_MARKER: i += 4
        elif marker == NEURON_MARKER: i += 5
        else: i += 1
    
    return True

@njit(cache=True)
def count_genes(g_ptr, g_count, g_genome):
    s_count = 0
    h_count = 0
    i = g_ptr + 8 # Skip physics header
    end = g_ptr + g_count - 3
    while i < end:
        marker = g_genome[i]
        if marker == GENE_MARKER and i + 3 < g_count:
            s_count += 1
            i += 4
        elif marker == NEURON_MARKER and i + 4 < g_count:
            h_count += 1
            i += 5
        elif marker == RECEPTOR_MARKER and i + 9 < g_count:
            i += 10
        else:
            i += 1
            
    return s_count, h_count

@njit(cache=True)
def decode_genome(
    g_ptr, g_count, global_genome,
    n_ptr, n_c, s_ptr,
    global_conn_src, global_conn_dst, global_conn_weight,
    global_thresh, global_tau, global_rec_id,
    o_rec_v_rest, o_rec_tau_def, org_id
):
    s_idx = 0
    h_idx = 0
    
    for i in range(N_IO):
        global_rec_id[n_ptr + i] = 0
        global_thresh[n_ptr + i] = o_rec_v_rest[org_id, 0] + 15.0
        global_tau[n_ptr + i] = o_rec_tau_def[org_id, 0]
        
    i = 0
    while i < g_count - 3:
        marker = global_genome[g_ptr + i]
        if marker == GENE_MARKER:
            if i + 3 < g_count:
                src = global_genome[g_ptr + i + 1]
                dst = global_genome[g_ptr + i + 2]
                w_raw = global_genome[g_ptr + i + 3]
                
                actual_src = src % n_c
                actual_dst = dst % n_c
                
                if actual_dst >= N_INPUT:
                    global_conn_src[s_ptr + s_idx] = actual_src
                    global_conn_dst[s_ptr + s_idx] = actual_dst
                    global_conn_weight[s_ptr + s_idx] = (np.float32(w_raw) - 128.0) / 8.0
                    s_idx += 1
            i += 4
        elif marker == NEURON_MARKER and i + 4 < g_count:
            if N_IO + h_idx < n_c:
                rec_id = global_genome[g_ptr + i + 2] % MAX_RECEPTORS_PER_ORG
                global_rec_id[n_ptr + N_IO + h_idx] = rec_id
                t = np.float32(global_genome[g_ptr + i + 3]) / 255.0 * 20.0
                global_thresh[n_ptr + N_IO + h_idx] = o_rec_v_rest[org_id, rec_id] + 10.0 + t
                global_tau[n_ptr + N_IO + h_idx] = np.float32(global_genome[g_ptr + i + 4]) / 255.0 * 40.0 + 5.0
                h_idx += 1
            i += 5
        elif marker == RECEPTOR_MARKER and i + 9 < g_count:
            i += 10
        else:
            i += 1
    return s_idx

@njit(cache=True)
def sense(pos, ram_substrate, org_grid, energy, oracle_val, vocal_cords, sense_buf):
    sense_buf.fill(0.0)
    sense_buf[0] = energy / ATP_MAX
    sense_buf[1] = 0.5
    sense_buf[2] = 0.5
    
    addr = pos % RAM_SIZE
    v = ram_substrate[addr] / np.float32(255.0)
    sense_buf[3] = v
    
    left_pos = (pos - 1) % RAM_SIZE
    right_pos = (pos + 1) % RAM_SIZE
    
    voice_acc = 0
    if org_grid[left_pos] != -1: voice_acc |= vocal_cords[org_grid[left_pos]]
    if org_grid[right_pos] != -1: voice_acc |= vocal_cords[org_grid[right_pos]]
    
    sense_buf[4] = (voice_acc & 0x07) / 7.0
    sense_buf[5] = ((voice_acc >> 3) & 0x07) / 7.0
    sense_buf[6] = ((voice_acc >> 6) & 0x03) / 3.0
    
    for bit in range(8):
        if oracle_val & (1 << bit):
            sense_buf[7 + bit] = 1.0

@njit(cache=True)
def apply_stdp(n_ptr, s_ptr, s_count, g_conn_src, g_conn_dst, g_conn_weight, g_t_last, t,
               org, global_rec_id, o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m):
    for c in range(s_count):
        src = g_conn_src[s_ptr + c]
        dst = g_conn_dst[s_ptr + c]
        
        t_pre = g_t_last[n_ptr + src]
        t_post = g_t_last[n_ptr + dst]
        
        if t_pre < 0 or t_post < 0:
            continue
            
        dt = np.float32(t_post - t_pre) * DT
        weight = g_conn_weight[s_ptr + c]
        r_idx = global_rec_id[n_ptr + dst]
        if dt > 0:
            weight += o_rec_a_plus[org, r_idx] * np.exp(-dt / o_rec_tau_p[org, r_idx])
        elif dt < 0:
            weight -= o_rec_a_minus[org, r_idx] * np.exp(dt / o_rec_tau_m[org, r_idx])
            
        if weight > W_MAX: weight = W_MAX
        elif weight < W_MIN: weight = W_MIN
        g_conn_weight[s_ptr + c] = weight

@njit(cache=True)
def world_tick_numba(
    ram_substrate, org_grid, positions, alive, energy, age,
    global_v, global_ref, global_t_last, global_thresh, global_tau, global_rec_id,
    global_conn_src, global_conn_dst, global_conn_weight,
    neuron_map, synapse_map, genome_map,
    org_n_ptr, org_n_count, org_s_ptr, org_s_count,
    global_genome, org_g_ptr, org_g_count,
    o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m, o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max,
    viscosity, global_time, n_lif_steps,
    b_pos, b_parent, b_g_start, b_g_count, b_genomes,
    oracle_val, oracle_target, voice_buf, vocal_cords
):
    max_org = alive.shape[0]
    sense_buf = np.zeros(N_INPUT, dtype=np.float32)
    atp_buf = np.zeros(1, dtype=np.float32)
    out_accum = np.zeros(N_OUTPUT, dtype=np.int32)
    
    n_births = np.int32(0)

    for org in range(max_org):
        if not alive[org]:
            continue

        pos = positions[org]
        for o in range(N_OUTPUT):
            out_accum[o] = 0
            
        total_atp = np.float32(0.0)
        n_count = org_n_count[org]
        prev_spk = np.zeros(n_count, dtype=np.bool_)

        for step in range(n_lif_steps):
            if random.random() < viscosity[org]:
                total_atp += np.float32(n_count)
                continue
                
            sense(pos, ram_substrate, org_grid, energy[org], oracle_val, vocal_cords, sense_buf)
            current_spk = np.zeros(n_count, dtype=np.bool_)
            t_now = global_time + step
            
            n_ptr = org_n_ptr[org]
            for n in range(n_count):
                r_idx = global_rec_id[n_ptr + n]
                spike_val = 1.0 * o_rec_spk_max[org, r_idx]
                if spike_val > 1.0: spike_val = 1.0
                
                # Internal spike logic placeholder
                if n < N_INPUT:
                    if random.random() < sense_buf[n] * spike_val:
                        current_spk[n] = True
                
            total_atp += 0.1
            apply_stdp(
                org_n_ptr[org], org_s_ptr[org], org_s_count[org], global_conn_src, global_conn_dst, global_conn_weight, global_t_last, t_now,
                org, global_rec_id, o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m
            )
            prev_spk = current_spk

        best_a = -1
        best_n = 0
        for o in range(6): 
            if out_accum[o] > best_n:
                best_n = out_accum[o]
                best_a = o
                
        org_char_val = 0
        for v_idx in range(8):
            if out_accum[6 + v_idx] > 0:
                org_char_val |= (1 << v_idx)
        
        if org == 0:
            if org_char_val >= 32 and org_char_val <= 126:
                for v_buf_idx in range(len(voice_buf)):
                    if voice_buf[v_buf_idx] == 0:
                        voice_buf[v_buf_idx] = org_char_val
                        break

        vocal_cords[org] = org_char_val
        energy[org] -= total_atp

        if best_n > 0 and best_a >= 0:
            if best_a == OUT_JMP_FWD:
                npos = (pos + 1) % RAM_SIZE
                energy[org] -= CYCLES_PER_MOVE
                if org_grid[npos] == -1:
                    org_grid[pos] = -1
                    positions[org] = npos; org_grid[npos] = org
                    pos = npos
            elif best_a == OUT_JMP_BCK:
                npos = (pos - 1) % RAM_SIZE
                if npos < 0: npos += RAM_SIZE
                energy[org] -= CYCLES_PER_MOVE
                if org_grid[npos] == -1:
                    org_grid[pos] = -1
                    positions[org] = npos; org_grid[npos] = org
                    pos = npos
            elif best_a == OUT_JMP_FWD_10:
                npos = (pos + 10) % RAM_SIZE
                energy[org] -= CYCLES_PER_MOVE
                if org_grid[npos] == -1:
                    org_grid[pos] = -1
                    positions[org] = npos; org_grid[npos] = org
                    pos = npos
            elif best_a == OUT_JMP_BCK_10:
                npos = (pos - 10) % RAM_SIZE
                if npos < 0: npos += RAM_SIZE
                energy[org] -= CYCLES_PER_MOVE
                if org_grid[npos] == -1:
                    org_grid[pos] = -1
                    positions[org] = npos; org_grid[npos] = org
                    pos = npos
            elif best_a == OUT_CONSUME:
                val = ram_substrate[pos]
                if val == 0x55:
                    energy[org] += CYCLES_PER_EAT_GAIN
                    ram_substrate[pos] = 0x00
                    if energy[org] > ATP_MAX:
                        energy[org] = ATP_MAX
                elif val == 0xFF:
                    energy[org] -= 1000.0
                    ram_substrate[pos] = 0x00

            elif best_a == OUT_REPRODUCE:
                g_count = org_g_count[org]
                copy_cost = np.float32(g_count) * CYCLES_PER_BYTE_COPY
                child_reserve = np.float32(25000.0)
                
                if energy[org] >= copy_cost + child_reserve and n_births < b_pos.shape[0]:
                    energy[org] -= (copy_cost + child_reserve)
                    b_pos[n_births]    = pos
                    b_parent[n_births] = org
                    
                    g_start = org_g_ptr[org]
                    b_g_start[n_births] = g_start
                    b_g_count[n_births] = g_count
                    
                    for x in range(g_count):
                        b_genomes[n_births, x] = global_genome[g_start + x]
                        
                    n_births += 1

        age[org] += n_lif_steps

        if energy[org] <= np.float32(0.0):
            alive[org] = False
            org_grid[positions[org]] = -1
            free_block(org_n_ptr[org], org_n_count[org], neuron_map)
            free_block(org_s_ptr[org], org_s_count[org], synapse_map)
            free_block(org_g_ptr[org], org_g_count[org], genome_map)

    n_alive_new = np.int32(0)
    for i in range(max_org):
        if alive[i]:
            n_alive_new += 1

    return n_alive_new, n_births
