"""Contract models for pfp_core root refactor scope."""

from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_core.contracts.artifact_production_result import ArtifactProductionResult
from pfp_core.contracts.produced_artifact import ProducedArtifact

# Backward-compatible contract aliases for legacy integration/test surface.
BuildResult = ArtifactProductionResult
Artifact = ProducedArtifact

__all__ = [
    "ArtifactMetadata",
    "ArtifactProductionResult",
    "ProducedArtifact",
    "BuildResult",
    "Artifact",
]
