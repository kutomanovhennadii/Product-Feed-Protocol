"""Local filesystem archiver for archive_type: local.

Implements the Archiver protocol by writing artifact chunks to a local file
using an atomic temp-file-then-replace strategy. The output filename is generated
as {filename_base}_{YYYYMMDD_HHMMSS} (UTC) on each open() call, ensuring a unique
file per pipeline run and a natural audit history.

Why atomic write despite unique filenames
-----------------------------------------
Each run produces a unique timestamp-based filename, so concurrent readers and
overwrite conflicts are not a concern. However, atomic write (write to a temp file
then os.replace) is still used to protect against process crashes mid-write:
if the pipeline is killed while chunks are being written, the temp file is left
incomplete — but the final timestamp filename never appears in output_dir. Without
this guard, a partial file would be indistinguishable from a complete one, and the
user would have no immediate signal that the pipeline failed.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, List, Optional

from pydantic import BaseModel, ConfigDict

from pfp_runtime.publishing.archivers.archiver_contract import ArchiveResult
from pfp_runtime.publishing.support.filesystem_safety import (
    SAFE_FILE_MODE,
    ensure_directory,
)


class LocalArchiverError(RuntimeError):
    """Raised when LocalArchiver encounters a configuration or filesystem error."""


class LocalArchiverIaC(BaseModel):
    """IaC model for the local filesystem archiver.

    Attributes:
        output_dir: Path to the destination directory. The archiver creates the
            directory tree on demand before the first write.
        filename_base: Base name for the output file. A UTC timestamp suffix is
            appended automatically: {filename_base}_{YYYYMMDD_HHMMSS}.
            Do not include a file extension — the archiver does not know the
            artifact format.
    """

    model_config = ConfigDict(extra="forbid")

    output_dir: str
    filename_base: str


class LocalArchiver:
    """Archiver that writes artifact chunks to a local file atomically.

    Satisfies the Archiver protocol structurally. Instantiated by archiver_builder
    when archive_type is 'local', using the standard 5-step build path.

    The output filename is generated on each open() call as
    {filename_base}_{YYYYMMDD_HHMMSS} (UTC). Each pipeline run produces a
    unique file — no overwrite, no retention limit (see Layer 13 notes).

    Args:
        iac: Validated LocalArchiverIaC instance.

    Raises:
        LocalArchiverError: If output_dir cannot be prepared as a directory.
    """

    def __init__(self, iac: LocalArchiverIaC) -> None:
        """Resolve and validate configuration. Prepare output_dir on demand.

        Args:
            iac: Validated LocalArchiverIaC instance.

        Raises:
            LocalArchiverError: If output_dir cannot be prepared as a directory.
        """
        output_dir = Path(iac.output_dir).expanduser().resolve()
        try:
            ensure_directory(output_dir)
        except OSError as exc:
            raise LocalArchiverError(
                "failed to prepare output_dir: " + str(output_dir)
            ) from exc
        if not output_dir.is_dir():  # pragma: no cover — defensive
            # ensure_directory() already raises when the path exists as a file,
            # so this guard only fires if the path is replaced concurrently
            # between mkdir() and this check.
            raise LocalArchiverError(
                "output_dir is not a directory: " + str(output_dir)
            )
        self._output_dir: Path = output_dir
        self._filename_base: str = iac.filename_base
        # runtime state — populated by open()
        self._final_path: Optional[Path] = None
        self._tmp_path: Optional[Path] = None
        self._tmp_handle: Optional[IO[bytes]] = None
        self._finalized: bool = False

    def open(self) -> None:
        """Generate a timestamp-based filename and open a temporary file for streaming writes.

        The final filename is {filename_base}_{YYYYMMDD_HHMMSS} (UTC).
        Resets finalized state, allowing the archiver to be reused across runs.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._final_path = self._output_dir / "{}_{}".format(self._filename_base, ts)
        self._finalized = False
        handle = tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=str(self._output_dir),
            prefix=self._final_path.name + ".",
            suffix=".tmp",
        )
        self._tmp_path = Path(handle.name)
        self._tmp_handle = handle

    def write_chunk(self, chunk: bytes) -> None:
        """Write one chunk of payload bytes to the temporary file.

        Args:
            chunk: Payload bytes to append to the archive.

        Raises:
            LocalArchiverError: If open() has not been called.
        """
        if self._tmp_handle is None:
            raise LocalArchiverError("write_chunk() called before open()")
        self._tmp_handle.write(chunk)

    def finalize(self) -> ArchiveResult:
        """Flush, close, and atomically promote the temp file to the final path.

        Returns:
            ArchiveResult with skipped=False and location set to the absolute
            path of the written file.

        Raises:
            LocalArchiverError: If open() has not been called, finalize() has
                already been called, or the atomic replace fails. On replace
                failure the temp file is preserved and its path is included in
                the error message.
        """
        if self._tmp_path is None:
            raise LocalArchiverError("finalize() called before open()")
        if self._finalized:
            raise LocalArchiverError(
                "finalize() already called; call open() to start a new run"
            )

        tmp_path = self._tmp_path
        final_path = self._final_path
        handle = self._tmp_handle

        if handle is not None:
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            self._tmp_handle = None

        _apply_safe_permissions(tmp_path)

        try:
            os.replace(str(tmp_path), str(final_path))
        except OSError as exc:
            # Do NOT remove temp — it contains successfully written content.
            # Caller can recover data from the temp path included in the message.
            raise LocalArchiverError(
                "atomic replace failed; temp file preserved at: " + str(tmp_path)
            ) from exc

        self._finalized = True
        _apply_safe_permissions(final_path)
        return ArchiveResult(skipped=False, location=str(final_path))


def _apply_safe_permissions(path: Optional[Path]) -> None:
    """Apply SAFE_FILE_MODE to path with Windows-safe best-effort behaviour.

    Args:
        path: File path to chmod, or None (no-op).
    """
    if path is None:
        return
    try:
        path.chmod(SAFE_FILE_MODE)
    except OSError:
        if os.name != "nt":
            raise


__all__: List[str] = ["LocalArchiverIaC", "LocalArchiver", "LocalArchiverError"]
