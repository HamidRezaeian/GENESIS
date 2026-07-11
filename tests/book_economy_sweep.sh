#!/usr/bin/env bash
# Economy-flip sweep (Rules 9/10): does making book-solving pay (and food subsistence) grow readers?
# Columns: read_scale (reward multiplier on solved symbols), eat_gain (mindless-food value).
# Baseline first (default economy), then flip: raise read reward, cut food to subsistence.
set -u
PY=py; ARG="-3.13"
run(){ $PY $ARG tests/book_read_test.py "$1" "$2" "${3:-300}" 2>&1 | grep -E "RESULT|Traceback|Error" | tail -3; }

echo "== BASELINE (reading pays raw byte, food pays 1024) =="
run 1    1024
echo "== FLIP 1: reading x8, food still lush 1024 =="
run 8    1024
echo "== FLIP 2: reading x8, food subsistence 128 =="
run 8    128
echo "== FLIP 3: reading x32, food subsistence 128 =="
run 32   128
echo "== FLIP 4: reading x32, food near-zero 16 =="
run 32   16
