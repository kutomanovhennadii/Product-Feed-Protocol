"""Integration tests for filesystem safety helper."""

import io
import os
import tempfile
from pathlib import Path
from typing import Iterator, cast

import pytest

from pfp_runtime.publishing import fs_safe


def test_resolve_safe_target_path_rejects_traversal(tmp_path: Path) -> None:
    """Reject path traversal attempts that escape allowed base directory."""
    with pytest.raises(fs_safe.FSSafePathError, match="escapes"):
        fs_safe.resolve_safe_target_path(tmp_path, "../escape.csv")


def test_resolve_safe_target_path_rejects_absolute(tmp_path: Path) -> None:
    """Reject absolute target paths for base-bound publication."""
    with pytest.raises(fs_safe.FSSafePathError, match="absolute"):
        fs_safe.resolve_safe_target_path(tmp_path, str(tmp_path / "x.csv"))


def test_resolve_safe_target_path_rejects_empty_target(tmp_path: Path) -> None:
    """Reject empty target path before any filesystem interaction."""
    with pytest.raises(fs_safe.FSSafePathError, match="non-empty"):
        fs_safe.resolve_safe_target_path(tmp_path, " ")


def test_atomic_write_creates_nested_directories_and_final_file(tmp_path: Path) -> None:
    """Write final file atomically and create missing nested directories."""
    target = fs_safe.resolve_safe_target_path(tmp_path, "a/b/catalog.csv")

    fs_safe.atomic_write_bytes(target, iter([b"h\n", b"1\n"]), overwrite=True)

    assert target.read_bytes() == b"h\n1\n"
    assert target.parent.exists()
    assert list(target.parent.glob("*.tmp")) == []


def test_atomic_write_overwrite_false_preserves_existing_file(tmp_path: Path) -> None:
    """Refuse overwrite when disabled and keep original file content intact."""
    target = fs_safe.resolve_safe_target_path(tmp_path, "catalog.csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"old\n")

    with pytest.raises(fs_safe.FSSafeOverwriteError):
        fs_safe.atomic_write_bytes(target, iter([b"new\n"]), overwrite=False)

    assert target.read_bytes() == b"old\n"
    assert list(target.parent.glob("*.tmp")) == []


def test_atomic_write_payload_failure_has_no_partial_file(tmp_path: Path) -> None:
    """Cleanup temp data and avoid final partial file when payload stream fails."""

    def _broken_payload() -> Iterator[bytes]:
        yield b"chunk\n"
        raise RuntimeError("stream interrupted")

    target = fs_safe.resolve_safe_target_path(tmp_path, "catalog.csv")

    with pytest.raises(fs_safe.FSSafeWriteError):
        fs_safe.atomic_write_bytes(target, _broken_payload(), overwrite=True)

    assert not target.exists()
    assert list(target.parent.glob("*.tmp")) == []


def test_atomic_write_replace_failure_cleans_temp_and_keeps_old_file(
    monkeypatch, tmp_path: Path
) -> None:
    """Keep existing file stable and cleanup temp file when replace fails."""
    target = fs_safe.resolve_safe_target_path(tmp_path, "catalog.csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"stable\n")

    original_replace = fs_safe.os.replace

    def _broken_replace(src: str, dst: str) -> None:
        del src, dst
        raise OSError("replace failed")

    monkeypatch.setattr(fs_safe.os, "replace", _broken_replace)
    try:
        with pytest.raises(fs_safe.FSSafeWriteError, match="atomic write failed"):
            fs_safe.atomic_write_bytes(target, iter([b"new\n"]), overwrite=True)
    finally:
        monkeypatch.setattr(fs_safe.os, "replace", original_replace)

    assert target.read_bytes() == b"stable\n"
    assert list(target.parent.glob("*.tmp")) == []


def test_atomic_write_overwrite_race_detected_after_temp_write(
    monkeypatch, tmp_path: Path
) -> None:
    """Detect late overwrite race and return controlled overwrite error."""
    target = fs_safe.resolve_safe_target_path(tmp_path, "catalog.csv")
    original_exists = fs_safe.Path.exists
    calls = {"count": 0}

    def _flaky_exists(path_self: Path) -> bool:
        if path_self == target:
            calls["count"] += 1
            return calls["count"] >= 2
        return original_exists(path_self)

    monkeypatch.setattr(fs_safe.Path, "exists", _flaky_exists)

    with pytest.raises(fs_safe.FSSafeOverwriteError):
        fs_safe.atomic_write_bytes(target, iter([b"new\n"]), overwrite=False)

    assert not original_exists(target)
    assert list(target.parent.glob("*.tmp")) == []


def test_atomic_write_cleanup_failure_keeps_cause_chain(
    monkeypatch, tmp_path: Path
) -> None:
    """Raise write error variant when temp cleanup also fails in exception path."""
    target = fs_safe.resolve_safe_target_path(tmp_path, "catalog.csv")

    def _broken_replace(src: str, dst: str) -> None:
        del src, dst
        raise OSError("replace failed")

    monkeypatch.setattr(fs_safe.os, "replace", _broken_replace)
    monkeypatch.setattr(
        fs_safe,
        "_cleanup_temp_file",
        lambda _temp: OSError("cleanup failed"),
    )

    with pytest.raises(fs_safe.FSSafeWriteError, match="cleanup also failed"):
        fs_safe.atomic_write_bytes(target, iter([b"new\n"]), overwrite=True)


def test_cleanup_temp_file_none_and_missing_path_branches(tmp_path: Path) -> None:
    """Return None for absent temp path and for already-missing temp file."""
    assert fs_safe._cleanup_temp_file(None) is None
    assert fs_safe._cleanup_temp_file(tmp_path / "missing.tmp") is None


def test_cleanup_temp_file_returns_oserror_on_unlink_failure(monkeypatch) -> None:
    """Return OSError object when temp unlink fails during cleanup."""
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        temp_path = Path(handle.name)

    def _broken_unlink(path_self: Path) -> None:
        del path_self
        raise OSError("unlink failed")

    monkeypatch.setattr(fs_safe.Path, "unlink", _broken_unlink)
    err = fs_safe._cleanup_temp_file(temp_path)
    assert isinstance(err, OSError)
    if temp_path.exists():
        os.unlink(temp_path)


def test_apply_permissions_raises_on_non_windows_chmod_failure(
    monkeypatch, tmp_path: Path
) -> None:
    """Propagate chmod errors when platform is non-Windows."""

    def _broken_chmod(path_self: Path, mode: int) -> None:
        del path_self, mode
        raise OSError("chmod failed")

    monkeypatch.setattr(fs_safe.Path, "chmod", _broken_chmod)
    monkeypatch.setattr(fs_safe.os, "name", "posix", raising=False)

    with pytest.raises(OSError, match="chmod failed"):
        fs_safe._apply_permissions(tmp_path, fs_safe.SAFE_DIRECTORY_MODE)


def test_write_payload_bytes_rejects_non_bytes_chunks() -> None:
    """Payload writer fails fast when iterable yields non-bytes chunks."""

    with pytest.raises(fs_safe.FSSafePayloadError, match="must yield bytes"):
        fs_safe._write_payload_chunks(
            io.BytesIO(),
            cast(Iterator[bytes], iter(["bad"])),
        )
