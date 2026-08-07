"""Produced artifact contract — payload + metadata container."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pfp_core.contracts.artifact_metadata import ArtifactMetadata


@dataclass
class ProducedArtifact:
    """Container for a generated feed artifact.

    Carries the streaming payload and its associated metadata.
    After publish, payload is materialized (tuple of chunks) and
    metadata is upgraded to PublishMetadata.

    Attributes:
        payload: Byte chunks of the artifact. Generator before publish,
            tuple after publish (re-iterable).
        metadata: Artifact metadata. ArtifactMetadata before publish,
            PublishMetadata (subclass) after publish.
    """

    payload: Iterable[bytes]
    metadata: ArtifactMetadata


__all__ = ["ProducedArtifact"]
