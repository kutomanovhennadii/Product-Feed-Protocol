"""Publishing contract and delivery errors.

Defines the Publisher stack assembled by publisher_builder:
  Publisher: Concrete orchestrator streaming artifact chunks to archiver
             and delivery client.
  PublisherConfigError / PublisherRuntimeError: Shared error types.
"""

from __future__ import annotations

import logging
from typing import List

from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_runtime.publishing.archivers.archiver_contract import (
    Archiver,
    ArchiveResult,
)
from pfp_runtime.publishing.clients.client_contract import (
    DeliveryClient,
    DeliveryResult,
)
from pfp_runtime.publishing.contracts.publish_metadata import PublishMetadata
from pfp_utils.logging import LogContext, LogPipeline


class Publisher:
    """Orchestrator that streams artifact chunks to archiver and delivery client.

    Assembled in the init phase by publisher_builder.build_publisher().
    Satisfies the observability triple contract: LogContext, structured logging,
    and result metadata hooks (archived.location, delivered.status_code).
    """

    def __init__(
        self,
        archiver: Archiver,
        client: DeliveryClient,
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        """Store pre-configured archiver and delivery client.

        Args:
            archiver: Configured archiver instance (LocalArchiver, S3Archiver, etc.).
            client: Configured delivery client instance (HttpDeliveryClient, etc.).
            log_pipeline: Runtime log pipeline propagated from manifest assembly.
        """
        self.archiver = archiver
        self.client = client
        self._log_pipeline = log_pipeline

    def publish(self, artifact: ProducedArtifact) -> ProducedArtifact:
        """Stream artifact payload chunks to archiver and delivery client.

        Opens both instruments, streams all chunks, finalizes both.
        Materializes payload into tuple (re-iterable). Returns a new
        ProducedArtifact with materialized payload and PublishMetadata.

        Args:
            artifact: Produced artifact with iterable payload of bytes chunks.

        Returns:
            ProducedArtifact with tuple payload and PublishMetadata.

        Raises:
            Exception: Any exception from archiver or client is logged and re-raised.
        """
        with LogContext(stage="publish", component="publisher"):
            self._log_pipeline.log_process(
                logging.INFO,
                __name__,
                "Starting publish cycle",
                extra={"force_log": True},
            )
            try:
                chunks: List[bytes] = []
                self.archiver.open()
                self.client.open()
                for chunk in artifact.payload:
                    chunks.append(chunk)
                    self.archiver.write_chunk(chunk)
                    self.client.send_chunk(chunk)
                archived: ArchiveResult = self.archiver.finalize()
                delivered: DeliveryResult = self.client.finalize()
                self._log_pipeline.log_process(
                    logging.INFO,
                    __name__,
                    "Publish cycle complete",
                    extra={
                        "force_log": True,
                        "archived_skipped": archived.skipped,
                        "archived_location": archived.location,
                        "delivered_skipped": delivered.skipped,
                        "delivered_status_code": delivered.status_code,
                    },
                )
                metadata: ArtifactMetadata = PublishMetadata.from_publish_results(
                    artifact.metadata, archived, delivered
                )
                return ProducedArtifact(payload=tuple(chunks), metadata=metadata)
            except Exception as exc:
                # Fail-fast: cleanup is intentionally skipped on exception.
                # Callers (archiver/client) are responsible for their own resource
                # management. Best-effort abort/close is deferred to Слой 13.
                self._log_pipeline.log_process(
                    logging.ERROR,
                    __name__,
                    "Publish cycle failed",
                    exc_info=exc,
                    extra={"force_log": True},
                )
                raise


# ---------------------------------------------------------------------------
# Shared errors
# ---------------------------------------------------------------------------


class PublisherConfigError(ValueError):
    """Raised when publisher configuration is invalid or incomplete."""


class PublisherRuntimeError(RuntimeError):
    """Raised when publishing fails due to runtime/infrastructure issues."""


__all__ = [
    "Publisher",
    "PublisherConfigError",
    "PublisherRuntimeError",
]
