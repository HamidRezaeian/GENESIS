"""Export Substrate 7 Latent MCTS Trained Brain to JSON for Browser Loading.
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from experiments.sub7_latent_mcts_agent import Substrate7LatentMCTSAgent, MultiRoomMazeEnvironment, MCTS_SIMS, MCTS_DEPTH, N_ACTIONS

def train_and_export_brain(ticks=30000, seed=100):
    print(f"Training Substrate 7 Latent MCTS Brain on Seed {seed} across {ticks:,} ticks...")
    env = MultiRoomMazeEnvironment(seed=seed)
    agent = Substrate7LatentMCTSAgent(seed=seed)

    obs = env.get_observation()
    h_curr = agent.encode(obs)

    goals = 0
    doors = 0
    food = 0
    hazards = 0

    for tick in range(ticks):
        _, action_probs = agent.run_mcts(h_curr, n_sims=MCTS_SIMS, max_depth=MCTS_DEPTH)
        action = agent.rng.choice(N_ACTIONS, p=action_probs)

        next_obs, reward, door_unlocked, goal_reached = env.step(action)
        h_next = agent.encode(next_obs)

        agent.update(h_curr, action, reward, h_next)

        if door_unlocked: doors += 1
        if goal_reached: goals += 1
        if reward == 10.0: food += 1
        if reward <= -5.0: hazards += 1

        obs = next_obs
        h_curr = h_next

    print(f"Training Complete! Goals={goals}, Doors={doors}, Food={food}, Hazards={hazards}")

    # Serialize to web JSON format
    brain_data = {
        "tickCount": ticks,
        "goalsSolved": goals,
        "foodHarvested": food,
        "doorsUnlocked": doors,
        "hazardCollisions": hazards,
        "W_vis": agent.W_vis.tolist(),
        "W_pos": agent.W_pos.tolist(),
        "W_q": agent.W_q.tolist(),
        "W_k": agent.W_k.tolist(),
        "W_v": agent.W_v.tolist(),
        "W_out": agent.W_out.tolist(),
        "W_ff1": agent.W_ff1.tolist(),
        "W_ff2": agent.W_ff2.tolist(),
        "W_dyn": agent.W_dyn.tolist(),
        "W_rew": agent.W_rew.tolist(),
        "W_val": agent.W_val.tolist(),
        "W_policy": agent.W_policy.tolist()
    }

    out_brain = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Brain", "sub7_mcts_trained_brain.json"))
    out_public = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "sub7_mcts_trained_brain.json"))

    with open(out_brain, "w") as f:
        json.dump(brain_data, f)
    with open(out_public, "w") as f:
        json.dump(brain_data, f)

    print(f"✅ Exported to: {out_brain}")
    print(f"✅ Exported to: {out_public}")

if __name__ == "__main__":
    train_and_export_brain(ticks=30000, seed=100)
