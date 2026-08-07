"""JSON formatter for observability log output."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List


class JSONFormatter(logging.Formatter):
    """JSON formatter that captures non-standard LogRecord attributes as context."""

    _standard_attrs = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Render the log record as a JSON string.

        Args:
            record: Log record to serialize.

        Returns:
            JSON string with base fields, optional context, and optional exception.
        """
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }

        context = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self._standard_attrs and not key.startswith("_")
        }
        if context:
            log_data["context"] = context

        exc_text = record.exc_text
        if not exc_text and record.exc_info:
            exc_text = self.formatException(record.exc_info)
        if exc_text:
            log_data["exception"] = exc_text

        return json.dumps(log_data)


def build_json_formatter() -> JSONFormatter:
    """Build a JSONFormatter instance.

    Returns:
        A new JSONFormatter ready for log serialization.
    """
    return JSONFormatter()


__all__: List[str] = ["JSONFormatter", "build_json_formatter"]
