"""Stage-level profiling helpers for observability."""

import functools
import logging
import time
from typing import Any, Callable, Dict, Optional

from pfp_utils.logging.log_context import get_context
from pfp_utils.telemetry.telemetry_protocol import TelemetryHandler


def profile_stage(stage_name: str) -> Callable:
    """Decorator to measure function execution time and report it via telemetry.

    The decorated function MUST accept a 'telemetry' keyword argument of type
    Optional[TelemetryHandler] and a 'log_pipeline' keyword argument.

    Args:
        stage_name: Name of the processing stage (e.g., "normalization", "validation").

    Returns:
        Callable: Decorator for stage profiling.
    """

    def decorator(func: Callable) -> Callable:
        """Wrap a callable with stage-duration measurement logic.

        Args:
            func: Callable instrumented with profiling and telemetry reporting.

        Returns:
            Callable: Wrapped callable preserving the original signature contract.
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Execute the wrapped callable and report elapsed stage duration.

            Args:
                *args: Positional arguments forwarded to the wrapped callable.
                **kwargs: Keyword arguments forwarded to the wrapped callable.

            Returns:
                Result returned by the wrapped callable.
            """

            telemetry: Optional[TelemetryHandler] = kwargs.get("telemetry")
            if "log_pipeline" not in kwargs:
                raise TypeError(
                    "profile_stage requires 'log_pipeline' keyword argument"
                )
            log_pipeline = kwargs["log_pipeline"]

            start_time = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start_time

                context = get_context()
                labels: Dict[str, str] = {}
                for key in ["target", "artifact_profile", "policy_name"]:
                    if key in context:
                        labels[key] = str(context[key])

                log_pipeline.log_process(
                    logging.DEBUG,
                    __name__,
                    "Stage '%s' finished (duration=%.6fs, labels=%s)",
                    stage_name,
                    duration,
                    labels,
                )

                if telemetry:
                    telemetry.observe_duration(stage_name, duration, labels)

        return wrapper

    return decorator


__all__ = [
    "profile_stage",
]
