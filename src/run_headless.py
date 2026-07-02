import time
import argparse
import numpy as np
from genesis_engine import initialize_universe

def run_headless():
    parser = argparse.ArgumentParser(description="GENESIS Headless Engine")
    parser.add_argument('--gpu', action='store_true', help='Use GPU (CUDA) if available')
    args = parser.parse_args()

    print(f"🚀 Starting GENESIS Headless Engine (Pure Physics Mode)")
    print(f"GPU Acceleration: {'Enabled' if args.gpu else 'Disabled'}")
    
    arena = initialize_universe(use_gpu=args.gpu)
    
    start_time = time.time()
    last_report_time = start_time
    
    REPORT_INTERVAL_TICKS = 50000  # Report every 50k ticks
    
    try:
        while True:
            arena.tick()
            
            if arena.tick_count % REPORT_INTERVAL_TICKS == 0:
                now = time.time()
                elapsed = now - last_report_time
                ticks_per_sec = REPORT_INTERVAL_TICKS / elapsed if elapsed > 0 else 0
                
                # Calculate True Physics Metrics
                pop = arena.num_threads
                if pop > 0:
                    avg_energy = np.mean(arena.threads[:pop, 3])
                    total_replications = np.sum(arena.threads[:pop, 8])
                else:
                    avg_energy = 0
                    total_replications = 0
                
                print(f"[{arena.tick_count:,} Cycles] "
                      f"Speed: {ticks_per_sec:,.0f} cycles/sec | "
                      f"Pop: {pop} | "
                      f"Avg Energy: {avg_energy:,.0f} | "
                      f"Total Replications: {total_replications:,}", flush=True)
                
                last_report_time = now
                
    except KeyboardInterrupt:
        print("\n🛑 Evolution halted by user.")
        print(f"Total Cycles Simulated: {arena.tick_count:,}")
        
if __name__ == "__main__":
    run_headless()
