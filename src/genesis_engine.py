"""
GENESIS Engine v0.4 — Digital Universe with Red Queen Coevolution
=================================================================
Two factions compete in an evolutionary arms race:
  - BUILDERS (Faction 0, Blue): Thrive by creating stable, complex structures.
    They gain bonus energy from maintaining stable edges with allies.
  - EXPLOITERS (Faction 1, Red): Thrive by predicting and disrupting Builders.
    They gain bonus energy from accurately predicting cross-faction neighbors.

Neither faction can rest — when one gets ahead, the other is under pressure
to evolve. This is the Red Queen Hypothesis: "You have to run as fast as you
can just to stay in the same place."
"""

import random
import math
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Faction constants
BUILDER = 0
EXPLOITER = 1
FACTION_NAMES = {BUILDER: "Builder", EXPLOITER: "Exploiter"}

class DynamicBrain:
    def __init__(self, input_size, output_size, hidden_size=0):
        import random
        self.i_sz = input_size
        self.o_sz = output_size
        self.w_in = [[random.uniform(-1, 1) for _ in range(input_size)] for _ in range(hidden_size)]
        self.b_in = [random.uniform(-1, 1) for _ in range(hidden_size)]
        self.w_out = [[random.uniform(-1, 1) for _ in range(hidden_size)] for _ in range(output_size)]
        self.b_out = [random.uniform(-1, 1) for _ in range(output_size)]
        self.direct_w = [[random.uniform(-1, 1) for _ in range(input_size)] for _ in range(output_size)]
        
    def predict(self, x):
        hidden_acts = []
        for i in range(len(self.w_in)):
            val = sum(x[j] * self.w_in[i][j] for j in range(self.i_sz)) + self.b_in[i]
            val = max(0.01 * val, val)
            hidden_acts.append(val)
            
        out = []
        for o in range(self.o_sz):
            val = sum(x[j] * self.direct_w[o][j] for j in range(self.i_sz)) + self.b_out[o]
            val += sum(hidden_acts[i] * self.w_out[o][i] for i in range(len(hidden_acts)))
            out.append(max(0.0, min(1.0, val))) # clamp output
        
        context = {'x': list(x), 'hidden_acts': hidden_acts}
        return out, context
        
    def learn(self, lr, errors, context):
        x = context['x']
        hidden_acts = context['hidden_acts']
        grad_x = [0.0] * self.i_sz
        
        for o in range(self.o_sz):
            err = errors[o]
            self.b_out[o] -= lr * err
            for j in range(self.i_sz):
                self.direct_w[o][j] -= lr * err * x[j]
                grad_x[j] += err * self.direct_w[o][j]
                
            for i in range(len(self.w_out[o])):
                h_act = hidden_acts[i]
                self.w_out[o][i] -= lr * err * h_act
                hidden_error = err * self.w_out[o][i]
                grad = 1 if h_act > 0 else 0.01
                hidden_error *= grad
                self.b_in[i] -= lr * hidden_error
                for j in range(self.i_sz):
                    self.w_in[i][j] -= lr * hidden_error * x[j]
                    grad_x[j] += hidden_error * self.w_in[i][j]
                    
        return grad_x
        
    def get_weight_count(self):
        return self.o_sz + (self.o_sz * self.i_sz) + (self.o_sz * len(self.w_in)) + len(self.w_in) + (len(self.w_in) * self.i_sz)

            
    def clone_and_mutate(self):
        import random
        new_brain = DynamicBrain(self.i_sz, self.o_sz, len(self.w_in))
        
        for o in range(self.o_sz):
            new_brain.b_out[o] = self.b_out[o] + random.gauss(0, 0.01)
            for j in range(self.i_sz):
                new_brain.direct_w[o][j] = self.direct_w[o][j] + random.gauss(0, 0.01)
            for i in range(len(self.w_in)):
                new_brain.w_out[o][i] = self.w_out[o][i] + random.gauss(0, 0.01)
                
        for i in range(len(self.w_in)):
            new_brain.b_in[i] = self.b_in[i] + random.gauss(0, 0.01)
            for j in range(self.i_sz):
                new_brain.w_in[i][j] = self.w_in[i][j] + random.gauss(0, 0.01)
        
        # Phase 2: Structural Mutation - 2% chance to grow a new neuron
        if random.random() < 0.02:
            new_brain.w_in.append([random.uniform(-1, 1) for _ in range(self.i_sz)])
            new_brain.b_in.append(random.uniform(-1, 1))
            for o in range(self.o_sz):
                new_brain.w_out[o].append(random.uniform(-1, 1))
            
        return new_brain

class Food:
    def __init__(self, x, y, energy):
        self.x = x
        self.y = y
        self.energy = energy

class Node:
    def __init__(self, node_id, initial_energy, faction=BUILDER,
                 learning_rate=None, generation=0, parent=None):
        self.id = node_id
        self.energy = initial_energy
        self.visible_nodes = set()

        # Lineage
        self.generation = generation
        self.parent_id = parent.id if parent else None
        self.children_spawned = 0
        
        self.is_egg = False
        self.incubation_timer = 0
        
        self.memory = [0.0, 0.0]
        self.bindings = set()

        # Observable state
        self.state = 0.0
        self._update_state()

        # Spatial physics
        self.x = random.uniform(0, 1000)
        self.y = random.uniform(0, 1000)
        self.vx = 0.0
        self.vy = 0.0
        self.thrust_x = 0.0
        self.thrust_y = 0.0

        # Internal World Model
        self.internal_model = {}
        self.predictions = {}
        self.predicted_next_state = None

        # Genetic traits
        if parent:
            self.lr = max(0.001, min(0.2, parent.lr + random.gauss(0, 0.01)))
            self.reproduction_threshold = max(20, min(100, parent.reproduction_threshold + random.gauss(0, 5)))
            self.faction = parent.faction
            self.brain = parent.brain.clone_and_mutate()
        else:
            self.lr = learning_rate if learning_rate is not None else random.uniform(0.01, 0.1)
            self.reproduction_threshold = 25.0
            self.faction = faction
            self.brain = DynamicBrain(input_size=5, output_size=9, hidden_size=0) 
            
        self.stability = random.uniform(0.0, 1.0)
        self.aggression = random.uniform(0.0, 0.5)
        self.signal = 0.0
        self.defended = False
        self.attacking = False
        self.received_signal_error = 0.0
        self.next_received_signal_error = 0.0

        # Statistics
        self.total_prediction_error = 0.0
        self.prediction_count = 0
        self.avg_prediction_error = 1.0
        self.age = 0

    def _update_state(self):
        if self.is_egg:
            self.state = 0.5
        else:
            self.state = 1.0 / (1.0 + math.exp(-0.1 * (self.energy - 5.0)))

    def predict_neighbors(self, universe, env_warning):
        if self.is_egg: return
        self.predictions = {}
        my_total_signal = 0
        my_total_defend = 0
        my_total_thrust_x = 0
        my_total_thrust_y = 0
        my_total_next_mem = [0.0, 0.0]
        self.naive_surprise = 0.0
        
        if not self.visible_nodes:
            outs, context = self.brain.predict([0.0, env_warning, 0.0] + self.memory)
            self.signal = outs[2]
            self.defended = outs[1] > 0.5
            self.thrust_x = outs[3] * 2.0 - 1.0
            self.thrust_y = outs[4] * 2.0 - 1.0
            self.memory = outs[5:7]
            self.attacking = outs[8] > 0.5
            self.predictions['ENV'] = {
                'pred_state': 0.0,
                'def_action': outs[1],
                'sig': outs[2],
                'thrust_x': outs[3] * 2.0 - 1.0,
                'thrust_y': outs[4] * 2.0 - 1.0,
                'next_mem': outs[5:7],
                'bind_action': outs[7],
                'attack_action': outs[8],
                'context': context,
                'actual_state_before_tick': 0.0
            }
            return

        my_total_attack = 0

        for neighbor_id in self.visible_nodes:
            neighbor = universe.get_node(neighbor_id)
            if neighbor:
                outs, context = self.brain.predict([neighbor.state, env_warning, neighbor.signal] + self.memory)
                pred_state, def_action, sig = outs[0], outs[1], outs[2]
                thrust_x = outs[3] * 2.0 - 1.0
                thrust_y = outs[4] * 2.0 - 1.0
                next_mem = outs[5:7]
                bind_action = outs[7]
                attack_action = outs[8]
                self.predictions[neighbor_id] = {
                    'pred_state': pred_state,
                    'def_action': def_action,
                    'sig': sig,
                    'thrust_x': thrust_x,
                    'thrust_y': thrust_y,
                    'next_mem': next_mem,
                    'bind_action': bind_action,
                    'attack_action': attack_action,
                    'context': context,
                    'actual_state_before_tick': neighbor.state
                }
                my_total_signal += sig
                my_total_defend += def_action
                my_total_thrust_x += thrust_x
                my_total_thrust_y += thrust_y
                my_total_next_mem[0] += next_mem[0]
                my_total_next_mem[1] += next_mem[1]
                my_total_attack += attack_action
                
        self.signal = my_total_signal / len(self.visible_nodes)
        self.defended = (my_total_defend / len(self.visible_nodes)) > 0.5
        self.thrust_x = my_total_thrust_x / len(self.visible_nodes)
        self.thrust_y = my_total_thrust_y / len(self.visible_nodes)
        self.attacking = (my_total_attack / len(self.visible_nodes)) > 0.5
        self.memory = [m / len(self.visible_nodes) for m in my_total_next_mem]

    def evaluate_predictions(self, universe):
        if self.is_egg or not self.predictions:
            return 1.0, 1.0
        total_error = 0.0
        total_naive_error = 0.0
        valid = 0
        for nid, outs in self.predictions.items():
            neighbor = universe.get_node(nid)
            if neighbor is None:
                continue
            error = (outs['pred_state'] - neighbor.state) ** 2
            naive_error = (outs['actual_state_before_tick'] - neighbor.state) ** 2
            total_error += error
            total_naive_error += naive_error
            valid += 1
            
        if valid == 0:
            return 1.0, 1.0
        me = total_error / valid
        self.naive_surprise = total_naive_error / valid
        self.total_prediction_error += me
        self.prediction_count += 1
        self.avg_prediction_error = self.total_prediction_error / self.prediction_count
        return me, self.naive_surprise

    def learn(self, universe, target_defend):
        if self.is_egg: return
        err_sig = self.received_signal_error
        
        for nid, outs in self.predictions.items():
            if nid == 'ENV':
                err_state = 0.0
                err_defend = outs['def_action'] - target_defend
                grad_x = self.brain.learn(self.lr, [err_state, err_defend, err_sig, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], outs['context'])
                continue

            neighbor = universe.get_node(nid)
            if neighbor is None:
                continue
                
            err_state = outs['pred_state'] - neighbor.state
            err_defend = outs['def_action'] - target_defend
            
            # Backprop errors through DynamicBrain
            grad_x = self.brain.learn(self.lr, [err_state, err_defend, err_sig, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], outs['context'])
            
            # grad_x[2] is the gradient w.r.t the neighbor's signal input
            neighbor.next_received_signal_error += grad_x[2]
            
    def update_signal_error_for_next_tick(self):
        self.received_signal_error = self.next_received_signal_error
        self.next_received_signal_error = 0.0

    def can_reproduce(self):
        return not self.is_egg and self.energy >= self.reproduction_threshold

    def create_offspring(self, child_id, mutation_rate=0.15):
        child_energy = self.energy * 0.4
        self.energy *= 0.6
        self.children_spawned += 1

        child = Node(
            node_id=child_id,
            initial_energy=child_energy,
            faction=self.faction,
            parent=self,
            generation=self.generation + 1
        )
        child.x = (self.x + random.uniform(-10, 10)) % 1000.0
        child.y = (self.y + random.uniform(-10, 10)) % 1000.0
        child.is_egg = True
        child.incubation_timer = 30
        child._update_state()
        return child


class GraphUniverse:
    def __init__(self, config):
        self.nodes = {}
        self.tick_count = 0
        self.config = config
        self._next_node_id = 0

        self.metabolism_cost = config.get('metabolism_cost', 0.1)
        self.edge_cost = config.get('edge_cost', 0.03)
        self.env_energy_total = config.get('env_energy_total', 120.0)
        self.env_energy_nodes = config.get('env_energy_nodes', 40)
        self.prediction_bonus = config.get('prediction_bonus', 0.3)
        self.surprise_penalty = config.get('surprise_penalty', 0.15)
        self.model_cost_per_weight = config.get('model_cost_per_weight', 0.008)
        self.mutation_rate = config.get('mutation_rate', 0.15)
        self.max_population = config.get('max_population', 1500)

        # Red Queen parameters
        self.cross_faction_bonus = config.get('cross_faction_bonus', 0.4)
        self.same_faction_edge_discount = config.get('same_faction_edge_discount', 0.5)
        self.exploit_steal = config.get('exploit_steal', 0.1)

        self.history = []
        self.total_births = 0
        self.total_deaths = 0
        self.max_generation_seen = 0
        
        self.storm_queue = []
        self.foods = []

    def _get_next_id(self):
        nid = self._next_node_id
        self._next_node_id += 1
        return nid

    def add_node(self, node):
        self.nodes[node.id] = node
        if node.id >= self._next_node_id:
            self._next_node_id = node.id + 1

    def get_node(self, nid):
        return self.nodes.get(nid)

    def remove_node(self, nid):
        if nid in self.nodes:
            del self.nodes[nid]

    def tick(self):
        self.tick_count += 1
        for n in self.nodes.values():
            if not n.is_egg:
                n.age += 1
            else:
                n.incubation_timer -= 1
                if n.incubation_timer <= 0:
                    n.is_egg = False

        # Phase 0: SPATIAL VISION SENSORS
        grid = {}
        cell_size = 80.0
        for n in self.nodes.values():
            n.visible_nodes = set()
            cx = int(n.x / cell_size)
            cy = int(n.y / cell_size)
            if (cx, cy) not in grid:
                grid[(cx, cy)] = []
            grid[(cx, cy)].append(n)
            
        grid_w = int(1000 / cell_size) + 1
        for n in self.nodes.values():
            cx = int(n.x / cell_size)
            cy = int(n.y / cell_size)
            
            # Check 3x3 cells (with wrap around)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx = (cx + dx) % grid_w
                    ny = (cy + dy) % grid_w
                    if (nx, ny) in grid:
                        for other in grid[(nx, ny)]:
                            if other.id != n.id:
                                # Toroidal distance
                                dist_x = min(abs(n.x - other.x), 1000 - abs(n.x - other.x))
                                dist_y = min(abs(n.y - other.y), 1000 - abs(n.y - other.y))
                                if dist_x*dist_x + dist_y*dist_y <= cell_size*cell_size:
                                    n.visible_nodes.add(other.id)

        # Phase 1: PREDICT (and Storm spawning)
        new_warnings = set()
        if random.random() < 0.2:
            target_count = max(1, int(len(self.nodes) * 0.05))
            new_warnings = set(random.sample(list(self.nodes.keys()), min(target_count, len(self.nodes))))
            
        for n in self.nodes.values():
            env_warning = 1.0 if n.id in new_warnings else 0.0
            n.predict_neighbors(self, env_warning)

        # Phase 1.5: FORM MUTUAL BINDINGS
        for n in self.nodes.values():
            if n.is_egg: continue
            for nid, outs in n.predictions.items():
                if nid == 'ENV': continue
                neighbor = self.get_node(nid)
                if neighbor and not neighbor.is_egg:
                    if outs.get('bind_action', 0) > 0.5:
                        n_pred = neighbor.predictions.get(n.id)
                        if n_pred and n_pred.get('bind_action', 0) > 0.5:
                            dist_x = min(abs(n.x - neighbor.x), 1000 - abs(n.x - neighbor.x))
                            dist_y = min(abs(n.y - neighbor.y), 1000 - abs(n.y - neighbor.y))
                            if dist_x*dist_x + dist_y*dist_y < 900: # distance < 30
                                n.bindings.add(neighbor.id)
                                neighbor.bindings.add(n.id)

        # Phase 1.6: PREDATION (ARMS RACE)
        for n in self.nodes.values():
            if n.is_egg or not n.attacking: continue
            
            # Find closest visible node to attack
            closest_dist = float('inf')
            closest_target = None
            for nid in n.visible_nodes:
                if nid in n.bindings: continue # Don't attack bound partners
                target = self.get_node(nid)
                if target and not target.is_egg:
                    dist_x = min(abs(n.x - target.x), 1000 - abs(n.x - target.x))
                    dist_y = min(abs(n.y - target.y), 1000 - abs(n.y - target.y))
                    dist_sq = dist_x*dist_x + dist_y*dist_y
                    if dist_sq < 400 and dist_sq < closest_dist: # Distance < 20
                        closest_dist = dist_sq
                        closest_target = target
            
            if closest_target:
                if not closest_target.defended:
                    # Successful attack!
                    n.energy += 15
                    closest_target.energy -= 15
                else:
                    # Failed attack on armored target
                    n.energy -= 5
            

        # Storm hits nodes from 3 ticks ago
        self.storm_queue.append(new_warnings)
        self.hitting_storm = set()
        if len(self.storm_queue) > 3:
            self.hitting_storm = self.storm_queue.pop(0)
            for nid in self.hitting_storm:
                node = self.get_node(nid)
                if node:
                    is_defended = node.defended
                    if not is_defended:
                        for bid in node.bindings:
                            partner = self.get_node(bid)
                            if partner and partner.defended:
                                is_defended = True
                                break
                    if is_defended:
                        node.energy -= 5 # cost of defense
                    else:
                        node.energy -= 30 # massive damage!

        # Phase 2: PHYSICAL FOOD (WORLD CHANGES)
        # Spawn new food randomly (N pieces per tick)
        if len(self.foods) < 300: # Cap food to prevent memory blowup
            for _ in range(3):
                self.foods.append(Food(
                    x=random.uniform(0, 1000),
                    y=random.uniform(0, 1000),
                    energy=random.uniform(10, 30)
                ))
        
        # Nodes eat food if they overlap
        for n in self.nodes.values():
            if n.is_egg: continue
            # Find food close to node
            eaten = []
            for i, f in enumerate(self.foods):
                dx = n.x - f.x
                dy = n.y - f.y
                if dx*dx + dy*dy < 225: # radius 15
                    n.energy += f.energy
                    eaten.append(i)
            # Remove eaten food
            for i in sorted(eaten, reverse=True):
                self.foods.pop(i)

        # Phase 2.5: MOVEMENT & BINDING PHYSICS
        for n in self.nodes.values():
            if n.is_egg:
                n.vx = 0.0
                n.vy = 0.0
                continue
                
            n.vx += n.thrust_x * 0.5
            n.vy += n.thrust_y * 0.5
            
            # Binding Springs
            broken_bindings = set()
            for bid in n.bindings:
                bound_partner = self.get_node(bid)
                if bound_partner:
                    dx = bound_partner.x - n.x
                    dy = bound_partner.y - n.y
                    if dx > 500: dx -= 1000
                    if dx < -500: dx += 1000
                    if dy > 500: dy -= 1000
                    if dy < -500: dy += 1000
                    
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist > 80:
                        broken_bindings.add(bid)
                    elif dist > 0.01:
                        # Spring physics (rest dist = 20)
                        force = (dist - 20) * 0.05
                        fx = (dx / dist) * force
                        fy = (dy / dist) * force
                        n.vx += fx
                        n.vy += fy
            
            n.bindings -= broken_bindings
            
            # Friction
            n.vx *= 0.9
            n.vy *= 0.9
            
            n.x = (n.x + n.vx) % 1000.0
            n.y = (n.y + n.vy) % 1000.0

        # Phase 3: THERMODYNAMIC COSTS & SHARED ENERGY
        for node in self.nodes.values():
            cost = self.metabolism_cost * (0.5 if node.is_egg else 1.0)
            
            # Senescence (Aging) penalty
            if node.age > 500:
                cost += (node.age - 500) * 0.05

            for eid in node.visible_nodes:
                neighbor = self.get_node(eid)
                if neighbor and neighbor.faction == node.faction:
                    # Same-faction edges are cheaper (cooperation)
                    cost += self.edge_cost * self.same_faction_edge_discount
                else:
                    cost += self.edge_cost
            cost += node.brain.get_weight_count() * self.model_cost_per_weight
            
            # Movement cost based on thrust applied
            movement_cost = (abs(node.thrust_x) + abs(node.thrust_y)) * 0.02
            cost += movement_cost
            
            node.energy -= cost
            
        # Shared Energy Pool
        for node in self.nodes.values():
            for bid in node.bindings:
                if bid > node.id: # Process each pair once
                    partner = self.get_node(bid)
                    if partner:
                        diff = node.energy - partner.energy
                        transfer = diff * 0.05
                        node.energy -= transfer
                        partner.energy += transfer

        # Phase 4: UPDATE STATES
        for n in self.nodes.values():
            n._update_state()

        # Phase 5: EVALUATE PREDICTIONS + RED QUEEN DYNAMICS
        total_surprise = 0.0
        total_naive = 0.0
        predicting = 0
        faction_surprise = {BUILDER: 0.0, EXPLOITER: 0.0}
        faction_count = {BUILDER: 0, EXPLOITER: 0}

        for node in self.nodes.values():
            if not node.predictions:
                continue
            me, naive = node.evaluate_predictions(self)
            predicting += 1
            total_surprise += me
            total_naive += naive
            faction_surprise[node.faction] += me
            faction_count[node.faction] += 1

            acc = 1.0 - me
            if acc > 0.5:
                node.energy += self.prediction_bonus * (acc - 0.5)
            else:
                node.energy -= self.surprise_penalty * (0.5 - acc)

            # Red Queen: cross-faction prediction dynamics
            for nid, outs in node.predictions.items():
                neighbor = self.get_node(nid)
                if neighbor is None or neighbor.faction == node.faction:
                    continue
                cross_err = (outs['pred_state'] - neighbor.state) ** 2

                if node.faction == EXPLOITER:
                    # Exploiters gain energy from accurate cross-faction prediction
                    if cross_err < 0.1:
                        steal = node.aggression * self.exploit_steal
                        node.energy += steal
                        neighbor.energy -= steal * 0.5
                elif node.faction == BUILDER:
                    # Builders gain stability bonus for being unpredictable to exploiters
                    if cross_err > 0.3:
                        node.energy += node.stability * 0.05

        # Phase 6: LEARN
        for n in self.nodes.values():
            storm_that_hit = self.hitting_storm if hasattr(self, 'hitting_storm') else set()
            target_defend = 1.0 if n.id in storm_that_hit else 0.0
            n.learn(self, target_defend)
            
        for n in self.nodes.values():
            n.update_signal_error_for_next_tick()

        # Phase 7: REPRODUCTION
        births = 0
        if len(self.nodes) < self.max_population:
            parents = [n for n in self.nodes.values() if n.can_reproduce()]
            for parent in parents:
                if len(self.nodes) >= self.max_population:
                    break
                cid = self._get_next_id()
                child = parent.create_offspring(cid, self.mutation_rate)
                self.add_node(child)
                        
                births += 1
                self.total_births += 1
                if child.generation > self.max_generation_seen:
                    self.max_generation_seen = child.generation

        # Phase 8: DEATH
        dead = [nid for nid, n in self.nodes.items() if n.energy <= 0]
        for nid in dead:
            self.remove_node(nid)
            # Cleanup bindings
            for n in self.nodes.values():
                if nid in n.bindings:
                    n.bindings.remove(nid)
        self.total_deaths += len(dead)

        # Stats
        alive_nodes = list(self.nodes.values())
        builders = [n for n in alive_nodes if n.faction == BUILDER]
        exploiters = [n for n in alive_nodes if n.faction == EXPLOITER]

        stats = {
            'tick': self.tick_count,
            'alive': len(self.nodes),
            'builders': len(builders),
            'exploiters': len(exploiters),
            'births': births,
            'dead': len(dead),
            'avg_surprise': total_surprise / predicting if predicting else 0,
            'avg_naive': total_naive / predicting if predicting else 0,
            'builder_surprise': (
                faction_surprise[BUILDER] / faction_count[BUILDER]
                if faction_count[BUILDER] else 0
            ),
            'exploiter_surprise': (
                faction_surprise[EXPLOITER] / faction_count[EXPLOITER]
                if faction_count[EXPLOITER] else 0
            ),
            'avg_generation': (
                sum(n.generation for n in alive_nodes) / len(alive_nodes)
                if alive_nodes else 0
            ),
            'max_generation': self.max_generation_seen,
            'avg_lr': (
                sum(n.lr for n in alive_nodes) / len(alive_nodes)
                if alive_nodes else 0
            ),
            'total_energy': sum(n.energy for n in alive_nodes),
        }
        self.history.append(stats)
        return stats

    def export_state_json(self):
        """Export current state for the visualizer."""
        nodes = []
        edges = []
        binding_edges = []
        for n in self.nodes.values():
            nodes.append({
                'id': n.id, 'energy': round(n.energy, 2),
                'faction': n.faction, 'generation': n.generation,
                'age': n.age, 'lr': round(n.lr, 4),
                'avg_err': round(n.avg_prediction_error, 4),
                'brain_size': n.brain.get_weight_count() if n.brain else 0,
                'x': round(n.x, 2), 'y': round(n.y, 2),
                'is_egg': n.is_egg,
                'is_attacking': n.attacking
            })
            for eid in n.visible_nodes:
                if eid in self.nodes and n.id < eid:
                    edges.append({'source': n.id, 'target': eid})
            for bid in n.bindings:
                if bid in self.nodes and n.id < bid:
                    binding_edges.append({'source': n.id, 'target': bid})
        foods_json = [{'x': round(f.x, 2), 'y': round(f.y, 2), 'e': round(f.energy, 2)} for f in self.foods]
        return json.dumps({
            'tick': self.tick_count,
            'nodes': nodes, 'edges': edges, 'binding_edges': binding_edges, 'foods': foods_json,
            'stats': self.history[-1] if self.history else {},
        })

    def trigger_catastrophe(self, rewire_ratio=0.7):
        import random
        num_teleport = int(len(self.nodes) * rewire_ratio)
        if num_teleport == 0: return
        
        node_ids = random.sample(list(self.nodes.keys()), num_teleport)
        for nid in node_ids:
            if self.get_node(nid):
                self.nodes[nid].x = random.uniform(0, 1000)
                self.nodes[nid].y = random.uniform(0, 1000)



def initialize_universe(num_nodes=500, connection_prob=0.006,
                        initial_energy=10.0, builder_ratio=0.6):
    config = {
        'metabolism_cost': 0.1, 'edge_cost': 0.03,
        'env_energy_total': 120.0, 'env_energy_nodes': 40,
        'prediction_bonus': 0.3, 'surprise_penalty': 0.15,
        'model_cost_per_weight': 0.008, 'mutation_rate': 0.15,
        'max_population': 1500,
        'cross_faction_bonus': 0.4,
        'same_faction_edge_discount': 0.5,
        'exploit_steal': 0.1,
    }
    universe = GraphUniverse(config)

    for i in range(num_nodes):
        faction = BUILDER if random.random() < builder_ratio else EXPLOITER
        universe.add_node(Node(node_id=i, initial_energy=initial_energy,
                               faction=faction))

    b = sum(1 for n in universe.nodes.values() if n.faction == BUILDER)
    e = num_nodes - b
    logging.info(f"Universe: {num_nodes} nodes ({b} builders, {e} exploiters)")
    return universe


if __name__ == "__main__":
    random.seed(42)
    universe = initialize_universe(num_nodes=500)

    logging.info("=" * 95)
    logging.info("  GENESIS v0.4 — Red Queen Coevolution")
    logging.info("  Builders (Blue) vs Exploiters (Red) — An Arms Race")
    logging.info("=" * 95)

    for t in range(1, 501):
        s = universe.tick()
        if t % 50 == 0 or s['births'] > 3 or s['dead'] > 5:
            logging.info(
                f"T{s['tick']:04d} | "
                f"Pop:{s['alive']:4d} (B:{s['builders']:3d} E:{s['exploiters']:3d}) | "
                f"Born:{s['births']:2d} Died:{s['dead']:3d} | "
                f"Gen:{s['avg_generation']:4.1f} (max {s['max_generation']}) | "
                f"Surp B:{s['builder_surprise']:.4f} E:{s['exploiter_surprise']:.4f} | "
                f"Net Surp:{s['avg_surprise']:.4f} (Naive:{s['avg_naive']:.4f})"
            )
        if s['alive'] == 0:
            logging.info("Heat death.")
            break

    if universe.nodes:
        builders = [n for n in universe.nodes.values() if n.faction == BUILDER]
        exploiters = [n for n in universe.nodes.values() if n.faction == EXPLOITER]
        logging.info("=" * 95)
        logging.info(f"  FINAL — Tick {universe.tick_count}")
        logging.info(f"  Builders: {len(builders)}  |  Exploiters: {len(exploiters)}")
        logging.info(f"  Total Births: {universe.total_births}  |  "
                     f"Total Deaths: {universe.total_deaths}")
        if builders:
            best_b = min(builders, key=lambda n: n.avg_prediction_error)
            logging.info(f"  🔵 Best Builder: Node {best_b.id} "
                         f"(gen {best_b.generation}, stab={best_b.stability:.3f})")
        if exploiters:
            best_e = min(exploiters, key=lambda n: n.avg_prediction_error)
            logging.info(f"  🔴 Best Exploiter: Node {best_e.id} "
                         f"(gen {best_e.generation}, aggr={best_e.aggression:.3f})")
        logging.info("=" * 95)
