import re

with open(r"C:\Users\Hamid\source\repos\GENESIS\prev_user_input.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Match the html code block
match = re.search(r"```html\r?\n(<!DOCTYPE html>.*?)\r?\n```", text, re.DOTALL)
if match:
    html_content = match.group(1)
    target = r"C:\Users\Hamid\source\repos\GENESIS\public\embodied_deck.html"
    with open(target, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Successfully wrote {len(html_content)} bytes to {target}")
else:
    # Try finding between <!DOCTYPE html> and </html>
    start = text.find("<!DOCTYPE html>")
    end = text.rfind("</html>")
    if start != -1 and end != -1:
        html_content = text[start:end+7]
        target = r"C:\Users\Hamid\source\repos\GENESIS\public\embodied_deck.html"
        with open(target, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Successfully extracted fallback {len(html_content)} bytes to {target}")
    else:
        print("ERROR: Could not find HTML content!")
