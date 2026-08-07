"""Pass-through log filters used between pipeline steps."""

from __future__ import annotations

import logging
from typing import Any, List, Mapping, Optional, Protocol

from pfp_utils.diagnostics.diagnostic_models import DiagnosticSeverity
from pfp_utils.diagnostics.validation_report import ValidationReport
from pfp_utils.sanitization import sanitize_text


class _ProcessLogger(Protocol):
    """Minimal runtime logging contract required by log filters."""

    def log_process(
        self,
        level: int,
        name: str,
        msg: str,
        *args: Any,
        exc_info: Optional[Any] = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Emit a structured runtime log record.

        Args:
            level: Numeric stdlib logging level.
            name: Logger name describing the call site.
            msg: Log message template.
            *args: Positional arguments interpolated into the message.
            exc_info: Optional exception context.
            extra: Optional extra record attributes.

        Returns:
            None.
        """


def log_validation_diagnostics(
    report: ValidationReport,
    *,
    logger: _ProcessLogger,
    metric_labels: Mapping[str, str],
    run_id: Optional[str],
    correlation_id: Optional[str],
) -> ValidationReport:
    """Log each validation diagnostic and return the original report.

    Args:
        report: Validation report with diagnostics to log.
        logger: Runtime logger providing a log_process method.
        metric_labels: Metric labels containing target/stage log context.
        run_id: Optional run identifier.
        correlation_id: Optional correlation identifier.

    Returns:
        The original report object.
    """
    for diagnostic in report.diagnostics:
        logger.log_process(
            logging.INFO,
            __name__,
            "Runtime diagnostics event: target=%s stage=%s run_id=%s correlation_id=%s severity=%s code=%s item_ref=%s path=%s message=%s",
            metric_labels.get("target", "unknown"),
            metric_labels.get("stage", "total"),
            run_id or "",
            correlation_id or "",
            str(DiagnosticSeverity.normalize(diagnostic.severity)),
            diagnostic.code,
            diagnostic.item_ref or "",
            diagnostic.path or "",
            sanitize_text(diagnostic.message),
        )
    return report


__all__: List[str] = ["log_validation_diagnostics"]
