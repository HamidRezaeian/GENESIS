with open(r"C:\Users\Hamid\source\repos\GENESIS\prev_user_input.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Let's find all occurrences of <!DOCTYPE html>
indices = []
idx = 0
while True:
    pos = text.find("<!DOCTYPE html>", idx)
    if pos == -1:
        break
    indices.append(pos)
    idx = pos + 1

print(f"Found <!DOCTYPE html> at positions: {indices}")

# Let's inspect where </html> occurs
h_indices = []
idx = 0
while True:
    pos = text.find("</html>", idx)
    if pos == -1:
        break
    h_indices.append(pos)
    idx = pos + 1

print(f"Found </html> at positions: {h_indices}")
