"""Anti-fabrication guard (2026-07-31, Exp 95 — deep-review honesty).

Scans the ACTIVE experiment drivers and tests for the fabrication signatures that were
root-caused in the quarantined benchmark chain (see experiments/legacy_fabricated/README.md):

  S1  accuracy-by-constant-plus-jitter:  ``p_acc = 0.814 + float(np.random.uniform(...))``
  S2  hardcoded "audit-grade" p-values:  Wilcoxon ``0.001953`` / permutation ``0.000976``
      literals assigned as if they were computed statistics.

Quarantine directories (legacy_fabricated, tests/legacy) are excluded by construction —
they are the historical record, loudly labelled. Everything else must be free of these
patterns for the suite to pass. A guard that only lives in CI/resume docs would be checked
by hand exactly once; this one runs on every `pytest -m "not slow"`.

Run: python tests/fabrication_scan_test.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE_DIRS = {"legacy", "legacy_fabricated", ".git", "__pycache__", ".venv", "node_modules"}
SCAN_DIRS = ["experiments", "tests", "src"]

# constant + jitter assigned into a result-like variable
S1 = re.compile(
    r"(acc|accuracy|delta|baseline|reflex)\w*\s*=\s*0?\.\d+\s*\+\s*"
    r"(float\()?np\.random\.(uniform|normal)\(",
    re.IGNORECASE,
)
# hardcoded p-value literals presented as computed statistics (exact session-era values)
S2 = re.compile(
    r"p_value_(wilcoxon|permutation|ttest)\s*=\s*(0\.001953|0\.000976|1e-6\b|0\.05\b)"
)


def scan():
    hits = []
    for top in SCAN_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, top)):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                except OSError:
                    continue
                in_docstring_scan = path.endswith("fabrication_scan_test.py")
                for i, line in enumerate(lines, 1):
                    # This guard's own regex source obviously contains the literals it
                    # hunts; skip self. Quarantine README/docstrings are .md or excluded.
                    if in_docstring_scan:
                        continue
                    if S1.search(line):
                        hits.append(("S1", path, i, line.strip()[:120]))
                    if S2.search(line):
                        hits.append(("S2", path, i, line.strip()[:120]))
    return hits


def main():
    hits = scan()
    if hits:
        print("FABRICATION SCAN FAILED — fabricator signatures found outside quarantine:")
        for sig, path, i, snippet in hits:
            rel = os.path.relpath(path, ROOT)
            print(f"  [{sig}] {rel}:{i}: {snippet}")
        print("See experiments/legacy_fabricated/README.md for why these are banned.")
        sys.exit(1)
    print("FABRICATION_SCAN_PASSED (no fabricator signatures outside quarantine)")


if __name__ == "__main__":
    main()
