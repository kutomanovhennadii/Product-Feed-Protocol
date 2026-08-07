"""Tests for the MessageRedactionStrategy implementation."""

from __future__ import annotations

import logging
from typing import Any

from pfp_utils.logging.filters.redaction_strategies.message_redaction_strategy import (
    MessageRedactionStrategy,
    build_message_redaction_strategy,
)
from pfp_utils.sanitization import sanitize_text


def _make_record(msg: Any, args: Any = None) -> logging.LogRecord:
    """Build a LogRecord for message-redaction tests.

    Args:
        msg: Raw ``LogRecord.msg`` value to test.
        args: Raw ``LogRecord.args`` payload to test.

    Returns:
        LogRecord configured with the supplied message and args.
    """
    return logging.LogRecord(
        name="message-redaction",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=args,
        exc_info=None,
    )


def test_message_redaction_strategy_masks_inline_secret() -> None:
    """Inline secret fragments must be masked in the baked message.

    Returns:
        None.
    """
    record = _make_record("url=https://a?token=abc")

    MessageRedactionStrategy().apply(record)

    assert "token=***" in record.msg
    assert record.args is None


def test_message_redaction_strategy_bakes_and_sanitizes_format_args() -> None:
    """Formatted args must be folded into the sanitized message text.

    Returns:
        None.
    """
    record = _make_record("user=%s", ("token=abc",))

    MessageRedactionStrategy().apply(record)

    assert record.msg == "user=token=***"
    assert record.args is None


def test_message_redaction_strategy_sanitizes_non_string_message_repr() -> None:
    """Non-string ``msg`` values must be stringified and sanitized unconditionally.

    Returns:
        None.
    """
    payload = {"token": "abc", "safe": "ok"}
    record = _make_record(payload)

    MessageRedactionStrategy().apply(record)

    assert record.msg == sanitize_text(str(payload))
    assert record.args is None


def test_message_redaction_strategy_is_idempotent() -> None:
    """Applying the strategy twice must keep the same sanitized result.

    Returns:
        None.
    """
    record = _make_record("user=%s", ("token=abc",))
    strategy = MessageRedactionStrategy()

    strategy.apply(record)
    first_msg = record.msg
    first_args = record.args
    strategy.apply(record)

    assert record.msg == first_msg
    assert record.args == first_args


def test_message_redaction_strategy_preserves_secret_free_message_meaning() -> None:
    """Messages without secrets must keep their visible meaning after apply().

    Returns:
        None.
    """
    record = _make_record("plain message")

    MessageRedactionStrategy().apply(record)

    assert record.msg == "plain message"
    assert record.args is None


def test_build_message_redaction_strategy_returns_strategy_instance() -> None:
    """Builder must return a MessageRedactionStrategy instance.

    Returns:
        None.
    """
    assert isinstance(build_message_redaction_strategy(), MessageRedactionStrategy)
