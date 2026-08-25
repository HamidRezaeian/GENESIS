import subprocess

with open(r"C:\Users\Hamid\source\repos\GENESIS\public\embodied_deck.html", "r", encoding="utf-8") as f:
    content = f.read()

# Extract the script content between <script> and </script>
start = content.find("<script>")
end = content.rfind("</script>")

if start != -1 and end != -1:
    js_code = content[start+8:end]
    with open("temp_deck.js", "w", encoding="utf-8") as js_f:
        js_f.write(js_code)
    print("Saved script to temp_deck.js")
    
    # Run node --check
    res = subprocess.run(["node", "--check", "temp_deck.js"], capture_output=True, text=True)
    print("Node check returncode:", res.returncode)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
else:
    print("Could not find <script> tags")
