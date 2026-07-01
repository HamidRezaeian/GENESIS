import http.server
import socketserver
import threading
import time
import json
import logging
from urllib.parse import urlparse, parse_qs
from genesis_engine import initialize_universe

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Global state
universe_lock = threading.Lock()
universe = initialize_universe(num_nodes=300, builder_ratio=0.7)
is_paused = False

def simulation_loop():
    global is_paused
    while True:
        if not is_paused:
            with universe_lock:
                universe.tick()
        time.sleep(0.1)  # 10 ticks per second

sim_thread = threading.Thread(target=simulation_loop, daemon=True)
sim_thread.start()

import os

PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'public'))

class APIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)
    def do_GET(self):
        global is_paused, universe
        
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/state':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with universe_lock:
                state_json = universe.export_state_json()
                
            data = json.loads(state_json)
            data['is_paused'] = is_paused
            data['settings'] = {
                "mutation_rate": universe.mutation_rate,
                "env_energy_total": universe.env_energy_total,
                "metabolism_cost": universe.metabolism_cost,
                "edge_cost": universe.edge_cost
            }
            self.wfile.write(json.dumps(data).encode('utf-8'))
            
        elif parsed_path.path == '/api/control':
            qs = parse_qs(parsed_path.query)
            action = qs.get('action', [''])[0]
            
            if action == 'pause':
                is_paused = True
            elif action == 'play':
                is_paused = False
            elif action == 'restart':
                with universe_lock:
                    universe = initialize_universe(num_nodes=300, builder_ratio=0.7)
                is_paused = False
            elif action == 'catastrophe':
                with universe_lock:
                    universe.trigger_catastrophe()
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "action": action}).encode('utf-8'))
            
        elif parsed_path.path == '/api/settings':
            qs = parse_qs(parsed_path.query)
            
            if 'mutation_rate' in qs:
                universe.mutation_rate = float(qs['mutation_rate'][0])
            if 'env_energy_total' in qs:
                universe.env_energy_total = float(qs['env_energy_total'][0])
            if 'metabolism_cost' in qs:
                universe.metabolism_cost = float(qs['metabolism_cost'][0])
            if 'edge_cost' in qs:
                universe.edge_cost = float(qs['edge_cost'][0])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "mutation_rate": universe.mutation_rate,
                "env_energy_total": universe.env_energy_total,
                "metabolism_cost": universe.metabolism_cost,
                "edge_cost": universe.edge_cost
            }).encode('utf-8'))
            
        elif self.path == '/':
            self.path = '/index.html'
            return super().do_GET()
        else:
            return super().do_GET()

    def log_message(self, format, *args):
        pass

PORT = 8002
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), APIHandler) as httpd:
    logging.info(f"Visualizer server running at http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
