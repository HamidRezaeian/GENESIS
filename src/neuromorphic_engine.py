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

# V_THRESH_IO removed: was dead code (defined but never referenced)
DT           = np.float32(1.0)
TAU_REF      = 1
W_MIN   = np.float32(-128.0)
W_MAX   = np.float32(127.0)

# THERMODYNAMICS = RAW EXECUTION CYCLES
CYCLES_PER_SPIKE_CHECK = np.float32(1.0)
CYCLES_PER_SYNAPSE_READ = np.float32(1.0)
CYCLES_PER_MOVE = np.float32(3.0)
CYCLES_PER_EAT_GAIN = np.float32(1024.0)
CYCLES_PER_BYTE_COPY = np.float32(1.0)
# Honest raw-cycle accounting (Rule 15/17): one canonical executed operation costs 1 cycle,
# the same unit already used for a synapse read (1) and a move (3). A neuron membrane update
# is real work done for every neuron every step, so it costs 1 cycle/neuron — replacing the
# old arbitrary 0.1 discount that made neuron footprint effectively non-selective. An STDP
# weight update (read + exp + scale + clamp + write) is likewise real work, charged only when
# it actually fires (activity-gated), so a large but sparsely-firing brain stays cheap — the
# 20W massive-sparse-parallelism paradigm (Rule 11), not a penalty on merely HAVING synapses.
CYCLES_PER_NEURON_UPDATE = np.float32(1.0)
CYCLES_PER_STDP_UPDATE   = np.float32(1.0)
ATP_MAX = np.float32(1000000.0)

# STDP increment scaling: raw receptor bytes are 0-255 but the whole weight range is only
# 256 wide, so an unscaled step slams weights to the rail (bang-bang STDP). Dividing by
# STDP_SCALE makes plasticity graded (max step ~32, ~12% of the range).
STDP_SCALE = np.float32(8.0)

# Computational viscosity (Rule 13): stall probability = (synapses / neurons) / this scale,
# capped at 0.5. Dense brains stall more, rewarding sparse parallel topologies.
SYN_DENSITY_SCALE = np.float32(8.0)

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
        o_rec_tau_p[org_id, i] = 1.0
        o_rec_tau_m[org_id, i] = 1.0
        o_rec_v_rest[org_id, i] = 0.0
        o_rec_v_reset[org_id, i] = 0.0
        o_rec_tau_def[org_id, i] = 1.0
        o_rec_spk_max[org_id, i] = 1.0
        
    i = 0
    rec_found = 0
    while i < g_count - 9:
        marker = global_genome[g_ptr + i]
        if marker == RECEPTOR_MARKER:
            r_idx = global_genome[g_ptr + i + 1] % MAX_RECEPTORS_PER_ORG
            o_rec_a_plus[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 2]) / STDP_SCALE
            o_rec_a_minus[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 3]) / STDP_SCALE
            o_rec_tau_p[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 4]) + 1.0
            o_rec_tau_m[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 5]) + 1.0
            # V_REST / V_RESET are now DNA-encoded (Rule 17 meta-learning), not hardcoded.
            # Ancestor header bytes are 0 -> identical to the previous behaviour, but
            # evolution can now raise the resting/reset potential of each receptor type.
            o_rec_v_rest[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 6])
            o_rec_v_reset[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 7])
            o_rec_tau_def[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 8]) + 1.0
            o_rec_spk_max[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 9]) / 255.0
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
    i = g_ptr
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
        global_thresh[n_ptr + i] = o_rec_v_rest[org_id, 0] + 128.0
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
                    global_conn_weight[s_ptr + s_idx] = np.float32(w_raw) - 128.0
                    s_idx += 1
            i += 4
        elif marker == NEURON_MARKER and i + 4 < g_count:
            if N_IO + h_idx < n_c:
                rec_id = global_genome[g_ptr + i + 2] % MAX_RECEPTORS_PER_ORG
                global_rec_id[n_ptr + N_IO + h_idx] = rec_id
                t = np.float32(global_genome[g_ptr + i + 3])
                global_thresh[n_ptr + N_IO + h_idx] = o_rec_v_rest[org_id, rec_id] + t
                global_tau[n_ptr + N_IO + h_idx] = np.float32(global_genome[g_ptr + i + 4]) + 1.0
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
def world_tick_numba(
    ram_substrate, org_grid, positions, alive, energy, age,
    global_v, global_ref, global_t_last, global_thresh, global_tau, global_rec_id,
    global_conn_src, global_conn_dst, global_conn_weight,
    neuron_map, synapse_map, genome_map,
    org_n_ptr, org_n_count, org_s_ptr, org_s_count,
    global_genome, org_g_ptr, org_g_count,
    o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m, o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max,
    viscosity, global_time, n_lif_steps,
    b_pos, b_parent, b_g_start, b_g_count, b_genomes, b_energy,
    oracle_val, oracle_target, voice_buf, vocal_cords, read_log
):
    max_org = alive.shape[0]
    sense_buf = np.zeros(N_INPUT, dtype=np.float32)
    atp_buf = np.zeros(1, dtype=np.float32)
    out_accum = np.zeros(N_OUTPUT, dtype=np.int32)
    
    n_births = np.int32(0)

    # Pre-allocate reusable buffers for spiking to avoid inside-loop allocations (massive speedup)
    prev_spk_buf = np.zeros(2048, dtype=np.bool_)
    curr_spk_buf = np.zeros(2048, dtype=np.bool_)

    # Cosmic Radiation Phase (Thermodynamic Entropy)
    # Flip bits INSIDE living genomes (germline mutation). Targeting allocated regions
    # rather than the whole multi-MB arena makes radiation a real evolutionary pressure
    # instead of ~99% of flips landing harmlessly in vacuum.
    for _ in range(2):
        tries = 0
        while tries < 16:
            o = random.randint(0, max_org - 1)
            if alive[o] and org_g_count[o] > 0:
                byte_off = random.randint(0, org_g_count[o] - 1)
                r_bit = random.randint(0, 7)
                global_genome[org_g_ptr[o] + byte_off] ^= (1 << r_bit)
                break
            tries += 1

    for org in range(max_org):
        if not alive[org]:
            continue

        pos = positions[org]
        for o in range(N_OUTPUT):
            out_accum[o] = 0
            
        total_atp = np.float32(0.0)
        n_count = org_n_count[org]
        
        # Zero the portion of the pre-allocated buffer we need
        for i in range(n_count):
            prev_spk_buf[i] = False

        # Spatial crowding: fraction of neighbouring RAM cells occupied by other organisms
        # (0..1). Fed to sensory input 2 so organisms can feel density and evolve dispersal.
        crowd_count = np.float32(0.0)
        for offset in range(-16, 17):
            if org_grid[(pos + offset + RAM_SIZE) % RAM_SIZE] != -1:
                crowd_count += 1.0
        crowding = crowd_count / np.float32(33.0)

        # Computational viscosity (Rule 13): stall probability rises with the organism's own
        # synaptic DENSITY (synapses per neuron), not mere spatial crowding. Dense brains
        # stall more often, rewarding sparse, parallel topologies (the 20W paradigm).
        code_density = np.float32(org_s_count[org]) / (np.float32(n_count) + np.float32(1.0))
        local_viscosity = code_density / SYN_DENSITY_SCALE
        if local_viscosity > np.float32(0.5):
            local_viscosity = np.float32(0.5)
        viscosity[org] = local_viscosity

        # Sensory input is invariant across this organism's LIF sub-steps: energy, pointer
        # position, the oracle broadcast and neighbour voices only change between world-ticks,
        # not within the step loop, and sense() is deterministic (no RNG). So compute it ONCE
        # per tick instead of re-scanning neighbours every step — a pure engine speedup with
        # identical dynamics, so the simulator itself needs less hardware for the same physics.
        sense(pos, ram_substrate, org_grid, energy[org], oracle_val, vocal_cords, sense_buf)
        # Input 2 = local spatial crowding (previously a dead constant 0.5), so organisms can
        # feel population density and evolve migration/dispersal away from the trap.
        sense_buf[2] = crowding

        for step in range(n_lif_steps):
            if random.random() < viscosity[org]:
                total_atp += np.float32(n_count)
                continue

            # Zero current spike buffer
            for i in range(n_count):
                curr_spk_buf[i] = False
                
            t_now = global_time + step
            
            n_ptr = org_n_ptr[org]
            s_ptr = org_s_ptr[org]
            s_count = org_s_count[org]
            
            # Phase 1: Forward propagate spikes from previous step
            for c in range(s_count):
                src = global_conn_src[s_ptr + c]
                dst = global_conn_dst[s_ptr + c]
                if prev_spk_buf[src]:
                    w = global_conn_weight[s_ptr + c]
                    global_v[n_ptr + dst] += w
                    total_atp += CYCLES_PER_SYNAPSE_READ
            
            # Phase 2: Input and Hidden/Output LIF logic
            for n in range(n_count):
                r_idx = global_rec_id[n_ptr + n]
                spike_val = 1.0 * o_rec_spk_max[org, r_idx]
                if spike_val > 1.0: spike_val = 1.0
                
                if n < N_INPUT:
                    if random.random() < sense_buf[n] * spike_val:
                        curr_spk_buf[n] = True
                        global_t_last[n_ptr + n] = t_now
                else:
                    if global_ref[n_ptr + n] > 0:
                        global_ref[n_ptr + n] -= 1
                    else:
                        v = global_v[n_ptr + n]
                        v_rest = o_rec_v_rest[org, r_idx]
                        tau = global_tau[n_ptr + n]
                        thresh = global_thresh[n_ptr + n]
                        
                        # Leak
                        v += (v_rest - v) / tau * DT
                        
                        if v >= thresh:
                            curr_spk_buf[n] = True
                            global_v[n_ptr + n] = o_rec_v_reset[org, r_idx]
                            global_ref[n_ptr + n] = TAU_REF
                            global_t_last[n_ptr + n] = t_now
                            
                            if n >= N_INPUT and n < N_IO:
                                out_idx = n - N_INPUT
                                out_accum[out_idx] += 1
                        else:
                            global_v[n_ptr + n] = v

            # Phase 3: STDP Updates only for spiking neurons
            for c in range(s_count):
                src = global_conn_src[s_ptr + c]
                dst = global_conn_dst[s_ptr + c]
                
                if curr_spk_buf[dst]:
                    t_pre = global_t_last[n_ptr + src]
                    if t_pre >= 0 and t_pre < t_now:
                        dt = np.float32(t_now - t_pre) * DT
                        r_idx = global_rec_id[n_ptr + dst]
                        w = global_conn_weight[s_ptr + c]
                        w += o_rec_a_plus[org, r_idx] * np.exp(-dt / o_rec_tau_p[org, r_idx])
                        if w > W_MAX: w = W_MAX
                        global_conn_weight[s_ptr + c] = w
                        # Plasticity is real compute (an exp() + weight write). Charge it when
                        # it actually fires, so learning carries its own honest energy cost and
                        # a brain thrashing a huge plastic fabric pays for it — activity-gated,
                        # so sparse-firing large brains are not penalised (Rule 7/11/17).
                        total_atp += CYCLES_PER_STDP_UPDATE

                elif curr_spk_buf[src]:
                    t_post = global_t_last[n_ptr + dst]
                    if t_post >= 0 and t_post < t_now:
                        dt = np.float32(t_now - t_post) * DT
                        r_idx = global_rec_id[n_ptr + dst]
                        w = global_conn_weight[s_ptr + c]
                        w -= o_rec_a_minus[org, r_idx] * np.exp(-dt / o_rec_tau_m[org, r_idx])
                        if w < W_MIN: w = W_MIN
                        global_conn_weight[s_ptr + c] = w
                        total_atp += CYCLES_PER_STDP_UPDATE

            # Membrane update for every neuron this step is real executed work: charge the
            # honest 1 cycle/neuron (was an arbitrary 0.1 discount that made brain size cost
            # ~10x too little to matter). This is the emergent thermodynamic pressure that
            # makes a cheaper brain reproductively fitter (Rule 7) — not a top-down fitness term.
            total_atp += CYCLES_PER_NEURON_UPDATE * n_count

            # Pointer swap buffers
            temp = prev_spk_buf
            prev_spk_buf = curr_spk_buf
            curr_spk_buf = temp

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
            if best_a in (OUT_JMP_FWD, OUT_JMP_BCK, OUT_JMP_FWD_10, OUT_JMP_BCK_10):
                npos = pos
                if best_a == OUT_JMP_FWD: npos = (pos + 1) % RAM_SIZE
                elif best_a == OUT_JMP_BCK: npos = (pos - 1 + RAM_SIZE) % RAM_SIZE
                elif best_a == OUT_JMP_FWD_10: npos = (pos + 10) % RAM_SIZE
                elif best_a == OUT_JMP_BCK_10: npos = (pos - 10 + RAM_SIZE) % RAM_SIZE
                
                energy[org] -= CYCLES_PER_MOVE
                if org_grid[npos] == -1:
                    val = ram_substrate[npos]
                    if val >= 32 and val <= 126 and val != 0x55:
                        if org_char_val == val:
                            energy[org] += np.float32(val)
                            ram_substrate[npos] = 0x00
                            idx = read_log[0]
                            if idx < 996:
                                read_log[idx] = 1
                                read_log[idx+1] = org
                                read_log[idx+2] = val
                                read_log[0] = idx + 3
                        else:
                            if org_char_val == 0:
                                # Null pointer trap: Thermodynamic core dump cost based on organism mass
                                dump_cost = np.float32(org_g_count[org]) * CYCLES_PER_BYTE_COPY
                                energy[org] -= dump_cost
                            else:
                                energy[org] -= np.float32(val)
                            
                            idx = read_log[0]
                            if idx < 993:  # 4-element write needs idx+3 < 1000
                                read_log[idx] = 2
                                read_log[idx+1] = org
                                read_log[idx+2] = val
                                read_log[idx+3] = org_char_val
                                read_log[0] = idx + 4
                            
                    org_grid[pos] = -1
                    positions[org] = npos
                    org_grid[npos] = org
                    pos = npos
            elif best_a == OUT_CONSUME:
                val = ram_substrate[pos]
                if val == 0x55:
                    energy[org] += CYCLES_PER_EAT_GAIN
                    ram_substrate[pos] = 0x00
                    if energy[org] > ATP_MAX:
                        energy[org] = ATP_MAX

            elif best_a == OUT_REPRODUCE:
                g_count = org_g_count[org]
                copy_cost = np.float32(g_count) * CYCLES_PER_BYTE_COPY
                
                if energy[org] >= copy_cost + 10.0 and n_births < b_pos.shape[0]:
                    energy[org] -= copy_cost
                    child_energy = energy[org] / 2.0
                    energy[org] -= child_energy
                    b_pos[n_births]    = pos
                    b_parent[n_births] = org
                    b_energy[n_births] = child_energy
                    
                    g_start = org_g_ptr[org]
                    b_g_start[n_births] = g_start
                    b_g_count[n_births] = g_count

                    for x in range(g_count):
                        b_genomes[n_births, x] = global_genome[g_start + x]

                    # Lamarckian consolidation (generational memory): blend each synapse's
                    # DNA-encoded initial weight 50/50 with the weight the parent actually
                    # LEARNED via STDP this lifetime, so hard-won plasticity is partially
                    # inherited instead of being wiped every generation (Rule 6). The walk
                    # mirrors decode_genome so synapse indices line up with the learned array.
                    n_c_org = org_n_count[org]
                    s_ptr_org = org_s_ptr[org]
                    s_cap = org_s_count[org]
                    s_local = 0
                    xi = 0
                    while xi < g_count - 3:
                        m = b_genomes[n_births, xi]
                        if m == GENE_MARKER:
                            if xi + 3 < g_count:
                                dst = b_genomes[n_births, xi + 2]
                                if (dst % n_c_org) >= N_INPUT:
                                    if s_local < s_cap:
                                        dna_w = np.float32(b_genomes[n_births, xi + 3])
                                        learned_w = global_conn_weight[s_ptr_org + s_local] + np.float32(128.0)
                                        blend = np.float32(0.5) * dna_w + np.float32(0.5) * learned_w
                                        iw = int(blend + np.float32(0.5))
                                        if iw < 0: iw = 0
                                        elif iw > 255: iw = 255
                                        b_genomes[n_births, xi + 3] = np.uint8(iw)
                                    s_local += 1
                            xi += 4
                        elif m == NEURON_MARKER and xi + 4 < g_count:
                            xi += 5
                        elif m == RECEPTOR_MARKER and xi + 9 < g_count:
                            xi += 10
                        else:
                            xi += 1

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
