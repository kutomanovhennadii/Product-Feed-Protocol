"""Sanitization helpers for diagnostics and validation reports.

This module provides two stateless free functions for producing safe copies
of ``Diagnostic`` and ``ValidationReport`` values before they are logged,
returned from the pipeline runner, or serialized into an ``ExecutionReport``.

Functions:
    - **sanitize_diagnostic(diagnostic)**: return a new ``Diagnostic`` with
      ``message`` passed through ``sanitize_text`` and ``metadata`` (if it is
      a mapping) passed through ``sanitize_mapping``. Other fields
            (``severity``, ``code``, ``path``, ``item_ref``) are preserved as-is.
    - **sanitize_validation_report(report)**: return a new
      ``ValidationReport`` with the same ``target`` / ``artifact_profile`` and
      every diagnostic sanitized via ``sanitize_diagnostic``.

When to use:
    Call these on any ``Diagnostic`` or ``ValidationReport`` that is about to
    leave the pipeline runner — whether it goes into logs, into an
    ``ExecutionReport`` surface, or into an exception message. The helpers
    centralize the redaction policy so callers do not have to know which
    fields may carry secrets.

Guarantees:
        - Input values are never mutated; the functions return new instances.
        - ``Diagnostic`` already normalizes ``metadata`` to a mapping, so metadata
            is always redacted through ``sanitize_mapping``.
        - Redaction uses ``sanitize_text`` / ``sanitize_mapping``, so the same
            masking patterns apply consistently everywhere.
"""

from __future__ import annotations

from pfp_utils.diagnostics.diagnostic_models import Diagnostic
from pfp_utils.diagnostics.validation_report import ValidationReport
from pfp_utils.sanitization import sanitize_mapping, sanitize_text


def sanitize_diagnostic(diagnostic: Diagnostic) -> Diagnostic:
    """Return a sanitized copy of ``diagnostic`` safe for logging/reporting.

    Args:
        diagnostic: Diagnostic to sanitize.

    Returns:
        New Diagnostic with ``message`` and ``metadata`` redacted.
    """
    safe_metadata = dict(sanitize_mapping(diagnostic.metadata))

    return Diagnostic(
        severity=diagnostic.severity,
        code=diagnostic.code,
        message=sanitize_text(diagnostic.message),
        path=diagnostic.path,
        item_ref=diagnostic.item_ref,
        metadata=safe_metadata,
    )


def sanitize_validation_report(report: ValidationReport) -> ValidationReport:
    """Return a sanitized copy of ``report`` safe for logging/reporting.

    Args:
        report: Validation report to sanitize.

    Returns:
        New ValidationReport with every diagnostic passed through
        ``sanitize_diagnostic``.
    """
    sanitized_report = ValidationReport(
        target=report.target,
        artifact_profile=report.artifact_profile,
    )
    for diagnostic in report.diagnostics:
        sanitized_report.add(sanitize_diagnostic(diagnostic))
    return sanitized_report
