"""Pipeline manifest provider for init-phase manifest pipeline."""

from __future__ import annotations

from pfp_runtime.config.infra_provider import InfraProvider
from pfp_runtime.manifest.connector_manifest_builder import build_connector_manifest
from pfp_runtime.manifest.core_manifest_builder import build_core_manifest
from pfp_runtime.manifest.observability_manifest_builder import (
    build_observability_manifest,
)
from pfp_runtime.manifest.pipeline_manifest import PipelineManifest
from pfp_runtime.manifest.pipeline_manifest_builder import (
    build_pipeline_manifest_from_parts,
)
from pfp_runtime.manifest.publish_manifest_builder import build_publish_manifest
from pfp_utils.logging import LogPipeline


def build_pipeline_manifest(infra_path: str) -> PipelineManifest:
    """Build full runtime PipelineManifest from infra YAML path.

    Args:
        infra_path: Path to infra YAML configuration.

    Returns:
        Fully assembled and validated PipelineManifest.
    """
    infra = InfraProvider().get_infra(infra_path)
    observability = build_observability_manifest(infra)
    log_pipeline: LogPipeline = observability.log_pipeline
    connector = build_connector_manifest(infra, log_pipeline=log_pipeline)
    core = build_core_manifest(infra, log_pipeline=log_pipeline)
    publish = build_publish_manifest(infra, log_pipeline=log_pipeline)
    return build_pipeline_manifest_from_parts(
        connector=connector,
        core=core,
        publish=publish,
        observability=observability,
    )


__all__ = ["build_pipeline_manifest"]
