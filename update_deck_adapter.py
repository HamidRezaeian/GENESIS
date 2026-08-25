import re

path = r"C:\Users\Hamid\source\repos\GENESIS\public\embodied_deck.html"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Collapse double newlines
lines = [l.strip("\r") for l in code.split("\n")]
collapsed = []
prev_blank = False
for l in lines:
    is_blank = not l.strip()
    if is_blank:
        if not prev_blank:
            collapsed.append("")
        prev_blank = True
    else:
        collapsed.append(l)
        prev_blank = False

code = "\n".join(collapsed)

# Enhanced normalize function
norm_replacement = """/* -------- defensive normalizer: many alias → canonical -------- */
function normalize(d){
  const o={};
  const env=d.env||d.environment||d.world||{};
  const cog=d.cog||d.cognitive||d.brain||d.mcts||{};
  const meta=d.meta||d.metabolic||d.stats||{};
  if(d.tick!=null||d.t!=null||d.step!=null)o.tick=+(d.tick??d.t??d.step);
  if(d.generation!=null)o.generation=+d.generation;
  if(d.difficulty!=null)o.difficulty=typeof d.difficulty==='object'?(d.difficulty.size>12?2:1):+d.difficulty;
  
  // Grid
  const rawGrid = env.grid || env.tiles || d.grid;
  if(rawGrid) o.env = o.env || {}, o.env.grid = normGrid(rawGrid);
  
  // Chem
  const rawChem = env.chem || env.chemical || env.field || d.chem;
  if(rawChem) o.env = o.env || {}, o.env.chem = normChem(rawChem);
  
  if(env.w)o.env=o.env||{},o.env.w=+env.w; if(env.h)o.env=o.env||{},o.env.h=+env.h;
  
  // Agent Pos & Dir
  const ag = env.agent || d.agent;
  if(ag){
    o.env=o.env||{},o.env.agent={x:+(ag.x??ag.ax??0),y:+(ag.y??ag.ay??0),dir:+(ag.dir??ag.direction??0)%4};
  } else if (d.agentPos) {
    o.env=o.env||{},o.env.agent={x:+d.agentPos[0],y:+d.agentPos[1],dir:+(d.agentDir??0)%4};
  }
  
  if(env.hasKey!=null) o.env=o.env||{},o.env.hasKey=!!env.hasKey;
  else if(d.hasKey!=null) o.env=o.env||{},o.env.hasKey=!!d.hasKey;
  
  // Vision observation
  if(d.vis||d.visual) o.vis=normVis(d.vis||d.visual);
  else if(d.obs) o.vis=normVis(d.obs);
  
  // Cognitive / MCTS / Symbols
  const sym = cog.symbol ?? cog.emitted_symbol ?? cog.emittedSymbol ?? cog.token ?? d.symbol ?? (d.mcts && d.mcts.emitted_symbol);
  const ap = cog.actionProbs || cog.action_probs || cog.policy || d.actionProbs || (d.mcts && d.mcts.action_probs);
  const tr = cog.tree || d.tree || d.mcts || cog;
  const cp = cog.concepts || d.concepts;
  const optId = cog.optionId ?? cog.selected_option ?? (d.mcts && d.mcts.selected_option);
  const optLbl = cog.optionLabel ?? (d.mcts && d.mcts.selected_option != null ? OPTION_NAMES[d.mcts.selected_option % 8] : null);
  
  if(sym!=null || ap || tr || cp || optId!=null || optLbl){
    o.cog={};
    if(sym!=null)o.cog.symbol=clamp(+sym,0,63);
    if(optId!=null)o.cog.optionId=+optId;
    if(optLbl!=null)o.cog.optionLabel=String(optLbl);
    if(ap)o.cog.actionProbs=normProbs(ap);
    if(cp)o.cog.concepts=Array.from(cp).map(v=>clamp01(+v||0));
    if(tr)o.cog.tree=normTree(tr);
  }
  
  // Metabolic / Energy / Hippo
  const rawEnergy = meta.energy ?? (d.energy != null ? d.energy / 100.0 : null);
  if(rawEnergy!=null || meta.hippocampus || meta.hippo || meta.entropyIncome!=null || d.hippoCount!=null || d.vVal!=null){
    o.meta={};
    if(rawEnergy!=null) o.meta.energy=clamp01(+rawEnergy);
    const hp=meta.hippocampus||meta.hippo||{};
    if(hp.count!=null) o.meta.hippoCount=+hp.count;
    else if(d.hippoCount!=null) o.meta.hippoCount=+d.hippoCount;
    if(hp.cap!=null) o.meta.hippoCap=+hp.cap;
    if(meta.entropyIncome!=null) o.meta.entropyIncome=+meta.entropyIncome;
    else if(d.vVal!=null) o.meta.entropyIncome=Math.abs(+d.vVal);
  }
  return o;
}"""

# Update normTree to handle direct mcts objects
tree_replacement = """function normTree(t){
  if (!t) return null;
  // If t has action_probs or visitCounts instead of children, adapt it into hierarchical tree
  if (!t.children && (t.action_probs || t.visitCounts || t.action_qValues)) {
    const root = { label: 'ROOT', visits: 32, value: 0.5, children: [], key: 'ROOT' };
    const probs = t.action_probs || [0.25, 0.25, 0.25, 0.25];
    const qVals = t.action_qValues || [0, 0, 0, 0];
    const visits = t.visitCounts || [8, 8, 8, 8];
    const labels = ['FORWARD', 'TURN_LEFT', 'TURN_RIGHT', 'INTERACT'];
    
    for (let i = 0; i < 4; i++) {
      const vCount = +(visits[i] || Math.round(probs[i] * 32));
      const optNode = {
        label: labels[i],
        visits: vCount,
        value: clamp01(qVals[i] > 0 ? qVals[i] / 2.0 : (probs[i] || 0.5)),
        children: [],
        key: 'O' + i
      };
      root.children.push(optNode);
    }
    let selO = root.children[0];
    root.children.forEach(o => { if (o.visits > selO.visits) selO = o; });
    const selPath = new Set(['ROOT', selO.key]);
    return { root, selO, selA: null, selPath };
  }
  
  // flatten to 3 display levels: root → options (≤8) → actions (≤5 each)
  const mk=(n,key)=>({label:String(n.label??n.name??'?'),visits:+n.visits||0,
    value:clamp01(+n.value||0),children:[],key});
  const root=mk(t,'ROOT');root.label='ROOT';
  (t.children||[]).slice(0,8).forEach((c,i)=>{
    const o=mk(c,'O'+i);o.label=String(c.label??('O'+i));
    (c.children||[]).slice(0,5).forEach(k=>{
      const a=mk(k,o.key+'/'+String(k.label??k.name??'?'));
      o.children.push(a);
    });
    root.children.push(o);
  });
  let selO=null;root.children.forEach(o=>{if(!selO||o.visits>selO.visits)selO=o;});
  let selA=null;if(selO)selO.children.forEach(a=>{if(!selA||a.visits>selA.visits)selA=a;});
  const selPath=new Set(['ROOT']);if(selO)selPath.add(selO.key);if(selA)selPath.add(selA.key);
  return{root,selO,selA,selPath};
}"""

# Replace in code
code = re.sub(r"/\* -------- defensive normalizer: many alias → canonical -------- \*/.*?return o;\s*}", norm_replacement, code, flags=re.DOTALL)
code = re.sub(r"function normTree\(t\)\{.*?return\{root,selO,selA,selPath\};\s*}", tree_replacement, code, flags=re.DOTALL)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print(f"Successfully updated {path} with enhanced telemetry adapter. Total lines: {len(code.splitlines())}")
