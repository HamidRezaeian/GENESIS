"""AST Duplicate Definition Test (2026-07-30).

Scans all Python source files in `src/` to ensure no duplicate top-level
function or class definitions exist (preventing dead code / overwrite bugs).
"""
import ast
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def check_file_duplicates(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    tree = ast.parse(code, filename=filepath)
    seen_defs = set()
    duplicates = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in seen_defs:
                duplicates.append((node.name, node.lineno))
            else:
                seen_defs.add(node.name)

    return duplicates


def main():
    src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
    py_files = glob.glob(os.path.join(src_dir, "*.py")) + glob.glob(os.path.join(src_dir, "**", "*.py"), recursive=True)

    failed = False
    for py_file in py_files:
        dupes = check_file_duplicates(py_file)
        if dupes:
            failed = True
            rel_path = os.path.relpath(py_file, src_dir)
            print(f"FAILED: Duplicate definitions found in {rel_path}: {dupes}")

    if failed:
        sys.exit(1)
    else:
        print(f"ALL_AST_DUPLICATE_TESTS_PASSED ({len(py_files)} files checked)")


if __name__ == "__main__":
    main()
