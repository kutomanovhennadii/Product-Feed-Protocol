"""Filter that injects thread-local LogContext into each LogRecord."""

from __future__ import annotations

import logging
from typing import List

from pfp_utils.logging.log_context import get_context


class ContextFilter(logging.Filter):
    """Inject current thread-local context into each LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Copy the active thread-local context onto the log record.

        Args:
            record: Log record that will be enriched with context attributes.

        Returns:
            True so the logging pipeline keeps processing the record.
        """
        context = get_context()
        for key, value in context.items():
            setattr(record, key, value)
        return True


def build_context_filter() -> ContextFilter:
    """Build a ContextFilter instance.

    Returns:
        A new ContextFilter ready to inject thread-local context values.
    """
    return ContextFilter()


__all__: List[str] = ["ContextFilter", "build_context_filter"]
