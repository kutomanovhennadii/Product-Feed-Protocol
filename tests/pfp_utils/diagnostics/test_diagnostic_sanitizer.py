"""Mirror tests for diagnostic_sanitizer — sanitize_diagnostic / sanitize_validation_report."""

from __future__ import annotations

from pfp_utils.diagnostics.diagnostic_models import Diagnostic
from pfp_utils.diagnostics.diagnostic_sanitizer import (
    sanitize_diagnostic,
    sanitize_validation_report,
)
from pfp_utils.diagnostics.validation_report import ValidationReport

# ---------------------------------------------------------------------------
# sanitize_diagnostic
# ---------------------------------------------------------------------------


def test_sanitize_diagnostic_masks_message() -> None:
    """Secret-like fragments in message are redacted via sanitize_text."""
    diag = Diagnostic(
        severity="WARN",
        code="X.Y",
        message="password=super-secret",
    )

    sanitized = sanitize_diagnostic(diag)

    assert "super-secret" not in sanitized.message
    assert "password=***" in sanitized.message


def test_sanitize_diagnostic_masks_metadata_keys() -> None:
    """Sensitive-keyed metadata entries are masked via sanitize_mapping."""
    diag = Diagnostic(
        severity="WARN",
        code="X.Y",
        message="ok",
        metadata={"api_key": "raw-value", "safe": "visible"},
    )

    sanitized = sanitize_diagnostic(diag)

    assert sanitized.metadata["api_key"] == "***"
    assert sanitized.metadata["safe"] == "visible"


def test_sanitize_diagnostic_none_metadata_passthrough() -> None:
    """metadata=None is normalized by Diagnostic to {} and survives sanitize."""
    diag = Diagnostic(severity="INFO", code="X.Y", message="ok", metadata=None)

    sanitized = sanitize_diagnostic(diag)

    assert sanitized.metadata == {}


def test_sanitize_diagnostic_preserves_non_secret_fields() -> None:
    """Non-secret Diagnostic attributes are passed through unchanged."""
    diag = Diagnostic(
        severity="ERROR",
        code="A.B",
        message="hello",
        path="$.items[0]",
        item_ref="SKU-1",
        metadata={"safe": "value"},
    )

    sanitized = sanitize_diagnostic(diag)

    assert str(sanitized.severity) == str(diag.severity)
    assert sanitized.code == "A.B"
    assert sanitized.path == "$.items[0]"
    assert sanitized.item_ref == "SKU-1"


# ---------------------------------------------------------------------------
# sanitize_validation_report
# ---------------------------------------------------------------------------


def test_sanitize_validation_report_masks_all_diagnostics() -> None:
    """Every diagnostic in the report passes through sanitize_diagnostic."""
    report = ValidationReport(target="stripe.product")
    report.add(
        Diagnostic(
            severity="WARN",
            code="X.1",
            message="token=abc",
            metadata={"password": "p1"},
        )
    )
    report.add(
        Diagnostic(
            severity="WARN",
            code="X.2",
            message="api_key=def",
            metadata={"secret": "p2"},
        )
    )

    sanitized = sanitize_validation_report(report)
    rendered = str(sanitized.to_dict())

    assert "abc" not in rendered
    assert "def" not in rendered
    assert "p1" not in rendered
    assert "p2" not in rendered
    assert "***" in rendered


def test_sanitize_validation_report_preserves_target() -> None:
    """Report-level identity fields survive sanitization."""
    report = ValidationReport(
        target="stripe.product",
        artifact_profile="catalog_snapshot",
    )

    sanitized = sanitize_validation_report(report)

    assert sanitized.target == "stripe.product"
    assert sanitized.artifact_profile == "catalog_snapshot"
