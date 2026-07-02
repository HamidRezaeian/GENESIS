import re
import os

with open('src/genesis_engine.py', 'r') as f:
    content = f.read()

# 1. Remove DynamicBrain
content = re.sub(r'class DynamicBrain:.*?return new_brain\n', '', content, flags=re.DOTALL)

# 2. Add CodeBrain import
content = content.replace("import logging\n", "import logging\nfrom brain import CodeBrain\n")

# 3. Rewrite Node.__init__
node_init_old = r'    def __init__\(self.*?self\.total_prediction_error = 0\.0\n.*?self\.age = 0\n'
node_init_new = """    def __init__(self, node_id, initial_energy, faction=BUILDER,
                 learning_rate=None, generation=0, parent=None):
        self.id = node_id
        self.energy = initial_energy
        self.visible_nodes = set()

        self.generation = generation
        self.parent_id = parent.id if parent else None
        self.children_spawned = 0
        
        self.is_egg = False
        self.incubation_timer = 0
        
        self.memory = {} # Arbitrary memory dict
        self.bindings = set()

        self.state = 0.0
        self._update_state()

        self.x = random.uniform(0, 1000)
        self.y = random.uniform(0, 1000)
        self.vx = 0.0
        self.vy = 0.0
        self.thrust_x = 0.0
        self.thrust_y = 0.0
        self.mass = 1.0 # Base mass

        self.faction = faction
        
        if parent:
            self.reproduction_threshold = max(20, min(100, parent.reproduction_threshold + random.gauss(0, 5)))
            self.brain = parent.brain.clone_and_mutate(parent.last_error)
        else:
            self.reproduction_threshold = 25.0
            self.brain = CodeBrain() 
            
        self.age = 0
        self.expected_delta = 0.0
        self.last_error = 0.0
        self.energy_before_tick = initial_energy
"""
content = re.sub(node_init_old, node_init_new, content, flags=re.DOTALL)

# 4. Replace predict_neighbors and evaluate_predictions with a single `think` method
predict_old = r'    def predict_neighbors\(self.*?def create_offspring'
predict_new = """    def think(self, universe, env_warning):
        if self.is_egg: return
        
        # Build context
        neighbors_data = []
        for nid in self.visible_nodes:
            neighbor = universe.get_node(nid)
            if neighbor and not neighbor.is_egg:
                dx = neighbor.x - self.x
                dy = neighbor.y - self.y
                dist = math.sqrt(dx*dx + dy*dy)
                neighbors_data.append({
                    'dx': dx, 'dy': dy, 'dist': dist,
                    'energy': neighbor.energy,
                    'vx': neighbor.vx, 'vy': neighbor.vy
                })
                
        context = {
            'x': self.x, 'y': self.y, 'energy': self.energy,
            'vx': self.vx, 'vy': self.vy, 'age': self.age,
            'env_warning': env_warning,
            'neighbors': neighbors_data
        }
        
        tx, ty, exp_delta, new_mem = self.brain.predict(context, self.memory)
        self.thrust_x = tx
        self.thrust_y = ty
        self.expected_delta = exp_delta
        self.memory = new_mem

    def evaluate_critique(self):
        if self.is_egg: return
        actual_delta = self.energy - self.energy_before_tick
        self.last_error = abs(actual_delta - self.expected_delta)
        self.energy_before_tick = self.energy

    def create_offspring"""
content = re.sub(predict_old, predict_new, content, flags=re.DOTALL)

# 5. Overhaul tick()
tick_old = r'        # Phase 1: PREDICT.*?# Phase 4: MOVEMENT & FRICTION'
tick_new = """        # Phase 1: PREDICT (and Storm spawning)
        new_warnings = set()
        if random.random() < 0.2:
            target_count = max(1, int(len(self.nodes) * 0.05))
            new_warnings = set(random.sample(list(self.nodes.keys()), min(target_count, len(self.nodes))))
            
        for n in self.nodes.values():
            env_warning = 1.0 if n.id in new_warnings else 0.0
            n.think(self, env_warning)

        # Storm hits (just generic damage now)
        self.storm_queue.append(new_warnings)
        self.hitting_storm = set()
        if len(self.storm_queue) > 3:
            self.hitting_storm = self.storm_queue.pop(0)
            for nid in self.hitting_storm:
                node = self.get_node(nid)
                if node:
                    node.energy -= 2.0 # Fixed storm damage

        # Phase 2: PHYSICAL COLLISIONS & EATING FOOD
        for n in self.nodes.values():
            if n.is_egg: continue
            
            # Eat food
            for food in self.foods[:]:
                dist_sq = (n.x - food.x)**2 + (n.y - food.y)**2
                if dist_sq < 400: # 20 radius
                    n.energy += food.energy
                    self.foods.remove(food)

            # Node Collisions (Kinetic Energy Transfer)
            for nid in n.visible_nodes:
                if nid <= n.id: continue # Only process pairs once
                other = self.get_node(nid)
                if other and not other.is_egg:
                    dx = other.x - n.x
                    dy = other.y - n.y
                    # Toroidal wrap
                    if dx > 500: dx -= 1000
                    elif dx < -500: dx += 1000
                    if dy > 500: dy -= 1000
                    elif dy < -500: dy += 1000
                    
                    dist_sq = dx*dx + dy*dy
                    if dist_sq < 400: # Collision radius 20
                        # Calculate relative velocity
                        dvx = n.vx - other.vx
                        dvy = n.vy - other.vy
                        impact_speed = math.sqrt(dvx*dvx + dvy*dvy)
                        
                        # Physical bouncing
                        n.vx += dx * 0.01
                        n.vy += dy * 0.01
                        other.vx -= dx * 0.01
                        other.vy -= dy * 0.01
                        
                        # If impact is fast enough, the faster node damages the slower node (Predation via physics!)
                        if impact_speed > 2.0:
                            n_speed = math.sqrt(n.vx**2 + n.vy**2)
                            other_speed = math.sqrt(other.vx**2 + other.vy**2)
                            
                            # Transfer 10% of target's energy per collision
                            if n_speed > other_speed:
                                transfer = other.energy * 0.10
                                other.energy -= transfer
                                n.energy += transfer
                            else:
                                transfer = n.energy * 0.10
                                n.energy -= transfer
                                other.energy += transfer

        # Phase 3: SELF-CRITIQUE
        for n in self.nodes.values():
            n.evaluate_critique()

        # Phase 4: MOVEMENT & FRICTION"""
content = re.sub(tick_old, tick_new, content, flags=re.DOTALL)

# 6. Remove Phase 6 backprop inside tick()
phase6_old = r'        # Phase 6: LEARNING \(Red Queen Dynamics\).*?# Phase 7: REPRODUCTION'
phase6_new = """        # Phase 6: LEARNING (Removed - Handled by genetic mutation in AST)
        
        # Phase 7: REPRODUCTION"""
content = re.sub(phase6_old, phase6_new, content, flags=re.DOTALL)

# 7. Update export_state_json (remove brain_size, add code_len)
export_old = r"'avg_err'.*?'is_attacking': n\.attacking\n"
export_new = """'code_len': len(n.brain.code_str) if n.brain else 0,
                'x': round(n.x, 2), 'y': round(n.y, 2),
                'is_egg': n.is_egg,
                'error': round(n.last_error, 2)
"""
content = re.sub(export_old, export_new, content, flags=re.DOTALL)

with open('src/genesis_engine.py', 'w') as f:
    f.write(content)

print("Rewrite complete")
