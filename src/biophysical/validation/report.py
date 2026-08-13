"""report.py - Validation report generation."""

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

    def add(self, result) -> None:
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
                {"name": r.name, "passed": r.passed, "actual": getattr(r, 'actual_value', None),
                 "expected": getattr(r, 'expected_range', ''), "unit": getattr(r, 'unit', ''),
                 "message": getattr(r, 'message', '')}
                for r in self.results
            ],
        }

    def __str__(self) -> str:
        return generate_text_report(self)


def _get_val(obj, attr, default=None):
    """Safely get attribute from any object."""
    return getattr(obj, attr, default)


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
    n_passed = sum(1 for r in results if _get_val(r, 'passed', False))
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
        name = _get_val(r, 'name', 'unknown')
        passed = _get_val(r, 'passed', False)
        mark = "[PASS]" if passed else "[FAIL]"
        lines.append(f"  {mark} {name}")

        actual = _get_val(r, 'actual_value', _get_val(r, 'actual', _get_val(r, 'value', None)))
        unit = _get_val(r, 'unit', '')
        expected = _get_val(r, 'expected_range', _get_val(r, 'expected', _get_val(r, 'target', '')))

        if actual is not None:
            lines.append(f"      Value: {actual} {unit}")
        if expected:
            lines.append(f"      Expected: {expected}")

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
            if not _get_val(r, 'passed', False):
                lines.append(f"  X {_get_val(r, 'name', 'unknown')}")
                msg = _get_val(r, 'message', '')
                if msg:
                    lines.append(f"      {msg}")
        lines.append("")

    lines.append("=" * 60)
    status = "ALL CHECKS PASSED" if n_failed == 0 else "SOME CHECKS FAILED"
    lines.append(f"  Status: {status}")
    lines.append("=" * 60)

    return "\n".join(lines)