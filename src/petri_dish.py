import pygame
import numpy as np
import time
import sys
import os
from numba import njit
from turing_engine import tick_numba

# --- CONFIGURATION ---
GRID_SIZE = 181 # 181x181 = 32761 (close to 32768)
CELL_SIZE = 3   # Make cells slightly larger since grid is smaller
WIDTH = GRID_SIZE * CELL_SIZE
HEIGHT = GRID_SIZE * CELL_SIZE
MEM_SIZE = 32768

# Colors
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)      # Energy (255)
WHITE = (255, 255, 255)  # DNA (Regular opcodes)
RED = (255, 0, 0)        # Crypto Molecules (254)
BLUE = (0, 100, 255)     # Instruction Pointers

import glob
import os

def load_state():
    memory = np.zeros(MEM_SIZE, dtype=np.uint8)
    max_ips = 1000
    ips = np.zeros(max_ips, dtype=np.int32)
    registers = np.zeros((max_ips, 4), dtype=np.int32)
    bonus_cycles = np.zeros(max_ips, dtype=np.int32)
    num_ips = 0
    
    MILESTONES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Milestones")
    milestones = glob.glob(os.path.join(MILESTONES_DIR, "AGI_MILESTONE_*.npz"))
    
    if milestones:
        # Load the latest milestone
        latest = max(milestones, key=os.path.getctime)
        print(f"Loading evolutionary milestone: {latest}")
        data = np.load(latest)
        memory[:] = data['memory']
        ips[:] = data['ips']
        registers[:] = data['registers']
        bonus_cycles[:] = data['bonus_cycles']
        num_ips = data['num_ips'].item()
    elif os.path.exists(os.path.join(MILESTONES_DIR, "AGI_STATE.npz")):
        print("Loading exact CPU state from AGI_STATE.npz...")
        data = np.load(os.path.join(MILESTONES_DIR, "AGI_STATE.npz"))
        memory[:] = data['memory']
        ips[:] = data['ips']
        registers[:] = data['registers']
        bonus_cycles[:] = data['bonus_cycles']
        num_ips = data['num_ips'].item()
    elif os.path.exists(os.path.join(MILESTONES_DIR, "AGI_SEED.bin")):
        print("Loading DNA from AGI_SEED.bin...")
        with open(os.path.join(MILESTONES_DIR, "AGI_SEED.bin"), "rb") as f:
            data = f.read()
            length = min(MEM_SIZE, len(data))
            memory[:length] = np.frombuffer(data[:length], dtype=np.uint8)
        
        # Jump-start IP
        for i in range(0, MEM_SIZE - 20):
            if np.sum(memory[i:i+20]) > 100:
                ips[0] = i
                num_ips = 1
                print(f"Jump-started IP at {i}")
                break
        if num_ips == 0:
            ips[0] = MEM_SIZE // 2
            num_ips = 1
    else:
        print("Could not find AGI state. Starting with empty soup.")
        ips[0] = MEM_SIZE // 2
        num_ips = 1
        
    return memory, ips, registers, bonus_cycles, num_ips

def index_to_xy(idx):
    """Convert a 1D memory index to 2D grid coordinates."""
    idx = idx % (GRID_SIZE * GRID_SIZE)
    y = idx // GRID_SIZE
    x = idx % GRID_SIZE
    return x, y

def xy_to_index(x, y):
    """Convert 2D grid coordinates back to 1D memory index."""
    if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
        return y * GRID_SIZE + x
    return -1

def render_grid(surface, memory, ips, num_ips):
    # Create a 2D pixel array representing the grid
    pixels = np.zeros((GRID_SIZE, GRID_SIZE, 3), dtype=np.uint8)
    
    # We map the 1D memory into a 2D array of colors
    # For performance, we'll do this in Python. If it's too slow, we can move to Numba.
    
    # 0 -> Black
    # 255 -> Green
    # 254 -> Red
    # 1-253 -> White
    
    # We truncate memory to exactly fit the grid for easy reshaping
    grid_mem = memory[:GRID_SIZE*GRID_SIZE].reshape((GRID_SIZE, GRID_SIZE))
    
    # Color mapping
    pixels[grid_mem == 255] = GREEN
    pixels[grid_mem == 254] = RED
    
    # DNA (1 to 253)
    dna_mask = (grid_mem > 0) & (grid_mem < 254)
    pixels[dna_mask] = WHITE
    
    # Draw Instruction Pointers
    for i in range(num_ips):
        idx = ips[i]
        if idx < GRID_SIZE * GRID_SIZE:
            x, y = index_to_xy(idx)
            pixels[y, x] = BLUE # Note: y is rows, x is cols
            
    # Surface plotting requires Transposed pixels (X, Y)
    pygame.surfarray.blit_array(surface, np.transpose(pixels, (1, 0, 2)))

def drop_puzzle(memory, idx, x_val, y_val):
    if idx >= 0 and idx < MEM_SIZE - 4:
        memory[idx] = 254
        memory[idx+1] = x_val
        memory[idx+2] = y_val
        memory[idx+3] = 0
        print(f"Dropped puzzle [254, {x_val}, {y_val}, 0] at index {idx}")

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Genesis Interactive Petri Dish")
    
    # Create an offscreen surface for rendering the pixel grid
    grid_surface = pygame.Surface((GRID_SIZE, GRID_SIZE))
    
    # Engine state
    memory, ips, registers, bonus_cycles, num_ips = load_state()
    max_ips = 2000
    
    bounties_solved = np.zeros(1, dtype=np.int32)
    
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    
    running = True
    paused = False
    cycles_per_frame = 500
    noise_rate = 1e-6
    total_cycles = 0
    
    # Input state for God Mode
    awaiting_input = False
    input_str = ""
    target_idx = -1
    
    while running:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not awaiting_input:
                    paused = not paused
                elif event.key == pygame.K_UP and not awaiting_input:
                    cycles_per_frame = min(cycles_per_frame + 500, 10000)
                elif event.key == pygame.K_DOWN and not awaiting_input:
                    cycles_per_frame = max(cycles_per_frame - 500, 100)
                
                # Handle Input Box
                if awaiting_input:
                    if event.key == pygame.K_RETURN:
                        # Parse X, Y
                        try:
                            parts = input_str.split(',')
                            if len(parts) == 2:
                                x_val = int(parts[0].strip())
                                y_val = int(parts[1].strip())
                                drop_puzzle(memory, target_idx, x_val, y_val)
                        except ValueError:
                            pass
                        awaiting_input = False
                        input_str = ""
                    elif event.key == pygame.K_BACKSPACE:
                        input_str = input_str[:-1]
                    else:
                        input_str += event.unicode
                        
            elif event.type == pygame.MOUSEBUTTONDOWN and not awaiting_input:
                if event.button == 1: # Left click
                    # Enter God Mode
                    mx, my = pygame.mouse.get_pos()
                    gx, gy = mx // CELL_SIZE, my // CELL_SIZE
                    target_idx = xy_to_index(gx, gy)
                    if target_idx != -1:
                        awaiting_input = True
                        input_str = ""
        
        # Physics update
        if not paused and not awaiting_input:
            num_ips = tick_numba(
                memory, ips, registers, bonus_cycles, num_ips,
                max_ips, cycles_per_frame, noise_rate, bounties_solved
            )
            total_cycles += cycles_per_frame
            
        # Rendering
        screen.fill(BLACK)
        
        # 1. Update Grid Surface
        render_grid(grid_surface, memory, ips, num_ips)
        
        # 2. Scale and Blit
        scaled_grid = pygame.transform.scale(grid_surface, (WIDTH, HEIGHT))
        screen.blit(scaled_grid, (0, 0))
        
        # 3. UI Overlay
        status_color = WHITE if not paused else RED
        status_text = f"Cycles: {total_cycles:,} | Pop: {num_ips} | Solved: {bounties_solved[0]}"
        text_surface = font.render(status_text, True, status_color)
        screen.blit(text_surface, (10, 10))
        
        speed_text = f"Speed: {cycles_per_frame} cycles/frame (Up/Down to change)"
        speed_surface = font.render(speed_text, True, WHITE)
        screen.blit(speed_surface, (10, 30))
        
        # 4. God Mode Overlay
        if awaiting_input:
            # Draw semi-transparent overlay
            s = pygame.Surface((WIDTH,HEIGHT))
            s.set_alpha(128)
            s.fill(BLACK)
            screen.blit(s, (0,0))
            
            prompt = font.render(f"God Mode - Drop Puzzle at index {target_idx}", True, WHITE)
            screen.blit(prompt, (WIDTH//2 - 150, HEIGHT//2 - 50))
            
            hint = font.render("Enter X,Y (e.g. 45,12) and press ENTER:", True, GREEN)
            screen.blit(hint, (WIDTH//2 - 150, HEIGHT//2 - 20))
            
            input_box = font.render(input_str + "_", True, WHITE)
            screen.blit(input_box, (WIDTH//2 - 150, HEIGHT//2 + 10))
            
        pygame.display.flip()
        clock.tick(60) # 60 FPS

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
