import numpy as np
from numba import njit, prange
import time
import random
import os
from turing_engine import tick_numba
from primordial_seed import build_ancestor

@njit(parallel=True)
def run_lab_batch(memories, ips_all, registers_all, bonus_cycles_all, num_ips_all, max_ips, cycles, noise_rate, bounties_solved_all):
    N = memories.shape[0]
    mem_size = memories.shape[1]
    
    for i in prange(N):
        # Drop puzzles based on cycle count (rate = 0.1 per tick)
        num_puzzles = int(cycles * 0.1)
        for _ in range(num_puzzles):
            idx = random.randint(0, mem_size - 4)
            memories[i, idx] = 254
            x = random.randint(1, 255)
            y = random.randint(1, 255)
            while (x + y) % 256 == 0:
                y = random.randint(1, 255)
            memories[i, idx+1] = x
            memories[i, idx+2] = y
            memories[i, idx+3] = 0
            
        num_ips = tick_numba(
            memories[i], ips_all[i], registers_all[i], bonus_cycles_all[i],
            num_ips_all[i], max_ips, cycles, noise_rate, bounties_solved_all[i]
        )
        num_ips_all[i] = num_ips

from collections import Counter

def extract_dominant_dna(memory):
    """Finds the most repeated sequence in the memory of a successful universe."""
    counts = Counter()
    # Sample sliding windows of length 30
    for i in range(0, len(memory) - 30, 5):
        seq = tuple(memory[i:i+30])
        # Ignore empty space or purely NOPs
        if seq.count(0) < 25: 
            counts[seq] += 1
    if len(counts) > 0:
        return list(counts.most_common(1)[0][0])
    return None

def main():
    print("========================================================")
    print("      GENESIS LAB - META-EVOLUTIONARY GA BOOTSTRAP      ")
    print("========================================================")
    
    MILESTONES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Milestones")
    if not os.path.exists(MILESTONES_DIR):
        os.makedirs(MILESTONES_DIR)
    
    N = 250           # Number of parallel universes (balanced for CPU cores)
    size = 100000     # Memory size
    max_ips = 2000    # Lower max ips to speed up simulation per universe
    noise_rate = 2e-5 # Double mutagenic rate to compensate for smaller N
    cycles_per_batch = 10000
    
    seed_code = build_ancestor()
    best_dna = list(seed_code)
    
    print(f"Parallel Universes: {N}")
    print(f"Mutation Rate (Noise): {noise_rate}")
    print(f"Cycles per Batch: {cycles_per_batch}")
    print("Initializing Quantum Matrix...")
    
    checkpoint_file = os.path.join(MILESTONES_DIR, "CHECKPOINT.npz")
    
    # Pre-allocate numpy arrays
    memories = np.zeros((N, size), dtype=np.uint8)
    ips_all = np.zeros((N, max_ips), dtype=np.int32)
    registers_all = np.zeros((N, max_ips, 4), dtype=np.int32)
    bonus_cycles_all = np.zeros((N, max_ips), dtype=np.int32)
    num_ips_all = np.zeros(N, dtype=np.int32)
    bounties_solved_all = np.zeros((N, max_ips), dtype=np.int32)
    
    if os.path.exists(checkpoint_file):
        print(f"Resuming from {checkpoint_file}...")
        data = np.load(checkpoint_file)
        
        best_mem = data['memory']
        best_ips = data['ips']
        best_regs = data['registers']
        best_bonus = data['bonus_cycles']
        best_num = data['num_ips']
        batch_count = data['batch_count'].item()
        historical_max_bounties = int(data.get('historical_max', 0))
        historical_max_pop = int(data.get('historical_max_pop', 0))
        
        for i in range(N):
            memories[i] = np.copy(best_mem)
            ips_all[i] = np.copy(best_ips)
            registers_all[i] = np.copy(best_regs)
            bonus_cycles_all[i] = np.copy(best_bonus)
            num_ips_all[i] = best_num
            # Kill 50% for diversity
            kill_count = num_ips_all[i] // 2
            if kill_count > 0:
                ips_all[i, :kill_count] = ips_all[i, num_ips_all[i]-kill_count:num_ips_all[i]]
                num_ips_all[i] -= kill_count
                
        print(f"Successfully resumed at Batch {batch_count}")
    else:
        print("No checkpoint found. Starting from scratch...")
        batch_count = 0
        historical_max_bounties = 0
        historical_max_pop = 0
        # Seed all universes
        seed_idx = size // 2
        for i in range(N):
            for j, byte in enumerate(best_dna):
                memories[i, (seed_idx + j) % size] = byte
            ips_all[i, 0] = seed_idx
            num_ips_all[i] = 1
        
    print("Warming up Numba JIT compiler...")
    # Warmup
    run_lab_batch(memories, ips_all, registers_all, bonus_cycles_all, num_ips_all, max_ips, 1, noise_rate, bounties_solved_all)
    
    print("JIT Compiled. Commencing GA Search...")
    
    start_time = time.time()
    last_save_time = time.time()
    
    while True:
        # Rule 8: Efficiency Selection
        # 1. Primary: Intelligence (bounties solved)
        # 2. Secondary: Efficiency (population size - smaller/faster code reproduces more)
        max_bounties = np.max(bounties_solved_all)
        
        # Find the universe with the best bounties. If tie, find the one with highest population.
        best_bounty_universes = np.where(np.max(bounties_solved_all, axis=1) == max_bounties)[0]
        winning_idx = best_bounty_universes[np.argmax(num_ips_all[best_bounty_universes])]
        winning_pop = num_ips_all[winning_idx]

        is_new_milestone = False
        old_historical_max_bounties = historical_max_bounties
        old_historical_max_pop = historical_max_pop
        
        if max_bounties > historical_max_bounties:
            is_new_milestone = True
            historical_max_bounties = max_bounties
            historical_max_pop = winning_pop
        elif max_bounties > 0 and max_bounties == historical_max_bounties and winning_pop > historical_max_pop:
            is_new_milestone = True
            historical_max_pop = winning_pop
            
        if is_new_milestone:
            print("\n========================================================")
            print(f"            !!! INTELLIGENCE CANDIDATE !!!            ")
            print("========================================================")
            print("Running baseline validation on noise-free environment...")
            test_mem = np.copy(memories[winning_idx])
            test_ips = np.copy(ips_all[winning_idx])
            test_regs = np.copy(registers_all[winning_idx])
            test_bonus = np.copy(bonus_cycles_all[winning_idx])
            test_num = num_ips_all[winning_idx]
            test_bounties = np.zeros(max_ips, dtype=np.int32)
            
            # Inject puzzles to test
            num_puzzles = int(cycles_per_batch * 0.1)
            for _ in range(num_puzzles):
                idx = random.randint(0, size - 4)
                test_mem[idx] = 254
                x = random.randint(1, 255)
                y = random.randint(1, 255)
                while (x + y) % 256 == 0:
                    y = random.randint(1, 255)
                test_mem[idx+1] = x
                test_mem[idx+2] = y
                test_mem[idx+3] = 0
                
            tick_numba(test_mem, test_ips, test_regs, test_bonus, test_num, max_ips, cycles_per_batch, 0.0, test_bounties)
            
            if np.max(test_bounties) > 0:
                print("Validation PASSED! Intelligence is robust.")
                print(f"Universe {winning_idx} solved {max_bounties} puzzles with Population {winning_pop}!")
                print(f"Total physics cycles searched: {batch_count * cycles_per_batch * N:,}")
                
                timestamp = int(time.time())
                milestone_bin = os.path.join(MILESTONES_DIR, f"AGI_MILESTONE_B{historical_max_bounties}_P{winning_pop}_{timestamp}.bin")
                milestone_npz = os.path.join(MILESTONES_DIR, f"AGI_MILESTONE_B{historical_max_bounties}_P{winning_pop}_{timestamp}.npz")
                
                # Save the winning universe's memory
                with open(milestone_bin, "wb") as f:
                    f.write(memories[winning_idx].tobytes())
                
                # Save the full exact state too
                np.savez(milestone_npz, 
                         memory=memories[winning_idx], 
                         ips=ips_all[winning_idx], 
                         registers=registers_all[winning_idx], 
                         bonus_cycles=bonus_cycles_all[winning_idx], 
                         num_ips=num_ips_all[winning_idx],
                         batch_count=batch_count)
                print(f"Saved highly efficient milestone to {milestone_bin} and {milestone_npz}")
            else:
                print("Validation FAILED! The intelligence was an artifact of noise.")
                print("Killing false-positive universe to accelerate search...")
                num_ips_all[winning_idx] = 0
                historical_max_bounties = old_historical_max_bounties
                historical_max_pop = old_historical_max_pop

        # Check if we should re-seed dead universes using GA selection
        dead_count = np.sum(num_ips_all == 0)
        
        # Extinction Recovery: If the max population is less than 2, the multiverse is functionally dead (stagnant/sterile).
        # We must recover from the original seed to prevent "Survival of the Stagnant".
        if np.max(num_ips_all) < 2:
            print("!!! TOTAL MULTIVERSE EXTINCTION OR STAGNATION !!! Recovering from original seed...")
            for i in range(N):
                memories[i] = np.zeros(size, dtype=np.uint8)
                seed_pos = random.randint(0, size - len(seed_code))
                for j, byte in enumerate(seed_code):
                    memories[i, (seed_pos + j) % size] = byte
                ips_all[i, 0] = seed_pos
                registers_all[i] = np.zeros((max_ips, 4), dtype=np.int32)
                bonus_cycles_all[i] = np.zeros(max_ips, dtype=np.int32)
                num_ips_all[i] = 1
                bounties_solved_all[i] = np.zeros(max_ips, dtype=np.int32)
            
        elif dead_count > 0:
            # GA Selection: Find the most robust universe
            best_idx = np.argmax(num_ips_all)
            
            # Re-seed all dead universes by CLONING the best universe!
            for i in range(N):
                if num_ips_all[i] == 0:
                    # Clone memory (add tiny noise)
                    memories[i] = np.copy(memories[best_idx])
                    # Clone IPs and Registers
                    ips_all[i] = np.copy(ips_all[best_idx])
                    registers_all[i] = np.copy(registers_all[best_idx])
                    bonus_cycles_all[i] = np.copy(bonus_cycles_all[best_idx])
                    num_ips_all[i] = num_ips_all[best_idx]
                    bounties_solved_all[i] = bounties_solved_all[best_idx]
                    
                    # Randomly kill 50% of the population in the cloned universe to increase diversity
                    kill_count = num_ips_all[i] // 2
                    if kill_count > 0:
                        ips_all[i, :kill_count] = ips_all[i, num_ips_all[i]-kill_count:num_ips_all[i]]
                        num_ips_all[i] -= kill_count

        # Run the batch
        t0 = time.time()
        run_lab_batch(memories, ips_all, registers_all, bonus_cycles_all, num_ips_all, max_ips, cycles_per_batch, noise_rate, bounties_solved_all)
        t1 = time.time()
        
        batch_count += 1
        speed = (N * cycles_per_batch) / (t1 - t0) if t1 > t0 else 0
        total_cycles = batch_count * cycles_per_batch
        
        max_pop = np.max(num_ips_all)
        print(f"[Batch {batch_count}] Elapsed: {time.time()-start_time:.1f}s | Speed: {speed:,.0f} c/s | Extinctions: {dead_count}/{N} | Max Pop: {max_pop}", flush=True)

        current_time = time.time()
        if current_time - last_save_time >= 60:  # Save every 60 seconds
            best_idx = np.argmax(num_ips_all)
            np.savez(checkpoint_file, 
                     memory=memories[best_idx], 
                     ips=ips_all[best_idx], 
                     registers=registers_all[best_idx], 
                     bonus_cycles=bonus_cycles_all[best_idx], 
                     num_ips=num_ips_all[best_idx],
                     batch_count=batch_count,
                     historical_max=historical_max_bounties,
                     historical_max_pop=historical_max_pop)
            print(f"Saved Checkpoint at Batch {batch_count}", flush=True)
            last_save_time = current_time

if __name__ == "__main__":
    main()
