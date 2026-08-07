"""Infrastructure policies: Logging, Telemetry, Fault Isolation."""

from dataclasses import dataclass
from typing import Any, List, Mapping

from pfp_core.policies.infra.fault_isolation_policy import FaultIsolationPolicy
from pfp_core.policies.infra.telemetry_policy import TelemetryPolicy
from pfp_core.policies.utils.policy_utils import _require_mapping, _validate_keys
from pfp_utils.logging import build_log_pipeline, get_context
from pfp_utils.telemetry import create_telemetry_handler

__all__: List[str] = [
    "FaultIsolationPolicy",
    "LoggingConfig",
    "LoggingPolicy",
    "TelemetryPolicy",
    "create_telemetry_handler",
    "get_context",
]


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    format: str = "json"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LoggingConfig":
        data = _require_mapping(data, "infrastructure.logging")
        _validate_keys(data, {"level", "format"}, "infrastructure.logging")

        level = data.get("level", "INFO")
        if not isinstance(level, str):
            raise ValueError("infrastructure.logging.level must be a string")

        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in valid_levels:
            raise ValueError(f"Invalid log level '{level}'")

        format_ = data.get("format", "json")
        if not isinstance(format_, str):
            raise ValueError("infrastructure.logging.format must be a string")

        valid_formats = {"json", "text"}
        if format_.lower() not in valid_formats:
            raise ValueError(f"Invalid log format '{format_}'")

        return cls(level=level, format=format_)


class LoggingPolicy:
    def __init__(self, config: LoggingConfig):
        self._config = config

    def apply(self) -> None:
        build_log_pipeline(
            self._config.level, self._config.format.upper(), {}
        ).install()
