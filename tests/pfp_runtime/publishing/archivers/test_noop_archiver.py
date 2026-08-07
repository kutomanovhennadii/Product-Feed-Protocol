"""Tests for publishing/archivers/noop_archiver.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pfp_runtime.publishing.archivers.archiver_contract import Archiver, ArchiveResult
from pfp_runtime.publishing.archivers.noop_archiver import NoopArchiver, NoopArchiverIaC

# ---------------------------------------------------------------------------
# NoopArchiverIaC
# ---------------------------------------------------------------------------


def test_iac_model_validate_empty_dict() -> None:
    """NoopArchiverIaC.model_validate({}) succeeds without error."""
    iac = NoopArchiverIaC.model_validate({})
    assert isinstance(iac, NoopArchiverIaC)


def test_iac_extra_fields_forbidden() -> None:
    """NoopArchiverIaC.model_validate({'x': 1}) raises ValidationError."""
    with pytest.raises(ValidationError):
        NoopArchiverIaC.model_validate({"x": 1})


# ---------------------------------------------------------------------------
# NoopArchiver construction
# ---------------------------------------------------------------------------


def test_init_accepts_iac() -> None:
    """NoopArchiver(iac) is constructed without error."""
    iac = NoopArchiverIaC.model_validate({})
    archiver = NoopArchiver(iac)
    assert isinstance(archiver, NoopArchiver)


# ---------------------------------------------------------------------------
# Protocol methods
# ---------------------------------------------------------------------------


def test_open_does_not_raise() -> None:
    """open() completes without raising."""
    iac = NoopArchiverIaC.model_validate({})
    archiver = NoopArchiver(iac)
    archiver.open()


def test_write_chunk_does_not_raise() -> None:
    """write_chunk(b'data') completes without raising."""
    iac = NoopArchiverIaC.model_validate({})
    archiver = NoopArchiver(iac)
    archiver.write_chunk(b"data")


def test_write_chunk_empty_bytes() -> None:
    """write_chunk(b'') completes without raising."""
    iac = NoopArchiverIaC.model_validate({})
    archiver = NoopArchiver(iac)
    archiver.write_chunk(b"")


# ---------------------------------------------------------------------------
# finalize
# ---------------------------------------------------------------------------


def test_finalize_returns_skipped_result() -> None:
    """finalize() returns ArchiveResult(skipped=True, location=None)."""
    iac = NoopArchiverIaC.model_validate({})
    archiver = NoopArchiver(iac)
    result = archiver.finalize()
    assert result == ArchiveResult(skipped=True, location=None)


def test_finalize_result_is_frozen() -> None:
    """Attempt to mutate the finalize() result raises FrozenInstanceError."""
    iac = NoopArchiverIaC.model_validate({})
    archiver = NoopArchiver(iac)
    result = archiver.finalize()
    with pytest.raises(AttributeError):
        result.skipped = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_satisfies_archiver_protocol() -> None:
    """isinstance(NoopArchiver(iac), Archiver) is True."""
    iac = NoopArchiverIaC.model_validate({})
    archiver = NoopArchiver(iac)
    assert isinstance(archiver, Archiver)


# ---------------------------------------------------------------------------
# Full cycle
# ---------------------------------------------------------------------------


def test_full_cycle() -> None:
    """open() -> write_chunk() x2 -> finalize() completes and returns skipped result."""
    iac = NoopArchiverIaC.model_validate({})
    archiver = NoopArchiver(iac)
    archiver.open()
    archiver.write_chunk(b"a")
    archiver.write_chunk(b"b")
    result = archiver.finalize()
    assert result.skipped is True
    assert result.location is None
