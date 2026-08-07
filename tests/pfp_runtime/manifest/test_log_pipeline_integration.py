"""End-to-end integration tests for manifest-owned LogPipeline."""

from __future__ import annotations

import logging
import time
from types import TracebackType
from typing import cast

import pytest

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.manifest import observability_manifest_builder as builder_module
from pfp_runtime.manifest.observability_manifest_builder import (
    build_observability_manifest,
)
from pfp_utils.logging import LogContext
from pfp_utils.logging.filters.flood_control_filter import FloodControlFilter
from pfp_utils.logging.filters.flood_control_filter.flood_control_filter import (
    _get_current_time,
    _get_summary_logger,
)
from pfp_utils.logging.log_pipeline import _normalize_exc_info, _to_numeric
from pfp_utils.telemetry import NoOpTelemetryHandler


def _make_infra() -> InfraConfig:
    """Build a minimal valid infra config for observability manifest tests.

    Returns:
        Valid InfraConfig instance suitable for manifest-owned logging tests.
    """
    return InfraConfig.model_validate(
        {
            "input": {
                "format": "csv",
                "config": {"connector_mapping": "./mapping.yaml"},
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
            "observability": {
                "log_format": "TEXT",
                "labels": {},
                "logging": {
                    "level": "INFO",
                },
                "telemetry": {
                    "provider": "none",
                },
            },
        }
    )


def _make_infra_without_observability() -> InfraConfig:
    """Build a minimal valid infra config without observability settings.

    Returns:
        Valid InfraConfig instance whose observability section is omitted.
    """
    return InfraConfig.model_validate(
        {
            "input": {
                "format": "csv",
                "config": {"connector_mapping": "./mapping.yaml"},
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
    )


def test_build_observability_manifest_log_pipeline_e2e(capsys) -> None:
    """Verify stdout emission, traceback rendering, and flood-control behavior.

    Args:
        capsys: Pytest capture fixture used to inspect stdout emitted by LogPipeline.

    Returns:
        None.
    """
    manifest = build_observability_manifest(_make_infra())

    manifest.log_pipeline.log_process(
        logging.INFO,
        "test.module",
        "hello %s",
        "world",
        extra={"target": "http://x"},
    )
    output = capsys.readouterr().out
    assert "hello world" in output
    assert "target=http://x" in output

    try:
        raise RuntimeError("boom")
    except RuntimeError as error:
        manifest.log_pipeline.log_process(
            logging.ERROR,
            "test.module",
            "runtime failure",
            exc_info=error,
        )

    output = capsys.readouterr().out
    assert "runtime failure" in output
    assert "Traceback (most recent call last)" in output
    assert "RuntimeError: boom" in output

    with LogContext(item_ref="a"):
        manifest.log_pipeline.log_process(
            logging.INFO,
            "test.module",
            "suppressed info",
        )

    output = capsys.readouterr().out
    assert "suppressed info" not in output

    with LogContext(item_ref="a"):
        manifest.log_pipeline.log_process(
            logging.WARNING,
            "test.module",
            "visible warning",
        )

    output = capsys.readouterr().out
    assert "visible warning" in output


def test_build_observability_manifest_defaults_without_observability(capsys) -> None:
    """Verify omitted observability uses default TEXT/INFO pipeline settings.

    Args:
        capsys: Pytest capture fixture used to inspect stdout emitted by LogPipeline.

    Returns:
        None.
    """
    manifest = build_observability_manifest(_make_infra_without_observability())

    assert manifest.log_pipeline.level == "INFO"
    assert manifest.log_pipeline.format_type == "TEXT"
    assert isinstance(manifest.telemetry_handler, NoOpTelemetryHandler)
    assert manifest.telemetry_enabled is False

    manifest.log_pipeline.log_process(logging.INFO, "test.module", "default message")

    output = capsys.readouterr().out
    assert "default message" in output


def test_build_observability_manifest_rejects_second_installation() -> None:
    """Verify manifest assembly rejects repeated LogPipeline installation in one process.

    Returns:
        None.
    """
    build_observability_manifest(_make_infra())

    with pytest.raises(RuntimeError, match="cannot install LogPipeline twice"):
        build_observability_manifest(_make_infra())


def test_build_observability_manifest_wraps_missing_prometheus_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Prometheus dependency failures are translated into a config-facing error.

    Args:
        monkeypatch: Pytest helper used to replace the Prometheus handler constructor.

    Returns:
        None.
    """
    infra = _make_infra()
    observability = infra.observability
    assert observability is not None
    object.__setattr__(observability.telemetry, "provider", "prometheus")

    def _raise_import_error() -> NoOpTelemetryHandler:
        raise ImportError("missing dependency")

    monkeypatch.setattr(
        builder_module, "PrometheusTelemetryHandler", _raise_import_error
    )

    with pytest.raises(ValueError, match="prometheus_client is required"):
        build_observability_manifest(infra)


def test_build_telemetry_handler_blank_provider_defaults_to_none() -> None:
    """Verify blank telemetry provider values normalize to the disabled path.

    Returns:
        None.
    """
    handler = builder_module._build_telemetry_handler("   ", telemetry_enabled=False)

    assert isinstance(handler, NoOpTelemetryHandler)


def test_flood_control_filter_properties_and_force_log_bypass(capsys) -> None:
    """Verify flood-control exposes canonical settings and honors force_log bypass.

    Args:
        capsys: Pytest capture fixture used to inspect stdout emitted by LogPipeline.

    Returns:
        None.
    """
    manifest = build_observability_manifest(_make_infra())
    flood_control = next(
        log_filter
        for log_filter in manifest.log_pipeline.filters
        if isinstance(log_filter, FloodControlFilter)
    )

    assert flood_control.enabled is True
    assert flood_control.mode == "context_info_suppression"
    assert flood_control.context_keys == ("item_ref",)
    assert flood_control.suppressed_levels == (logging.INFO,)
    assert flood_control.force_log_attr == "force_log"
    assert flood_control.key_fields == ("name", "levelno", "msg", "item_ref")
    assert flood_control.window_seconds == 30.0
    assert flood_control.max_events_per_window == 1
    assert flood_control.emit_summary is False
    assert flood_control.summary_level == logging.INFO
    assert flood_control.summary_interval_seconds == 30.0
    assert flood_control.max_cache_size == 10000

    with LogContext(item_ref="a"):
        manifest.log_pipeline.log_process(
            logging.INFO,
            "test.module",
            "forced info",
            extra={"force_log": True},
        )

    output = capsys.readouterr().out
    assert "forced info" in output


def test_log_pipeline_below_threshold_is_not_emitted(capsys) -> None:
    """Verify records below the pipeline threshold are ignored before handler dispatch.

    Args:
        capsys: Pytest capture fixture used to inspect stdout emitted by LogPipeline.

    Returns:
        None.
    """
    manifest = build_observability_manifest(_make_infra())

    manifest.log_pipeline.log_process(logging.DEBUG, "test.module", "skip me")

    assert capsys.readouterr().out == ""


def test_log_pipeline_install_rejects_repeated_attachment() -> None:
    """Verify installed pipelines reject a second explicit install call.

    Returns:
        None.
    """
    manifest = build_observability_manifest(_make_infra())

    with pytest.raises(RuntimeError, match="LogPipeline already installed"):
        manifest.log_pipeline.install()


def test_log_pipeline_helper_contracts() -> None:
    """Verify helper functions keep their low-level normalization contracts.

    Returns:
        None.
    """
    assert _to_numeric("WARNING") == logging.WARNING
    assert _normalize_exc_info(None) is None

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        exc_info = cast(
            tuple[type[BaseException], BaseException, TracebackType | None],
            __import__("sys").exc_info(),
        )

    assert _normalize_exc_info(exc_info) is exc_info

    with pytest.raises(ValueError, match="Invalid log level: BOGUS"):
        _to_numeric("BOGUS")


def test_flood_control_helper_contracts() -> None:
    """Verify low-level flood-control helpers expose stdlib-backed primitives.

    Returns:
        None.
    """
    before = time.monotonic()
    current_time = _get_current_time()
    after = time.monotonic()

    assert before <= current_time <= after
    assert _get_summary_logger("test.summary") is logging.getLogger("test.summary")
