"""Tests for StrictnessPolicy."""

from typing import Dict, List, Optional, Tuple

import pytest

from pfp_core.policies.domain.strictness import (
    StrictnessConfig,
    StrictnessMode,
    StrictnessPolicy,
)
from pfp_utils.diagnostics.diagnostic_models import Diagnostic, DiagnosticSeverity


def test_fail_on_error_marks_should_fail() -> None:
    """Strategy fail_on_error marks should_fail when error diagnostics are present."""
    diagnostics = [
        Diagnostic(severity=DiagnosticSeverity.ERROR, code="E1", message="err")
    ]
    decision = StrictnessPolicy("fail_on_error").apply(diagnostics)
    assert decision.should_fail is True
    assert decision.drop_invalid is False


def test_drop_invalid_marks_drop() -> None:
    """Strategy drop_invalid marks invalid records for drop without fail-fast."""
    diagnostics = [
        Diagnostic(severity=DiagnosticSeverity.ERROR, code="E1", message="err")
    ]
    decision = StrictnessPolicy("drop_invalid").apply(diagnostics)
    assert decision.should_fail is False
    assert decision.drop_invalid is True


def test_warn_only_downgrades_error() -> None:
    """Strategy warn_only downgrades errors to warnings."""
    diagnostics = [
        Diagnostic(severity=DiagnosticSeverity.ERROR, code="E1", message="err")
    ]
    decision = StrictnessPolicy("warn_only").apply(diagnostics)
    assert decision.should_fail is False
    assert decision.drop_invalid is False
    assert all(
        DiagnosticSeverity.normalize(d.severity) is not DiagnosticSeverity.ERROR
        for d in decision.diagnostics
    )


def test_mode_normalize_accepts_enum() -> None:
    """StrictnessMode.normalize returns the same enum instance."""
    assert (
        StrictnessMode.normalize(StrictnessMode.FAIL_ON_ERROR)
        is StrictnessMode.FAIL_ON_ERROR
    )


def test_unknown_strategy_raises() -> None:
    """StrictnessMode.normalize rejects unknown strategy strings."""
    with pytest.raises(ValueError, match="Unknown strictness strategy"):
        StrictnessMode.normalize("nonexistent_strategy")


def test_strictness_config_rejects_non_string_strategy() -> None:
    """StrictnessConfig rejects non-string strategy values."""
    with pytest.raises(ValueError, match="core.strictness.strategy must be a string"):
        StrictnessConfig.from_dict({"strategy": 123})  # type: ignore[arg-type]


def test_warn_only_preserves_non_error_diagnostics() -> None:
    """warn_only keeps WARN diagnostics unchanged while downgrading only errors."""
    diagnostics = [
        Diagnostic(
            severity=DiagnosticSeverity.ERROR,
            code="E1",
            message="err",
        ),
        Diagnostic(
            severity=DiagnosticSeverity.WARN,
            code="W1",
            message="warn",
        ),
    ]

    decision = StrictnessPolicy("warn_only").apply(diagnostics)
    assert (
        DiagnosticSeverity.normalize(decision.diagnostics[0].severity)
        is DiagnosticSeverity.WARN
    )
    assert (
        DiagnosticSeverity.normalize(decision.diagnostics[1].severity)
        is DiagnosticSeverity.WARN
    )


def test_apply_reports_outcome_to_telemetry() -> None:
    """StrictnessPolicy emits strategy and outcome labels to telemetry."""

    class _TelemetryStub:
        def __init__(self) -> None:
            self.calls: List[Tuple[str, float, Optional[Dict[str, str]]]] = []

        def inc(
            self,
            name: str,
            value: float = 1,
            labels: Optional[Dict[str, str]] = None,
        ) -> None:
            self.calls.append((name, value, labels))

        def observe_duration(
            self,
            stage: str,
            duration: float,
            labels: Dict[str, str],
        ) -> None:
            self.calls.append((stage, duration, labels))

    diagnostics = [
        Diagnostic(
            severity=DiagnosticSeverity.ERROR,
            code="E1",
            message="err",
        )
    ]

    fail_telemetry = _TelemetryStub()
    drop_telemetry = _TelemetryStub()
    pass_telemetry = _TelemetryStub()

    StrictnessPolicy("fail_on_error").apply(diagnostics, telemetry=fail_telemetry)
    StrictnessPolicy("drop_invalid").apply(diagnostics, telemetry=drop_telemetry)
    StrictnessPolicy("warn_only").apply(diagnostics, telemetry=pass_telemetry)

    assert fail_telemetry.calls[0][0] == "strictness_decision"
    assert fail_telemetry.calls[0][2] == {
        "strategy": "fail_on_error",
        "outcome": "fail",
    }
    assert drop_telemetry.calls[0][2] == {
        "strategy": "drop_invalid",
        "outcome": "drop",
    }
    assert pass_telemetry.calls[0][2] == {
        "strategy": "warn_only",
        "outcome": "pass",
    }


def test_apply_rejects_unknown_internal_strategy_value() -> None:
    """apply guards against invalid internal strategy value."""
    policy = StrictnessPolicy("fail_on_error")
    policy.strategy = "invalid"  # type: ignore[assignment]

    with pytest.raises(ValueError, match="Unknown strictness strategy"):
        policy.apply([])
