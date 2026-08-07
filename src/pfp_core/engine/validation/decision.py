"""Validation runtime helpers for final decision calculation."""

from __future__ import annotations

from typing import Literal, Sequence

ValidationDecision = Literal["PASS", "WARN", "DROP", "FAIL"]


def _decision_without_policies(items: Sequence[object]) -> ValidationDecision:
    """Compute validation decision without strictness policy overrides."""

    if any(getattr(item, "DiagnosticSeverity") == "FAIL" for item in items):
        return "FAIL"
    if any(getattr(item, "DiagnosticSeverity") == "DROP" for item in items):
        return "DROP"
    if any(getattr(item, "DiagnosticSeverity") == "WARN" for item in items):
        return "WARN"
    return "PASS"


def _decision_from_strictness(
    strictness_result: object, items: Sequence[object]
) -> ValidationDecision:
    """Compute decision using strictness policy output."""

    if getattr(strictness_result, "should_fail", False):
        return "FAIL"
    if getattr(strictness_result, "drop_invalid", False):
        return "DROP"
    if any(getattr(item, "DiagnosticSeverity") == "DROP" for item in items):
        return "DROP"
    if any(getattr(item, "DiagnosticSeverity") == "WARN" for item in items):
        return "WARN"
    return "PASS"
