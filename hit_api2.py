import urllib.request, json, time
urllib.request.urlopen("http://localhost:8001/api/control?action=restart")
time.sleep(0.5)
r = urllib.request.urlopen("http://localhost:8001/api/state")
data = json.loads(r.read())
print("tick:", data['tick'])
print("builders:", data['stats'].get('builders'))
print("exploiters:", data['stats'].get('exploiters'))
