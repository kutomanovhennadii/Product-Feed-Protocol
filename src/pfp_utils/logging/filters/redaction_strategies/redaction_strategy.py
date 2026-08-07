"""Protocol for LogRecord field-level redaction strategies."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable


@runtime_checkable
class RedactionStrategy(Protocol):
    """Describe a field-level redaction strategy for ``logging.LogRecord`` objects.

    Implementations mutate a selected region of the supplied record in-place and
    must be safe to invoke repeatedly on the same object.

    Returns:
        A runtime-checkable structural contract for redaction strategy objects.
    """

    def apply(self, record: logging.LogRecord) -> None:
        """Mutate record fields to remove secret-like patterns.

        Args:
            record: LogRecord instance whose fields may be redacted in-place.

        Returns:
            None.

        Raises:
            None. Implementations must skip malformed or missing fields safely.
        """
        ...


__all__ = ["RedactionStrategy"]
