"""Archiver contract and result type for the v2 publisher stack.

Defines the streaming runtime cycle (open / write_chunk / finalize) used by
Publisher.publish(). Concrete implementations are configured via
__init__(self, iac: ConcreteIaC) and instantiated by archiver_builder.
NoopArchiver accepts NoopArchiverIaC — an empty Pydantic model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class ArchiveResult:
    """Result returned by Archiver.finalize().

    Attributes:
        skipped: True when archiving was intentionally skipped (NoopArchiver).
        location: URI or path of the stored archive, or None when skipped.
    """

    skipped: bool
    location: Optional[str] = None


@runtime_checkable
class Archiver(Protocol):
    """Structural protocol for the runtime archiver interface.

    Defines the streaming runtime cycle used by Publisher.publish().
    Concrete implementations are configured via __init__(self, iac: ConcreteIaC)
    and instantiated by archiver_builder. NoopArchiver accepts NoopArchiverIaC — an empty Pydantic model.

    Implementations: LocalArchiver, S3Archiver, S3CompatArchiver, NoopArchiver.
    """

    def open(self) -> None:
        """Prepare destination (open file handle, initiate S3 multipart upload, etc.)."""
        ...

    def write_chunk(self, chunk: bytes) -> None:
        """Write one chunk of payload bytes to the archive destination."""
        ...

    def finalize(self) -> ArchiveResult:
        """Flush, close destination, and return result metadata."""
        ...


__all__ = ["Archiver", "ArchiveResult"]
