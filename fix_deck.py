with open(r"C:\Users\Hamid\source\repos\GENESIS\prev_user_input.txt", "r", encoding="utf-8") as f:
    text = f.read()

v1 = text[468:69835+7]
v2 = text[72086:141453+7]

print(f"v1 len: {len(v1)}, v2 len: {len(v2)}")
print("v1 vs v2 identical?:", v1 == v2)

# Fix the syntax error in the HTML:
# In connectWS():
# url=over||((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws');
fixed_html = v1.replace(
    "url=over||((location.protocol==='https:'?'wss://ws')+location.host+'/ws');",
    "url=over||((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws');"
)

# Also ensure default fallback wsUrl if file:// or standalone:
fixed_html = fixed_html.replace(
    "const url=over||((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws');",
    "const defaultHost = (!location.host || location.protocol === 'file:') ? 'localhost:8088' : location.host;\n  const url=over||((location.protocol==='https:'?'wss://':'ws://')+defaultHost+'/ws');"
)

target = r"C:\Users\Hamid\source\repos\GENESIS\public\embodied_deck.html"
with open(target, "w", encoding="utf-8") as f:
    f.write(fixed_html)

print(f"Successfully written single clean fixed HTML ({len(fixed_html)} bytes) to {target}")
