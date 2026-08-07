"""Tests for ChunkBuffer — reusable in-memory chunk accumulator."""

import pytest

from pfp_runtime.publishing.support.chunk_buffer import ChunkBuffer, ChunkBufferError

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestChunkBufferHappyPath:
    """Normal open -> write -> get_body -> close lifecycle."""

    def test_single_chunk(self) -> None:
        """Single write produces identical bytes from get_body."""
        buf = ChunkBuffer()
        buf.open()
        buf.write(b"hello")
        assert buf.get_body() == b"hello"
        buf.close()

    def test_multiple_chunks_concatenated(self) -> None:
        """Multiple writes are concatenated in order."""
        buf = ChunkBuffer()
        buf.open()
        buf.write(b"aaa")
        buf.write(b"bbb")
        buf.write(b"ccc")
        assert buf.get_body() == b"aaabbbccc"
        buf.close()

    def test_empty_buffer(self) -> None:
        """get_body on buffer with no writes returns empty bytes."""
        buf = ChunkBuffer()
        buf.open()
        assert buf.get_body() == b""
        buf.close()

    def test_size_tracks_written_bytes(self) -> None:
        """size() reflects cumulative bytes written."""
        buf = ChunkBuffer()
        buf.open()
        assert buf.size() == 0
        buf.write(b"12345")
        assert buf.size() == 5
        buf.write(b"67890")
        assert buf.size() == 10
        buf.close()

    def test_reopen_resets_buffer_and_freeze(self) -> None:
        """open() after get_body resets both data and frozen state."""
        buf = ChunkBuffer()
        buf.open()
        buf.write(b"first")
        assert buf.get_body() == b"first"
        # Buffer is frozen after get_body(), but open() resets everything.
        buf.open()
        buf.write(b"second")
        assert buf.get_body() == b"second"
        buf.close()

    def test_size_available_after_get_body(self) -> None:
        """size() still works after get_body() — only write() is frozen."""
        buf = ChunkBuffer()
        buf.open()
        buf.write(b"data")
        buf.get_body()
        assert buf.size() == 4
        buf.close()

    def test_close_is_idempotent(self) -> None:
        """Calling close() twice does not raise."""
        buf = ChunkBuffer()
        buf.open()
        buf.close()
        buf.close()  # should not raise


# ---------------------------------------------------------------------------
# max_bytes enforcement
# ---------------------------------------------------------------------------


class TestChunkBufferMaxBytes:
    """Size limit enforcement."""

    def test_write_within_limit(self) -> None:
        """Writes that stay within max_bytes succeed."""
        buf = ChunkBuffer(max_bytes=10)
        buf.open()
        buf.write(b"12345")
        buf.write(b"67890")
        assert buf.size() == 10
        buf.close()

    def test_write_exceeds_limit(self) -> None:
        """Second write that would exceed max_bytes raises ChunkBufferError."""
        buf = ChunkBuffer(max_bytes=5)
        buf.open()
        buf.write(b"123")
        with pytest.raises(ChunkBufferError, match="max_bytes=5"):
            buf.write(b"456")

    def test_single_write_exceeds_limit(self) -> None:
        """First write exceeding max_bytes raises immediately."""
        buf = ChunkBuffer(max_bytes=3)
        buf.open()
        with pytest.raises(ChunkBufferError, match="max_bytes=3"):
            buf.write(b"toolong")

    def test_exact_limit_ok(self) -> None:
        """Write that fills buffer exactly to max_bytes succeeds."""
        buf = ChunkBuffer(max_bytes=5)
        buf.open()
        buf.write(b"exact")
        assert buf.size() == 5
        assert buf.get_body() == b"exact"
        buf.close()

    def test_zero_max_bytes_means_unlimited(self) -> None:
        """max_bytes=0 disables size limit."""
        buf = ChunkBuffer(max_bytes=0)
        buf.open()
        big = b"x" * 10_000
        buf.write(big)
        assert buf.size() == 10_000
        buf.close()

    def test_negative_max_bytes_rejected(self) -> None:
        """Negative max_bytes is rejected at construction time."""
        with pytest.raises(ValueError, match="max_bytes must be >= 0"):
            ChunkBuffer(max_bytes=-1)


# ---------------------------------------------------------------------------
# Lifecycle errors
# ---------------------------------------------------------------------------


class TestChunkBufferLifecycleErrors:
    """Invalid call sequences raise ChunkBufferError."""

    def test_write_before_open(self) -> None:
        """write() before open() raises with 'before open' message."""
        buf = ChunkBuffer()
        with pytest.raises(ChunkBufferError, match="before open"):
            buf.write(b"x")

    def test_get_body_before_open(self) -> None:
        """get_body() before open() raises with 'before open' message."""
        buf = ChunkBuffer()
        with pytest.raises(ChunkBufferError, match="before open"):
            buf.get_body()

    def test_size_before_open(self) -> None:
        """size() before open() raises with 'before open' message."""
        buf = ChunkBuffer()
        with pytest.raises(ChunkBufferError, match="before open"):
            buf.size()

    def test_write_after_close(self) -> None:
        """write() after close() raises with 'after close' message."""
        buf = ChunkBuffer()
        buf.open()
        buf.close()
        with pytest.raises(ChunkBufferError, match="after close"):
            buf.write(b"x")

    def test_get_body_after_close(self) -> None:
        """get_body() after close() raises with 'after close' message."""
        buf = ChunkBuffer()
        buf.open()
        buf.close()
        with pytest.raises(ChunkBufferError, match="after close"):
            buf.get_body()

    def test_size_after_close(self) -> None:
        """size() after close() raises with 'after close' message."""
        buf = ChunkBuffer()
        buf.open()
        buf.close()
        with pytest.raises(ChunkBufferError, match="after close"):
            buf.size()

    def test_write_after_get_body_frozen(self) -> None:
        """write() is forbidden after get_body() — buffer is frozen."""
        buf = ChunkBuffer()
        buf.open()
        buf.write(b"data")
        buf.get_body()
        with pytest.raises(ChunkBufferError, match="after get_body"):
            buf.write(b"more")

    def test_reopen_after_close_works(self) -> None:
        """open() after close() starts a fresh cycle."""
        buf = ChunkBuffer()
        buf.open()
        buf.write(b"first")
        buf.close()

        buf.open()
        buf.write(b"second")
        assert buf.get_body() == b"second"
        buf.close()


# ---------------------------------------------------------------------------
# take_body — consuming read
# ---------------------------------------------------------------------------


class TestChunkBufferTakeBody:
    """take_body() returns data and releases the buffer."""

    def test_take_body_returns_data(self) -> None:
        """take_body() returns all accumulated bytes."""
        buf = ChunkBuffer()
        buf.open()
        buf.write(b"payload")
        assert buf.take_body() == b"payload"

    def test_take_body_closes_buffer(self) -> None:
        """After take_body(), buffer is closed — write/get_body/size fail."""
        buf = ChunkBuffer()
        buf.open()
        buf.write(b"data")
        buf.take_body()
        with pytest.raises(ChunkBufferError, match="after close"):
            buf.write(b"x")
        with pytest.raises(ChunkBufferError, match="after close"):
            buf.get_body()
        with pytest.raises(ChunkBufferError, match="after close"):
            buf.size()

    def test_take_body_before_open(self) -> None:
        """take_body() before open() raises with 'before open' message."""
        buf = ChunkBuffer()
        with pytest.raises(ChunkBufferError, match="before open"):
            buf.take_body()

    def test_take_body_after_close(self) -> None:
        """take_body() after close() raises with 'after close' message."""
        buf = ChunkBuffer()
        buf.open()
        buf.close()
        with pytest.raises(ChunkBufferError, match="after close"):
            buf.take_body()

    def test_reopen_after_take_body(self) -> None:
        """open() after take_body() starts a fresh cycle."""
        buf = ChunkBuffer()
        buf.open()
        buf.write(b"first")
        buf.take_body()

        buf.open()
        buf.write(b"second")
        assert buf.get_body() == b"second"
        buf.close()

    def test_take_body_empty_buffer(self) -> None:
        """take_body() on empty buffer returns empty bytes."""
        buf = ChunkBuffer()
        buf.open()
        assert buf.take_body() == b""
