"""Builder for a plain StreamHandler(sys.stdout)."""

from __future__ import annotations

import logging
import sys
from typing import List


def build_stdout_handler() -> logging.StreamHandler:
    """Build a stdout stream handler without additional wiring.

    Returns:
        StreamHandler configured to write to sys.stdout.
    """
    return logging.StreamHandler(sys.stdout)


__all__: List[str] = ["build_stdout_handler"]
