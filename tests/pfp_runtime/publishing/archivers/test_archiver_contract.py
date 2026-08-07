"""Tests for publishing/archivers/archiver_contract.py."""

from __future__ import annotations

import pytest

from pfp_runtime.publishing.archivers.archiver_contract import (
    Archiver,
    ArchiveResult,
)

# ---------------------------------------------------------------------------
# ArchiveResult
# ---------------------------------------------------------------------------


def test_archive_result_skipped_defaults_location_to_none() -> None:
    """Verify ArchiveResult(skipped=True) sets location to None by default."""
    result = ArchiveResult(skipped=True)
    assert result.skipped is True
    assert result.location is None


def test_archive_result_with_location() -> None:
    """Verify ArchiveResult(skipped=False, location=...) stores both fields correctly."""
    result = ArchiveResult(skipped=False, location="s3://bucket/key")
    assert result.skipped is False
    assert result.location == "s3://bucket/key"


def test_archive_result_is_frozen() -> None:
    """Verify ArchiveResult raises AttributeError on field mutation (frozen dataclass)."""
    result = ArchiveResult(skipped=True)
    with pytest.raises(AttributeError):
        result.skipped = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Archiver Protocol (duck typing via runtime_checkable)
# ---------------------------------------------------------------------------


def test_archiver_protocol_accepts_valid_stub() -> None:
    """Verify class implementing open/write_chunk/finalize passes isinstance check."""

    class StubArchiver:
        def open(self) -> None:
            pass

        def write_chunk(self, chunk: bytes) -> None:
            pass

        def finalize(self) -> ArchiveResult:
            return ArchiveResult(skipped=True)

    assert isinstance(StubArchiver(), Archiver)


def test_archiver_protocol_rejects_missing_method() -> None:
    """Verify class missing finalize() fails isinstance check against Archiver."""

    class IncompleteArchiver:
        def open(self) -> None:
            pass

        def write_chunk(self, chunk: bytes) -> None:
            pass

    assert not isinstance(IncompleteArchiver(), Archiver)
