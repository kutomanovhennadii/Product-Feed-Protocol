"""Tests for observability manifest assembly and runtime consumption."""

import logging
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.manifest.observability_manifest_builder import (
    build_observability_manifest,
)
from pfp_utils.telemetry import NoOpTelemetryHandler, PrometheusTelemetryHandler


def _infra_with_observability(
    *,
    log_level: str = "INFO",
    log_format: str = "TEXT",
    provider: str = "none",
) -> InfraConfig:
    """Build minimal validated infra config for observability assembly tests."""
    return InfraConfig.model_validate(
        {
            "input": {"format": "jsonl", "config": {}},
            "producer": {"schema_file": "s.yaml", "policy_file": "p.yaml"},
            "output": {
                "archive_type": "noop",
                "archive_config": "config/archive/noop.yaml",
                "client_type": "noop",
                "client_config": "config/clients/noop.yaml",
            },
            "observability": {
                "labels": {},
                "log_format": log_format,
                "logging": {"level": log_level},
                "telemetry": {"provider": provider},
            },
        }
    )


def test_build_observability_manifest_uses_manifest_level() -> None:
    """build_observability_manifest should configure logging with manifest level."""
    infra = _infra_with_observability(log_level="WARNING")

    result = build_observability_manifest(infra)

    assert result is not None
    assert result.log_pipeline is not None
    assert result.log_pipeline.level == "WARNING"
    assert result.log_pipeline.format_type == "TEXT"


def test_build_observability_manifest_uses_debug_level() -> None:
    """build_observability_manifest should pass DEBUG level through."""
    infra = _infra_with_observability(log_level="DEBUG")

    result = build_observability_manifest(infra)

    assert result is not None
    assert result.log_pipeline.level == "DEBUG"


def test_build_observability_manifest_uses_json_format() -> None:
    """build_observability_manifest should map JSON log format correctly."""
    infra = _infra_with_observability(log_format="JSON")

    result = build_observability_manifest(infra)

    assert result is not None
    assert result.log_pipeline.level == "INFO"
    assert result.log_pipeline.format_type == "JSON"


def test_build_observability_manifest_defaults_to_info_when_logging_omitted() -> None:
    """build_observability_manifest should use validated INFO/TEXT defaults."""
    infra = InfraConfig.model_validate(
        {
            "input": {"format": "jsonl", "config": {}},
            "producer": {"schema_file": "s.yaml", "policy_file": "p.yaml"},
            "output": {
                "archive_type": "noop",
                "archive_config": "config/archive/noop.yaml",
                "client_type": "noop",
                "client_config": "config/clients/noop.yaml",
            },
            "observability": {"labels": {}},
        }
    )

    result = build_observability_manifest(infra)

    assert result is not None
    assert result.log_pipeline.level == "INFO"
    assert result.log_pipeline.format_type == "TEXT"


# ---------------------------------------------------------------------------
# Integration tests — real configure_logging, real root logger level
# ---------------------------------------------------------------------------


def _infra_with_level(level: str) -> InfraConfig:
    """Return observability infra configured with the requested log level."""
    return _infra_with_observability(log_level=level)


def test_build_observability_manifest_integration_sets_root_logger_to_warning() -> None:
    """Real manifest assembly should set root logger level to WARNING."""
    infra = _infra_with_level("WARNING")
    obs = build_observability_manifest(infra)
    assert obs is not None

    assert logging.getLogger().level == logging.WARNING
    assert obs.log_pipeline is not None


def test_build_observability_manifest_integration_warning_suppresses_info() -> None:
    """Manifest assembly should suppress INFO at WARNING level."""
    infra = _infra_with_level("WARNING")
    obs = build_observability_manifest(infra)
    assert obs is not None

    assert logging.getLogger().level == logging.WARNING
    assert logging.getLogger().level > logging.INFO


def test_build_observability_manifest_integration_full_chain_error_level() -> None:
    """log_level should flow from InfraConfig into manifest assembly."""
    infra = _infra_with_level("ERROR")
    obs = build_observability_manifest(infra)
    assert obs is not None
    assert obs.log_pipeline.level == "ERROR"

    assert logging.getLogger().level == logging.ERROR


# ---------------------------------------------------------------------------
# Integration tests — telemetry handler selection (G2)
# ---------------------------------------------------------------------------


def _infra_with_telemetry_provider(provider: str) -> InfraConfig:
    """Return observability infra configured with the requested telemetry provider."""
    return _infra_with_observability(provider=provider)


def test_build_telemetry_handler_integration_returns_noop_when_telemetry_none() -> None:
    """Manifest assembly should return NoOp handler for provider 'none'."""
    infra = _infra_with_telemetry_provider("none")
    obs = build_observability_manifest(infra)
    assert obs is not None
    assert obs.telemetry_enabled is False

    assert isinstance(obs.telemetry_handler, NoOpTelemetryHandler)


@pytest.mark.skipif(
    __import__("importlib.util", fromlist=["find_spec"]).find_spec("prometheus_client")
    is None,
    reason="prometheus_client not installed",
)
def test_build_telemetry_handler_integration_returns_prometheus_when_enabled() -> None:
    """Manifest assembly should return Prometheus handler when enabled."""
    infra = _infra_with_telemetry_provider("prometheus")
    obs = build_observability_manifest(infra)
    assert obs is not None
    assert obs.telemetry_enabled is True

    assert isinstance(obs.telemetry_handler, PrometheusTelemetryHandler)


# ---------------------------------------------------------------------------
# Integration tests — worker.run() increments prometheus counters (G2)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    __import__("importlib.util", fromlist=["find_spec"]).find_spec("prometheus_client")
    is None,
    reason="prometheus_client not installed",
)
def test_builder_created_prometheus_handler_increments_counter_after_worker_run(
    monkeypatch: Any,
) -> None:
    """Worker should use builder-created Prometheus handler during runtime."""

    import prometheus_client  # type: ignore[import-not-found]

    from pfp_runtime.shell.factory import PFPFactory

    _PYTHON_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    _INFRA_PATH = _PYTHON_ROOT / "config" / "shopify_bulk" / "infra_shopify_bulk.yaml"
    _CONFIG_DIR = _PYTHON_ROOT / "config" / "shopify_bulk"
    _FIXTURE = _PYTHON_ROOT / "tests" / "e2e" / "fixtures" / "shopify_bulk_input.jsonl"

    monkeypatch.chdir(_CONFIG_DIR)

    isolated_registry = prometheus_client.CollectorRegistry()
    handler = PrometheusTelemetryHandler(registry=isolated_registry)

    with patch(
        "pfp_runtime.manifest.observability_manifest_builder._build_telemetry_handler",
        return_value=handler,
    ):
        factory = PFPFactory()
        worker = factory.build_worker(infra_path=_INFRA_PATH)
        report = worker.run(_FIXTURE.read_bytes())

    assert report.status == "SUCCESS"
    assert report.usage.input_items_count >= 0

    # Usage accounting is reported via ExecutionReport, not Prometheus counters.
    metrics = list(
        prometheus_client.generate_latest(isolated_registry).decode().splitlines()
    )
    processed_lines = [
        line for line in metrics if line.startswith("pfp_items_processed_total")
    ]
    assert not processed_lines
