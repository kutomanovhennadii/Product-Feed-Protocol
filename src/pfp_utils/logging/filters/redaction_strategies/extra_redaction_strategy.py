"""Strategy: sanitize non-standard string attributes on LogRecord."""

from __future__ import annotations

import logging
from typing import FrozenSet

from pfp_utils.sanitization import sanitize_text

# Blacklist: standard LogRecord/Formatter attributes that must never be
# sanitized. Synchronized with JSONFormatter._standard_attrs and
# TextFormatterWithContext._ignored. Adding a new entry to either of
# those must be reflected here (and vice versa).
_STANDARD_ATTRS: FrozenSet[str] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "extra",
        "filename",
        "funcName",
        "getMessage",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class ExtraRedactionStrategy:
    """Sanitize every non-standard string attribute on the record.

    The strategy iterates over ``record.__dict__``, skips standard LogRecord
    attributes and private underscore-prefixed keys, and sanitizes only
    string-valued custom attributes. Non-string values are left unchanged.

    Returns:
        A stateless strategy object for mutating custom LogRecord context.
    """

    def apply(self, record: logging.LogRecord) -> None:
        """Sanitize eligible custom string attributes on a log record.

        Args:
            record: LogRecord instance whose custom string attributes may be
                sanitized in-place.

        Returns:
            None.
        """
        for key, value in list(record.__dict__.items()):
            if key in _STANDARD_ATTRS or key.startswith("_"):
                continue
            if isinstance(value, str):
                setattr(record, key, sanitize_text(value))


def build_extra_redaction_strategy() -> ExtraRedactionStrategy:
    """Build an ``ExtraRedactionStrategy`` instance.

    Returns:
        New ``ExtraRedactionStrategy`` instance.
    """
    return ExtraRedactionStrategy()


__all__ = ["ExtraRedactionStrategy", "build_extra_redaction_strategy"]
