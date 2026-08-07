"""Observability manifest builder for init-phase manifest pipeline."""

from __future__ import annotations

import logging
from typing import Any

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.manifest.pipeline_manifest import ObservabilityManifest
from pfp_utils.diagnostics import FeedUsageCollector
from pfp_utils.logging import build_log_pipeline
from pfp_utils.telemetry import (
    NoOpTelemetryHandler,
    PrometheusTelemetryHandler,
    TelemetryHandler,
)

_LOG_PIPELINE_HANDLER_MARKER = "_pfp_log_pipeline_installed"


def _has_installed_log_pipeline() -> bool:
    """Return whether a PFP log pipeline handler is already attached.

    Returns:
        True when a handler installed by build_observability_manifest is present.
    """
    return any(
        getattr(handler, _LOG_PIPELINE_HANDLER_MARKER, False)
        for handler in logging.getLogger().handlers
    )


def _mark_log_pipeline_handler(manifest: ObservabilityManifest) -> None:
    """Tag the installed pipeline handler so repeated installs can be rejected.

    Args:
        manifest: Observability manifest whose pipeline handler is already installed.

    Returns:
        None.
    """
    setattr(manifest.log_pipeline.handler, _LOG_PIPELINE_HANDLER_MARKER, True)


def build_observability_manifest(
    infra: InfraConfig,
) -> ObservabilityManifest:
    """Build observability section of pipeline manifest from validated infra.

    Args:
        infra: Validated canonical infra configuration.

    Returns:
        ObservabilityManifest with an installed LogPipeline and ready instruments.

    Raises:
        RuntimeError: If logging has already been installed for the current process.
        ValueError: If configured Prometheus telemetry cannot be initialized.
    """
    if _has_installed_log_pipeline():
        raise RuntimeError(
            "build_observability_manifest cannot install LogPipeline twice"
        )

    if infra.observability is None:
        log_pipeline = build_log_pipeline("INFO", "TEXT", {})
        manifest = ObservabilityManifest(log_pipeline=log_pipeline)
        _mark_log_pipeline_handler(manifest)
        return manifest

    observability = infra.observability
    level = observability.logging.level
    format_type = observability.log_format
    flood_control_config: dict[str, Any] = (
        observability.logging.flood_control_config.model_dump(exclude_none=True)
    )
    log_pipeline = build_log_pipeline(level, format_type, flood_control_config)
    telemetry_provider = observability.telemetry.provider
    telemetry_enabled = telemetry_provider == "prometheus"
    telemetry_handler = _build_telemetry_handler(
        telemetry_provider=telemetry_provider,
        telemetry_enabled=telemetry_enabled,
    )
    usage_collector = FeedUsageCollector()

    manifest = ObservabilityManifest(
        log_pipeline=log_pipeline,
        telemetry_handler=telemetry_handler,
        usage_collector=usage_collector,
        telemetry_enabled=telemetry_enabled,
        telemetry_provider=telemetry_provider,
        labels=dict(observability.labels),
    )
    _mark_log_pipeline_handler(manifest)
    return manifest


def _build_telemetry_handler(
    telemetry_provider: str,
    telemetry_enabled: bool,
) -> TelemetryHandler:
    """Create telemetry handler from resolved provider setting.

    Args:
        telemetry_provider: Provider name from infra config.
        telemetry_enabled: Whether telemetry is active.

    Returns:
        Ready-to-use telemetry handler instance.

    Raises:
        ValueError: If Prometheus telemetry is requested without dependency.
    """
    provider = telemetry_provider.strip().lower()
    if provider == "":
        provider = "prometheus" if telemetry_enabled else "none"

    if provider != "prometheus":
        return NoOpTelemetryHandler()

    try:
        return PrometheusTelemetryHandler()
    except ImportError as exc:
        raise ValueError(
            "prometheus_client is required when telemetry_enabled=true"
        ) from exc


__all__ = ["build_observability_manifest"]
