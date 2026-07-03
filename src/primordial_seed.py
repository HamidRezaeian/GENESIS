import time
import numpy as np
from turing_engine import Universe, OP_GET_IP_A, OP_SET_C_IMM, OP_ALLOC_B_IMM, OP_READ_A_TO_D, OP_WRITE_B_FROM_D, OP_INC_A, OP_INC_B, OP_DEC_C, OP_JNZ_BWD_IMM, OP_SPLIT_B, OP_KILL

def build_ancestor():
    # 19-byte perfect replicator
    # Copies itself to IP + 41, spawns a new IP there, and then jumps back to start.
    return [
        OP_GET_IP_A,               # 0: A = IP
        OP_SET_C_IMM, 19,          # 1-2: C = 19 (Length)
        OP_ALLOC_B_IMM, 41,        # 3-4: B = IP + 41
        
        # Copy Loop
        OP_READ_A_TO_D,            # 5: D = mem[A]
        OP_WRITE_B_FROM_D,         # 6: mem[B] = D
        OP_INC_A,                  # 7: A++
        OP_INC_B,                  # 8: B++
        OP_DEC_C,                  # 9: C--
        OP_JNZ_BWD_IMM, 7,         # 10-11: if C!=0: IP -= 7 (Jumps back to 5)
        
        # Spawn
        OP_ALLOC_B_IMM, 41,        # 12-13: B = IP + 41 
        OP_SPLIT_B,                # 14: Spawn new IP at B
        OP_SET_C_IMM, 1,           # 15-16: Set C to 1 so we can jump unconditionally
        OP_JNZ_BWD_IMM, 19         # 17-18: Jump back 19 bytes to the start of the code!
    ]

def main():
    universe = Universe(size=100000, max_ips=10000, noise_rate=0.0)
    
    seed_code = build_ancestor()
    print(f"Ancestor length: {len(seed_code)} bytes")
    
    # Inject at address 100
    universe.seed(100, seed_code)
    
    print(f"Initial Population: {universe.num_ips}")
    
    # Run a few ticks manually to trace execution
    print("\n--- TRACE ---")
    for step in range(120):
        if universe.num_ips > 0:
            ip = universe.ips[0]
            op = universe.memory[ip]
            print(f"Step {step}: IP={ip}, OP={op}, A={universe.registers[0,0]}, B={universe.registers[0,1]}, C={universe.registers[0,2]}, D={universe.registers[0,3]}")
        universe.tick(cycles=1)
        
    print(f"\nPopulation after 50 cycles: {universe.num_ips}")
    
    print("\n--- PERFORMANCE TEST ---")
    universe = Universe(size=100000, max_ips=10000, noise_rate=0.0)
    universe.seed(100, seed_code)
    
    start_time = time.time()
    for _ in range(10):
        universe.tick(cycles=1000)
    
    end_time = time.time()
    elapsed = end_time - start_time
    total_cycles = 10 * 1000
    print(f"Executed {total_cycles:,} cycles in {elapsed:.4f} seconds")
    print(f"Speed: {total_cycles / elapsed:,.0f} cycles/sec")
    print(f"Final Population: {universe.num_ips}")

if __name__ == "__main__":
    main()
