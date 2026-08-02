import json
from pathlib import Path
for n in ['00', '01', '02', '03', '04']:
    p = Path('graphify-out/.graphify_chunk_' + n + '.json')
    if not p.exists():
        print('chunk ' + n + ': MISSING')
        continue
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
        print('chunk ' + n + ': ' + str(len(d.get('nodes', []))) + ' nodes, ' +
              str(len(d.get('edges', []))) + ' edges, ' + str(len(d.get('hyperedges', []))) + ' hyperedges')
    except Exception as e:
        print('chunk ' + n + ': INVALID JSON - ' + str(e))
