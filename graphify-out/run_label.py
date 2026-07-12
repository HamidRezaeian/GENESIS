import sys, json
from graphify.build import build_from_json
from graphify.cluster import score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from pathlib import Path

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding='utf-8'))
detection  = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-16'))
analysis   = json.loads(Path('graphify-out/.graphify_analysis.json').read_text(encoding='utf-8'))

G = build_from_json(extraction, root='.', directed=False)
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
tokens = {'input': extraction.get('input_tokens', 0), 'output': extraction.get('output_tokens', 0)}

labels = {
    0: 'CLI Scripts',
    1: 'Genesis Lab Engine',
    2: 'Frontend Visualizer',
    3: 'Validation Tools',
    4: 'Curriculum Injection',
    5: 'Self Sustain Test',
    6: 'Benchmark Scripts',
    7: 'AGI Analyzer',
    8: 'Genome Extraction',
    9: 'Forage Race Tests',
    10: 'Live Economy Tests',
    11: 'Economy Sweep',
    12: 'Genome Analyzer',
    13: 'Book Read Tests',
    14: 'Smoke Tests',
    15: 'Init Scripts',
    16: 'Brain Migration',
    17: 'Book Economy Tests',
    18: 'Eat Gain Tests',
    19: 'Mutate Crash Tests',
    20: 'Simulation Tests',
    21: 'Baseline Verifier'
}

questions = suggest_questions(G, communities, labels)
report = generate(G, communities, cohesion, labels, analysis['gods'], analysis['surprises'], detection, tokens, '.', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding='utf-8')
Path('graphify-out/.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False), encoding='utf-8')
print('Report updated with community labels')
