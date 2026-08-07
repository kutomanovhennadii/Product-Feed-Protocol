"""Strategy: force-format exc_info into exc_text and sanitize."""

from __future__ import annotations

import logging

from pfp_utils.sanitization import sanitize_text

_STATIC_FORMATTER = logging.Formatter()


class ExcInfoRedactionStrategy:
    """Format ``exc_info`` eagerly into sanitized ``exc_text``.

    On ``apply()``, when ``record.exc_info`` carries an exception triple, the
    strategy formats the traceback immediately, sanitizes the resulting
    multi-line text, stores it in ``record.exc_text``, and clears
    ``record.exc_info``. If ``record.exc_info`` is absent, the strategy is a
    no-op and leaves any existing ``record.exc_text`` untouched.

    Returns:
        A stateless strategy object for mutating traceback-related LogRecord
        fields.
    """

    def apply(self, record: logging.LogRecord) -> None:
        """Sanitize exception data carried via ``record.exc_info``.

        Args:
            record: LogRecord instance whose ``exc_info`` may be formatted into
                sanitized ``exc_text`` in-place.

        Returns:
            None.
        """
        if not record.exc_info:
            return
        formatted = _STATIC_FORMATTER.formatException(record.exc_info)
        record.exc_text = sanitize_text(formatted)
        record.exc_info = None


def build_exc_info_redaction_strategy() -> ExcInfoRedactionStrategy:
    """Build an ``ExcInfoRedactionStrategy`` instance.

    Returns:
        New ``ExcInfoRedactionStrategy`` instance.
    """
    return ExcInfoRedactionStrategy()


__all__ = ["ExcInfoRedactionStrategy", "build_exc_info_redaction_strategy"]
