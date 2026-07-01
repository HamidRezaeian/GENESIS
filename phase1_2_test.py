import logging
from genesis_engine import initialize_universe, BUILDER, EXPLOITER

def run_test():
    universe = initialize_universe(num_nodes=300)
    
    pre_catastrophe_error = 0
    post_catastrophe_error = 0
    recovery_tick = -1
    
    print("Running simulation...")
    for t in range(1, 1001):
        stats = universe.tick()
        
        # Trigger catastrophe at tick 500
        if t == 500:
            pre_catastrophe_error = stats['avg_surprise']
            print(f"Tick 499 (Pre-Catastrophe) Avg Error: {pre_catastrophe_error:.5f}")
            universe.trigger_catastrophe(rewire_ratio=0.8) # 80% rewire
            print(">>> CATASTROPHE TRIGGERED <<<")
            
        if t == 501:
            post_catastrophe_error = stats['avg_surprise']
            print(f"Tick 500 (Post-Catastrophe) Avg Error: {post_catastrophe_error:.5f}")
            
        # Check recovery
        if t > 501 and recovery_tick == -1 and stats['avg_surprise'] <= pre_catastrophe_error * 1.5:
            recovery_tick = t
            print(f"Recovered at Tick {t} (Took {t - 500} ticks)")
            
    # Gather Brain Size data
    brain_sizes = {}
    for n in universe.nodes.values():
        size = len(n.brain.w_in)
        brain_sizes[size] = brain_sizes.get(size, 0) + 1
        
    print("\n--- Final Brain Size Distribution ---")
    for size, count in sorted(brain_sizes.items()):
        print(f"Hidden Nodes: {size} -> Population: {count}")

if __name__ == "__main__":
    run_test()
