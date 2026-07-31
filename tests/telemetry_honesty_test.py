"""Telemetry & Dashboard Honesty Contract Test (2026-07-31, deep review P1-1/P1-9/P1-10/P1-11).

Source-level invariants that guard the 2026-07-31 "telemetry honesty overhaul". These run
WITHOUT importing the engine or compiling the kernel, so they stay in the fast suite.

What broke historically (and must never come back):
  * TWO competing live state paths — a 5 Hz direct broadcast AND a 10 Hz mailbox that re-sent
    one full-RAM snapshot up to 50x — each stuffing the entire RAM as base64 into every frame.
  * FABRICATED telemetry constants on the dashboard: elite_iq=78.65, solve_pct=78.65,
    sensors=32, actuators=8 (mailbox path) and a `|| 78.65` fallback in app.js, plus a fully
    fabricated "Series 1200 Level 1 CERTIFIED" leaderboard in index.html (Rule-16 violations).
  * Birth provenance counters (natural/refuge/ark/auto_repro births, natural deaths,
    extinctions) defined but never incremented nor published — the Exp-85/86 survivorship
    confound enabler.
  * GENESIS_LIVE_WEB=0 ("benchmark mode") being ignored, so even the deterministic live-web
    fallback text was tiled across 100% of RAM.

Run: python tests/telemetry_honesty_test.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def strip_html_comments(html):
    return re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)


def main():
    print("Telemetry & Dashboard Honesty Contract Test")
    print("=" * 60)

    lab = read("src/genesis_lab.py")
    app = read("public/app.js")
    html_raw = read("public/index.html")
    html = strip_html_comments(html_raw)  # audit-note comments may mention removed values

    # [1] No fabricated constant anywhere in live telemetry code.
    record("[1] No fabricated '78.65' in engine telemetry", "78.65" not in lab)
    record("[1b] No fabricated '78.65' in app.js", "78.65" not in app)
    record("[1c] No fabricated '78.65' in visible dashboard", "78.65" not in html)

    # [2] Single mailbox publisher; competing paths deleted.
    record("[2] Fake mailbox publisher removed", "publish_telemetry_snapshot" not in lab)
    record("[2b] Direct per-client broadcast removed", "broadcast_msg" not in lab)
    record("[2c] Single publisher exists", "def _publish_state(" in lab
           and "_publish_state(data)" in lab)
    record("[2d] Sequence-gated streaming (no unchanged resend)",
           "g_snapshot_seq" in lab and "seq != last_sent" in lab)

    # [3] RAM cadence split: ram_b64 is conditional, not every frame.
    record("[3] RAM attached only at low cadence",
           "attach_ram" in lab and "last_ram_push" in lab)

    # [4] Birth/death provenance is wired AND published (Exp 85/86 confound enabler closed).
    record("[4] Births provenance in state payload", '"births"' in lab)
    record("[4b] Natural deaths actually counted",
           re.search(r"g_run_natural_deaths \+=", lab) is not None)
    record("[4c] Run extinctions actually counted",
           re.search(r"g_run_extinctions \+=", lab) is not None)

    # [5] Live-web demo vs reproducible benchmark separation is effective.
    record("[5] GENESIS_LIVE_WEB gate in sim_loop + _lay_library",
           lab.count("live_web_streamer.LIVE_WEB_ENABLED") >= 2)

    # [6] Dashboard shows no fabricated leaderboard claims outside comments.
    for bad in ["148.5M", "2,000,000", "ULTRA-LEAN", "81.49%", "IN-LIFETIME</span>",
                "REMAP-TRACKING", 'tag-emerald">CERTIFIED', "LEVEL 1 CERTIFIED"]:
        record(f"[6] '{bad}' absent from visible dashboard", bad not in html)

    # [7] elite_iq is displayed as what it is (a rate), not a fake percentage.
    record("[7] elite_iq not dressed as a percentage", "s.elite_iq + '%'" not in app)

    # [8] Schema versioned snapshot.
    record("[8] Snapshot carries schema_version", '"schema_version": 2' in lab)

    # [9] Energy-accounting basis is named in telemetry (deep review P1-6).
    record("[9] energy_basis exposed in telemetry", '"energy_basis"' in lab)
    record("[9b] basis classes documented",
           os.path.exists(os.path.join(ROOT, "Docs/Architecture/ENERGY_ACCOUNTING.md")))

    print("=" * 60)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"TELEMETRY HONESTY: {passed}/{total} checks passed")
    if passed != total:
        print("FAILED CHECKS:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  - {name}")
        sys.exit(1)
    print("ALL_TELEMETRY_HONESTY_TESTS_PASSED")


if __name__ == "__main__":
    main()
