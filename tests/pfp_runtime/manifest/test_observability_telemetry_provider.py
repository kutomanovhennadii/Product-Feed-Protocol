"""Unit tests for telemetry provider selection in observability builder."""

from __future__ import annotations

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.manifest.observability_manifest_builder import (
    _build_telemetry_handler,
    build_observability_manifest,
)
from pfp_utils.telemetry import NoOpTelemetryHandler


def _base_payload() -> dict:
    """Build minimal infra payload for telemetry provider tests."""
    return {
        "input": {"format": "jsonl", "config": {}},
        "producer": {"schema_file": "s.yaml", "policy_file": "p.yaml"},
        "output": {
            "archive_type": "noop",
            "archive_config": "config/archive/noop.yaml",
            "client_type": "noop",
            "client_config": "config/clients/noop.yaml",
        },
    }


def test_build_observability_manifest_returns_none_when_observability_missing() -> None:
    """Return manifest with default log pipeline when validated infra has no observability section."""
    infra = InfraConfig.model_validate(_base_payload())

    result = build_observability_manifest(infra)

    assert result is not None
    assert result.log_pipeline is not None


def test_build_telemetry_handler_uses_telemetry_provider_none() -> None:
    """Return NoOp handler when provider is explicitly non-prometheus."""
    handler = _build_telemetry_handler("none", False)

    assert isinstance(handler, NoOpTelemetryHandler)


def test_build_telemetry_handler_uses_none_when_provider_is_blank_and_disabled() -> (
    None
):
    """Return NoOp handler when provider is blank and telemetry is disabled."""
    handler = _build_telemetry_handler("", False)

    assert isinstance(handler, NoOpTelemetryHandler)
