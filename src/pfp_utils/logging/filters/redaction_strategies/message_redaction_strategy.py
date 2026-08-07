"""Strategy: bake record.msg via getMessage() and sanitize the result."""

from __future__ import annotations

import logging

from pfp_utils.sanitization import sanitize_text


class MessageRedactionStrategy:
    """Sanitize the rendered log message and clear deferred formatting arguments.

    After ``apply()`` the record keeps only the sanitized rendered message in
    ``record.msg`` and clears ``record.args`` so downstream formatters do not
    re-run interpolation against raw secret-bearing values.

    Returns:
        A stateless strategy object for mutating ``logging.LogRecord`` messages.
    """

    def apply(self, record: logging.LogRecord) -> None:
        """Render, sanitize, and freeze the message portion of a log record.

        Args:
            record: LogRecord instance whose ``msg`` and ``args`` fields will be
                normalized in-place.

        Returns:
            None.
        """
        record.msg = sanitize_text(record.getMessage())
        record.args = None


def build_message_redaction_strategy() -> MessageRedactionStrategy:
    """Build a message-redaction strategy instance.

    Returns:
        New ``MessageRedactionStrategy`` instance.
    """
    return MessageRedactionStrategy()


__all__ = ["MessageRedactionStrategy", "build_message_redaction_strategy"]
