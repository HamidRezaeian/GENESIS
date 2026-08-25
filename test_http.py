import urllib.request

resp = urllib.request.urlopen('http://localhost:8088/embodied_deck.html')
content = resp.read().decode('utf-8')
print('Status:', resp.status)
print('Len:', len(content))
print('Has normalize:', 'function normalize' in content)
print('Has syntax error string:', 'wss://ws' in content)
