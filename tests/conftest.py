import logging
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

_LOG_PIPELINE_HANDLER_MARKER = "_pfp_log_pipeline_installed"


@pytest.fixture(autouse=True)
def _reset_log_pipeline_handlers():
    """Remove log pipeline handlers installed by build_observability_manifest after each test."""
    yield
    root_logger = logging.getLogger()
    to_remove = [
        h
        for h in list(root_logger.handlers)
        if getattr(h, _LOG_PIPELINE_HANDLER_MARKER, False)
    ]
    for h in to_remove:
        root_logger.removeHandler(h)
