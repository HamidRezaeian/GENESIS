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

class Node:
    def __init__(self, node_id, initial_energy, faction=BUILDER,
                 learning_rate=None, generation=0, parent=None):
        self.id = node_id
        self.energy = initial_energy
        self.edges = set()

        # Lineage
        self.generation = generation
        self.parent_id = parent.id if parent else None
        self.children_spawned = 0

        # Observable state
        self.state = 0.0
        self._update_state()

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
            self.brain = DynamicBrain(input_size=3, output_size=3, hidden_size=0) 
            
        self.stability = random.uniform(0.0, 1.0)
        self.aggression = random.uniform(0.0, 0.5)
        self.signal = 0.0
        self.defended = False
        self.received_signal_error = 0.0
        self.next_received_signal_error = 0.0

        # Statistics
        self.total_prediction_error = 0.0
        self.prediction_count = 0
        self.avg_prediction_error = 1.0
        self.age = 0

    def _update_state(self):
        self.state = 1.0 / (1.0 + math.exp(-0.1 * (self.energy - 5.0)))

    def add_edge(self, target_id):
        self.edges.add(target_id)

    def remove_edge(self, target_id):
        if target_id in self.edges:
            self.edges.remove(target_id)

    def predict_neighbors(self, universe, env_warning):
        self.predictions = {}
        my_total_signal = 0
        my_total_defend = 0
        self.naive_surprise = 0.0
        for neighbor_id in self.edges:
            neighbor = universe.get_node(neighbor_id)
            if neighbor:
                outs, context = self.brain.predict([neighbor.state, env_warning, neighbor.signal])
                pred_state, def_action, sig = outs[0], outs[1], outs[2]
                self.predictions[neighbor_id] = {
                    'pred_state': pred_state,
                    'def_action': def_action,
                    'sig': sig,
                    'context': context,
                    'actual_state_before_tick': neighbor.state
                }
                my_total_signal += sig
                my_total_defend += def_action
                
        if self.edges:
            self.signal = my_total_signal / len(self.edges)
            self.defended = (my_total_defend / len(self.edges)) > 0.5
        else:
            self.signal = 0.0
            self.defended = False

    def evaluate_predictions(self, universe):
        if not self.predictions:
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
        err_sig = self.received_signal_error
        
        for nid, outs in self.predictions.items():
            neighbor = universe.get_node(nid)
            if neighbor is None:
                continue
                
            err_state = outs['pred_state'] - neighbor.state
            err_defend = outs['def_action'] - target_defend
            
            # Backprop errors through DynamicBrain
            grad_x = self.brain.learn(self.lr, [err_state, err_defend, err_sig], outs['context'])
            
            # grad_x[2] is the gradient w.r.t the neighbor's signal input
            neighbor.next_received_signal_error += grad_x[2]
            
    def update_signal_error_for_next_tick(self):
        self.received_signal_error = self.next_received_signal_error
        self.next_received_signal_error = 0.0

    def can_reproduce(self):
        return self.energy >= self.reproduction_threshold

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
        
        for nid in self.edges:
            child.edges.add(nid)
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
        
        self.active_storms = set()

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
            for n in self.nodes.values():
                n.remove_edge(nid)
            del self.nodes[nid]

    def tick(self):
        self.tick_count += 1
        for n in self.nodes.values():
            n.age += 1

        # Phase 1: PREDICT (and Storm spawning)
        new_warnings = set()
        if random.random() < 0.2:
            target_count = max(1, int(len(self.nodes) * 0.05))
            new_warnings = set(random.sample(list(self.nodes.keys()), min(target_count, len(self.nodes))))
            
        for n in self.nodes.values():
            env_warning = 1.0 if n.id in new_warnings else 0.0
            n.predict_neighbors(self, env_warning)
            
        # Storm hits nodes from previous tick
        for nid in self.active_storms:
            node = self.get_node(nid)
            if node:
                if node.defended:
                    node.energy -= 5 # cost of defense
                else:
                    node.energy -= 30 # massive damage!
                    
        self.active_storms = new_warnings

        # Phase 2: WORLD CHANGES
        if self.nodes:
            cnt = min(self.env_energy_nodes, len(self.nodes))
            receivers = random.sample(list(self.nodes.values()), cnt)
            ep = self.env_energy_total / cnt
            for n in receivers:
                n.energy += ep

            # Spontaneous edge formation (Network Plasticity)
            if len(self.nodes) > 1:
                num_new_edges = max(1, int(len(self.nodes) * 0.01))
                node_ids = list(self.nodes.keys())
                for _ in range(num_new_edges):
                    u, v = random.sample(node_ids, 2)
                    self.nodes[u].add_edge(v)
                    self.nodes[v].add_edge(u)

        # Phase 3: THERMODYNAMIC COSTS (with faction-aware edge costs)
        for node in self.nodes.values():
            cost = self.metabolism_cost
            for eid in node.edges:
                neighbor = self.get_node(eid)
                if neighbor and neighbor.faction == node.faction:
                    # Same-faction edges are cheaper (cooperation)
                    cost += self.edge_cost * self.same_faction_edge_discount
                else:
                    cost += self.edge_cost
            cost += node.brain.get_weight_count() * self.model_cost_per_weight
            node.energy -= cost

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
            target_defend = 1.0 if n.id in self.active_storms else 0.0
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
                for eid in list(child.edges):
                    nb = self.get_node(eid)
                    if nb:
                        nb.add_edge(child.id)
                
                # Edge Mutation: Child has a chance to form a new random connection
                if random.random() < self.mutation_rate and len(self.nodes) > 1:
                    target_id = random.choice(list(self.nodes.keys()))
                    if target_id != child.id:
                        child.add_edge(target_id)
                        self.nodes[target_id].add_edge(child.id)
                        
                births += 1
                self.total_births += 1
                if child.generation > self.max_generation_seen:
                    self.max_generation_seen = child.generation

        # Phase 8: DEATH
        dead = [nid for nid, n in self.nodes.items() if n.energy <= 0]
        for nid in dead:
            self.remove_node(nid)
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
        for n in self.nodes.values():
            nodes.append({
                'id': n.id, 'energy': round(n.energy, 2),
                'faction': n.faction, 'generation': n.generation,
                'age': n.age, 'lr': round(n.lr, 4),
                'avg_err': round(n.avg_prediction_error, 4),
                'brain_size': n.brain.get_weight_count() if n.brain else 0,
            })
            for eid in n.edges:
                if eid in self.nodes:
                    edges.append({'source': n.id, 'target': eid})
        return json.dumps({
            'tick': self.tick_count,
            'nodes': nodes, 'edges': edges,
            'stats': self.history[-1] if self.history else {},
        })

    def trigger_catastrophe(self, rewire_ratio=0.7):
        import random
        num_edges_to_break = int(len(self.nodes) * rewire_ratio)
        if num_edges_to_break == 0: return
        
        edges_list = []
        for n in self.nodes.values():
            for e in n.edges:
                edges_list.append((n.id, e))
                
        if not edges_list: return
        
        # We can't safely sample more edges than exist
        num_edges_to_break = min(num_edges_to_break, len(edges_list))
        edges_to_break = random.sample(edges_list, num_edges_to_break)
        
        for u, v in edges_to_break:
            if self.get_node(u): self.nodes[u].remove_edge(v)
            if self.get_node(v): self.nodes[v].remove_edge(u)
            
        node_ids = list(self.nodes.keys())
        for _ in range(num_edges_to_break):
            u, v = random.sample(node_ids, 2)
            if u != v:
                self.nodes[u].add_edge(v)
                self.nodes[v].add_edge(u)



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

    ids = list(universe.nodes.keys())
    for i in ids:
        for j in ids:
            if i != j and random.random() < connection_prob:
                universe.nodes[i].add_edge(j)

    b = sum(1 for n in universe.nodes.values() if n.faction == BUILDER)
    e = num_nodes - b
    te = sum(len(n.edges) for n in universe.nodes.values())
    logging.info(f"Universe: {num_nodes} nodes ({b} builders, {e} exploiters), "
                 f"{te} edges")
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
