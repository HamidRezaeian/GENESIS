import logging
from genesis_engine import initialize_universe

def run_verify():
    universe = initialize_universe(num_nodes=300)
    
    print("Running verification simulation...")
    naive_beats_net = 0
    net_beats_naive = 0
    
    for t in range(1, 501):
        stats = universe.tick()
        
        if stats['avg_surprise'] < stats['avg_naive']:
            net_beats_naive += 1
        elif stats['avg_surprise'] > stats['avg_naive']:
            naive_beats_net += 1
            
        if t % 100 == 0:
            print(f"Tick {t} | Net Err: {stats['avg_surprise']:.5f} | Naive Err: {stats['avg_naive']:.5f}")
            
    print(f"\nFinal Tally: Net won {net_beats_naive} times, Naive won {naive_beats_net} times.")
    if net_beats_naive > naive_beats_net:
        print("SUCCESS: The Neural Network is learning and outperforming the naive baseline!")
    else:
        print("FAILURE: The Neural Network is still worse than doing nothing.")

if __name__ == "__main__":
    run_verify()
