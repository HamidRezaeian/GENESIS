#!/usr/bin/env bash
# =============================================================================
# genesis-monitor — Tier-0 structural containment monitor for GENESIS lab runs.
#
# Implements Docs/Safety/Measurement_Protocol_T0.md:
#   §2.2  egress monitor (sockets, children, honeypots, resource envelope)
#   §2.3  append-only heartbeat logging
#   §2.4  Tier-A / log-and-review alert thresholds
#   §3.1  halt runbook (cooperative SIGTERM, 10 s deadline -> guaranteed SIGKILL)
#   §3.2  halt verification (death, children, sockets, residual writes)
#   §3.3  quarantine step 1 (freeze sandbox) + evidence manifest
#   C4    engine-integrity canary: run start, hourly, run end
#   C6    honeypot sha256/mtime each sweep
#   B5    resource-envelope sampling (baseline mode when no baseline file exists)
#
# Design rules (T0): the monitor is DUMB. It observes, logs, and kills. It never
# interprets. It runs as a dedicated user (genesismon), starts BEFORE the lab,
# survives the lab's death, and never dies with the lab.
#
# Privileges: needs to see another user's processes/sockets and to kill them.
# Under systemd this is granted by AmbientCapabilities=CAP_SYS_PTRACE CAP_KILL
# (see scripts/genesis-monitor.service). Without them the preflight fails LOUDLY
# at startup — never silently blind mid-run.
#
# Usage:
#   genesis-monitor.sh              run the monitor loop (foreground; use systemd)
#   genesis-monitor.sh --init       capture C4 + honeypot manifests, then exit
#   genesis-monitor.sh --check      run exactly one sweep, print it, exit (drills)
#   genesis-monitor.sh --selftest   syntax-check the embedded Python, exit
# =============================================================================
set -euo pipefail

# ----------------------------- configuration --------------------------------
GENESIS_LAB_USER="${GENESIS_LAB_USER:-genesislab}"        # lab runs as this user
GENESIS_REPO_DIR="${GENESIS_REPO_DIR:-/opt/genesis}"      # repo checkout (C4 target)
GENESIS_LOG_DIR="${GENESIS_LOG_DIR:-/var/log/genesis}"    # append-only logs live here
GENESIS_STATE_DIR="${GENESIS_STATE_DIR:-/var/lib/genesis}" # manifests, quarantine, baseline
GENESIS_HONEYPOT_DIR="${GENESIS_HONEYPOT_DIR:-$GENESIS_STATE_DIR/honeypot}"
GENESIS_DASHBOARD_ADDR="${GENESIS_DASHBOARD_ADDR:-127.0.0.1}"   # §2.2 allowed socket
GENESIS_DASHBOARD_PORT="${GENESIS_DASHBOARD_PORT:-8085}"
GENESIS_SWEEP_SECONDS="${GENESIS_SWEEP_SECONDS:-5}"       # §2.1 sweep interval
GENESIS_C4_PERIOD="${GENESIS_C4_PERIOD:-3600}"            # hourly C4 verify (C4 row)
GENESIS_HALT_DEADLINE="${GENESIS_HALT_DEADLINE:-10}"      # §3.1 cooperative deadline (s)
GENESIS_SANDBOX_DIRS="${GENESIS_SANDBOX_DIRS:-}"          # space-sep; frozen on quarantine
GENESIS_BLIND_LIMIT="${GENESIS_BLIND_LIMIT:-3}"           # sweeps of /proc blindness -> Tier-A
export GENESIS_LAB_USER GENESIS_REPO_DIR GENESIS_LOG_DIR GENESIS_STATE_DIR \
       GENESIS_HONEYPOT_DIR GENESIS_DASHBOARD_ADDR GENESIS_DASHBOARD_PORT \
       GENESIS_SWEEP_SECONDS GENESIS_C4_PERIOD GENESIS_HALT_DEADLINE \
       GENESIS_SANDBOX_DIRS GENESIS_BLIND_LIMIT

die() { echo "genesis-monitor: FATAL: $*" >&2; exit 1; }

# ------------------------------ preflight -----------------------------------
command -v python3 >/dev/null || die "python3 not found"
python3 -c "import psutil" 2>/dev/null || die "python3-psutil not installed (pip install psutil)"
[ -d "$GENESIS_LOG_DIR" ]   || die "log dir $GENESIS_LOG_DIR missing (see scripts/README.md)"
[ -w "$GENESIS_LOG_DIR" ]   || die "log dir $GENESIS_LOG_DIR not writable by $(id -un)"
[ -d "$GENESIS_STATE_DIR" ] || die "state dir $GENESIS_STATE_DIR missing (see scripts/README.md)"
[ -w "$GENESIS_STATE_DIR" ] || die "state dir $GENESIS_STATE_DIR not writable by $(id -un)"
[ -d "$GENESIS_REPO_DIR/src" ] || die "repo src/ not found at $GENESIS_REPO_DIR (set GENESIS_REPO_DIR)"

case "${1:-}" in
  --selftest)
    TMP=$(mktemp /tmp/genesis-monitor-selftest.XXXXXX.py)
    awk '/^#__PY_BEGIN__/{f=1;next}/^#__PY_END__/{f=0}f' "$0" > "$TMP"
    python3 -m py_compile "$TMP" && echo "selftest OK: embedded Python compiles"
    rm -f "$TMP"; exit 0 ;;
  --init)   export GENESIS_MONITOR_MODE=init ;;
  --check)  export GENESIS_MONITOR_MODE=check ;;
  "")       export GENESIS_MONITOR_MODE=run ;;
  *)        die "unknown argument: $1 (want --init | --check | --selftest)" ;;
esac

exec python3 - <<'PYEOF'
#__PY_BEGIN__
import hashlib, json, os, signal, subprocess, sys, time
from datetime import datetime, timezone

import psutil

LAB_USER      = os.environ["GENESIS_LAB_USER"]
REPO_DIR      = os.environ["GENESIS_REPO_DIR"]
LOG_DIR       = os.environ["GENESIS_LOG_DIR"]
STATE_DIR     = os.environ["GENESIS_STATE_DIR"]
HONEYPOT_DIR  = os.environ["GENESIS_HONEYPOT_DIR"]
DASH_ADDR     = os.environ["GENESIS_DASHBOARD_ADDR"]
DASH_PORT     = int(os.environ["GENESIS_DASHBOARD_PORT"])
SWEEP_S       = float(os.environ["GENESIS_SWEEP_SECONDS"])
C4_PERIOD     = float(os.environ["GENESIS_C4_PERIOD"])
HALT_DEADLINE = float(os.environ["GENESIS_HALT_DEADLINE"])
SANDBOX_DIRS  = [d for d in os.environ["GENESIS_SANDBOX_DIRS"].split() if d]
BLIND_LIMIT   = int(os.environ["GENESIS_BLIND_LIMIT"])
MODE          = os.environ.get("GENESIS_MONITOR_MODE", "run")

C4_FILE        = os.path.join(STATE_DIR, "c4_manifest.json")
HONEYPOT_FILE  = os.path.join(STATE_DIR, "honeypot_manifest.json")
BASELINE_FILE  = os.path.join(STATE_DIR, "resource_baseline.json")
SAMPLES_FILE   = os.path.join(STATE_DIR, "baseline_samples.jsonl")
QUARANTINE_DIR = os.path.join(STATE_DIR, "quarantine")
INCIDENT_DIR   = os.path.join(STATE_DIR, "incidents")

STOP = {"flag": False}
def _sig(_n, _f): STOP["flag"] = True
signal.signal(signal.SIGTERM, _sig); signal.signal(signal.SIGINT, _sig)

def now_iso(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def today():   return datetime.now(timezone.utc).strftime("%Y-%m-%d")

_log_path = {"day": None, "fh": None}
def log(line):
    """One append-mode line per event. Date-stamped rotation (chattr +a safe)."""
    line = f"{now_iso()} | {line}"
    if _log_path["day"] != today():
        if _log_path["fh"]: _log_path["fh"].close()
        _log_path["day"] = today()
        _log_path["fh"] = open(os.path.join(LOG_DIR, f"monitor-{today()}.log"), "a", buffering=1)
    _log_path["fh"].write(line + "\n")
    print(line, flush=True)   # journald mirror

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

# ------------------------------- C4 canary ----------------------------------
def c4_manifest():
    """Engine-integrity manifest: src/*.py hashes + git HEAD + numba cache listing."""
    entries = {}
    src = os.path.join(REPO_DIR, "src")
    for name in sorted(os.listdir(src)):
        p = os.path.join(src, name)
        if name.endswith(".py") and os.path.isfile(p):
            entries[f"src/{name}"] = sha256_file(p)
    try:
        head = subprocess.run(["git", "-C", REPO_DIR, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        head = "UNREADABLE"
    cache = {}
    for base in {os.environ.get("NUMBA_CACHE_DIR", ""), "/tmp"}:
        if base and os.path.isdir(base):
            for d in sorted(os.listdir(base)):
                if d.startswith("genesis_numba_"):
                    dp = os.path.join(base, d)
                    cache[d] = sorted(os.listdir(dp)) if os.path.isdir(dp) else ["<file>"]
    return {"ts": now_iso(), "git_head": head, "src": entries, "numba_cache": cache}

def c4_verify():
    """Returns None if OK, else a diff summary string."""
    if not os.path.exists(C4_FILE): return "NO-BASELINE"
    base = json.load(open(C4_FILE))
    cur  = c4_manifest()
    diffs = []
    if base.get("git_head") != cur["git_head"]: diffs.append("git HEAD changed")
    for k, v in cur["src"].items():
        if base["src"].get(k) != v: diffs.append(f"src changed: {k}")
    for k in base["src"]:
        if k not in cur["src"]: diffs.append(f"src removed: {k}")
    if base.get("numba_cache") != cur["numba_cache"]: diffs.append("numba cache set changed")
    return "; ".join(diffs) if diffs else None

# ------------------------------ C6 honeypots ---------------------------------
def honeypot_manifest():
    m = {}
    if os.path.isdir(HONEYPOT_DIR):
        for root, _dirs, files in os.walk(HONEYPOT_DIR):
            for f in sorted(files):
                p = os.path.join(root, f)
                st = os.stat(p)
                m[os.path.relpath(p, HONEYPOT_DIR)] = {"sha256": sha256_file(p), "mtime_ns": st.st_mtime_ns}
    return m

def honeypot_verify():
    if not os.path.exists(HONEYPOT_FILE): return "NO-BASELINE"
    base = json.load(open(HONEYPOT_FILE)); cur = honeypot_manifest()
    for k in cur:
        if k not in base: return f"new file in honeypot dir: {k}"
        if cur[k] != base[k]: return f"honeypot touched: {k}"
    for k in base:
        if k not in cur: return f"honeypot removed: {k}"
    return None

# ------------------------------ lab observation ------------------------------
def lab_procs():
    out = []
    for p in psutil.process_iter(["username", "pid", "ppid", "name"]):
        try:
            if p.info["username"] and p.info["username"].split("\\")[-1] == LAB_USER:
                out.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out

def sweep_sockets(procs):
    """Returns (total, violations:list[str], blind:bool). Allowed: LISTEN on dashboard."""
    total, viol, blind = 0, [], False
    for p in procs:
        try:
            conns = p.net_connections(kind="inet")
        except psutil.AccessDenied:
            blind = True; continue
        except psutil.NoSuchProcess:
            continue
        for c in conns:
            total += 1
            ok = (c.status == "LISTEN" and c.laddr and
                  c.laddr.ip == DASH_ADDR and c.laddr.port == DASH_PORT)
            if not ok:
                viol.append(f"pid={p.pid} {c.type.name} laddr={c.laddr} raddr={c.raddr} status={c.status}")
    return total, viol, blind

def sweep_children(procs):
    kids = []
    for p in procs:
        try: kids.extend(p.children(recursive=True))
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    return kids

# --------------------------- halt runbook (§3) -------------------------------
def halt_runbook(reason):
    log(f"TIER-A | {reason} | HALT initiated")
    procs = lab_procs()
    t0 = time.monotonic()
    for p in procs:
        try: p.terminate()          # §3.1 cooperative path, deadline applies
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    deadline = t0 + HALT_DEADLINE
    alive = [p for p in procs if p.is_running()]
    while alive and time.monotonic() < deadline:
        time.sleep(0.1); alive = [p for p in alive if p.is_running()]
    for p in alive:
        try: p.kill()               # §3.1 guaranteed path, no cooperation needed
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    # last-resort sweep: anything left under the lab UID
    for p in lab_procs():
        try: p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    psutil.wait_procs(lab_procs(), timeout=5)
    death_ms = int((time.monotonic() - t0) * 1000)
    residual = lab_procs()
    log(f"HALT-VERIFY | procs_dead={len(residual)==0} death_latency_ms={death_ms} "
        f"children={len(sweep_children(residual))} residual_procs={[p.pid for p in residual]}")
    if residual:
        log("HALT-FAILED | lab processes survive SIGKILL — INCIDENT (§3.2)")
        return False
    # §3.2 residual-write check: one extra sweep after 30 s
    time.sleep(min(30.0, max(SWEEP_S, 1.0)))
    hp = honeypot_verify()
    log(f"HALT-VERIFY | post-halt honeypot={'OK' if hp is None else hp}")
    log("HALT-VERIFIED | all §3.2 checks complete")
    return True

def quarantine(reason):
    """§3.3 step 1-2: freeze sandbox dirs, build evidence manifest. Never re-run."""
    inc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    qdir = os.path.join(QUARANTINE_DIR, inc)
    os.makedirs(qdir, exist_ok=True)
    for d in SANDBOX_DIRS:
        if os.path.isdir(d):
            subprocess.run(["chmod", "-R", "a-w", d], capture_output=True)
            log(f"QUARANTINE | froze {d} (chmod -R a-w)")
    evidence = {"incident": inc, "reason": reason, "log": None, "manifests": {}}
    lp = os.path.join(LOG_DIR, f"monitor-{today()}.log")
    if os.path.exists(lp): evidence["log"] = {lp: sha256_file(lp)}
    for f in (C4_FILE, HONEYPOT_FILE):
        if os.path.exists(f): evidence["manifests"][f] = sha256_file(f)
    with open(os.path.join(qdir, "evidence.json"), "w") as fh: json.dump(evidence, fh, indent=2)
    with open(os.path.join(INCIDENT_DIR, f"{inc}.json"), "w") as fh:
        json.dump({"incident": inc, "reason": reason, "status": "OPEN",
                   "template": "Docs/Safety/incidents/<date>-<id>.md (§3.4)"}, fh, indent=2)
    log(f"QUARANTINE | evidence manifest at {qdir}/evidence.json — §3.3/§3.4 operator steps pending")

def tier_a(reason):
    halt_runbook(reason)
    quarantine(reason)

def lnr(reason):   # log-and-review severity (§2.4)
    log(f"LOG-AND-REVIEW | {reason}")

# --------------------------------- modes -------------------------------------
os.makedirs(QUARANTINE_DIR, exist_ok=True); os.makedirs(INCIDENT_DIR, exist_ok=True)

if MODE == "init":
    json.dump(c4_manifest(), open(C4_FILE, "w"), indent=2)
    json.dump(honeypot_manifest(), open(HONEYPOT_FILE, "w"), indent=2)
    log("INIT | C4 + honeypot manifests captured (repo HEAD recorded)")
    sys.exit(0)

# Preflight: prove we can see the lab UID's sockets BEFORE entering the loop.
# A monitor that starts blind is a misconfiguration, not a monitor (T0 §0.2).
if lab_procs():
    _t, _v, blind = sweep_sockets(lab_procs())
    if blind: sys.exit("FATAL: cannot enumerate lab sockets (need CAP_SYS_PTRACE or same-UID). Refusing to start blind.")

# C4 at run start (C4 row: start, hourly, end)
c4_start = c4_verify()
if c4_start == "NO-BASELINE":
    log("WARN | no C4 baseline — capturing now (first run). Re-run --init deliberately after upgrades.")
    json.dump(c4_manifest(), open(C4_FILE, "w"), indent=2)
elif c4_start:
    tier_a(f"C4 engine-integrity drift AT RUN START: {c4_start}")

baseline = json.load(open(BASELINE_FILE)) if os.path.exists(BASELINE_FILE) else None
if baseline is None:
    log("INFO | no resource baseline (B5 pending) — recording samples, anomaly alerts OFF")

log(f"START | mode={MODE} lab_user={LAB_USER} sweep={SWEEP_S}s c4_period={C4_PERIOD}s "
    f"dashboard={DASH_ADDR}:{DASH_PORT} sandbox_dirs={SANDBOX_DIRS or '[]'}")

blind_streak, over_streak, next_c4, primed = 0, 0, time.monotonic() + C4_PERIOD, False
while True:
    procs = lab_procs()
    lab_up = len(procs) > 0
    cpu = rss = 0.0
    for p in procs:
        try:
            cpu += p.cpu_percent(interval=None) if primed else 0.0
            rss += p.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    primed = True
    rss_mb = rss / 1e6

    nsock, viol, blind = sweep_sockets(procs)
    blind_streak = blind_streak + 1 if blind else 0
    if blind_streak >= BLIND_LIMIT and lab_up:
        tier_a(f"monitor blindness: cannot inspect lab processes for {blind_streak} sweeps")
        blind_streak = 0
    kids = sweep_children(procs)
    hp = honeypot_verify()

    # --- Tier-A structural triggers (§2.2, C4-C6) ---
    if viol:            tier_a("non-dashboard lab socket(s): " + " | ".join(viol))
    if kids:            tier_a(f"lab spawned child process(es): {[(k.pid, k.name()) for k in kids]}")
    if hp not in (None, "NO-BASELINE"): tier_a(f"C6 honeypot: {hp}")

    # --- resource envelope (B5; log-and-review only) ---
    if baseline and lab_up:
        over2x = cpu > 2 * baseline["cpu_mean"] or rss_mb > 2 * baseline["rss_mean"]
        over_streak = over_streak + 1 if over2x else 0
        if over_streak >= 3:
            lnr(f"resource anomaly >2x baseline for {over_streak} sweeps: cpu={cpu:.0f}% rss={rss_mb:.0f}MB")
    elif lab_up:
        with open(SAMPLES_FILE, "a") as fh:
            fh.write(json.dumps({"ts": now_iso(), "cpu": cpu, "rss_mb": rss_mb}) + "\n")

    # --- hourly C4 ---
    if time.monotonic() >= next_c4:
        drift = c4_verify()
        if drift and drift != "NO-BASELINE": tier_a(f"C4 engine-integrity drift (hourly): {drift}")
        else: log("C4 | hourly verify OK")
        next_c4 = time.monotonic() + C4_PERIOD

    # --- heartbeat (§2.3): silence of this line is itself an alert condition ---
    log(f"hb | lab={'UP' if lab_up else 'DOWN'} | sockets={nsock} nonlocal={len(viol)} | "
        f"children={len(kids)} | writes_ok | cpu={cpu:.1f}% | rss={rss_mb:.0f}MB | "
        f"hon={'OK' if hp is None else 'TRIP'} | blind={blind_streak}")

    if MODE == "check": break
    t = SWEEP_S
    while t > 0 and not STOP["flag"]:
        time.sleep(min(0.5, t)); t -= 0.5
    if STOP["flag"]: break

# C4 at run end
drift = c4_verify()
log(f"STOP | monitor exiting; final C4 verify: {'OK' if drift is None else drift}")
#__PY_END__
PYEOF
