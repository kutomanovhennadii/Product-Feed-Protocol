"""Filesystem safety helpers for runtime artifact publication."""

import os
import tempfile
from pathlib import Path
from typing import Iterable, Optional

SAFE_DIRECTORY_MODE = 0o750
SAFE_FILE_MODE = 0o640


class FSSafePathError(ValueError):
    """Raised when publish path is invalid or escapes allowed base directory."""


class FSSafePayloadError(TypeError):
    """Raised when artifact payload stream contains non-bytes chunks."""


class FSSafeOverwriteError(FileExistsError):
    """Raised when overwrite is disabled and target file already exists."""


class FSSafeWriteError(RuntimeError):
    """Raised when atomic write flow fails at filesystem boundary."""


def resolve_safe_target_path(base_directory: Path, target_path: str) -> Path:
    """Resolve a safe absolute target path within an allowed base directory.

    Args:
        base_directory: Root directory that bounds allowed publication targets.
        target_path: Relative artifact path provided by publish configuration.

    Returns:
        Absolute normalized target path guaranteed to remain under base_directory.

    Raises:
        FSSafePathError: If target_path is empty, absolute, or escapes base_directory.
    """
    normalized_base = Path(base_directory).expanduser().resolve()

    if not isinstance(target_path, str) or not target_path.strip():
        raise FSSafePathError("target path must be non-empty string")

    raw_target = Path(target_path.strip())
    if raw_target.is_absolute() or raw_target.anchor or raw_target.drive:
        raise FSSafePathError("absolute target path is not allowed")

    candidate = (normalized_base / raw_target).resolve()
    common = os.path.commonpath((str(normalized_base), str(candidate)))
    if common != str(normalized_base):
        raise FSSafePathError("target path escapes allowed base directory")

    return candidate


def ensure_directory(directory: Path, mode: int = SAFE_DIRECTORY_MODE) -> None:
    """Create directory tree if missing and apply safe permissions when supported.

    Args:
        directory: Directory path that must exist before file publication.
        mode: Permission mode applied to created directory path.

    Returns:
        None.

    Raises:
        OSError: Propagated on non-Windows platforms when chmod fails.
    """
    normalized = Path(directory).expanduser().resolve()
    normalized.mkdir(parents=True, exist_ok=True)
    _apply_permissions(normalized, mode)


def atomic_write_bytes(
    target_path: Path,
    payload: Iterable[bytes],
    overwrite: bool,
    directory_mode: int = SAFE_DIRECTORY_MODE,
    file_mode: int = SAFE_FILE_MODE,
) -> Path:
    """Write payload to target path atomically using temp file + replace.

    Args:
        target_path: Final artifact path resolved for publication.
        payload: Iterable byte stream containing artifact payload chunks.
        overwrite: Controls whether an existing target can be replaced.
        directory_mode: Permission mode applied to the target parent directory.
        file_mode: Permission mode applied to temp and final files.

    Returns:
        Final target path after successful atomic replacement.

    Raises:
        FSSafeOverwriteError: If overwrite is disabled and target already exists.
        FSSafePayloadError: If payload yields non-bytes chunks.
        FSSafeWriteError: If write/replace flow fails at filesystem boundary.
    """
    final_path = Path(target_path).expanduser().resolve()
    parent = final_path.parent
    ensure_directory(parent, mode=directory_mode)

    if not overwrite and final_path.exists():
        raise FSSafeOverwriteError("target file exists and overwrite is disabled")

    temp_path: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=str(parent),
            prefix=final_path.name + ".",
            suffix=".tmp",
        ) as handle:
            temp_path = Path(handle.name)
            _write_payload_chunks(handle, payload)
            handle.flush()
            os.fsync(handle.fileno())

        _apply_permissions(temp_path, file_mode)

        if not overwrite and final_path.exists():
            raise FSSafeOverwriteError("target file exists and overwrite is disabled")

        os.replace(str(temp_path), str(final_path))
        _apply_permissions(final_path, file_mode)
        return final_path
    except (FSSafePathError, FSSafePayloadError, FSSafeOverwriteError):
        _cleanup_temp_file(temp_path)
        raise
    except Exception as exc:
        cleanup_error = _cleanup_temp_file(temp_path)
        if cleanup_error is not None:
            raise FSSafeWriteError(
                "atomic write failed; temp cleanup also failed: " + str(cleanup_error)
            ) from exc
        raise FSSafeWriteError("atomic write failed") from exc


def _write_payload_chunks(handle, payload: Iterable[bytes]) -> None:
    """Write payload chunks to an opened binary file handle.

    Args:
        handle: Open binary file handle used for temporary write.
        payload: Iterable byte stream containing artifact payload chunks.

    Returns:
        None.

    Raises:
        FSSafePayloadError: If payload yields a non-bytes chunk.
    """
    for chunk in payload:
        if not isinstance(chunk, bytes):
            raise FSSafePayloadError("artifact payload must yield bytes")
        handle.write(chunk)


def _cleanup_temp_file(temp_path: Optional[Path]) -> Optional[OSError]:
    """Attempt to delete an existing temporary file.

    Args:
        temp_path: Temporary file path created during atomic write flow.

    Returns:
        OSError from cleanup failure, otherwise None.
    """
    if temp_path is None:
        return None
    if not temp_path.exists():
        return None
    try:
        temp_path.unlink()
    except OSError as exc:
        return exc
    return None


def _apply_permissions(path: Path, mode: int) -> None:
    """Apply permission mode with Windows-safe best-effort behavior.

    Args:
        path: File or directory path that receives permission update.
        mode: Permission mode to apply.

    Returns:
        None.

    Raises:
        OSError: On non-Windows platforms when chmod fails.
    """
    try:
        path.chmod(mode)
    except OSError:
        if os.name != "nt":
            raise
