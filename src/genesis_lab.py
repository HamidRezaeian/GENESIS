import numpy as np
import time
import os
import json
import base64
import random
from http.server import HTTPServer, BaseHTTPRequestHandler

from neuromorphic_engine import (
    WORLD_W, WORLD_H, WORLD_SZ, MAX_ORGANISMS, BIRTH_BUF_SZ, GENOME_SZ,
    N_INPUT, N_HIDDEN, N_OUTPUT, N_ALL, ATP_INIT, ATP_CHILD_INIT,
    decode_genome, world_tick_numba
)

# Global State for API
GLOBAL_FOOD = None
GLOBAL_POSITIONS = None
GLOBAL_ALIVE = None
GLOBAL_NUM_ORGS = 0
GLOBAL_CYCLES = 0
GLOBAL_EXT = 0
GLOBAL_EXT_HISTORY = []
GLOBAL_GENOMES = None
GLOBAL_AGE = None
GLOBAL_ELITE_AGE = 0
GLOBAL_ELITE_IQ = 100

def evaluate_brain(w_ih, w_ho, thresh_h, tau_h):
    import numpy as np
    from neuromorphic_engine import V_REST, N_ALL, lif_step, N_OUTPUT
    
    scenarios = [
        {"name": "Food North", "sense": [0.0, 1.0, 0.0, 0.0, 0.0, 0.5, 0.0], "expected": 0},
        {"name": "Food South", "sense": [0.0, 0.0, 1.0, 0.0, 0.0, 0.5, 0.0], "expected": 1},
        {"name": "Food East",  "sense": [0.0, 0.0, 0.0, 1.0, 0.0, 0.5, 0.0], "expected": 2},
        {"name": "Food West",  "sense": [0.0, 0.0, 0.0, 0.0, 1.0, 0.5, 0.0], "expected": 3},
        {"name": "Food Here (Starving)", "sense": [1.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0], "expected": 4}
    ]
    
    results = []
    passed = 0
    
    for s in scenarios:
        v = np.full(N_ALL, V_REST, dtype=np.float32)
        ref = np.zeros(N_ALL, dtype=np.int32)
        t_last = np.zeros(N_ALL, dtype=np.int32)
        sense_rates = np.array(s["sense"], dtype=np.float32)
        
        spike_counts = np.zeros(N_OUTPUT, dtype=np.int32)
        out_spikes = np.zeros(N_OUTPUT, dtype=np.bool_)
        
        for t in range(50):
            atp_dummy = np.zeros(1, dtype=np.float32)
            lif_step(v, ref, t_last, thresh_h, tau_h, w_ih, w_ho, sense_rates, t, out_spikes, atp_dummy)
            for o in range(N_OUTPUT):
                if out_spikes[o]:
                    spike_counts[o] += 1
                    
        if np.max(spike_counts) > 0:
            chosen = np.argmax(spike_counts)
        else:
            chosen = -1
            
        success = (chosen == s["expected"])
        if success: passed += 1
        
        action_names = ["Move North", "Move South", "Move East", "Move West", "Eat Food", "Reproduce"]
        chosen_name = action_names[chosen] if chosen >= 0 else "Catatonia"
        
        results.append({
            "scenario": s["name"],
            "passed": success,
            "action": chosen_name
        })
        
    iq = int((passed / len(scenarios)) * 100)
    return iq, results

class GenesisAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/state':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Active organisms
            active_pos = []
            if GLOBAL_ALIVE is not None and GLOBAL_POSITIONS is not None:
                for i in range(MAX_ORGANISMS):
                    if GLOBAL_ALIVE[i]:
                        active_pos.append(int(GLOBAL_POSITIONS[i]))
                
            state = {
                "tick": GLOBAL_CYCLES,
                "pop": GLOBAL_NUM_ORGS,
                "max_pop": MAX_ORGANISMS,
                "extinctions": GLOBAL_EXT,
                "food_b64": base64.b64encode(np.array(GLOBAL_FOOD, dtype=np.float32).tobytes()).decode('utf-8') if GLOBAL_FOOD is not None else "",
                "orgs": active_pos,
                "ext_history": GLOBAL_EXT_HISTORY,
                "world_w": WORLD_W,
                "world_h": WORLD_H,
                "elite_age": GLOBAL_ELITE_AGE,
                "elite_iq": GLOBAL_ELITE_IQ
            }
            self.wfile.write(json.dumps(state).encode('utf-8'))
            
        elif self.path == '/api/analyze':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if GLOBAL_GENOMES is None or GLOBAL_ALIVE is None or GLOBAL_AGE is None:
                self.wfile.write(json.dumps({"status": "extinct"}).encode('utf-8'))
                return
                
            dom_count, num_species, dom_hex, dom_genome, max_age = extract_dominant_species(GLOBAL_GENOMES, GLOBAL_ALIVE, GLOBAL_AGE)
            
            if dom_genome is None:
                self.wfile.write(json.dumps({"status": "extinct"}).encode('utf-8'))
                return
                
            w_ih = np.zeros((N_INPUT, N_HIDDEN), dtype=np.float32)
            w_ho = np.zeros((N_HIDDEN, N_OUTPUT), dtype=np.float32)
            thresh_h = np.zeros(N_HIDDEN, dtype=np.float32)
            tau_h = np.zeros(N_HIDDEN, dtype=np.float32)
            decode_genome(dom_genome, w_ih, w_ho, thresh_h, tau_h)
            
            INPUT_LABELS = ["Food Here", "Food N", "Food S", "Food E", "Food W", "Self Energy", "Crowding"]
            OUTPUT_LABELS = ["Move North", "Move South", "Move East", "Move West", "Eat Food", "Reproduce"]
            
            hidden_neurons = []
            for h in range(N_HIDDEN):
                hidden_neurons.append({"id": f"H{h:02d}", "threshold": float(thresh_h[h]), "tau": float(tau_h[h])})
                
            synapses = []
            for i in range(N_INPUT):
                for h in range(N_HIDDEN):
                    if abs(w_ih[i, h]) > 0.5:
                        synapses.append({"source": INPUT_LABELS[i], "target": f"H{h:02d}", "weight": float(w_ih[i, h])})
                        
            for h in range(N_HIDDEN):
                for o in range(N_OUTPUT):
                    if abs(w_ho[h, o]) > 0.5:
                        synapses.append({"source": f"H{h:02d}", "target": OUTPUT_LABELS[o], "weight": float(w_ho[h, o])})
                        
            iq, test_results = evaluate_brain(w_ih, w_ho, thresh_h, tau_h)
            
            res = {
                "status": "ok",
                "population": dom_count,
                "species": num_species,
                "hex": dom_hex,
                "max_age": int(max_age),
                "iq": iq,
                "test_results": test_results,
                "hidden_neurons": hidden_neurons,
                "synapses": synapses
            }
            self.wfile.write(json.dumps(res).encode('utf-8'))
        
        elif self.path == '/' or self.path == '/index.html':
            self._serve_static('public/index.html', 'text/html')
        elif self.path == '/styles.css':
            self._serve_static('public/styles.css', 'text/css')
        elif self.path == '/app.js':
            self._serve_static('public/app.js', 'application/javascript')
        else:
            self.send_response(404)
            self.end_headers()
            
    def _serve_static(self, filepath, content_type):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, filepath)
        try:
            with open(full_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass # Suppress logging

def run_server():
    server = HTTPServer(('0.0.0.0', 8081), GenesisAPIHandler)
    print("Dashboard Server running on http://localhost:8081")
    server.serve_forever()

def extract_dominant_species(genomes, alive, age_arr):
    from collections import Counter
    active_genomes = []
    genome_ages = {}
    for i in range(MAX_ORGANISMS):
        if alive[i]:
            g_bytes = bytes(genomes[i])
            active_genomes.append(g_bytes)
            if g_bytes not in genome_ages:
                genome_ages[g_bytes] = []
            genome_ages[g_bytes].append(age_arr[i])
            
    if not active_genomes:
        return 0, 0, "EXTINCT", None, 0
        
    counter = Counter(active_genomes)
    top = counter.most_common(1)[0]
    top_bytes = top[0]
    max_age = max(genome_ages[top_bytes])
    return GENOME_SZ, len(counter), top_bytes.hex()[:40], np.frombuffer(top_bytes, dtype=np.uint8), max_age


def main():
    print("========================================================")
    print("      GENESIS WORLD v2 - SNN NEUROMORPHIC ENGINE        ")
    print("========================================================")
    
    def create_intelligent_ancestor():
        from neuromorphic_engine import encode_weights_to_genome, GENOME_SZ, N_INPUT, N_HIDDEN, N_OUTPUT
        g = np.full(GENOME_SZ, 128, dtype=np.uint8)
        w_ih = np.zeros((N_INPUT, N_HIDDEN), dtype=np.float32)
        w_ho = np.zeros((N_HIDDEN, N_OUTPUT), dtype=np.float32)
        thresh_h = np.full(N_HIDDEN, -63.0, dtype=np.float32)
        tau_h = np.full(N_HIDDEN, 20.0, dtype=np.float32)
        
        # H00: Food Here -> Eat
        w_ih[0, 0] = 12.0; w_ho[0, 4] = 12.0
        # H01: Food N -> Move N
        w_ih[1, 1] = 12.0; w_ho[1, 0] = 12.0
        # H02: Food S -> Move S
        w_ih[2, 2] = 12.0; w_ho[2, 1] = 12.0
        # H03: Food E -> Move E
        w_ih[3, 3] = 12.0; w_ho[3, 2] = 12.0
        # H04: Food W -> Move W
        w_ih[4, 4] = 12.0; w_ho[4, 3] = 12.0
        # H05: Self Energy -> Reproduce
        w_ih[5, 5] = 12.0; w_ho[5, 5] = 12.0
        
        encode_weights_to_genome(g, w_ih, w_ho, thresh_h, tau_h)
        return g
    
    BRAIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Brain")
    if not os.path.exists(BRAIN_DIR):
        os.makedirs(BRAIN_DIR)
        
    # --- Allocation of V2 Arrays ---
    food_grid = np.zeros(WORLD_SZ, dtype=np.float32)
    org_grid = np.full(WORLD_SZ, -1, dtype=np.int32)
    
    positions = np.zeros(MAX_ORGANISMS, dtype=np.int32)
    alive = np.zeros(MAX_ORGANISMS, dtype=np.bool_)
    energy = np.zeros(MAX_ORGANISMS, dtype=np.float32)
    age = np.zeros(MAX_ORGANISMS, dtype=np.int32)
    
    v_mem = np.full((MAX_ORGANISMS, N_ALL), -65.0, dtype=np.float32)
    ref = np.zeros((MAX_ORGANISMS, N_ALL), dtype=np.int32)
    t_last = np.full((MAX_ORGANISMS, N_ALL), -1, dtype=np.int32)
    
    thresh_h = np.zeros((MAX_ORGANISMS, N_HIDDEN), dtype=np.float32)
    tau_h = np.zeros((MAX_ORGANISMS, N_HIDDEN), dtype=np.float32)
    w_ih = np.zeros((MAX_ORGANISMS, N_INPUT, N_HIDDEN), dtype=np.float32)
    w_ho = np.zeros((MAX_ORGANISMS, N_HIDDEN, N_OUTPUT), dtype=np.float32)
    genomes = np.zeros((MAX_ORGANISMS, GENOME_SZ), dtype=np.uint8)
    
    b_pos = np.zeros(BIRTH_BUF_SZ, dtype=np.int32)
    b_parent = np.zeros(BIRTH_BUF_SZ, dtype=np.int32)
    b_w_ih = np.zeros((BIRTH_BUF_SZ, N_INPUT, N_HIDDEN), dtype=np.float32)
    b_w_ho = np.zeros((BIRTH_BUF_SZ, N_HIDDEN, N_OUTPUT), dtype=np.float32)
    b_thresh = np.zeros((BIRTH_BUF_SZ, N_HIDDEN), dtype=np.float32)
    b_tau = np.zeros((BIRTH_BUF_SZ, N_HIDDEN), dtype=np.float32)
    b_genome = np.zeros((BIRTH_BUF_SZ, GENOME_SZ), dtype=np.uint8)
    
    global GLOBAL_FOOD, GLOBAL_POSITIONS, GLOBAL_ALIVE, GLOBAL_NUM_ORGS, GLOBAL_CYCLES, GLOBAL_EXT, GLOBAL_GENOMES
    GLOBAL_FOOD = food_grid
    GLOBAL_POSITIONS = positions
    GLOBAL_ALIVE = alive
    GLOBAL_GENOMES = genomes
    
    total_cycles = 0
    extinction_count = 0
    elite_ark = create_intelligent_ancestor()
    best_historical_age = 0
    
    global GLOBAL_ELITE_AGE, GLOBAL_ELITE_IQ
    GLOBAL_ELITE_AGE = 0
    GLOBAL_ELITE_IQ = 100

    def seed_universe():
        nonlocal extinction_count, elite_ark, best_historical_age
        
        # Ark mechanism: save the genome of the organism that lived the longest in this era
        best_idx = np.argmax(age)
        if age[best_idx] > best_historical_age and age[best_idx] > 50:
            best_historical_age = age[best_idx]
            elite_ark = genomes[best_idx].copy()
            GLOBAL_ELITE_AGE = int(age[best_idx])
            
            # Evaluate IQ of new Elite
            temp_w_ih = np.zeros((N_INPUT, N_HIDDEN), dtype=np.float32)
            temp_w_ho = np.zeros((N_HIDDEN, N_OUTPUT), dtype=np.float32)
            temp_thresh_h = np.zeros(N_HIDDEN, dtype=np.float32)
            temp_tau_h = np.zeros(N_HIDDEN, dtype=np.float32)
            decode_genome(elite_ark, temp_w_ih, temp_w_ho, temp_thresh_h, temp_tau_h)
            iq, _ = evaluate_brain(temp_w_ih, temp_w_ho, temp_thresh_h, temp_tau_h)
            GLOBAL_ELITE_IQ = int(iq)
            
            print(f"  [ARK] Ascension! Preserving Elite DNA (Age {age[best_idx]}, IQ {iq}) | Reseeding...")
        elif age[best_idx] > 0:
            print(f"  [ARK] Extinction too fast (Age {age[best_idx]}). Keeping previous Elite DNA.")
                
        extinction_count += 1
        
        # Wipe
        alive[:] = False
        org_grid[:] = -1
        food_grid[:] = 0.0
        
        seed_count = min(150, MAX_ORGANISMS)
        for i in range(seed_count):
            pos = random.randint(0, WORLD_SZ - 1)
            while org_grid[pos] != -1:
                pos = random.randint(0, WORLD_SZ - 1)
                
            positions[i] = pos
            org_grid[pos] = i
            alive[i] = True
            energy[i] = ATP_INIT
            age[i] = 0
            
            if elite_ark is not None:
                genomes[i, :] = elite_ark
            else:
                # Random ancestor
                genomes[i, :] = np.random.randint(0, 256, GENOME_SZ, dtype=np.uint8)
                
            decode_genome(genomes[i], w_ih[i], w_ho[i], thresh_h[i], tau_h[i])
            
            v_mem[i].fill(-65.0)
            ref[i].fill(0)
            t_last[i].fill(-1)

    seed_universe()
    extinction_count = 0 # Reset initial count

    import threading
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    print("Warming up Numba SNN Engine (JIT compile)...")
    # Dummy run to compile
    world_tick_numba(
        food_grid, org_grid, positions, alive, energy, age,
        v_mem, ref, t_last, thresh_h, tau_h, w_ih, w_ho, genomes,
        0, 1,
        b_pos, b_parent, b_w_ih, b_w_ho, b_thresh, b_tau, b_genome
    )
    print("JIT Complete. Entering Deep Time...")

    try:
        ticks_per_batch = 1000 # 1000 world ticks, each has e.g. 5 LIF steps
        n_lif_steps = 5
        
        while True:
            start_time = time.time()
            
            for _ in range(ticks_per_batch):
                n_alive, n_births = world_tick_numba(
                    food_grid, org_grid, positions, alive, energy, age,
                    v_mem, ref, t_last, thresh_h, tau_h, w_ih, w_ho, genomes,
                    total_cycles, n_lif_steps,
                    b_pos, b_parent, b_w_ih, b_w_ho, b_thresh, b_tau, b_genome
                )
                
                total_cycles += n_lif_steps
                
                # Process births
                for b in range(n_births):
                    empty_idx = -1
                    for i in range(MAX_ORGANISMS):
                        if not alive[i]:
                            empty_idx = i
                            break
                            
                    if empty_idx >= 0:
                        parent_pos = b_pos[b]
                        x = parent_pos % WORLD_W
                        y = parent_pos // WORLD_W
                        dx = random.randint(-1, 1)
                        dy = random.randint(-1, 1)
                        child_pos = ((y + dy + WORLD_H) % WORLD_H) * WORLD_W + ((x + dx + WORLD_W) % WORLD_W)
                        
                        if org_grid[child_pos] == -1:
                            positions[empty_idx] = child_pos
                            org_grid[child_pos] = empty_idx
                            alive[empty_idx] = True
                            energy[empty_idx] = ATP_CHILD_INIT
                            age[empty_idx] = 0
                            
                            genomes[empty_idx, :] = b_genome[b]
                            
                            # Mutate 1% chance per byte
                            for g in range(GENOME_SZ):
                                if random.random() < 0.01:
                                    genomes[empty_idx, g] = random.randint(0, 255)
                                    
                            decode_genome(genomes[empty_idx], w_ih[empty_idx], w_ho[empty_idx], thresh_h[empty_idx], tau_h[empty_idx])
                            
                            v_mem[empty_idx].fill(-65.0)
                            ref[empty_idx].fill(0)
                            n_alive += 1
                            
                GLOBAL_NUM_ORGS = n_alive
                GLOBAL_CYCLES = total_cycles
                
                if n_alive <= 0:
                    break

            elapsed = time.time() - start_time
            # cps is world-ticks per second
            cps = int(ticks_per_batch / elapsed) if elapsed > 0 else 0
            
            GLOBAL_NUM_ORGS = n_alive
            GLOBAL_CYCLES = total_cycles
            GLOBAL_EXT = extinction_count
            GLOBAL_AGE = age
            
            print(f"[LIF Time: {total_cycles:,}] | {cps:,} world-ticks/s | Pop: {n_alive}/{MAX_ORGANISMS} | Extinctions: {extinction_count}")
            
            if n_alive <= 0:
                print(">>> EXTINCTION DETECTED. Reseeding universe... <<<")
                era_lifespan = total_cycles - getattr(seed_universe, "last_ext_tick", 0)
                GLOBAL_EXT_HISTORY.append({"tick": total_cycles, "rate": era_lifespan})
                seed_universe.last_ext_tick = total_cycles
                if len(GLOBAL_EXT_HISTORY) > 50:
                    GLOBAL_EXT_HISTORY.pop(0)
                seed_universe()
                
            # Log dominant species and save Brain.npz every 10 batches
            if (total_cycles // (ticks_per_batch * n_lif_steps)) % 10 == 0:
                dom_len, num_species, dom_hex, _, _ = extract_dominant_species(genomes, alive, age)
                if n_alive > 0:
                    print(f"  [SNN] Dominant: {dom_len}B | Species: {num_species} | Hex: {dom_hex}...")
                
                # Save the complete physical state of the universe
                np.savez(os.path.join(BRAIN_DIR, "Brain.npz"), 
                         genomes=genomes, 
                         alive=alive,
                         positions=positions,
                         food_grid=food_grid)
    except KeyboardInterrupt:
        print("\nSimulation Halted. The universe is frozen.")

if __name__ == "__main__":
    main()
