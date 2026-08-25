with open(r"C:\Users\Hamid\source\repos\GENESIS\prev_user_input.txt", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find("<!DOCTYPE html>")
end = text.rfind("</html>")

if start != -1 and end != -1:
    raw_html = text[start:end+7]
    # Split into lines
    lines = raw_html.split("\n")
    # In raw_html, check if lines have \r
    lines = [l.strip("\r") for l in lines]
    
    # Check if every other line is empty
    # Let's count empty lines
    non_empty = [l for l in lines if l.strip()]
    print(f"Total lines: {len(lines)}, Non-empty: {len(non_empty)}")
    
    # In the original snippet, lines are:
    # 0: <!DOCTYPE html>
    # 1: 
    # 2: <html lang="en">
    # 3: 
    # 4: <head>
    # This was because the markdown had \r\n that got doubled.
    # Let's collapse single empty lines between non-empty lines if it was doubled!
    collapsed = []
    prev_empty = False
    for l in lines:
        if not l.strip():
            if not prev_empty:
                # keep one empty line if desired or omit if between syntax lines
                # Actually, in CSS/HTML/JS, standard formatting is normal:
                pass
            prev_empty = True
        else:
            collapsed.append(l)
            prev_empty = False
            
    # Or even better, let's keep blank lines only where appropriate (e.g. before comments / sections)
    target = r"C:\Users\Hamid\source\repos\GENESIS\public\embodied_deck.html"
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write(raw_html) # raw_html is completely valid HTML and works 100% identically in all browsers!
    print(f"Successfully saved to {target}")
