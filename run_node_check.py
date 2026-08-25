import subprocess

with open(r"C:\Users\Hamid\source\repos\GENESIS\public\embodied_deck.html", "r", encoding="utf-8") as f:
    content = f.read()

start = content.find("<script>")
end = content.rfind("</script>")

if start != -1 and end != -1:
    js_code = content[start+8:end]
    with open("temp_deck.js", "w", encoding="utf-8") as js_f:
        js_f.write(js_code)
    
    res = subprocess.run(["node", "--check", "temp_deck.js"], capture_output=True, text=True)
    with open("node_res.txt", "w", encoding="utf-8") as out:
        out.write(f"Return code: {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}\n")
    print("Done checking node syntax")
