"""Tests for the standalone stdout handler builder."""

from __future__ import annotations

import logging
import sys

from pfp_utils.logging.handlers.stdout_handler import build_stdout_handler


def test_build_stdout_handler_returns_stdout_stream_handler() -> None:
    """Builder must return a StreamHandler writing to sys.stdout."""
    handler = build_stdout_handler()

    assert isinstance(handler, logging.StreamHandler)
    assert handler.stream is sys.stdout


def test_build_stdout_handler_starts_without_formatter() -> None:
    """Builder must return a plain handler without formatter wiring."""
    handler = build_stdout_handler()

    assert handler.formatter is None


def test_build_stdout_handler_starts_without_filters() -> None:
    """Builder must return a plain handler without any attached filters."""
    handler = build_stdout_handler()

    assert handler.filters == []


def test_build_stdout_handler_supports_later_formatter_attachment() -> None:
    """Returned handler must accept formatter wiring by the owning builder."""
    handler = build_stdout_handler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")

    handler.setFormatter(formatter)

    assert handler.formatter is formatter


def test_build_stdout_handler_supports_later_filter_attachment() -> None:
    """Returned handler must preserve filter order added by the owning builder."""
    handler = build_stdout_handler()
    filters = [logging.Filter("first"), logging.Filter("second")]

    for log_filter in filters:
        handler.addFilter(log_filter)

    assert handler.filters == filters
