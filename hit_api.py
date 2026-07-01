import urllib.request, json
r = urllib.request.urlopen("http://localhost:8001/api/state")
data = json.loads(r.read())
print("stats keys:", data['stats'].keys())
print("builders:", data['stats'].get('builders'))
print("exploiters:", data['stats'].get('exploiters'))
