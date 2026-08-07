"""Tests for the standalone TextFormatterWithContext module."""

from __future__ import annotations

import logging
import re

from pfp_utils.logging.formatters.text_formatter import (
    TextFormatterWithContext,
    build_text_formatter,
)


def test_text_formatter_formats_base_line_without_context_suffix() -> None:
    """Formatter must emit the base line without an extra suffix when context is absent."""
    formatter = build_text_formatter()
    record = logging.LogRecord(
        name="text-formatter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)

    assert (
        re.match(
            r"^.+ \[INFO\] text-formatter: message$",
            output,
        )
        is not None
    )
    assert not output.endswith("]") or output.endswith("[INFO] text-formatter: message")


def test_text_formatter_appends_single_custom_attribute() -> None:
    """Formatter must append a single custom attribute as a context suffix."""
    formatter = TextFormatterWithContext("%(levelname)s: %(message)s")
    record = logging.LogRecord(
        name="text-formatter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )
    record.target = "demo"

    output = formatter.format(record)

    assert output == "INFO: message [target=demo]"


def test_text_formatter_sorts_multiple_custom_attributes_lexicographically() -> None:
    """Formatter must sort multiple custom attributes lexicographically in the suffix."""
    formatter = TextFormatterWithContext("%(levelname)s: %(message)s")
    record = logging.LogRecord(
        name="text-formatter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )
    record.b = 2
    record.a = 1

    output = formatter.format(record)

    assert output == "INFO: message [a=1, b=2]"


def test_text_formatter_ignores_none_and_callable_values() -> None:
    """Formatter must omit None and callable custom values from the suffix."""
    formatter = TextFormatterWithContext("%(levelname)s: %(message)s")
    record = logging.LogRecord(
        name="text-formatter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )
    record.none_value = None
    record.callable_value = lambda: None
    record.present = "yes"

    output = formatter.format(record)

    assert output == "INFO: message [present=yes]"


def test_build_text_formatter_returns_default_configured_instance() -> None:
    """Builder must return a TextFormatterWithContext using the default format string."""
    formatter = build_text_formatter()

    assert isinstance(formatter, TextFormatterWithContext)
    assert formatter._style._fmt == "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
