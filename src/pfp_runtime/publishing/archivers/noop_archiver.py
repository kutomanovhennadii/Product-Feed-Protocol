"""No-op archiver for archive_type: noop.

Implements the Archiver protocol without performing any I/O.
Used when archiving is intentionally disabled in the pipeline configuration.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict

from pfp_runtime.publishing.archivers.archiver_contract import ArchiveResult


class NoopArchiverIaC(BaseModel):
    """IaC model for the no-op archiver. Contains no fields.

    Accepts an empty mapping. Supports future extension without builder changes.
    """

    model_config = ConfigDict(extra="forbid")


class NoopArchiver:
    """Archiver that performs no I/O.

    Satisfies the Archiver protocol structurally. Instantiated by archiver_builder
    when archive_type is 'noop', using the standard 5-step build path.

    Args:
        iac: Validated NoopArchiverIaC instance (always empty).
    """

    def __init__(self, iac: NoopArchiverIaC) -> None:
        """Store IaC (unused, accepted for interface uniformity).

        Args:
            iac: Validated NoopArchiverIaC instance.
        """
        self._iac = iac

    def open(self) -> None:
        """No-op: no destination to prepare."""

    def write_chunk(self, chunk: bytes) -> None:
        """No-op: discard the chunk.

        Args:
            chunk: Payload bytes — ignored.
        """

    def finalize(self) -> ArchiveResult:
        """Return a skipped result with no location.

        Returns:
            ArchiveResult with skipped=True and location=None.
        """
        return ArchiveResult(skipped=True, location=None)


__all__: List[str] = ["NoopArchiverIaC", "NoopArchiver"]
