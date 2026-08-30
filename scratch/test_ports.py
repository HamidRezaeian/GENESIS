import urllib.request
import json

for port in [8089, 8088, 8090]:
    url = f"http://localhost:{port}/api/telepathic_chat"
    data = json.dumps({"text": "سلام وضعیت چگونه است؟"}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print(f"✅ SUCCESS on port {port}!")
            print(f"World: {res.get('world_id')} | Organism: {res.get('organism_id')} | Gen: {res.get('generation')}")
            print(f"Symbols: {res.get('symbols')}")
            print(f"Synthesis: {res.get('synthesis')}")
            break
    except Exception as e:
        print(f"Port {port} failed: {e}")
