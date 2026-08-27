import re
c=open('public/embodied_deck.html', encoding='utf-8').read()
idx = c.find('statTd')
print(c[max(0, idx-500):idx+800])
