"""Text formatter for observability log output."""

from __future__ import annotations

import logging
from typing import List

_DEFAULT_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class TextFormatterWithContext(logging.Formatter):
    """Text formatter that appends context fields as a stable, sorted suffix."""

    _ignored = {
        "name",
        "msg",
        "args",
        "created",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "thread",
        "threadName",
        "exc_info",
        "exc_text",
        "stack_info",
        "getMessage",
        "extra",
        "taskName",
        "asctime",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Render the log record as text with a stable context suffix.

        Args:
            record: Log record to serialize.

        Returns:
            Formatted log line with optional sorted context suffix.
        """
        base_msg = super().format(record)

        context_parts = []
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in self._ignored:
                continue
            if value is not None and not callable(value):
                context_parts.append("{0}={1}".format(key, value))

        if context_parts:
            context_parts.sort()
            return "{0} [{1}]".format(base_msg, ", ".join(context_parts))

        return base_msg


def build_text_formatter() -> TextFormatterWithContext:
    """Build a TextFormatterWithContext instance with the default format.

    Returns:
        A new TextFormatterWithContext configured with the default format string.
    """
    return TextFormatterWithContext(_DEFAULT_FMT)


__all__: List[str] = ["TextFormatterWithContext", "build_text_formatter"]
