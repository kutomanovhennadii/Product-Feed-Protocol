"""Streaming JSON adapter for SourceConnector orchestration.

Responsible for memory-safe streaming of large JSON structures using ijson.
Requires byte stream (IO[bytes] or Iterable[bytes]) to prevent memory exhaustion.
"""

from __future__ import annotations

import logging
from typing import IO, Any, Iterable, Iterator, Mapping, Protocol

try:
    import ijson  # type: ignore[import-not-found, import-untyped]
except ModuleNotFoundError:  # pragma: no cover
    ijson = None

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_utils.logging import LogPipeline


class _IterableBytesReader:
    """File-like wrapper for Iterable[bytes] to satisfy ijson's .read() contract."""

    def __init__(self, chunks: Iterable[bytes]) -> None:
        self._iterator: Iterator[bytes] = iter(chunks)
        self._buffer = bytearray()

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            parts = [bytes(self._buffer)] if self._buffer else []
            self._buffer.clear()
            for chunk in self._iterator:
                if not isinstance(chunk, (bytes, bytearray)):
                    raise TypeError("Iterable[bytes] yielded non-bytes chunk")
                parts.append(bytes(chunk))
            return b"".join(parts)

        while len(self._buffer) < n:
            try:
                chunk = next(self._iterator)
            except StopIteration:
                break
            if not isinstance(chunk, (bytes, bytearray)):
                raise TypeError("Iterable[bytes] yielded non-bytes chunk")
            self._buffer.extend(chunk)

        out = bytes(self._buffer[:n])
        del self._buffer[:n]
        return out


class _ByteReadable(Protocol):
    def read(self, n: int = -1) -> bytes: ...


class StreamingJsonAdapter:
    """Parse extremely large JSON payload from byte streams into mapping records."""

    format_name = "streaming_json"

    def __init__(
        self,
        constants: Mapping[str, Any],
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        """Initialize adapter with format constants.

        Args:
            constants: Must include 'items_path'.
        """
        self.constants = constants
        self.items_path = constants.get("items_path", "item")
        self.max_record_bytes = constants.get("max_record_bytes", 1048576)
        self._log_pipeline = log_pipeline

    def parse(
        self, raw_input: IO[bytes] | Iterable[bytes]
    ) -> Iterable[Mapping[str, Any]]:
        """Orchestrate pipeline for stream-parsing JSON input.

        Steps:
        1. Validate byte stream interface.
        2. Safe parsing via ijson.
        3. Filter, validate mappings and yield.

        Args:
            raw_input: Raw JSON byte stream (`IO[bytes]` or `Iterable[bytes]`).

        Returns:
            Generator yielding individual record mappings.
        """
        if ijson is None:
            raise AdapterFormatError(
                "Missing dependency: 'ijson' is required for streaming_json adapter"
            )

        stream = self._ensure_byte_stream(raw_input)
        item_generator = self._safe_ijson_parse(stream)
        yield from self._yield_record_mappings(item_generator)

    def _ensure_byte_stream(self, raw_input: Any) -> _ByteReadable:
        """Validate that input is a valid byte stream (Step 1).

        Args:
            raw_input: Target data.

        Returns:
            The valid byte stream.

        Raises:
            AdapterFormatError: If input is fully loaded in memory (str/bytes)
                or not a valid stream.
        """
        if isinstance(raw_input, (str, bytes)):
            raise AdapterFormatError(
                "streaming_json format requires a byte stream (IO[bytes] or Iterable[bytes]), "
                "not an in-memory string or bytes object."
            )

        if hasattr(raw_input, "read"):
            return raw_input  # type: ignore[return-value]

        if isinstance(raw_input, Iterable):
            return _IterableBytesReader(raw_input)

        raise AdapterFormatError(
            "Input must implement .read() (IO[bytes]) or be an Iterable[bytes]"
        )

    def _safe_ijson_parse(self, stream: _ByteReadable) -> Iterable[Any]:
        """Wrap ijson parser with safety boundaries (Step 2).

        Args:
            stream: Input byte stream.

        Returns:
            Generator of parsed items payload.

        Raises:
            AdapterFormatError: If syntax error occurs, shielding raw payload.
        """
        if ijson is None:  # pragma: no cover
            raise AdapterFormatError(
                "Missing dependency: 'ijson' is required for streaming_json adapter"
            )
        try:
            for item in ijson.items(stream, self.items_path):
                yield item
        except Exception as e:
            # ijson specific exceptions inherit from Exception, we mask data.
            self._log_pipeline.log_process(
                logging.ERROR,
                __name__,
                "Failed to parse streaming JSON payload",
                exc_info=e,
            )
            raise AdapterFormatError("Failed to decode JSON stream payload") from e

    def _yield_record_mappings(
        self, items: Iterable[Any]
    ) -> Iterable[Mapping[str, Any]]:
        """Iterate objects, ensuring mapping type and skipping scalars (Step 3).

        Args:
            items: Generator from ijson.

        Returns:
            Generator of valid dict mappings.
        """
        for i, item in enumerate(items):
            if isinstance(item, Mapping):
                yield dict(item)
            else:
                self._log_pipeline.log_process(
                    logging.WARNING,
                    __name__,
                    "Skipped non-mapping item",
                    extra={"record_index": i},
                )
