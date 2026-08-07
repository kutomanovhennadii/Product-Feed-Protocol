"""Connector manifest builder for init-phase manifest pipeline."""

from __future__ import annotations

from typing import Any

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.connectors.adapter_provider import AdapterRegistryError
from pfp_runtime.connectors.connector_builder import (
    ConnectorBuildError,
    build_connector,
)
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    ManifestBuildError,
)
from pfp_utils.logging import LogPipeline


def build_connector_manifest(
    infra: InfraConfig,
    *,
    log_pipeline: LogPipeline,
) -> ConnectorManifest:
    """Build connector section of pipeline manifest from validated infra.

    Args:
        infra: Validated canonical infra configuration.
        log_pipeline: Runtime log pipeline propagated from observability builder.

    Returns:
        ConnectorManifest containing a ready-to-use source connector.

    Raises:
        ManifestBuildError: If connector assembly fails.
    """
    input_config = _build_input_config_mapping(infra)
    try:
        connector = build_connector(
            format_name=infra.input.format,
            config=input_config,
            log_pipeline=log_pipeline,
        )
    except (AdapterRegistryError, ConnectorBuildError) as exc:
        raise ManifestBuildError(str(exc)) from exc

    return ConnectorManifest(connector=connector)


def _build_input_config_mapping(infra: InfraConfig) -> dict[str, Any]:
    """Convert typed infra input config to plain mapping for connector builder."""
    payload = dict(infra.input.config.model_dump(exclude_none=True))
    payload["format"] = infra.input.format
    return payload


__all__ = ["build_connector_manifest"]
