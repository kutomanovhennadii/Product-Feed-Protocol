"""Logging context utilities for observability.

This module provides thread-local context storage and a context manager for
enriching log records with stable, low-cardinality fields.
"""

import threading
from contextlib import contextmanager
from typing import Any, Dict, Generator

_log_context = threading.local()


def _get_context() -> Dict[str, Any]:
    """Retrieve current context from thread-local storage.

    Returns:
        Dict[str, Any]: Current logging context dictionary.
    """
    if not hasattr(_log_context, "data"):
        _log_context.data = {}
    return _log_context.data


def get_context() -> Dict[str, Any]:
    """Public accessor for current logging context.

    Returns:
        Dict[str, Any]: Current logging context dictionary.
    """

    return _get_context()


@contextmanager
def LogContext(**kwargs: Any) -> Generator[None, None, None]:
    """Context manager to add fields to the logging context.

    Args:
        **kwargs: Arbitrary key-value pairs to add to logging context.

    Yields:
        None

    Example:
        with LogContext(item_ref="item_123", stage="validation"):
            logger.info("Processing item")
    """

    context = _get_context()
    old_context = context.copy()
    context.update(kwargs)
    try:
        yield
    finally:
        _log_context.data = old_context


__all__ = [
    "LogContext",
    "_get_context",
    "_log_context",
    "get_context",
]
