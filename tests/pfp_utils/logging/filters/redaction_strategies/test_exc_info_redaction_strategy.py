"""Tests for the ExcInfoRedactionStrategy implementation."""

from __future__ import annotations

import logging
from types import TracebackType

from pfp_utils.logging.filters.redaction_strategies.exc_info_redaction_strategy import (
    ExcInfoRedactionStrategy,
    build_exc_info_redaction_strategy,
)

ExcInfoTriple = tuple[type[BaseException], BaseException, TracebackType | None]


def _make_record(*, exc_info: ExcInfoTriple | None = None) -> logging.LogRecord:
    """Build a LogRecord for exc-info redaction tests.

    Args:
        exc_info: Optional exception triple assigned to the test record.

    Returns:
        LogRecord configured with the supplied exception information.
    """
    return logging.LogRecord(
        name="exc-info-redaction",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="failed",
        args=(),
        exc_info=exc_info,
    )


def _capture_runtime_error_exc_info(message: str) -> ExcInfoTriple:
    """Capture an exception triple for a RuntimeError message.

    Args:
        message: RuntimeError text to raise and capture.

    Returns:
        Exception triple suitable for ``LogRecord.exc_info``.
    """
    try:
        raise RuntimeError(message)
    except RuntimeError as exc:
        return (type(exc), exc, exc.__traceback__)


def _capture_chained_exc_info() -> ExcInfoTriple:
    """Capture an exception triple for a chained exception scenario.

    Returns:
        Exception triple containing a chained traceback with secret-like text.
    """
    try:
        try:
            raise RuntimeError("Bearer xyz123")
        except RuntimeError as cause:
            raise ValueError("outer token=abc") from cause
    except ValueError as exc:
        return (type(exc), exc, exc.__traceback__)


def test_exc_info_redaction_strategy_sanitizes_formatted_traceback() -> None:
    """Formatted traceback text must be sanitized and detached from exc_info.

    Returns:
        None.
    """
    record = _make_record(exc_info=_capture_runtime_error_exc_info("Bearer xyz123"))

    ExcInfoRedactionStrategy().apply(record)

    assert record.exc_text is not None
    assert "Bearer ***" in record.exc_text
    assert "xyz123" not in record.exc_text
    assert record.exc_info is None


def test_exc_info_redaction_strategy_is_noop_without_exc_info() -> None:
    """Missing exc_info must leave exception fields unchanged.

    Returns:
        None.
    """
    record = _make_record(exc_info=None)

    ExcInfoRedactionStrategy().apply(record)

    assert record.exc_text is None
    assert record.exc_info is None


def test_exc_info_redaction_strategy_preserves_existing_exc_text_without_exc_info() -> (
    None
):
    """Existing exc_text must remain untouched when exc_info is absent.

    Returns:
        None.
    """
    record = _make_record(exc_info=None)
    record.exc_text = "already formatted"

    ExcInfoRedactionStrategy().apply(record)

    assert record.exc_text == "already formatted"
    assert record.exc_info is None


def test_exc_info_redaction_strategy_sanitizes_chained_traceback() -> None:
    """Chained tracebacks must be fully sanitized across the entire chain.

    Returns:
        None.
    """
    record = _make_record(exc_info=_capture_chained_exc_info())

    ExcInfoRedactionStrategy().apply(record)

    assert record.exc_text is not None
    assert "Bearer ***" in record.exc_text
    assert "token=***" in record.exc_text
    assert "xyz123" not in record.exc_text
    assert "token=abc" not in record.exc_text
    assert record.exc_info is None


def test_exc_info_redaction_strategy_is_idempotent_after_first_apply() -> None:
    """Second apply call must become a no-op after exc_info is consumed.

    Returns:
        None.
    """
    record = _make_record(exc_info=_capture_runtime_error_exc_info("Bearer xyz123"))
    strategy = ExcInfoRedactionStrategy()

    strategy.apply(record)
    first_exc_text = record.exc_text
    strategy.apply(record)

    assert record.exc_text == first_exc_text
    assert record.exc_info is None


def test_build_exc_info_redaction_strategy_returns_strategy_instance() -> None:
    """Builder must return an ExcInfoRedactionStrategy instance.

    Returns:
        None.
    """
    assert isinstance(build_exc_info_redaction_strategy(), ExcInfoRedactionStrategy)
