from genesis_engine import initialize_universe
universe = initialize_universe(num_nodes=300, builder_ratio=0.7)
print("Initial:", sum(1 for n in universe.nodes.values() if n.faction == 1))
for t in range(50):
    stats = universe.tick()
    if t < 10 or stats['exploiters'] == 0:
        print(f"Tick {t+1}: {stats['exploiters']} exploiters alive.")
        if stats['exploiters'] == 0:
            break
