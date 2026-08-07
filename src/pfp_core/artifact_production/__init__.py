"""Artifact production package surface."""

from pfp_core.artifact_production.artifact_producer import (
    ArtifactProducer,
    prepare_artifact_producer_from_files,
)

__all__ = [
    "ArtifactProducer",
    "prepare_artifact_producer_from_files",
]
