"""Mirror tests for pfp_runtime.pipeline.log_filters."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Optional

from pfp_runtime.pipeline.log_filters import log_validation_diagnostics
from pfp_utils.diagnostics.diagnostic_models import Diagnostic
from pfp_utils.diagnostics.validation_report import ValidationReport


class _LoggerStub:
    """Collect runtime log_process calls for assertions.

    Returns:
        None.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory log storage.

        Returns:
            None.
        """
        self.records: List[Dict[str, Any]] = []

    def log_process(
        self,
        level: int,
        name: str,
        msg: str,
        *args: Any,
        exc_info: Optional[Any] = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Store a rendered log entry for later assertions.

        Args:
            level: Numeric stdlib logging level.
            name: Logger name used by the filter.
            msg: Message template.
            *args: Positional arguments for message formatting.
            exc_info: Optional exception context.
            extra: Optional extra record attributes.

        Returns:
            None.
        """
        del exc_info, extra
        self.records.append(
            {
                "level": level,
                "name": name,
                "message": msg % args,
            }
        )


def test_log_validation_diagnostics_returns_report_and_logs_each_diagnostic() -> None:
    """Return the original report object and emit one runtime event per diagnostic.

    Returns:
        None.
    """
    report = ValidationReport(target="stripe.product")
    report.add(
        Diagnostic(
            severity="WARN",
            code="OBS.CONTRACT",
            message="warn message",
            item_ref="SKU-1",
            path="items[0]",
        )
    )
    report.add(
        Diagnostic(
            severity="INFO",
            code="OBS.INFO",
            message="info message",
        )
    )
    logger = _LoggerStub()

    result = log_validation_diagnostics(
        report,
        logger=logger,
        metric_labels={"target": "stripe.product_feed", "stage": "validation"},
        run_id="run-1",
        correlation_id="corr-1",
    )

    assert result is report
    assert len(logger.records) == 2
    assert logger.records[0]["level"] == logging.INFO
    assert logger.records[0]["name"] == "pfp_runtime.pipeline.log_filters"
    assert "Runtime diagnostics event" in logger.records[0]["message"]
    assert "target=stripe.product_feed" in logger.records[0]["message"]
    assert "stage=validation" in logger.records[0]["message"]
    assert "severity=WARN" in logger.records[0]["message"]
    assert "code=OBS.CONTRACT" in logger.records[0]["message"]
    assert "item_ref=SKU-1" in logger.records[0]["message"]
    assert "path=items[0]" in logger.records[0]["message"]
    assert "message=warn message" in logger.records[0]["message"]
    assert "severity=INFO" in logger.records[1]["message"]
    assert "code=OBS.INFO" in logger.records[1]["message"]


def test_log_validation_diagnostics_uses_default_context_values() -> None:
    """Fall back to default target, stage, and blank identifiers when absent.

    Returns:
        None.
    """
    report = ValidationReport(target=None)
    report.add(Diagnostic(severity="ERROR", code="OBS.FAIL", message="broken"))
    logger = _LoggerStub()

    log_validation_diagnostics(
        report,
        logger=logger,
        metric_labels={},
        run_id=None,
        correlation_id=None,
    )

    assert len(logger.records) == 1
    assert "target=unknown" in logger.records[0]["message"]
    assert "stage=total" in logger.records[0]["message"]
    assert "run_id=" in logger.records[0]["message"]
    assert "correlation_id=" in logger.records[0]["message"]
    assert "severity=ERROR" in logger.records[0]["message"]
