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
universe = initialize_universe()
is_paused = False

def simulation_loop():
    global is_paused
    while True:
        if not is_paused:
            with universe_lock:
                universe.tick()
        # Fast execution: 100 ticks per second
        time.sleep(0.01) 

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
                
            # It's already JSON string, just send it directly to save parsing/stringifying
            # But we need to add is_paused. Let's do string manipulation or just load it.
            data = json.loads(state_json)
            data['is_paused'] = is_paused
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
                    universe = initialize_universe()
                is_paused = False
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "action": action}).encode('utf-8'))
            
        else:
            super().do_GET()

PORT = 8002

with socketserver.ThreadingTCPServer(("", PORT), APIHandler) as httpd:
    logging.info(f"Visualizer server running at http://localhost:{PORT}")
    httpd.serve_forever()
