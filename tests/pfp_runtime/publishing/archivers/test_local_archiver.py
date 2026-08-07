"""Tests for publishing/archivers/local_archiver.py."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

import pfp_runtime.publishing.archivers.local_archiver as local_archiver_mod
from pfp_runtime.publishing.archivers.archiver_contract import Archiver, ArchiveResult
from pfp_runtime.publishing.archivers.local_archiver import (
    LocalArchiver,
    LocalArchiverError,
    LocalArchiverIaC,
    _apply_safe_permissions,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_iac(tmp_path: Path, filename_base: str = "feed") -> LocalArchiverIaC:
    return LocalArchiverIaC.model_validate(
        {"output_dir": str(tmp_path), "filename_base": filename_base}
    )


# ---------------------------------------------------------------------------
# LocalArchiverIaC
# ---------------------------------------------------------------------------


def test_iac_output_dir_required() -> None:
    """Missing output_dir raises ValidationError."""
    with pytest.raises(ValidationError):
        LocalArchiverIaC.model_validate({"filename_base": "feed"})


def test_iac_filename_base_required() -> None:
    """Missing filename_base raises ValidationError."""
    with pytest.raises(ValidationError):
        LocalArchiverIaC.model_validate({"output_dir": "/tmp"})


def test_iac_extra_fields_forbidden(tmp_path: Path) -> None:
    """Extra fields in IaC raise ValidationError."""
    with pytest.raises(ValidationError):
        LocalArchiverIaC.model_validate(
            {"output_dir": str(tmp_path), "filename_base": "feed", "extra": "x"}
        )


# ---------------------------------------------------------------------------
# LocalArchiver.__init__
# ---------------------------------------------------------------------------


def test_init_creates_missing_output_dir(tmp_path: Path) -> None:
    """__init__ creates output_dir when it does not exist yet."""
    missing = tmp_path / "does_not_exist"
    iac = LocalArchiverIaC.model_validate(
        {"output_dir": str(missing), "filename_base": "feed"}
    )
    archiver = LocalArchiver(iac)

    assert missing.is_dir()
    assert archiver._output_dir == missing.resolve()


def test_init_raises_if_output_dir_is_file(tmp_path: Path) -> None:
    """__init__ raises LocalArchiverError when output_dir resolves to a file."""
    not_a_directory = tmp_path / "not_a_directory.txt"
    not_a_directory.write_text("x", encoding="utf-8")
    iac = LocalArchiverIaC.model_validate(
        {"output_dir": str(not_a_directory), "filename_base": "feed"}
    )

    with pytest.raises(LocalArchiverError, match="failed to prepare output_dir"):
        LocalArchiver(iac)


# ---------------------------------------------------------------------------
# open()
# ---------------------------------------------------------------------------


def test_open_creates_temp_file(tmp_path: Path) -> None:
    """After open(), a temporary file exists inside output_dir."""
    archiver = LocalArchiver(_make_iac(tmp_path))
    archiver.open()
    assert archiver._tmp_path is not None
    assert archiver._tmp_path.exists()
    assert archiver._tmp_path.parent == tmp_path


def test_open_generates_timestamp_filename(tmp_path: Path) -> None:
    """_final_path name matches {filename_base}_{YYYYMMDD_HHMMSS} pattern."""
    archiver = LocalArchiver(_make_iac(tmp_path, "product_feed"))
    archiver.open()
    name = archiver._final_path.name  # type: ignore[union-attr]
    assert re.match(r"product_feed_\d{8}_\d{6}$", name), f"unexpected name: {name}"


def test_open_two_calls_produce_different_filenames(tmp_path: Path) -> None:
    """Two archiver instances opened at different UTC times produce different filenames."""
    iac = _make_iac(tmp_path)
    t1 = datetime(2026, 3, 18, 10, 30, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 3, 18, 10, 30, 1, tzinfo=timezone.utc)

    with patch("pfp_runtime.publishing.archivers.local_archiver.datetime") as mock_dt:
        mock_dt.now.return_value = t1
        a1 = LocalArchiver(iac)
        a1.open()
        name1 = a1._final_path.name  # type: ignore[union-attr]

    with patch("pfp_runtime.publishing.archivers.local_archiver.datetime") as mock_dt:
        mock_dt.now.return_value = t2
        a2 = LocalArchiver(iac)
        a2.open()
        name2 = a2._final_path.name  # type: ignore[union-attr]

    assert name1 != name2


# ---------------------------------------------------------------------------
# finalize()
# ---------------------------------------------------------------------------


def test_finalize_writes_content(tmp_path: Path) -> None:
    """The final file contains all chunks written via write_chunk()."""
    archiver = LocalArchiver(_make_iac(tmp_path))
    archiver.open()
    archiver.write_chunk(b"hello ")
    archiver.write_chunk(b"world")
    result = archiver.finalize()
    assert Path(result.location).read_bytes() == b"hello world"  # type: ignore[arg-type]


def test_finalize_result(tmp_path: Path) -> None:
    """finalize() returns ArchiveResult(skipped=False, location=<absolute path>)."""
    archiver = LocalArchiver(_make_iac(tmp_path))
    archiver.open()
    result = archiver.finalize()
    assert result.skipped is False
    assert result.location is not None
    assert Path(result.location).is_file()


def test_finalize_no_temp_file_after_success(tmp_path: Path) -> None:
    """After successful finalize(), the temporary file is gone."""
    archiver = LocalArchiver(_make_iac(tmp_path))
    archiver.open()
    tmp_path_captured = archiver._tmp_path
    archiver.finalize()
    assert tmp_path_captured is not None
    assert not tmp_path_captured.exists()


def test_finalize_temp_preserved_on_replace_error(tmp_path: Path) -> None:
    """On os.replace failure, the temp file is NOT deleted and its path is in the error."""
    archiver = LocalArchiver(_make_iac(tmp_path))
    archiver.open()
    archiver.write_chunk(b"data")
    tmp_path_captured = archiver._tmp_path

    with patch(
        "pfp_runtime.publishing.archivers.local_archiver.os.replace",
        side_effect=OSError("file locked"),
    ):
        with pytest.raises(LocalArchiverError) as exc_info:
            archiver.finalize()

    assert tmp_path_captured is not None
    assert tmp_path_captured.exists()
    assert str(tmp_path_captured) in str(exc_info.value)


# ---------------------------------------------------------------------------
# Lifecycle errors
# ---------------------------------------------------------------------------


def test_write_chunk_before_open_raises(tmp_path: Path) -> None:
    """write_chunk() before open() raises LocalArchiverError."""
    archiver = LocalArchiver(_make_iac(tmp_path))
    with pytest.raises(LocalArchiverError, match="before open"):
        archiver.write_chunk(b"data")


def test_finalize_before_open_raises(tmp_path: Path) -> None:
    """finalize() before open() raises LocalArchiverError."""
    archiver = LocalArchiver(_make_iac(tmp_path))
    with pytest.raises(LocalArchiverError, match="before open"):
        archiver.finalize()


def test_double_finalize_raises(tmp_path: Path) -> None:
    """Calling finalize() a second time raises LocalArchiverError."""
    archiver = LocalArchiver(_make_iac(tmp_path))
    archiver.open()
    archiver.finalize()
    with pytest.raises(LocalArchiverError, match="already called"):
        archiver.finalize()


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_satisfies_archiver_protocol(tmp_path: Path) -> None:
    """isinstance(LocalArchiver(iac), Archiver) is True."""
    archiver = LocalArchiver(_make_iac(tmp_path))
    assert isinstance(archiver, Archiver)


# ---------------------------------------------------------------------------
# _apply_safe_permissions (internal helper)
# ---------------------------------------------------------------------------


def test_apply_safe_permissions_none_is_noop() -> None:
    """_apply_safe_permissions(None) does not raise."""
    _apply_safe_permissions(None)


def test_apply_safe_permissions_chmod_oserror_on_windows_is_suppressed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """OSError from chmod is suppressed on Windows and re-raised on POSIX."""
    f = tmp_path / "test.txt"
    f.write_bytes(b"")
    with patch.object(Path, "chmod", side_effect=OSError("permission denied")):
        monkeypatch.setattr(os, "name", "nt", raising=False)
        _apply_safe_permissions(f)

        monkeypatch.setattr(os, "name", "posix", raising=False)
        with pytest.raises(OSError, match="permission denied"):
            _apply_safe_permissions(f)


# ---------------------------------------------------------------------------
# Full cycle
# ---------------------------------------------------------------------------


def test_full_cycle_multiple_chunks(tmp_path: Path) -> None:
    """open() -> write_chunk() x3 -> finalize() produces correct file content."""
    archiver = LocalArchiver(_make_iac(tmp_path, "report"))
    archiver.open()
    archiver.write_chunk(b"chunk1|")
    archiver.write_chunk(b"chunk2|")
    archiver.write_chunk(b"chunk3")
    result = archiver.finalize()

    assert result == ArchiveResult(skipped=False, location=result.location)
    assert result.location is not None
    final = Path(result.location)
    assert final.is_file()
    assert final.read_bytes() == b"chunk1|chunk2|chunk3"
    assert final.name.startswith("report_")


def test_local_archiver_module_exports_public_names() -> None:
    """Module export contract keeps the expected public names."""

    assert set(local_archiver_mod.__all__) == {
        "LocalArchiverIaC",
        "LocalArchiver",
        "LocalArchiverError",
    }
