import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'src'))
sys.path.append(os.path.join(os.getcwd(), 'src/genesis/server'))

from genesis_pytorch_brain import GenesisPyTorchBrain
from brain_server import GenesisEngineRunner

print('Initializing GENESIS engine...')
runner = GenesisEngineRunner()

print('Running 10 steps...')
for i in range(10):
    runner.step_once()
    symbol = getattr(runner, 'prev_symbol', 'None')
    option = getattr(runner, 'prev_option', 'None')
    print(f'Step {i}: Option={option}, Emitted Symbol={symbol}')
    
print('Engine test passed!')
