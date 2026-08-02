import json
from graphify.extract import collect_files, extract
from pathlib import Path

code_files = []
detect = json.loads(
    Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
for f in detect.get('files', {}).get('code', []):
    code_files.extend(collect_files(Path(f))
                      if Path(f).is_dir() else [Path(f)])

print('code files to AST-extract:', len(code_files))
if code_files:
    result = extract(code_files, cache_root=Path('.'), parallel=False)
    Path('graphify-out/.graphify_ast.json').write_text(json.dumps(result,
                                                                  indent=2, ensure_ascii=False), encoding='utf-8')
    n_nodes = len(result['nodes'])
    n_edges = len(result['edges'])
    print('AST: ' + str(n_nodes) + ' nodes, ' + str(n_edges) + ' edges')
else:
    Path('graphify-out/.graphify_ast.json').write_text(json.dumps({'nodes': [], 'edges': [
    ], 'input_tokens': 0, 'output_tokens': 0}, ensure_ascii=False), encoding='utf-8')
    print('No code files')
