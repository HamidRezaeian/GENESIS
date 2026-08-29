import cProfile
import pstats
from src.genesis.server.brain_server import GenesisEngineRunner

runner = GenesisEngineRunner()

# Warmup
for _ in range(5):
    runner.step_once()

# Profile
profiler = cProfile.Profile()
profiler.enable()
for _ in range(50):
    runner.step_once()
profiler.disable()

stats = pstats.Stats(profiler).sort_stats('cumtime')
stats.print_stats(20)
