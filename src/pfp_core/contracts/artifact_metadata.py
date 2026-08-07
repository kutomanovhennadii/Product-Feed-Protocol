"""Artifact metadata contract — base metadata for produced artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ArtifactMetadata:
    """Base metadata for a produced artifact.

    Carries identity and format descriptors. Does not include payload data
    or publish-time results — those are added by PublishMetadata at runtime.

    Attributes:
        target: Identifier of the target system (e.g., "stripe.product").
        schema_version: Version of the target schema.
        generated_at: UTC timestamp of generation.
        content_type: MIME type of the payload (e.g., "text/csv").
        encoding: Payload encoding (e.g., "utf-8").
        artifact_profile: Artifact profile used (e.g., "catalog_snapshot").
        filename_hint: Optional deterministic filename hint.
    """

    target: str
    schema_version: str
    generated_at: datetime
    content_type: str
    encoding: str
    artifact_profile: Optional[str] = None
    filename_hint: Optional[str] = None


__all__ = ["ArtifactMetadata"]
