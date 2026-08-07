"""Reusable in-memory chunk buffer for delivery clients.

Accumulates bytes from streaming chunks into a BytesIO buffer.
Used by HttpDeliveryClient and StripeDataManagementClient to collect
payload before sending.
"""

from __future__ import annotations

import io
from typing import Optional


class ChunkBufferError(RuntimeError):
    """Raised on invalid buffer lifecycle or size limit violation."""


class ChunkBuffer:
    """Accumulates chunks into a BytesIO buffer with optional size limit.

    Lifecycle: __init__ -> open() -> write() x N -> get_body()/take_body() -> close().
    After get_body()/take_body() the buffer is frozen — write() raises an error.
    Call open() to start a new cycle.

    Args:
        max_bytes: Maximum allowed buffer size in bytes.
            0 means unlimited. Must be >= 0.
    """

    def __init__(self, max_bytes: int = 0) -> None:
        if max_bytes < 0:
            raise ValueError("max_bytes must be >= 0")
        self._max_bytes = max_bytes
        self._buffer: Optional[io.BytesIO] = None
        self._closed = False
        self._frozen = False

    def open(self) -> None:
        """Prepare a fresh buffer for writing.

        Can be called multiple times to reset the buffer for a new cycle.
        """
        if self._buffer is not None:
            self._buffer.close()
        self._buffer = io.BytesIO()
        self._closed = False
        self._frozen = False

    def write(self, chunk: bytes) -> None:
        """Append chunk to the buffer.

        Args:
            chunk: Raw bytes to accumulate.

        Raises:
            ChunkBufferError: If called before open(), after close(),
                after get_body()/take_body() (frozen), or if the write
                would exceed max_bytes.
        """
        if self._closed:
            raise ChunkBufferError("write() called after close()")
        if self._frozen:
            raise ChunkBufferError("write() called after get_body()/take_body()")
        if self._buffer is None:
            raise ChunkBufferError("write() called before open()")
        if self._max_bytes > 0:
            new_size = self._buffer.tell() + len(chunk)
            if new_size > self._max_bytes:
                raise ChunkBufferError(
                    "Payload size ({size} bytes) would exceed "
                    "max_bytes={limit}".format(size=new_size, limit=self._max_bytes)
                )
        self._buffer.write(chunk)

    def get_body(self) -> bytes:
        """Return accumulated bytes and freeze the buffer.

        After this call, write() is forbidden until open() resets the cycle.
        The buffer remains open for size() inspection; call close() to release.

        Returns:
            Copy of all bytes written since open().

        Raises:
            ChunkBufferError: If called before open() or after close().
        """
        if self._closed:
            raise ChunkBufferError("get_body() called after close()")
        if self._buffer is None:
            raise ChunkBufferError("get_body() called before open()")
        self._frozen = True
        return self._buffer.getvalue()

    def take_body(self) -> bytes:
        """Return accumulated bytes and release the buffer.

        Unlike get_body(), this method closes the underlying BytesIO
        immediately, avoiding the 2x peak memory of holding both the
        buffer and the returned copy simultaneously.

        After this call, write()/get_body()/size() are forbidden
        until open() starts a new cycle.

        Returns:
            All bytes written since open().

        Raises:
            ChunkBufferError: If called before open() or after close().
        """
        if self._closed:
            raise ChunkBufferError("take_body() called after close()")
        if self._buffer is None:
            raise ChunkBufferError("take_body() called before open()")
        data = self._buffer.getvalue()
        self.close()
        return data

    def size(self) -> int:
        """Return current buffer size in bytes.

        Raises:
            ChunkBufferError: If called before open() or after close().
        """
        if self._closed:
            raise ChunkBufferError("size() called after close()")
        if self._buffer is None:
            raise ChunkBufferError("size() called before open()")
        return self._buffer.tell()

    def close(self) -> None:
        """Release the underlying BytesIO buffer.

        Safe to call multiple times. After close(), write/get_body/size
        will raise ChunkBufferError.
        """
        if self._buffer is not None:
            self._buffer.close()
            self._buffer = None
        self._closed = True


__all__ = ["ChunkBuffer", "ChunkBufferError"]
