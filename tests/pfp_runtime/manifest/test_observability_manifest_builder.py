"""Mirror unit tests for manifest.observability_manifest_builder."""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any

import pytest

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.config.infra_normalizer import normalize_infra_paths
from pfp_runtime.manifest import observability_manifest_builder as builder_module
from pfp_runtime.manifest.observability_manifest_builder import (
    build_observability_manifest,
)
from pfp_runtime.manifest.pipeline_manifest import ObservabilityManifest
from pfp_utils.diagnostics import FeedUsageCollector
from pfp_utils.logging import LogPipeline
from pfp_utils.logging.log_registry import LoggingRegistry
from pfp_utils.telemetry import NoOpTelemetryHandler


class _SentinelTelemetryHandler:
    """Minimal telemetry handler used to assert builder wiring.

    Returns:
        _SentinelTelemetryHandler: In-memory telemetry stub for tests.
    """

    def observe_duration(
        self,
        name: str,
        value: float,
        labels: Any = None,
    ) -> None:
        """Accept duration telemetry calls from the builder contract.

        Args:
            name: Telemetry metric name.
            value: Observed duration value.
            labels: Optional metric labels.

        Returns:
            None.
        """
        del name, value, labels

    def inc(
        self,
        name: str,
        value: float = 1.0,
        labels: Any = None,
    ) -> None:
        """Accept counter telemetry calls from the builder contract.

        Args:
            name: Telemetry metric name.
            value: Counter increment value.
            labels: Optional metric labels.

        Returns:
            None.
        """
        del name, value, labels


class _SentinelRegistry(LoggingRegistry):
    """Minimal registry used to construct a non-installing LogPipeline for tests.

    Returns:
        _SentinelRegistry: Logging registry stub that avoids global mutations.
    """

    def __init__(self) -> None:
        """Initialize the sentinel attached-state flag.

        Returns:
            None.
        """
        self._attached = False

    def clear_root_handlers(self) -> None:
        """Satisfy registry contract without mutating global logging state.

        Returns:
            None.
        """

    def add_root_handler(self, handler: logging.Handler) -> None:
        """Satisfy registry contract without mutating global logging state.

        Args:
            handler: Handler ignored by this sentinel registry.

        Returns:
            None.
        """
        del handler

    def set_root_level(self, level: int) -> None:
        """Satisfy registry contract without mutating global logging state.

        Args:
            level: Level ignored by this sentinel registry.

        Returns:
            None.
        """
        del level

    def mark_attached(self) -> None:
        """Mark the sentinel registry as attached.

        Returns:
            None.
        """
        self._attached = True

    def is_attached(self) -> bool:
        """Report whether the sentinel registry has been marked attached.

        Returns:
            True when mark_attached() was called.
        """
        return self._attached


def _sentinel_log_pipeline(
    level: str = "INFO",
    format_type: str = "TEXT",
) -> LogPipeline:
    """Build a non-installing LogPipeline instance for builder monkeypatch tests.

    Args:
        level: Pipeline level stored on the sentinel instance.
        format_type: Pipeline format stored on the sentinel instance.

    Returns:
        LogPipeline: Sentinel pipeline compatible with ObservabilityManifest.
    """
    return LogPipeline(
        level=level,
        format_type=format_type,
        filters=(),
        formatter=logging.Formatter("%(message)s"),
        handler=logging.NullHandler(),
        registry=_SentinelRegistry(),
    )


def _base_payload() -> dict:
    """Build minimal infra payload required for observability tests.

    Returns:
        Minimal validated payload accepted by InfraConfig.model_validate.
    """
    return {
        "input": {
            "format": "csv",
            "config": {
                "connector_mapping": "./mapping.yaml",
            },
        },
        "output": {
            "archive_type": "noop",
            "archive_config": "./archive/noop.yaml",
            "client_type": "noop",
            "client_config": "./clients/noop.yaml",
        },
        "producer": {
            "schema_file": "./schemas/product.yaml",
            "policy_file": "./config/policies.yaml",
        },
    }


@pytest.fixture(autouse=True)
def restore_root_logger() -> Generator[None, None, None]:
    """Restore root logger handlers and level after each test.

    Yields:
        None while the test executes.
    """
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level

    root.handlers[:] = []

    try:
        yield
    finally:
        root.handlers[:] = []
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)


def test_build_observability_manifest_returns_defaults_when_section_missing() -> None:
    """Build default observability manifest when infra has no section."""
    infra = InfraConfig.model_validate(_base_payload())

    result = build_observability_manifest(infra)

    assert isinstance(result, ObservabilityManifest)
    assert isinstance(result.log_pipeline, LogPipeline)
    assert result.log_pipeline.level == "INFO"
    assert result.log_pipeline.format_type == "TEXT"
    assert result.log_pipeline.registry.is_attached() is True
    assert isinstance(result.telemetry_handler, NoOpTelemetryHandler)
    assert isinstance(result.usage_collector, FeedUsageCollector)
    assert result.telemetry_enabled is False
    assert result.telemetry_provider == "none"
    assert result.labels == {}


def test_build_observability_manifest_builds_manifest_when_section_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build ready-to-use observability instruments when section is present."""
    payload = _base_payload()
    payload["observability"] = {
        "labels": {"pipeline": "test"},
        "log_format": "json",
        "logging": {"level": "warning"},
        "telemetry": {"provider": "prometheus"},
    }
    infra = normalize_infra_paths(
        InfraConfig.model_validate(payload),
        infra_path="./infra.yaml",
    )
    sentinel_handler = _SentinelTelemetryHandler()

    monkeypatch.setattr(
        builder_module,
        "PrometheusTelemetryHandler",
        lambda: sentinel_handler,
    )

    result = build_observability_manifest(infra)

    assert isinstance(result, ObservabilityManifest)
    assert isinstance(result.log_pipeline, LogPipeline)
    assert result.log_pipeline.level == "WARNING"
    assert result.log_pipeline.format_type == "JSON"
    assert result.log_pipeline.registry.is_attached() is True
    assert result.telemetry_handler is sentinel_handler
    assert isinstance(result.usage_collector, FeedUsageCollector)
    assert result.telemetry_enabled is True
    assert result.telemetry_provider == "prometheus"
    assert result.labels == {"pipeline": "test"}


def test_build_observability_manifest_passes_full_reference_config_to_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass full canonical flood-control config to build_log_pipeline without loss."""
    payload = _base_payload()
    payload["observability"] = {
        "labels": {"pipeline": "test"},
        "log_format": "json",
        "logging": {
            "level": "warning",
            "flood_control_config": {
                "enabled": True,
                "mode": "deduplicate",
                "context_keys": ["item_ref", "run_id"],
                "suppressed_levels": ["INFO", "WARNING"],
                "force_log_attr": "force_log",
                "key_fields": ["name", "levelno", "msg"],
                "window_seconds": 12.5,
                "max_events_per_window": 2,
                "emit_summary": True,
                "summary_level": "WARNING",
                "summary_interval_seconds": 60.0,
                "max_cache_size": 2048,
            },
        },
    }
    infra = normalize_infra_paths(
        InfraConfig.model_validate(payload),
        infra_path="./infra.yaml",
    )
    captured: dict[str, Any] = {}

    def _fake_build_log_pipeline(
        level: str,
        format_type: str,
        flood_control_config: dict[str, Any],
    ) -> LogPipeline:
        captured["level"] = level
        captured["format_type"] = format_type
        captured["flood_control_config"] = flood_control_config
        return _sentinel_log_pipeline(level, format_type)

    monkeypatch.setattr(builder_module, "build_log_pipeline", _fake_build_log_pipeline)

    result = build_observability_manifest(infra)

    assert isinstance(result, ObservabilityManifest)
    assert captured["level"] == "WARNING"
    assert captured["format_type"] == "JSON"
    assert captured["flood_control_config"] == {
        "enabled": True,
        "mode": "deduplicate",
        "context_keys": ["item_ref", "run_id"],
        "suppressed_levels": ["INFO", "WARNING"],
        "force_log_attr": "force_log",
        "key_fields": ["name", "levelno", "msg"],
        "window_seconds": 12.5,
        "max_events_per_window": 2,
        "emit_summary": True,
        "summary_level": "WARNING",
        "summary_interval_seconds": 60.0,
        "max_cache_size": 2048,
    }


def test_build_observability_manifest_passes_materialized_defaults_for_minimal_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass canonical defaults to build_log_pipeline for minimal baseline config."""
    payload = _base_payload()
    payload["observability"] = {
        "labels": {"pipeline": "baseline"},
        "logging": {
            "level": "info",
            "flood_control_config": {},
        },
    }
    infra = normalize_infra_paths(
        InfraConfig.model_validate(payload),
        infra_path="./infra.yaml",
    )
    captured: dict[str, Any] = {}

    def _fake_build_log_pipeline(
        level: str,
        format_type: str,
        flood_control_config: dict[str, Any],
    ) -> LogPipeline:
        captured["level"] = level
        captured["format_type"] = format_type
        captured["flood_control_config"] = flood_control_config
        return _sentinel_log_pipeline(level, format_type)

    monkeypatch.setattr(builder_module, "build_log_pipeline", _fake_build_log_pipeline)

    result = build_observability_manifest(infra)

    assert isinstance(result, ObservabilityManifest)
    assert captured["level"] == "INFO"
    assert captured["format_type"] == "TEXT"
    assert captured["flood_control_config"] == {
        "enabled": True,
        "mode": "context_info_suppression",
        "context_keys": ["item_ref"],
        "suppressed_levels": ["INFO"],
        "force_log_attr": "force_log",
        "key_fields": ["name", "levelno", "msg", "item_ref"],
        "window_seconds": 30.0,
        "max_events_per_window": 1,
        "emit_summary": False,
        "summary_level": "INFO",
        "summary_interval_seconds": 30.0,
        "max_cache_size": 10000,
    }


def test_build_observability_manifest_applies_defaults_without_optional_blocks() -> (
    None
):
    """Apply default level, format, and telemetry when optional blocks are omitted."""
    payload = _base_payload()
    payload["observability"] = {
        "labels": {"pipeline": "default-only"},
    }
    infra = normalize_infra_paths(
        InfraConfig.model_validate(payload),
        infra_path="./infra.yaml",
    )

    result = build_observability_manifest(infra)

    assert isinstance(result, ObservabilityManifest)
    assert isinstance(result.log_pipeline, LogPipeline)
    assert result.log_pipeline.level == "INFO"
    assert result.log_pipeline.format_type == "TEXT"
    assert result.log_pipeline.registry.is_attached() is True
    assert isinstance(result.telemetry_handler, NoOpTelemetryHandler)
    assert isinstance(result.usage_collector, FeedUsageCollector)
    assert result.labels == {"pipeline": "default-only"}
    assert result.telemetry_enabled is False
    assert result.telemetry_provider == "none"


def test_build_observability_manifest_returns_noop_handler_for_none_provider() -> None:
    """Create NoOp telemetry handler when provider is not Prometheus."""
    payload = _base_payload()
    payload["observability"] = {
        "labels": {"pipeline": "test"},
        "logging": {"level": "info"},
        "telemetry": {"provider": "none"},
    }
    infra = normalize_infra_paths(
        InfraConfig.model_validate(payload),
        infra_path="./infra.yaml",
    )

    result = build_observability_manifest(infra)

    assert isinstance(result, ObservabilityManifest)
    assert isinstance(result.telemetry_handler, NoOpTelemetryHandler)
    assert isinstance(result.usage_collector, FeedUsageCollector)
    assert result.log_pipeline.registry.is_attached() is True


def test_build_observability_manifest_rejects_second_install_in_same_test() -> None:
    """Raise RuntimeError when called twice without resetting root handlers."""
    infra = InfraConfig.model_validate(_base_payload())

    result = build_observability_manifest(infra)

    assert result.log_pipeline.registry.is_attached() is True

    with pytest.raises(RuntimeError, match="cannot install LogPipeline twice"):
        build_observability_manifest(infra)


def test_build_telemetry_handler_uses_noop_for_blank_disabled_provider() -> None:
    """Return NoOp handler when blank provider resolves with telemetry disabled."""
    result = builder_module._build_telemetry_handler(
        telemetry_provider="   ",
        telemetry_enabled=False,
    )

    assert isinstance(result, NoOpTelemetryHandler)


def test_build_observability_manifest_raises_when_prometheus_dependency_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise ValueError when Prometheus telemetry cannot be initialized."""
    payload = _base_payload()
    payload["observability"] = {
        "labels": {"pipeline": "test"},
        "logging": {"level": "info"},
        "telemetry": {"provider": "prometheus"},
    }
    infra = normalize_infra_paths(
        InfraConfig.model_validate(payload),
        infra_path="./infra.yaml",
    )

    def _raise_import_error() -> None:
        raise ImportError("missing")

    monkeypatch.setattr(
        builder_module,
        "PrometheusTelemetryHandler",
        _raise_import_error,
    )

    with pytest.raises(ValueError, match="prometheus_client is required"):
        build_observability_manifest(infra)
