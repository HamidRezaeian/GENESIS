with open(r"C:\Users\Hamid\source\repos\GENESIS\public\embodied_deck.html", "r", encoding="utf-8") as f:
    content = f.read()

# Normalize multiple consecutive blank lines if any, or normalize CRLF
# If it has \r\r\n or double newlines everywhere, normalize it.
import re
# check if every other line is blank
lines = content.splitlines()
print(f"Total lines: {len(lines)}")
# If the text has double spacing from copy-paste:
# Let's inspect first 20 lines
for l in lines[:20]:
    print(repr(l))
