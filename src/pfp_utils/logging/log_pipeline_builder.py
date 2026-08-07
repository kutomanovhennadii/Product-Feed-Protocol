"""Init-phase builder that assembles a LogPipeline from public builders."""

from __future__ import annotations

import logging
from typing import Any, Callable, Mapping

from pfp_utils.logging.filters.context_filter import build_context_filter
from pfp_utils.logging.filters.flood_control_filter import build_flood_control_filter
from pfp_utils.logging.filters.secret_redaction_filter import (
    build_secret_redaction_filter,
)
from pfp_utils.logging.formatters.json_formatter import build_json_formatter
from pfp_utils.logging.formatters.text_formatter import build_text_formatter
from pfp_utils.logging.handlers.stdout_handler import build_stdout_handler
from pfp_utils.logging.log_pipeline import LogPipeline
from pfp_utils.logging.log_registry import PythonLoggingRegistry

_FORMATTER_BUILDERS: Mapping[str, Callable[[], logging.Formatter]] = {
    "JSON": build_json_formatter,
    "TEXT": build_text_formatter,
}


def build_log_pipeline(
    level: str,
    format_type: str,
    flood_control_config: Mapping[str, Any],
) -> LogPipeline:
    """Assemble a LogPipeline from public logging builders.

    Args:
        level: Textual logging threshold stored on the assembled pipeline.
        format_type: Output format selector. Supported values are JSON and TEXT.
        flood_control_config: Configuration passed to the flood-control builder.

    Returns:
        Installed LogPipeline composed from the configured formatter, filters,
        handler, and a production logging registry.

    Raises:
        ValueError: If format_type is not one of the supported formatter keys.
    """
    key = format_type.upper()
    if key not in _FORMATTER_BUILDERS:
        raise ValueError(f"Invalid log format: {format_type}")

    formatter = _FORMATTER_BUILDERS[key]()
    filters = (
        build_context_filter(),
        build_secret_redaction_filter(),
        build_flood_control_filter(flood_control_config),
    )
    handler = build_stdout_handler()
    handler.setFormatter(formatter)
    for log_filter in filters:
        handler.addFilter(log_filter)

    pipeline = LogPipeline(
        level=level,
        format_type=key,
        filters=filters,
        formatter=formatter,
        handler=handler,
        registry=PythonLoggingRegistry(),
    )
    pipeline.install()
    return pipeline


__all__ = ["build_log_pipeline"]
