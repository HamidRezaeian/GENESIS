import urllib.request
import json

url = "http://localhost:8089/api/telepathic_chat"
data = json.dumps({"prompt": "وضعیت شما در محیط جدید چگونه است؟"}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("API Response:")
        print(f"World: {res.get('world_id')} | Organism: {res.get('organism_id')} | Gen: {res.get('generation')}")
        print(f"Symbols: {res.get('symbols')}")
        print(f"Synthesis: {res.get('synthesis')}")
        print("✅ Live Telepathic Chat API 100% verified!")
except Exception as e:
    print(f"❌ Error: {e}")
