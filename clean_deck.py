import re

target = r"C:\Users\Hamid\source\repos\GENESIS\public\embodied_deck.html"
with open(target, "r", encoding="utf-8") as f:
    raw = f.read()

# Fix \r\r\n -> \n and remove spurious double blank lines that were inserted
# If \r\n was split into \r\n\r\n, let's normalize
cleaned = raw.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")

# If every line is separated by \n\n, let's check
# In original code, single lines didn't have \n between every single line
# Let's inspect
lines = cleaned.split("\n")
if all(lines[i] == "" for i in range(1, len(lines), 2)):
    print("Detected exact alternate empty lines! Collapsing...")
    lines = [lines[i] for i in range(0, len(lines), 2)]
    cleaned = "\n".join(lines)

with open(target, "w", encoding="utf-8", newline="\n") as f:
    f.write(cleaned)

print(f"Cleaned embodied_deck.html: {len(cleaned.splitlines())} lines, {len(cleaned)} bytes")
