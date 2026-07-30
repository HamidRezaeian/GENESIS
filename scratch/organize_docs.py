import os
import shutil

docs_dir = r"C:\Users\Hamid\source\repos\GENESIS\Docs"
arch_dir = os.path.join(docs_dir, "Architecture")

os.makedirs(arch_dir, exist_ok=True)

files_to_move = [
    "Ascent.md",
    "DYNAMIC_COMPACT_RAM_DESIGN.md",
    "FixedRules.md",
    "HARDWARE_AWARE_CAPACITY_DESIGN.md",
    "RULE21_2_ENGINE_REFACTOR_DESIGN.md",
    "RULE21_INCOME_REFACTOR_DESIGN.md"
]

for f in files_to_move:
    src = os.path.join(docs_dir, f)
    dst = os.path.join(arch_dir, f)
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"Moved {f} -> Docs/Architecture/{f}")
    else:
        print(f"File not found: {f}")
