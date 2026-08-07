"""Publish manifest builder for init-phase manifest pipeline."""

from __future__ import annotations

from typing import Any, Dict

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.manifest.pipeline_manifest import (
    ManifestBuildError,
    PublishManifest,
)
from pfp_runtime.publishing.contracts.publisher_errors import PublisherBuildError
from pfp_runtime.publishing.publisher_builder import build_publisher
from pfp_utils.logging import LogPipeline


def build_publish_manifest(
    infra: InfraConfig,
    *,
    log_pipeline: LogPipeline,
) -> PublishManifest:
    """Build publish section of pipeline manifest from validated infra.

    Args:
        infra: Validated canonical infra configuration.
        log_pipeline: Runtime log pipeline propagated from observability builder.

    Returns:
        PublishManifest containing a ready-to-use Publisher instance.

    Raises:
        ManifestBuildError: If publisher assembly fails.
    """
    output_config = _build_output_config(infra)
    try:
        publisher = build_publisher(output_config, log_pipeline=log_pipeline)
    except PublisherBuildError as exc:
        raise ManifestBuildError(str(exc)) from exc

    return PublishManifest(publisher=publisher)


def _build_output_config(infra: InfraConfig) -> Dict[str, Any]:
    """Build plain output mapping consumed by publisher builder."""
    return {
        "archive_type": infra.output.archive_type,
        "archive_config": infra.output.archive_config,
        "client_type": infra.output.client_type,
        "client_config": infra.output.client_config,
    }


__all__ = ["build_publish_manifest"]
