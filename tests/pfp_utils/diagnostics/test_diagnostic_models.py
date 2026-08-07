from typing import Any, cast

import pytest

from pfp_utils.diagnostics.diagnostic_models import Diagnostic, DiagnosticSeverity


def test_diagnostic_severity_alias_warning_is_normalized() -> None:
    """Normalize warning alias into canonical WARN severity enum."""
    diag = Diagnostic(severity="warning", code="WARN_CODE", message="alias test")
    assert diag.severity is DiagnosticSeverity.WARN


def test_diagnostic_severity_normalize_rejects_unknown_value() -> None:
    """Raise ValueError for unsupported diagnostic severity tokens."""
    with pytest.raises(ValueError, match="Unknown severity"):
        DiagnosticSeverity.normalize("not-a-severity")


def test_diagnostic_requires_severity_argument() -> None:
    """Raise TypeError when required severity argument is omitted."""
    with pytest.raises(
        TypeError, match="missing 1 required positional argument: 'severity'"
    ):
        cast(Any, Diagnostic)(code="X", message="m")
