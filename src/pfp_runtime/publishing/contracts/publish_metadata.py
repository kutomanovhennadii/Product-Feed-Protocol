"""PublishMetadata — artifact metadata enriched with publish-time results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_runtime.publishing.archivers.archiver_contract import ArchiveResult
from pfp_runtime.publishing.clients.client_contract import DeliveryResult


@dataclass(frozen=True)
class PublishMetadata(ArtifactMetadata):
    """Artifact metadata enriched with archive and delivery outcomes.

    Inherits all fields from ArtifactMetadata and adds publish-time results.
    Built inside Publisher.publish() from ArtifactMetadata + ArchiveResult
    + DeliveryResult.

    Attributes:
        location: URI or path of the stored artifact, or None when skipped.
        archive_skipped: True when archiving was intentionally skipped.
        delivery_skipped: True when delivery was intentionally skipped.
        delivery_status_code: HTTP or SFTP status code, or None when not applicable.
    """

    location: Optional[str] = None
    archive_skipped: bool = False
    delivery_skipped: bool = False
    delivery_status_code: Optional[int] = None

    @classmethod
    def from_publish_results(
        cls,
        artifact_metadata: ArtifactMetadata,
        archived: ArchiveResult,
        delivered: DeliveryResult,
    ) -> PublishMetadata:
        """Build PublishMetadata from base metadata and publish outcomes.

        Args:
            artifact_metadata: Base metadata produced by artifact_producer.
            archived: Result returned by Archiver.finalize().
            delivered: Result returned by DeliveryClient.finalize().

        Returns:
            PublishMetadata combining all fields.
        """
        return cls(
            target=artifact_metadata.target,
            schema_version=artifact_metadata.schema_version,
            generated_at=artifact_metadata.generated_at,
            content_type=artifact_metadata.content_type,
            encoding=artifact_metadata.encoding,
            artifact_profile=artifact_metadata.artifact_profile,
            filename_hint=artifact_metadata.filename_hint,
            location=archived.location,
            archive_skipped=archived.skipped,
            delivery_skipped=delivered.skipped,
            delivery_status_code=delivered.status_code,
        )


__all__ = ["PublishMetadata"]
