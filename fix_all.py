import os

# Fix 1: simulation/__init__.py
path = 'src/biophysical/simulation/__init__.py'
with open(path, 'r') as f:
    content = f.read()
content = content.replace('from biophysical.simulation.recorder import StateRecorder',
                         'from biophysical.simulation.recorder import Recorder')
content = content.replace('from biophysical.simulation.current_clamp import CurrentClamp',
                         'from biophysical.simulation.current_clamp import CurrentClampProtocol as CurrentClamp')
content = content.replace('"StateRecorder"', '"Recorder"')
with open(path, 'w') as f:
    f.write(content)
print(f"Fixed: {path}")

# Fix 2: neuron_cell.py
path = 'src/biophysical/neuron_cell.py'
with open(path, 'r') as f:
    content = f.read()
content = content.replace('StateRecorder', 'Recorder')
with open(path, 'w') as f:
    f.write(content)
print(f"Fixed: {path}")

# Fix 3: report.py - complete rewrite
report_content = '''"""report.py - Validation report generation."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ValidationResult:
    name: str
    passed: bool
    actual_value: Any = None
    expected_range: str = ""
    unit: str = ""
    message: str = ""


@dataclass
class ValidationReport:
    results: List[ValidationResult] = field(default_factory=list)
    title: str = "Validation Report"

    @property
    def n_total(self) -> int:
        return len(self.results)

    @property
    def n_passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def n_failed(self) -> int:
        return self.n_total - self.n_passed

    @property
    def all_passed(self) -> bool:
        return self.n_failed == 0 and self.n_total > 0

    def add(self, result: ValidationResult) -> None:
        self.results.append(result)

    def add_check(self, name, passed, actual=None, expected="", unit="", message=""):
        self.add(ValidationResult(name=name, passed=passed, actual_value=actual,
                                  expected_range=expected, unit=unit, message=message))

    def summary_line(self) -> str:
        return f"{self.n_passed}/{self.n_total} checks passed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "n_total": self.n_total,
            "n_passed": self.n_passed,
            "n_failed": self.n_failed,
            "all_passed": self.all_passed,
            "results": [
                {"name": r.name, "passed": r.passed, "actual": r.actual_value,
                 "expected": r.expected_range, "unit": r.unit, "message": r.message}
                for r in self.results
            ],
        }

    def __str__(self) -> str:
        return generate_text_report(self)

    def print_report(self) -> None:
        print(generate_text_report(self))


def generate_text_report(report_or_results, benchmark=None, meta=None) -> str:
    lines = []

    if isinstance(report_or_results, ValidationReport):
        results = report_or_results.results
        title = report_or_results.title
    elif isinstance(report_or_results, list):
        results = report_or_results
        title = "Phase 0a Passive Validation"
    else:
        results = []
        title = "Validation Report"

    n_total = len(results)
    n_passed = sum(1 for r in results if r.passed)
    n_failed = n_total - n_passed

    lines.append("=" * 60)
    lines.append(f"  {title}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Summary: {n_passed}/{n_total} checks passed")
    lines.append("")
    lines.append("  Results:")
    lines.append("  " + "-" * 56)

    for r in results:
        mark = "[PASS]" if r.passed else "[FAIL]"
        lines.append(f"  {mark} {r.name}")
        if r.actual_value is not None:
            lines.append(f"      Value: {r.actual_value} {r.unit}")
        if r.expected_range:
            lines.append(f"      Expected: {r.expected_range}")

    lines.append("")

    if benchmark is not None:
        lines.append("  Performance Benchmark:")
        lines.append("  " + "-" * 56)
        if hasattr(benchmark, 'to_dict'):
            for key, val in benchmark.to_dict().items():
                lines.append(f"    {key}: {val}")
        elif isinstance(benchmark, dict):
            for key, val in benchmark.items():
                lines.append(f"    {key}: {val}")
        lines.append("")

    if meta is not None:
        lines.append("  Model Info:")
        lines.append("  " + "-" * 56)
        if isinstance(meta, dict):
            for key, val in meta.items():
                lines.append(f"    {key}: {val}")
        lines.append("")

    if n_failed > 0:
        lines.append(f"  Failures ({n_failed}):")
        lines.append("  " + "-" * 56)
        for r in results:
            if not r.passed:
                lines.append(f"  X {r.name}")
                if r.message:
                    lines.append(f"      {r.message}")
        lines.append("")

    lines.append("=" * 60)
    status = "ALL CHECKS PASSED" if n_failed == 0 else "SOME CHECKS FAILED"
    lines.append(f"  Status: {status}")
    lines.append("=" * 60)

    return "\\n".join(lines)
'''

path = 'src/biophysical/validation/report.py'
with open(path, 'w', encoding='utf-8') as f:
    f.write(report_content)
print(f"Fixed: {path}")

print("\nAll fixes applied!")