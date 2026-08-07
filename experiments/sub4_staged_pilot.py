#!/usr/bin/env python3
"""GENESIS Staged Pilot Driver — Gate A1 | rho metric | resume | flush"""
import argparse, json, os, sys, time, subprocess
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT / "src"))

TICKS_PER_WINDOW = 500
CHECKPOINT_EVERY = 5000
RHO_THR = 0.25
PROTOCOL = "SUBSTRATE_4_STAGED_PILOT_v1"
AMENDMENT = "SUBSTRATE_4_LEARNING_CURVE_v1"
GATE = "A1"

def git_sha():
    try:
        r = subprocess.run(["git","rev-parse","HEAD"],
                           capture_output=True,text=True,cwd=str(ROOT),timeout=5)
        return r.stdout.strip() if r.returncode==0 else "unknown"
    except Exception:
        return "unknown"

def rho(e0, e1):
    return (e0-e1)/e0 if e0 else 0.0

def slope_ci(vals, conf=0.95):
    n=len(vals)
    if n<3: return 0.0,(-1,1)
    x=np.arange(n)
    s,_,_,_,se = stats.linregress(x,vals)
    tc = stats.t.ppf((1+conf)/2, n-2)
    return s, (s-tc*se, s+tc*se)

def gap_ci(a,b,conf=0.95):
    g=np.array(a)-np.array(b)
    if len(g)<2: return 0.0,(-1,1)
    m=np.mean(g); se=stats.sem(g)
    tc=stats.t.ppf((1+conf)/2,len(g)-1)
    return m,(m-tc*se,m+tc*se)

def gates(rho_vals, le, nl):
    sl,sci = slope_ci(rho_vals)
    t_ok = sci[0]>0
    cr = rho_vals[-1] if rho_vals else 0.0
    m_ok = cr>=RHO_THR
    g,gci = gap_ci(le,nl)
    b_ok = gci[0]>0
    v = "PASS" if (t_ok and m_ok and b_ok) else "FAIL"
    return {"T":{"slope":sl,"ci":list(sci),"pass":t_ok},
            "M":{"rho":cr,"threshold":RHO_THR,"pass":m_ok},
            "B":{"gap":g,"ci":list(gci),"pass":b_ok},
            "verdict":v,"binding":v=="PASS"}

def meta(seed,stage,out):
    return {"protocol":PROTOCOL,"amendment":AMENDMENT,"gate_claim":GATE,
            "seed":seed,"stage":stage,"git_sha":git_sha(),
            "timestamp":datetime.now(timezone.utc).isoformat(),
            "ticks_per_window":TICKS_PER_WINDOW,"outdir":str(out)}

def run_arm(seed,arm,nw,out,resume=0):
    import sub4_small_transformer as st
    lr = 0.01 if arm=="LEARN" else 0.0
    rng = np.random.default_rng(seed*100)
    agent = st.build_agent(rng, readout_lr=lr)
    snap = Path(out)/f"{arm}_seed{seed}_snap.npz"
    sw = resume
    if resume>0 and snap.exists():
        d=np.load(snap,allow_pickle=True)
        agent=st.restore_agent({k:d[k] for k in d.files},readout_lr=lr)
    patch = st.build_patch(seed)
    errs,wins=[],[]
    for widx in range(sw,nw):
        we=[]
        for t in range(TICKS_PER_WINDOW):
            ti=widx*TICKS_PER_WINDOW+t
            tgt=patch[ti%len(patch)]
            pred,_=agent.predict(ti%len(patch))
            we.append(1.0 if pred!=tgt else 0.0)
            if lr>0: agent.update(tgt)
        errs.append(float(np.mean(we)))
        wins.append({"window":widx,"tick":(widx+1)*TICKS_PER_WINDOW,
                     "mean_error":errs[-1],"arm":arm,"seed":seed})
        if (widx+1)*TICKS_PER_WINDOW % CHECKPOINT_EVERY == 0:
            np.savez_compressed(snap,**agent.get_state())
    return wins,errs

def run_stage(stage,seed,nw,out,resume=False):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    jl=out/f"S{stage}_{seed}_windows.jsonl"
    rf=0
    if resume and jl.exists():
        rf=sum(1 for l in open(jl) if l.strip())//2
    print(f"  LEARN seed={seed} ...")
    lw,le=run_arm(seed,"LEARN",nw,out,rf)
    print(f"  NOLEARN seed={seed} ...")
    nw2,ne=run_arm(seed,"NOLEARN",nw,out,rf)
    rv=[rho(ne[i] if ne[i]>0 else 1, le[i]) for i in range(len(le))]
    g=gates(rv,le,ne)
    fin={**meta(seed,stage,out),"tick":nw*TICKS_PER_WINDOW,
         "windows":lw,"rho_values":rv,"final_gate":g,
         "smoke":nw<TICKS_PER_WINDOW*40}
    fp=out/f"S{stage}_{seed}_LEARN_final.json"
    fp.write_text(json.dumps(fin,indent=2))
    with open(jl,"w") as f:
        for r in lw: f.write(json.dumps(r)+"\n")
    return fin

def aggregate(stage,out,seeds):
    out=Path(out); res=[]
    for s in seeds:
        fp=out/f"S{stage}_{s}_LEARN_final.json"
        if fp.exists(): res.append(json.loads(fp.read_text()))
    if not res:
        return {"verdict":"NO_DATA","binding":False,"action":"HALT"}
    ar=[r["rho_values"][-1] for r in res if r.get("rho_values")]
    mr=float(np.mean(ar))
    ci=stats.t.interval(.95,len(ar)-1,loc=mr,scale=stats.sem(ar)) if len(ar)>1 else (mr,mr)
    p=sum(1 for r in res if r.get("final_gate",{}).get("verdict")=="PASS")
    v="PASS" if p==len(res) and mr>=RHO_THR else "FAIL"
    a={"stage":stage,"protocol":PROTOCOL,"amendment":AMENDMENT,"gate_claim":GATE,
       "seeds":seeds,"n_pass":p,"n_total":len(res),"mean_rho":mr,
       "rho_ci":[float(ci[0]),float(ci[1])],"verdict":v,"binding":v=="PASS",
       "action":"PROCEED" if v=="PASS" else "HALT_AND_REPORT",
       "timestamp":datetime.now(timezone.utc).isoformat()}
    (out/f"S{stage}_aggregate.json").write_text(json.dumps(a,indent=2))
    return a

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",default="S1")
    ap.add_argument("--seed",type=int,default=0)
    ap.add_argument("--seeds",type=int,nargs="+",default=[0])
    ap.add_argument("--ticks",type=int,default=20000)
    ap.add_argument("--outdir",default="sub4_results/staged_pilot")
    ap.add_argument("--resume",action="store_true")
    ap.add_argument("--aggregate",action="store_true")
    a=ap.parse_args()
    nw=a.ticks//TICKS_PER_WINDOW
    if a.aggregate:
        r=aggregate(a.stage,a.outdir,a.seeds)
        print(f"verdict={r['verdict']} action={r['action']}"); return
    r=run_stage(a.stage,a.seed,nw,a.outdir,a.resume)
    print(f"gate={r['final_gate']['verdict']}")

if __name__=="__main__":
    main()
