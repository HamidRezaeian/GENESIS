import numpy as np
from numba import njit
import random
import os

RAM_SIZE = 65536

N_INPUT  = 25   # 0-14 original senses; 15-22 = 8 bits of the RAM byte under the pointer (reading
                # eye); 23 = food-ahead, 24 = food-behind (nearby-memory scan). Grew 17->25 so the
                # eye emits the SAME 8-bit encoding the vocal cords use, making symbol-echo a copy.
N_OUTPUT = 14
N_IO     = N_INPUT + N_OUTPUT

RAM_BIT0_INPUT = 15   # inputs 15..22 = bit 0..7 of the byte under the pointer (the "reading eye")

# Food-seeking sense (Rule 5 "seeking" / Rule 10 gradient): each tick an organism samples the RAM
# window this many bytes ahead and behind its pointer and reports local food (0x55) density on the
# last two input channels, so it can climb toward food instead of blundering into it. Sampling
# 2*radius cells is real work, charged 2*radius cycles/tick in world_tick_numba (Rule 17 honest).
FOOD_SCAN_RADIUS = 16

# In the BOOK economy the seeking sense must climb toward READABLE SYMBOLS, not 0x55 food (which
# is barely present under books). Baked from GENESIS_ECONOMY at import — a compile-time constant
# inside the njit sense(), so it costs nothing at runtime; NUMBA_CACHE_DIR is economy-keyed
# (genesis_lab) so the food and book kernels never collide. In books mode food_ahead/food_behind
# then carry local TEXT density, and the ancestor's existing FOOD_AHEAD->JMP_FWD / FOOD_BEHIND->
# JMP_BCK wiring becomes a text-seeking reflex for free — reading as a navigable SKILL (Rule 10),
# not a random-walk lottery. Food mode is unchanged (scans 0x55 exactly as before).
SEEK_TEXT = os.environ.get("GENESIS_ECONOMY", "food").lower() == "books"

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
# A BYTE IS STORED ENERGY (no reward constants — 2026-07-11 "remove all game constants").
# RAM holds numbers; in this universe a number IS a quantity of energy (cycles). So RESOLVING a
# byte — eating food (0x55) or SOLVING a book symbol, either way writing the cell back to 0x00
# vacuum — releases EXACTLY the byte's own value in cycles. Nothing is multiplied, nothing is
# tuned: a food byte 0x55 pays 85, the letter 'A' pays 65, 'z' pays 122. Food and text are thereby
# NATURALLY comparable, so reading competes with eating without a single knob (retires the old
# CYCLES_PER_EAT_GAIN=15000 and READ_REWARD_SCALE=64 game constants — Rules 9/10/17). BITS_PER_BYTE
# is hardware (8), used only to grade partial reads: a partial solve pays value*net_bits/8.
BITS_PER_BYTE = np.float32(8.0)
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
        if marker == GENE_MARKER and i + 3 < g_ptr + g_count:
            s_count += 1
            i += 4
        elif marker == NEURON_MARKER and i + 4 < g_ptr + g_count:
            h_count += 1
            i += 5
        elif marker == RECEPTOR_MARKER and i + 9 < g_ptr + g_count:
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
    ram_byte = ram_substrate[addr]
    v = ram_byte / np.float32(255.0)
    sense_buf[3] = v

    # Reading eye: expose the 8 bits of the byte under the pointer on inputs 15..22, in the SAME
    # bit encoding the vocal cords (outputs 6..13 -> org_char_val) use. This makes "echo the symbol
    # you are standing on" a simple bit-in->bit-out copy an organism can seed, learn (STDP) or
    # evolve, instead of reconstructing 8 exact bits from a single analog scalar (Rules 9/10/15).
    for bit in range(8):
        if (ram_byte >> bit) & 1:
            sense_buf[RAM_BIT0_INPUT + bit] = 1.0
    
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

    # Food-seeking sense: local food (0x55) density ahead vs behind the pointer (nearby-memory
    # scan). Two channels on the last two input slots let an organism climb a food gradient
    # instead of blundering. Sampling cost is charged in world_tick_numba (2*FOOD_SCAN_RADIUS).
    food_ahead = np.float32(0.0)
    food_behind = np.float32(0.0)
    for k in range(1, FOOD_SCAN_RADIUS + 1):
        ba = ram_substrate[(addr + k) % RAM_SIZE]
        bb = ram_substrate[(addr - k + RAM_SIZE) % RAM_SIZE]
        if SEEK_TEXT:
            # Books economy: climb toward readable symbols (printable, non-food, non-empty).
            if ba >= 32 and ba <= 126 and ba != 0x55:
                food_ahead += np.float32(1.0)
            if bb >= 32 and bb <= 126 and bb != 0x55:
                food_behind += np.float32(1.0)
        else:
            if ba == 0x55:
                food_ahead += np.float32(1.0)
            if bb == 0x55:
                food_behind += np.float32(1.0)
    sense_buf[N_INPUT - 2] = food_ahead / np.float32(FOOD_SCAN_RADIUS)
    sense_buf[N_INPUT - 1] = food_behind / np.float32(FOOD_SCAN_RADIUS)



@njit(cache=True)
def world_tick_numba(
    ram_substrate, org_grid, positions, alive, energy, age,
    global_v, global_ref, global_t_last, global_thresh, global_tau, global_rec_id,
    global_conn_src, global_conn_dst, global_conn_weight,
    neuron_map, synapse_map, genome_map,
    org_n_ptr, org_n_count, org_s_ptr, org_s_count,
    global_genome, org_g_ptr, org_g_count,
    o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m, o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max,
    viscosity, global_time, org_lif_steps,
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
        # TOTAL HARDWARE FOOTPRINT (neurons + synapses). Dense, bloated brains stall
        # more often, rewarding sparse, minimal architectures (the 20W paradigm).
        # We scale by a large denominator so a typical organism (~30 neurons) has low viscosity.
        footprint = np.float32(n_count) + np.float32(org_s_count[org])
        local_viscosity = footprint / np.float32(1000.0)
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

        # Honest cost of the food-scan sample (2*radius memory reads), charged once per tick
        # since sense() is hoisted out of the LIF sub-step loop (Rule 17).
        total_atp += np.float32(2 * FOOD_SCAN_RADIUS)

        # Architecture-derived compute latency (no global step constant): this organism runs as many
        # LIF substeps this world-tick as its own synapse graph is deep — computed once at spawn into
        # org_lif_steps (longest input->node path + 1 final fire). Burn scales with real per-org
        # computational depth; a 1-hop echo reflex runs 2, a deeper evolved brain runs (and pays) more.
        n_steps = org_lif_steps[org]
        if n_steps < 1:
            n_steps = 1

        for step in range(n_steps):
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
                
        # A vocal bit is set if its neuron fired at all this tick. With random scratchpad synapses
        # kept OFF the vocal outputs and two max-weight copy synapses per bit driving each vocal
        # neuron cleanly above threshold, only the CORRECT bits fire — so a single spike is a
        # reliable signal and debouncing would only drop bits (the vocal neuron's 1-step refractory
        # stops it firing every step). Clean 8-bit echo = reading reliable enough to live on.
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

        # --- Stationary reading (2026-07-11): SOLVE the symbol you occupy ---
        # The original read reward only fired inside the movement branch and checked the byte at
        # the DESTINATION cell (predict-the-next-cell) — incompatible with an echo reflex that
        # vocalizes the byte UNDER the pointer, and skipped entirely whenever a vocal output (not a
        # jump) won winner-take-all. Reward reading the CURRENT cell every tick so "stand on a
        # letter and pronounce it" is the honest book-solving event evolution can climb (Rules 9/10).
        cur_byte = ram_substrate[pos]
        if cur_byte >= 32 and cur_byte <= 126 and cur_byte != 0x55:
            # PARTIAL-CREDIT reading (gradient, not cliff — Rule 10). Score bits the organism sets
            # correctly (1 where the symbol is 1) minus bits it wrongly sets (1 where symbol is 0),
            # so getting more bits right earns more energy and evolution/STDP can climb from partial
            # to full reading. Silence (0) scores 0 (no spurious reward). Each net-correct bit is
            # A partial solve pays the byte's OWN value scaled by the fraction of bits solved:
            # value * net_bits / 8 (BITS_PER_BYTE). A full exact match pays the whole byte value —
            # the same energy eating that byte as food would release (a byte is stored energy, no
            # multiplier). Full match = true solved read (consumed + logged type 1); nonzero miss
            # logs type 2.
            correct_bits = 0
            wrong_bits = 0
            for b in range(8):
                out_b = (org_char_val >> b) & 1
                tgt_b = (cur_byte >> b) & 1
                if out_b == 1 and tgt_b == 1:
                    correct_bits += 1
                elif out_b == 1 and tgt_b == 0:
                    wrong_bits += 1
            net = correct_bits - wrong_bits
            if net != 0:
                energy[org] += np.float32(cur_byte) * np.float32(net) / BITS_PER_BYTE
                # CONSUME ON ATTEMPT (2026-07-11 fix): Once an organism attempts to read a byte
                # (by outputting ANY net-positive guess), the byte is consumed. This prevents
                # "infinite reading money" from standing still and spamming the same character.
                ram_substrate[pos] = 0x00
            if org_char_val == cur_byte:
                idx = read_log[0]
                if idx < 996:
                    read_log[idx] = 1
                    read_log[idx+1] = org
                    read_log[idx+2] = cur_byte
                    read_log[0] = idx + 3
            elif org_char_val != 0:
                idx = read_log[0]
                if idx < 993:
                    read_log[idx] = 2
                    read_log[idx+1] = org
                    read_log[idx+2] = cur_byte
                    read_log[idx+3] = org_char_val
                    read_log[0] = idx + 4

        if best_n > 0 and best_a >= 0:
            if best_a in (OUT_JMP_FWD, OUT_JMP_BCK, OUT_JMP_FWD_10, OUT_JMP_BCK_10):
                npos = pos
                if best_a == OUT_JMP_FWD: npos = (pos + 1) % RAM_SIZE
                elif best_a == OUT_JMP_BCK: npos = (pos - 1 + RAM_SIZE) % RAM_SIZE
                elif best_a == OUT_JMP_FWD_10: npos = (pos + 10) % RAM_SIZE
                elif best_a == OUT_JMP_BCK_10: npos = (pos - 10 + RAM_SIZE) % RAM_SIZE
                
                energy[org] -= CYCLES_PER_MOVE
                if org_grid[npos] == -1:
                    # PREDICTION reward (problem-solving, Rules 6/9). The organism vocalized
                    # org_char_val THIS tick from context; if it matches the symbol it now steps
                    # ONTO, it ANTICIPATED the next symbol. For math text "1+1=" -> "2" that requires
                    # COMPUTING 1+1, not echoing — the real cognitive leap above reading-aloud.
                    # Partial credit (gradient), scaled by READ_REWARD_SCALE (solving = wealth).
                    # Distinct from the stationary echo read; a full correct prediction logs type 3.
                    pval = ram_substrate[npos]
                    if pval >= 32 and pval <= 126 and pval != 0x55:
                        pc = 0
                        pw = 0
                        for b in range(8):
                            ob = (org_char_val >> b) & 1
                            tb = (pval >> b) & 1
                            if ob == 1 and tb == 1:
                                pc += 1
                            elif ob == 1 and tb == 0:
                                pw += 1
                        pnet = pc - pw
                        if pnet != 0:
                            energy[org] += np.float32(pnet) * np.float32(8.0) * READ_REWARD_SCALE
                        if org_char_val == pval:
                            idx = read_log[0]
                            if idx < 996:
                                read_log[idx] = 3
                                read_log[idx+1] = org
                                read_log[idx+2] = pval
                                read_log[0] = idx + 3
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

        age[org] += n_steps

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
