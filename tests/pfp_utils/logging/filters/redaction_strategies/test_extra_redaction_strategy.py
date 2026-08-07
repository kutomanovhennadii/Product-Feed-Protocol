"""Tests for the ExtraRedactionStrategy implementation."""

from __future__ import annotations

import logging

from pfp_utils.logging.filters.redaction_strategies.extra_redaction_strategy import (
    _STANDARD_ATTRS,
    ExtraRedactionStrategy,
    build_extra_redaction_strategy,
)
from pfp_utils.logging.formatters.json_formatter import JSONFormatter
from pfp_utils.logging.formatters.text_formatter import TextFormatterWithContext


def _make_record() -> logging.LogRecord:
    """Build a LogRecord for extra-attribute redaction tests.

    Returns:
        LogRecord configured with a stable baseline payload.
    """
    return logging.LogRecord(
        name="extra-redaction",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="plain message",
        args=(),
        exc_info=None,
    )


def test_extra_redaction_strategy_sanitizes_auth_token_attribute() -> None:
    """Secret-like custom auth_token values must be sanitized.

    Returns:
        None.
    """
    record = _make_record()
    setattr(record, "auth_token", "Bearer abc")

    ExtraRedactionStrategy().apply(record)

    assert getattr(record, "auth_token") == "Bearer ***"


def test_extra_redaction_strategy_sanitizes_correlation_id_attribute() -> None:
    """Custom correlation_id values must be sanitized when they carry secrets.

    Returns:
        None.
    """
    record = _make_record()
    setattr(record, "correlation_id", "token=xyz")

    ExtraRedactionStrategy().apply(record)

    assert getattr(record, "correlation_id") == "token=***"


def test_extra_redaction_strategy_does_not_mutate_standard_attribute() -> None:
    """Standard LogRecord attributes must remain untouched.

    Returns:
        None.
    """
    record = _make_record()
    record.name = "token=xyz"

    ExtraRedactionStrategy().apply(record)

    assert record.name == "token=xyz"


def test_extra_redaction_strategy_does_not_mutate_non_string_attribute() -> None:
    """Non-string custom attributes must remain unchanged.

    Returns:
        None.
    """
    record = _make_record()
    setattr(record, "count", 42)

    ExtraRedactionStrategy().apply(record)

    assert getattr(record, "count") == 42


def test_extra_redaction_strategy_does_not_mutate_private_attribute() -> None:
    """Private custom attributes must be skipped.

    Returns:
        None.
    """
    record = _make_record()
    setattr(record, "_private", "Bearer abc")

    ExtraRedactionStrategy().apply(record)

    assert getattr(record, "_private") == "Bearer abc"


def test_extra_redaction_strategy_is_idempotent() -> None:
    """Applying the strategy twice must keep the same sanitized result.

    Returns:
        None.
    """
    record = _make_record()
    setattr(record, "correlation_id", "token=xyz")
    strategy = ExtraRedactionStrategy()

    strategy.apply(record)
    first_value = getattr(record, "correlation_id")
    strategy.apply(record)

    assert getattr(record, "correlation_id") == first_value


def test_extra_redaction_strategy_standard_attrs_stay_in_sync_with_formatters() -> None:
    """Local blacklist must cover the standard attrs used by both formatters.

    Returns:
        None.
    """
    formatter_attrs = set(JSONFormatter._standard_attrs) | set(
        TextFormatterWithContext._ignored
    )

    assert formatter_attrs <= _STANDARD_ATTRS


def test_build_extra_redaction_strategy_returns_strategy_instance() -> None:
    """Builder must return an ExtraRedactionStrategy instance.

    Returns:
        None.
    """
    assert isinstance(build_extra_redaction_strategy(), ExtraRedactionStrategy)
