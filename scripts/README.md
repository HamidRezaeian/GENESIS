# scripts/ — GENESIS operations tooling

## genesis-monitor.sh

Production implementation of `Docs/Safety/Measurement_Protocol_T0.md` (egress
monitor §2, halt runbook §3, canaries C4/C6, resource baseline B5). Bash wrapper
around an embedded Python (stdlib + `psutil`) sweep loop. Linux + systemd.

The monitor is **dumb by design**: it observes, logs, and kills. It never
interprets. It runs as a dedicated `genesismon` user, starts **before** the lab,
and survives the lab's death.

### What it watches (every 5 s sweep)

| Signal | Trip condition | Severity |
|---|---|---|
| Lab sockets | anything except `LISTEN 127.0.0.1:8085` (dashboard) | **Tier-A → halt** |
| Lab child processes | any child, recursive | **Tier-A → halt** |
| C6 honeypots | sha256/mtime change, new or removed file | **Tier-A → halt** |
| C4 engine integrity | `src/*.py` sha256, git HEAD, numba cache set — checked at start, **hourly**, and at stop | **Tier-A → halt** |
| Monitor blindness | cannot read lab `/proc` for ≥3 sweeps | **Tier-A → halt** |
| Resource envelope | CPU or RSS > 2× baseline, 3 consecutive sweeps | log-and-review |
| Heartbeat | one line per sweep; silence = external alert condition | — |

Tier-A runs the §3 halt runbook: SIGTERM (10 s cooperative deadline) → SIGKILL →
verification (death, children, sockets, +30 s residual check) → quarantine step 1
(`chmod -R a-w` on `$GENESIS_SANDBOX_DIRS`) + evidence manifest in
`$GENESIS_STATE_DIR/quarantine/<ts>/`. The monitor keeps running after a halt.

### Install (one-time, ≈1 h — T0 §5)

```bash
# 1. users + dirs
sudo useradd -r genesislab            # lab user  (if not already present)
sudo useradd -r genesismon            # monitor user
sudo mkdir -p /var/log/genesis /var/lib/genesis/honeypot
sudo chown root:genesismon /var/log/genesis && sudo chmod 0750 /var/log/genesis
sudo chown -R genesismon:genesismon /var/lib/genesis

# 2. repo checkout the monitor guards (C4 target)
sudo git clone https://github.com/HamidRezaeian/GENESIS /opt/genesis
sudo git -C /opt/genesis checkout feature/substrate-pivot

# 3. plant C6 honeypots OUTSIDE the lab sandbox, then record their hashes
echo "AKIA-FAKE-DECOY-KEY" | sudo tee /var/lib/genesis/honeypot/api_keys.txt >/dev/null

# 4. psutil for the monitor user
sudo pip3 install psutil

# 5. install + baseline + enable
sudo install -m 0755 scripts/genesis-monitor.sh /usr/local/bin/genesis-monitor.sh
sudo install -m 0644 scripts/genesis-monitor.service /etc/systemd/system/
sudo -u genesismon env GENESIS_REPO_DIR=/opt/genesis /usr/local/bin/genesis-monitor.sh --init
sudo systemctl daemon-reload && sudo systemctl enable --now genesis-monitor
journalctl -u genesis-monitor -f        # confirm heartbeat lines
```

### Structural egress enforcement (T0 §2.2 — the monitor verifies; the firewall is the boundary)

```bash
sudo iptables -A OUTPUT -m owner --uid-owner genesislab -o lo -j ACCEPT
sudo iptables -A OUTPUT -m owner --uid-owner genesislab -j DROP
sudo -u genesislab curl --max-time 3 https://example.com   # MUST fail; success = Tier-A incident
```

### Operations

- **Append-only logs (T0 §2.3):** after the first log appears,
  `sudo chattr +a /var/log/genesis/monitor-*.log`. Rotation is by date-stamped
  filename — `logrotate` copytruncate is intentionally incompatible.
- **Resource baseline (B5):** with no baseline the monitor records samples to
  `$GENESIS_STATE_DIR/baseline_samples.jsonl`. After ≥5 representative runs,
  compute `{cpu_mean, cpu_std, rss_mean, rss_std}` and write
  `$GENESIS_STATE_DIR/resource_baseline.json` to arm the anomaly alert.
- **Drills:** `genesis-monitor.sh --check` runs one sweep. Quarterly halt drill
  per T0 §3.5: start a lab run, `systemctl` watch, trip a canary, record
  latencies in `SafetyThresholds.md`.
- **After any engine upgrade:** re-run `--init` (C4 rebaseline) deliberately and
  record it in the incident log — otherwise the next hourly verify trips Tier-A.

### Known limits (T0 §0.4)

- Honeypot detection covers writes/reads-with-mtime; silent reads need `auditd`
  watches (T2 work).
- Requires `/proc` cross-UID visibility: on `hidepid=2` systems the service
  needs `gid=proc` or the capabilities already granted.
- Does not detect cognition; structural tripwires only.
