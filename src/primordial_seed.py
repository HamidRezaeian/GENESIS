import time
import numpy as np
import random
from turing_engine import Universe, DEFAULT_ZONE_RATES, OP_GET_IP_A, OP_SET_C_IMM, OP_ALLOC_B_IMM, OP_READ_A_TO_D, OP_WRITE_B_FROM_D, OP_INC_A, OP_INC_B, OP_DEC_C, OP_JNZ_BWD_IMM, OP_SPLIT_B, OP_SENSE_ZONE, OP_JZ_FWD_IMM_D

def build_ancestor():
    # 29-byte Smart Ancestor (Meta-Learning Seed)
    # Checks local thermodynamic zone. If cold (D==0), spawns near (+48). If hot (D!=0), spawns far (+128).
    return [
        # --- INITIALIZATION ---
        OP_GET_IP_A,               # 0: A = IP
        OP_SET_C_IMM, 29,          # 1-2: C = 29 (Length)
        OP_ALLOC_B_IMM, 45,        # 3-4: B = IP + 45 (Near spawn: 3+45 = 48)
        
        # --- ZONE CHECK 1 ---
        OP_SENSE_ZONE,             # 5: D = Zone
        OP_JZ_FWD_IMM_D, 2,        # 6-7: If D==0 (Cold), jump forward 2 (skips next instruction)
        OP_ALLOC_B_IMM, 120,       # 8-9: B = IP + 120 (Far spawn: 8+120 = 128). Executed only if Hot.
        
        # --- COPY LOOP ---
        OP_READ_A_TO_D,            # 10: D = mem[A]
        OP_WRITE_B_FROM_D,         # 11: mem[B] = D
        OP_INC_A,                  # 12: A++
        OP_INC_B,                  # 13: B++
        OP_DEC_C,                  # 14: C--
        OP_JNZ_BWD_IMM, 7,         # 15-16: if C!=0: IP -= 7 (Jumps to 10)
        
        # --- ZONE CHECK 2 (Restore B for Split) ---
        OP_ALLOC_B_IMM, 31,        # 17-18: B = IP + 31 (Near child start: 17+31 = 48)
        OP_SENSE_ZONE,             # 19: D = Zone
        OP_JZ_FWD_IMM_D, 2,        # 20-21: If D==0, skip next
        OP_ALLOC_B_IMM, 106,       # 22-23: B = IP + 106 (Far child start: 22+106 = 128)
        
        # --- SPLIT & RESTART ---
        OP_SPLIT_B,                # 24: Split! Child IP = B
        OP_SET_C_IMM, 1,           # 25-26: C=1
        OP_JNZ_BWD_IMM, 29         # 27-28: IP -= 29. Jump back to 0.
    ]

def main():
    universe = Universe(size=32768, max_ips=10000, noise_rate=0.0)
    
    seed_code = build_ancestor()
    print(f"Ancestor length: {len(seed_code)} bytes")
    
    # Inject at address 100
    universe.seed(100, seed_code)
    
    print(f"Initial Population: {universe.num_ips}")
    
    # Run a few ticks manually to trace execution
    print("\n--- TRACE ---")
    for step in range(250):
        if universe.num_ips > 0:
            ip = universe.ips[0]
            op = universe.memory[ip]
            print(f"Step {step}: IP={ip}, OP={op}, A={universe.registers[0,0]}, B={universe.registers[0,1]}, C={universe.registers[0,2]}, D={universe.registers[0,3]}")
        universe.tick(cycles=1)
        
    print(f"\nPopulation after 50 cycles: {universe.num_ips}")
    
    print("\n--- PERFORMANCE TEST ---")
    universe = Universe(size=131072, max_ips=10000, noise_rate=0.0)
    universe.seed(100, seed_code)
    
    start_time = time.time()
    for _ in range(10):
        universe.tick(cycles=1000)
    
    end_time = time.time()
    elapsed = max(end_time - start_time, 0.0001)
    total_cycles = 10 * 1000
    print(f"Executed {total_cycles:,} cycles in {elapsed:.4f} seconds")
    print(f"Speed: {total_cycles / elapsed:,.0f} cycles/sec")
    print(f"Final Population: {universe.num_ips}")

if __name__ == "__main__":
    main()
