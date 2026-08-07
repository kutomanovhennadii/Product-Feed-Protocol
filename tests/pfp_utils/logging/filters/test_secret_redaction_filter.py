"""Tests for the composed SecretRedactionFilter module."""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Mapping

from pfp_utils.logging.filters.redaction_strategies.exc_info_redaction_strategy import (
    ExcInfoRedactionStrategy,
)
from pfp_utils.logging.filters.redaction_strategies.extra_redaction_strategy import (
    ExtraRedactionStrategy,
)
from pfp_utils.logging.filters.redaction_strategies.message_redaction_strategy import (
    MessageRedactionStrategy,
)
from pfp_utils.logging.filters.secret_redaction_filter import (
    SecretRedactionFilter,
    build_secret_redaction_filter,
)

ExcInfoTriple = tuple[type[BaseException], BaseException, TracebackType | None]
LogRecordArgs = tuple[object, ...] | Mapping[str, object] | None


class _RecordingStrategy:
    """Record invocation order for SecretRedactionFilter strategy tests.

    Returns:
        A test double that appends its label when apply() is called.
    """

    def __init__(self, label: str, calls: list[str]) -> None:
        """Store the label and shared call log.

        Args:
            label: Marker appended when the strategy is invoked.
            calls: Shared list used to capture invocation order.

        Returns:
            None.
        """
        self._label = label
        self._calls = calls

    def apply(self, record: logging.LogRecord) -> None:
        """Record that the strategy was invoked for the supplied log record.

        Args:
            record: LogRecord passed through SecretRedactionFilter.

        Returns:
            None.
        """
        del record
        self._calls.append(self._label)


def _make_record(
    *,
    msg: object = "plain message",
    args: LogRecordArgs = (),
    exc_info: ExcInfoTriple | None = None,
) -> logging.LogRecord:
    """Build a LogRecord for SecretRedactionFilter tests.

    Args:
        msg: Raw LogRecord.msg payload.
        args: Raw LogRecord.args payload.
        exc_info: Optional exception triple to attach to the record.

    Returns:
        LogRecord configured with the supplied payload.
    """
    return logging.LogRecord(
        name="secret-redaction-filter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=args,
        exc_info=exc_info,
    )


def _capture_runtime_error_exc_info(message: str) -> ExcInfoTriple:
    """Capture an exception triple for a RuntimeError message.

    Args:
        message: RuntimeError text to raise and capture.

    Returns:
        Exception triple suitable for LogRecord.exc_info.
    """
    try:
        raise RuntimeError(message)
    except RuntimeError as exc:
        return (type(exc), exc, exc.__traceback__)


def test_secret_redaction_filter_returns_true_for_arbitrary_record() -> None:
    """Filter must always return True so later logging processing continues."""
    record = _make_record(msg="token=secret")

    assert SecretRedactionFilter(strategies=()).filter(record) is True


def test_secret_redaction_filter_invokes_strategies_in_order() -> None:
    """Filter must call each supplied strategy in the original tuple order."""
    calls: list[str] = []
    record = _make_record()
    filter_instance = SecretRedactionFilter(
        strategies=(
            _RecordingStrategy("message", calls),
            _RecordingStrategy("exc_info", calls),
            _RecordingStrategy("extra", calls),
        )
    )

    assert filter_instance.filter(record) is True
    assert calls == ["message", "exc_info", "extra"]


def test_secret_redaction_filter_sanitizes_message_exc_info_and_context() -> None:
    """Default filter must sanitize the message, traceback, and extra context."""
    record = _make_record(
        msg="user=%s",
        args=("token=secret",),
        exc_info=_capture_runtime_error_exc_info("Bearer xyz123"),
    )
    setattr(record, "correlation_id", "token=abc")

    assert build_secret_redaction_filter().filter(record) is True

    assert record.msg == "user=token=***"
    assert record.args is None
    assert record.exc_text is not None
    assert "Bearer ***" in record.exc_text
    assert "xyz123" not in record.exc_text
    assert record.exc_info is None
    assert getattr(record, "correlation_id") == "token=***"


def test_build_secret_redaction_filter_returns_default_strategy_pipeline() -> None:
    """Builder must wire message, exception, and extra strategies in order."""
    filter_instance = build_secret_redaction_filter()

    assert isinstance(filter_instance, SecretRedactionFilter)
    assert [type(strategy) for strategy in filter_instance._strategies] == [
        MessageRedactionStrategy,
        ExcInfoRedactionStrategy,
        ExtraRedactionStrategy,
    ]


def test_secret_redaction_filter_with_no_strategies_is_noop() -> None:
    """Empty strategy tuple must leave the record unchanged and return True."""
    record = _make_record(msg="token=secret")
    setattr(record, "target", "https://example.test")
    original_record = record.__dict__.copy()

    assert SecretRedactionFilter(strategies=()).filter(record) is True
    assert record.__dict__ == original_record
