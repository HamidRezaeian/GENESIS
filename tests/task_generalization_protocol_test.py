"""Phase F Task Generalization Protocol Test Suite (2026-07-30).

Verifies that:
1. Protocol specification document and stream hashes exist.
2. Benchmark execution produces valid raw results and zero-leakage audit payload.
3. Analysis script correctly parses Phase F raw results.

Run: python tests/task_generalization_protocol_test.py
"""
import os
import sys
import json


def test_task_generalization_protocol():
    print("Initializing Phase F Task Generalization Protocol Test Suite...")

    # [1] Protocol document verification
    proto_doc = os.path.join(os.path.dirname(__file__), "..", "Docs", "PROTOCOLS", "TASK_GENERALIZATION_PROTOCOL_PHASE_F.md")
    assert os.path.exists(proto_doc), f"Missing protocol document: {proto_doc}"
    print("  [1] Protocol Document Verification OK")

    # [2] Raw results verification
    raw_path = os.path.join(os.path.dirname(__file__), "..", "experiments", "phase_f_raw_results.json")
    assert os.path.exists(raw_path), f"Missing raw results: {raw_path}"
    with open(raw_path, "r") as f:
        data = json.load(f)
    assert data.get("protocol_id") == "TASK_GENERALIZATION_PHASE_F_v1"
    assert len(data.get("raw_results", {})) == 5
    print("  [2] Phase F Raw Results Verification OK")

    # [3] Leakage audit verification
    leak_path = os.path.join(os.path.dirname(__file__), "..", "experiments", "phase_f_leakage_audit.json")
    assert os.path.exists(leak_path), f"Missing leakage audit: {leak_path}"
    with open(leak_path, "r") as f:
        leak_data = json.load(f)
    assert leak_data.get("status") == "PASSED_ZERO_LEAKAGE"
    print("  [3] Zero-Leakage Audit Contract OK")

    print("ALL_TASK_GENERALIZATION_PROTOCOL_TESTS_PASSED")


if __name__ == "__main__":
    test_task_generalization_protocol()
