"""Filter that composes RedactionStrategy instances to sanitize LogRecord."""

from __future__ import annotations

import logging
from typing import Tuple

from pfp_utils.logging.filters.redaction_strategies.exc_info_redaction_strategy import (
    build_exc_info_redaction_strategy,
)
from pfp_utils.logging.filters.redaction_strategies.extra_redaction_strategy import (
    build_extra_redaction_strategy,
)
from pfp_utils.logging.filters.redaction_strategies.message_redaction_strategy import (
    build_message_redaction_strategy,
)
from pfp_utils.logging.filters.redaction_strategies.redaction_strategy import (
    RedactionStrategy,
)


class SecretRedactionFilter(logging.Filter):
    """Apply a tuple of redaction strategies to every log record.

    Returns:
        A logging filter that delegates sanitization to composed strategies.
    """

    def __init__(self, strategies: Tuple[RedactionStrategy, ...]) -> None:
        """Store the strategy tuple used for record sanitization.

        Args:
            strategies: Ordered redaction strategies applied to each record.

        Returns:
            None.
        """
        super().__init__()
        self._strategies = strategies

    def filter(self, record: logging.LogRecord) -> bool:
        """Apply every strategy to the record and keep the record flowing.

        Args:
            record: Log record that will be sanitized in-place.

        Returns:
            True so the logging pipeline keeps processing the record.
        """
        for strategy in self._strategies:
            strategy.apply(record)
        return True


def build_secret_redaction_filter() -> SecretRedactionFilter:
    """Build a SecretRedactionFilter with the default strategy pipeline.

    Returns:
        A new SecretRedactionFilter configured with message, exception, and
        extra-attribute redaction strategies.
    """
    return SecretRedactionFilter(
        strategies=(
            build_message_redaction_strategy(),
            build_exc_info_redaction_strategy(),
            build_extra_redaction_strategy(),
        )
    )


__all__ = ["SecretRedactionFilter", "build_secret_redaction_filter"]
