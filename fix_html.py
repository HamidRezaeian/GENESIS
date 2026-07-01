with open('e:/DevOps/Playground/GENESIS/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("\\`", "`").replace("\\$", "$")

with open('e:/DevOps/Playground/GENESIS/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
