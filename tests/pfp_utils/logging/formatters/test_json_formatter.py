"""Tests for the standalone JSONFormatter module."""

import json
import logging
import sys
from unittest.mock import Mock, patch

from pfp_utils.logging.formatters.json_formatter import (
    JSONFormatter,
    build_json_formatter,
)


def test_json_formatter_returns_valid_json_with_base_fields() -> None:
    """Formatter must emit valid JSON with the standard top-level fields."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="json-formatter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )

    log_data = json.loads(formatter.format(record))

    assert isinstance(log_data["timestamp"], str)
    assert log_data["level"] == "INFO"
    assert log_data["name"] == "json-formatter"
    assert log_data["message"] == "message"


def test_json_formatter_puts_custom_record_attributes_into_context() -> None:
    """Custom non-standard record attributes must be emitted in the context object."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="json-formatter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )
    record.target = "https://example.test"
    record.item_ref = "item-1"
    record._private = "hidden"

    log_data = json.loads(formatter.format(record))

    assert log_data["context"] == {
        "target": "https://example.test",
        "item_ref": "item-1",
    }


def test_json_formatter_uses_exc_info_when_exc_text_is_missing() -> None:
    """Formatter must fall back to formatting exc_info when exc_text is absent."""
    formatter = JSONFormatter()

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = logging.LogRecord(
            name="json-formatter",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="message",
            args=(),
            exc_info=sys.exc_info(),
        )

    log_data = json.loads(formatter.format(record))

    assert "exception" in log_data
    assert "RuntimeError: boom" in log_data["exception"]


def test_json_formatter_prioritizes_exc_text_when_exc_info_is_none() -> None:
    """Formatter must emit precomputed exc_text without requiring exc_info."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="json-formatter",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )
    record.exc_text = "Traceback...\nRuntimeError: ***\n"

    log_data = json.loads(formatter.format(record))

    assert log_data["exception"] == "Traceback...\nRuntimeError: ***\n"


def test_json_formatter_uses_exc_text_when_both_exc_text_and_exc_info_exist() -> None:
    """Formatter must prefer exc_text and avoid reformatting exc_info again."""
    formatter = JSONFormatter()

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = logging.LogRecord(
            name="json-formatter",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="message",
            args=(),
            exc_info=sys.exc_info(),
        )

    record.exc_text = "Traceback...\nRuntimeError: ***\n"
    with patch.object(
        formatter,
        "formatException",
        Mock(side_effect=AssertionError("unexpected call")),
    ):
        log_data = json.loads(formatter.format(record))

    assert log_data["exception"] == "Traceback...\nRuntimeError: ***\n"


def test_json_formatter_omits_exception_field_without_exception_data() -> None:
    """Formatter must omit the exception field when both exc_info and exc_text are absent."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="json-formatter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )

    log_data = json.loads(formatter.format(record))

    assert "exception" not in log_data


def test_json_formatter_omits_context_field_without_custom_attributes() -> None:
    """Formatter must omit the context field when no custom record attributes exist."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="json-formatter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )

    log_data = json.loads(formatter.format(record))

    assert "context" not in log_data


def test_build_json_formatter_returns_json_formatter_instance() -> None:
    """Builder must return a JSONFormatter instance."""
    assert isinstance(build_json_formatter(), JSONFormatter)
