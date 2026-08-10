"""report.py — Validation report generation.

Produces formatted text reports of validation results.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ValidationResult:
    """Single validation check result."""
    name: str
    passed: bool
    actual_value: Any = None
    expected_range: str = ""
    unit: str = ""
    message: str = ""

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.actual_value} {self.unit} (expected: {self.expected_range})"


@dataclass
class ValidationReport:
    """Aggregated validation report.
    
    Collects individual ValidationResult items and produces
    formatted output for console or file.
    """
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
        """Add a validation result."""
        self.results.append(result)
    
    def add_check(self, name: str, passed: bool, actual: Any = None,
                  expected: str = "", unit: str = "", message: str = "") -> None:
        """Convenience method to add a check."""
        self.add(ValidationResult(
            name=name,
            passed=passed,
            actual_value=actual,
            expected_range=expected,
            unit=unit,
            message=message,
        ))
    
    def summary_line(self) -> str:
        return f"{self.n_passed}/{self.n_total} checks passed"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "n_total": self.n_total,
            "n_passed": self.n_passed,
            "n_failed": self.n_failed,
            "all_passed": self.all_passed,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "actual": r.actual_value,
                    "expected": r.expected_range,
                    "unit": r.unit,
                    "message": r.message,
                }
                for r in self.results
            ],
        }
    
    def __str__(self) -> str:
        return generate_text_report(self)
    
    def print_report(self) -> None:
        """Print formatted report to console."""
        print(generate_text_report(self))


def generate_text_report(report: ValidationReport) -> str:
    """Generate a formatted text report.
    
    Produces a 5-section report:
    1. Header with title
    2. Summary line
    3. Individual results
    4. Failures detail (if any)
    5. Footer
    """
    lines: List[str] = []
    A = lines.append
    
    # Section 1: Header
    A("=" * 60)
    A(f"  {report.title}")
    A("=" * 60)
    A("")
    
    # Section 2: Summary
    A(f"  Summary: {report.summary_line()}")
    A("")
    
    # Section 3: Individual results
    A("  Results:")
    A("  " + "-" * 56)
    
    for r in report.results:
        check_mark = "\u2611"
        box_mark = "\u2610"
        mark = check_mark if r.passed else box_mark
        A(f"  {mark} {r.name}")
        if r.actual_value is not None:
            A(f"      Value: {r.actual_value} {r.unit}")
        if r.expected_range:
            A(f"      Expected: {r.expected_range}")
    
    A("")
    
    # Section 4: Failures detail
    if report.n_failed > 0:
        A(f"  Failures ({report.n_failed}):")
        A("  " + "-" * 56)
        for r in report.results:
            if not r.passed:
                A(f"  \u2717 {r.name}")
                if r.message:
                    A(f"      {r.message}")
        A("")
    
    # Section 5: Footer
    A("=" * 60)
    status = "ALL CHECKS PASSED" if report.all_passed else "SOME CHECKS FAILED"
    A(f"  Status: {status}")
    A("=" * 60)
    
    return "\n".join(lines)


def format_duration(ms: float) -> str:
    """Format milliseconds as human-readable string."""
    if ms < 1.0:
        return f"{ms*1000:.1f} \u03bcs"
    elif ms < 1000.0:
        return f"{ms:.1f} ms"
    else:
        return f"{ms/1000:.2f} s"


def format_resistance(mohm: float) -> str:
    """Format resistance in M\u03a9."""
    return f"{mohm:.1f} M\u03a9"


def format_voltage(mv: float) -> str:
    """Format voltage in mV."""
    return f"{mv:.2f} mV"


def format_time_constant(ms: float) -> str:
    """Format time constant in ms."""
    return f"{ms:.1f} ms"
