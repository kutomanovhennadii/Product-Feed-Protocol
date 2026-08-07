"""Telemetry handler factory for observability."""

import importlib
import logging
from typing import Any, Tuple, cast

from pfp_utils.logging import LogPipeline
from pfp_utils.telemetry.telemetry_handlers import (
    ConsoleTelemetryHandler,
    NoOpTelemetryHandler,
)
from pfp_utils.telemetry.telemetry_protocol import TelemetryHandler


def create_telemetry_handler(
    config: Any,
    *,
    log_pipeline: LogPipeline,
) -> TelemetryHandler:
    """Create a telemetry handler based on configuration.

    Args:
        config: TelemetryConfig or any object with 'enabled' and 'handler' attributes.

    Returns:
        TelemetryHandler: Configured handler.
    """

    if not getattr(config, "enabled", True):
        return NoOpTelemetryHandler()

    handler_value = getattr(config, "handler", "noop")

    has_observe = hasattr(handler_value, "observe_duration") and callable(
        getattr(handler_value, "observe_duration", None)
    )
    has_inc = hasattr(handler_value, "inc") and callable(
        getattr(handler_value, "inc", None)
    )
    if has_observe and has_inc:
        return cast(TelemetryHandler, handler_value)

    if not isinstance(handler_value, str):
        raise ValueError("Telemetry handler must be a string or handler instance")

    handler_type = handler_value.strip().lower()

    if handler_type == "console":
        return ConsoleTelemetryHandler(log_pipeline=log_pipeline)

    if handler_type in {"noop", "none", "null", "disabled"}:
        return NoOpTelemetryHandler()

    if ":" in handler_value or "." in handler_value:
        try:
            module_path, attr_name = _split_handler_path(handler_value)
            handler_cls = getattr(importlib.import_module(module_path), attr_name)
            handler = handler_cls()
            has_observe = hasattr(handler, "observe_duration") and callable(
                getattr(handler, "observe_duration", None)
            )
            has_inc = hasattr(handler, "inc") and callable(
                getattr(handler, "inc", None)
            )
            if not (has_observe and has_inc):
                _log_warning(
                    log_pipeline,
                    "Telemetry handler '%s' missing required methods; falling back to NoOp",
                    handler_value,
                )
                return NoOpTelemetryHandler()

            return cast(TelemetryHandler, handler)
        except Exception as exc:  # pragma: no cover
            _log_warning(
                log_pipeline,
                "Telemetry handler load failed; falling back to NoOp: %s",
                exc,
                exc_info=True,
            )
            return NoOpTelemetryHandler()

    _log_warning(
        log_pipeline, "Unknown telemetry handler '%s'; using NoOp.", handler_value
    )
    return NoOpTelemetryHandler()


def _log_warning(
    log_pipeline: LogPipeline,
    message: str,
    *args: Any,
    exc_info: Any = None,
) -> None:
    """Emit telemetry-factory warnings when a manifest-owned pipeline is available."""
    log_pipeline.log_process(
        logging.WARNING,
        __name__,
        message,
        *args,
        exc_info=exc_info,
    )


def _split_handler_path(path: str) -> Tuple[str, str]:
    """Split a handler path into module and attribute.

    Accepts "module:Class" or "module.Class" formats.
    """

    if ":" in path:
        module_path, attr_name = path.split(":", 1)
    else:
        module_path, attr_name = path.rsplit(".", 1)
    module_path = module_path.strip()
    attr_name = attr_name.strip()
    if not module_path or not attr_name:
        raise ValueError("Invalid telemetry handler path")
    return module_path, attr_name


__all__ = [
    "create_telemetry_handler",
]
