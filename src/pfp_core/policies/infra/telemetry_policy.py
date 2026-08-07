"""Telemetry policy implementation."""

from dataclasses import dataclass
from typing import Any, Mapping

from pfp_core.policies.utils.policy_utils import _require_mapping, _validate_keys
from pfp_utils.logging.log_pipeline import LogPipeline
from pfp_utils.telemetry import TelemetryHandler


@dataclass(frozen=True)
class TelemetryConfig:
    provider: str = "none"
    handler: str = "noop"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TelemetryConfig":
        data = _require_mapping(data, "infrastructure.telemetry")
        _validate_keys(data, {"provider"}, "infrastructure.telemetry")

        provider = data.get("provider", "none")
        if not isinstance(provider, str):
            raise ValueError("infrastructure.telemetry.provider must be a string")

        return cls(provider=provider, handler=provider)


class TelemetryPolicy:
    def __init__(
        self,
        config: TelemetryConfig,
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        from pfp_core.policies.infra import logging_policy

        self._handler = logging_policy.create_telemetry_handler(
            config,
            log_pipeline=log_pipeline,
        )

    @property
    def handler(self) -> TelemetryHandler:
        return self._handler
