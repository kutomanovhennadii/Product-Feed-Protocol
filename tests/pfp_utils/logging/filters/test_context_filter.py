"""Tests for the standalone ContextFilter module."""

import logging

from pfp_utils.logging import LogContext
from pfp_utils.logging.filters.context_filter import (
    ContextFilter,
    build_context_filter,
)
from pfp_utils.logging.log_context import get_context


def test_context_filter_returns_true_with_empty_context() -> None:
    """Empty context must leave the record unchanged and allow emission."""
    record = logging.LogRecord(
        name="context-filter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )
    context = get_context()
    original_context = context.copy()
    original_record = record.__dict__.copy()

    context.clear()
    try:
        assert ContextFilter().filter(record) is True
    finally:
        context.clear()
        context.update(original_context)

    assert record.__dict__ == original_record


def test_context_filter_injects_active_log_context() -> None:
    """Active thread-local values must be copied onto the record."""
    record = logging.LogRecord(
        name="context-filter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )

    with LogContext(target="https://x", item_ref="a"):
        assert ContextFilter().filter(record) is True

    assert record.__dict__["target"] == "https://x"
    assert record.__dict__["item_ref"] == "a"


def test_build_context_filter_returns_context_filter() -> None:
    """Builder must return a ContextFilter instance."""
    assert isinstance(build_context_filter(), ContextFilter)
