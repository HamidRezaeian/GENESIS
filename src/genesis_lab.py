import numpy as np
from numba import njit
import time
import random
import os
from turing_engine import tick_numba, DEFAULT_ZONE_RATES, NUM_ZONES
from primordial_seed import build_ancestor
import threading
import json
import base64
from http.server import SimpleHTTPRequestHandler, HTTPServer

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")

GLOBAL_MEM = None
GLOBAL_IPS = None
GLOBAL_NUM_IPS = [0]
GLOBAL_CYCLES = [0]
GLOBAL_EXT = [0]
GLOBAL_ZONES = None

class GenesisAPIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith('/api/state'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if GLOBAL_MEM is None:
                self.wfile.write(b'{}')
                return

            mem_b64 = base64.b64encode(GLOBAL_MEM.tobytes()).decode('ascii')
            active_ips = GLOBAL_IPS[:GLOBAL_NUM_IPS[0]].tolist() if GLOBAL_IPS is not None else []
            zones = GLOBAL_ZONES.tolist() if GLOBAL_ZONES is not None else []
            
            data = {
                'tick': GLOBAL_CYCLES[0],
                'pop': GLOBAL_NUM_IPS[0],
                'max_pop': 4000,
                'extinctions': GLOBAL_EXT[0],
                'memory_b64': mem_b64,
                'ips': active_ips,
                'zones': zones
            }
            self.wfile.write(json.dumps(data).encode('utf-8'))
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass # Suppress logging to avoid cluttering stdout

def run_server():
    server = HTTPServer(('0.0.0.0', 8081), GenesisAPIHandler)
    print("Dashboard Server running on http://localhost:8081")
    server.serve_forever()

def extract_dominant_species(memory, ips, num_ips, max_len=64):
    """Quick inline genome extraction for auto-logging."""
    from collections import Counter
    if num_ips == 0:
        return 0, 0, "EXTINCT"
    
    mem_size = len(memory)
    genomes = []
    for i in range(min(num_ips, 500)):  # Sample up to 500 for speed
        ip = ips[i]
        # Scan backward to find start of code block
        start = ip
        for _ in range(max_len):
            if memory[(start - 1) % mem_size] == 0:
                break
            start = (start - 1) % mem_size
        # Scan forward
        end = start
        for _ in range(max_len):
            if memory[end % mem_size] == 0:
                break
            end = (end + 1) % mem_size
        length = (end - start) % mem_size
        if length == 0 or length > max_len:
            length = max_len
            start = ip
        block = bytes([memory[(start + j) % mem_size] for j in range(length)])
        genomes.append(block)
    
    counter = Counter(genomes)
    top = counter.most_common(1)[0]
    num_species = len(counter)
    return len(top[0]), num_species, top[0].hex()[:40]

def main():
    print("========================================================")
    print("      GENESIS WORLD - CAMBRIAN ACCELERATION ENGINE      ")
    print("========================================================")
    
    MILESTONES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Milestones")
    if not os.path.exists(MILESTONES_DIR):
        os.makedirs(MILESTONES_DIR)
    
    # SINGLE MASSIVE UNIVERSE
    size = 131072      # Memory size (POWER OF 2)
    max_ips = 4000     # Adjusted max IPs for a large single universe
    noise_rate = 2e-7  # Cosmic radiation rate
    cycles_per_batch = 1000000 # Print status every 1M cycles
    zone_rotation_period = 20_000_000  # Phase 28: Longer tectonic period (20M)
    genome_log_period = 10_000_000  # Auto-extract genomes every 10M cycles
    
    seed_code = build_ancestor()
    
    print(f"Memory Size: {size} bytes")
    print(f"Max Population: {max_ips}")
    print(f"Mutation Rate (Noise): {noise_rate}")
    print(f"Tectonic Period: {zone_rotation_period:,} cycles")
    print("Initializing Quantum Matrix...")
    
    checkpoint_file = os.path.join(MILESTONES_DIR, "WORLD_CHECKPOINT.npz")
    
    memory = np.zeros(size, dtype=np.uint8)
    ips = np.zeros(max_ips, dtype=np.int32)
    registers = np.zeros((max_ips, 4), dtype=np.int32)
    zone_rates = DEFAULT_ZONE_RATES.copy()
    
    global GLOBAL_MEM, GLOBAL_IPS, GLOBAL_NUM_IPS, GLOBAL_CYCLES, GLOBAL_EXT, GLOBAL_ZONES
    GLOBAL_MEM = memory
    GLOBAL_IPS = ips
    GLOBAL_ZONES = zone_rates
    
    if os.path.exists(checkpoint_file):
        print(f"Resuming from {checkpoint_file}...")
        data = np.load(checkpoint_file)
        
        memory[:] = data['memory']
        ips[:] = data['ips']
        registers[:] = data['registers']
        num_ips = data['num_ips'].item()
        total_cycles = data['total_cycles'].item()
        historical_max_pop = data.get('historical_max_pop', 0).item()
        extinction_count = int(data['extinction_count'].item()) if 'extinction_count' in data else 0
        if 'zone_rates' in data:
            zone_rates[:] = data['zone_rates']
        
        print(f"Successfully resumed at {total_cycles:,} cycles (Extinctions: {extinction_count})")
    else:
        print("No checkpoint found. Starting from scratch...")
        total_cycles = 0
        historical_max_pop = 0
        extinction_count = 0
        
        # Seed the universe with 100 ancestors spaced evenly
        num_seeds = 100
        spacing = size // num_seeds
        for s in range(num_seeds):
            seed_pos = s * spacing
            for j, byte in enumerate(seed_code):
                memory[(seed_pos + j) % size] = byte
            ips[s] = seed_pos
        num_ips = num_seeds
        
    GLOBAL_NUM_IPS[0] = num_ips
    GLOBAL_CYCLES[0] = total_cycles
    GLOBAL_EXT[0] = extinction_count
    
    # Start web server thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    print("Warming up Numba JIT compiler...")
    # Warmup
    num_ips = tick_numba(memory, ips, registers, num_ips, max_ips, 1, noise_rate, zone_rates)
    
    print("JIT Compiled. Commencing Continuous Evolution...")
    
    start_time = time.time()
    last_save_time = time.time()
    
    while True:
        t0 = time.time()
        num_ips = tick_numba(memory, ips, registers, num_ips, max_ips, cycles_per_batch, noise_rate, zone_rates)
        t1 = time.time()
        
        total_cycles += cycles_per_batch
        speed = cycles_per_batch / (t1 - t0) if t1 > t0 else 0
        
        # Tectonic Zone Rotation
        if total_cycles % zone_rotation_period < cycles_per_batch:
            zone_rates = np.roll(zone_rates, 1)
            GLOBAL_ZONES[:] = zone_rates
            print(f"  [TECTONIC SHIFT] Zones rotated. New layout: {zone_rates}")
            
        GLOBAL_NUM_IPS[0] = num_ips
        GLOBAL_CYCLES[0] = total_cycles
        GLOBAL_EXT[0] = extinction_count
        
        print(f"[Cycle {total_cycles:,}] {time.time()-start_time:.0f}s | {speed:,.0f} c/s | Pop: {num_ips}/{max_ips} | Extinctions: {extinction_count}", flush=True)

        # Periodic Genome Analysis
        if total_cycles % genome_log_period < cycles_per_batch and num_ips > 0:
            dom_size, num_species, dom_hex = extract_dominant_species(memory, ips, num_ips)
            print(f"  [GENOME] Dominant: {dom_size}B | Species: {num_species} | Hex: {dom_hex}...")

        if num_ips > historical_max_pop:
            historical_max_pop = num_ips
            if historical_max_pop % 100 == 0: # Only alert on major boundaries
                print("\n========================================================")
                print(f"      !!! NEW POPULATION MILESTONE REACHED !!!           ")
                print("========================================================")
                print(f"Population reached {historical_max_pop}!")
                print(f"Total physics cycles searched: {total_cycles:,}")
                
                timestamp = int(time.time())
                milestone_bin = os.path.join(MILESTONES_DIR, f"AGI_MILESTONE_P{historical_max_pop}_{timestamp}.bin")
                
                with open(milestone_bin, "wb") as f:
                    f.write(memory.tobytes())
                print(f"Saved milestone to {milestone_bin}")

        # Phase 28: PANSPERMIA — Auto-restart on extinction
        if num_ips == 0:
            extinction_count += 1
            print(f"\n!!! EXTINCTION #{extinction_count} !!! Panspermia: Reseeding universe...", flush=True)
            
            # Save extinction snapshot
            timestamp = int(time.time())
            extinct_file = os.path.join(MILESTONES_DIR, f"EXTINCTION_{extinction_count}_{total_cycles}c_{timestamp}.npz")
            np.savez(extinct_file, memory=memory, total_cycles=total_cycles, extinction_count=extinction_count)
            
            # Reseed: inject fresh ancestors into the existing (corrupted) memory
            num_seeds = 100
            spacing = size // num_seeds
            for s in range(num_seeds):
                seed_pos = s * spacing
                for j, byte in enumerate(seed_code):
                    memory[(seed_pos + j) % size] = byte
                ips[s] = seed_pos
                for col in range(4):
                    registers[s, col] = 0
            num_ips = num_seeds
            zone_rates = DEFAULT_ZONE_RATES.copy()
            print(f"  Reseeded {num_seeds} ancestors. Evolution continues...\n")

        current_time = time.time()
        if current_time - last_save_time >= 60:  # Save every 60 seconds
            np.savez(checkpoint_file, 
                     memory=memory, 
                     ips=ips, 
                     registers=registers, 
                     num_ips=num_ips,
                     total_cycles=total_cycles,
                     historical_max_pop=historical_max_pop,
                     zone_rates=zone_rates,
                     extinction_count=extinction_count)
            print(f"Saved Checkpoint at {total_cycles:,} cycles", flush=True)
            last_save_time = current_time

if __name__ == "__main__":
    main()
