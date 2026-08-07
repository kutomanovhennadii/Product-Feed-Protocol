"""Pipeline manifest builder for init-phase manifest pipeline."""

from __future__ import annotations

from pfp_core.artifact_production.artifact_producer import ArtifactProducer
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    CoreManifest,
    ManifestBuildError,
    ObservabilityManifest,
    PipelineManifest,
    PublishManifest,
)


def build_pipeline_manifest_from_parts(
    connector: ConnectorManifest,
    core: CoreManifest,
    publish: PublishManifest,
    observability: ObservabilityManifest,
) -> PipelineManifest:
    """Build validated runtime pipeline manifest from prepared parts.

    Args:
        connector: Prepared connector manifest section.
        core: Prepared core manifest section.
        publish: Prepared publish manifest section.
        observability: Prepared observability manifest section.

    Returns:
        Validated PipelineManifest instance.

    Raises:
        ManifestBuildError: If any required manifest contract is invalid.
    """
    if connector is None:
        raise ManifestBuildError("connector manifest is required")
    if connector.connector is None:
        raise ManifestBuildError("connector manifest.connector is required")

    if core is None:
        raise ManifestBuildError("manifest.core is required")
    if not isinstance(core.producer, ArtifactProducer):
        raise ManifestBuildError("core.producer is required")

    if publish is None:
        raise ManifestBuildError("manifest.publish is required")
    if publish.publisher is None:
        raise ManifestBuildError("manifest.publish.publisher is required")
    if observability is None:
        raise ManifestBuildError("manifest.observability is required")

    return PipelineManifest(
        ingestion=connector,
        core=core,
        publish=publish,
        observability=observability,
    )


__all__ = ["build_pipeline_manifest_from_parts"]
