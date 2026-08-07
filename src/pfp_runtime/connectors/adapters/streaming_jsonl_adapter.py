"""Streaming JSON Lines (JSONL) adapter for SourceConnector orchestration.

Responsible for memory-safe streaming of large JSONL files.
Accepts a text stream (IO[str] or Iterable[str]) so each line is read and
processed individually — the full file is never loaded into RAM.

Use this adapter when the client opens a file handle (e.g. gzip.open in "rt" mode)
and passes it directly. Use JsonlAdapter for small payloads already in memory.
"""

from __future__ import annotations

import collections.abc
import json
import logging
from typing import IO, Any, Iterable, Mapping, Optional, Union

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_utils.logging import LogPipeline


class StreamingJsonlAdapter:
    """Parse extremely large JSONL payloads from text streams into mapping records.

    Processes one line at a time — peak memory usage is a single line plus its
    parsed dict, independent of total file size.
    """

    format_name = "streaming_jsonl"

    def __init__(
        self,
        constants: Mapping[str, Any],
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        """Initialize adapter with format constants.

        Args:
            constants: Mapping of constants from the registry.
                Supports 'max_line_bytes', 'max_json_depth', 'max_json_container_items'.
        """
        self.constants = constants
        self.max_line_bytes = constants.get("max_line_bytes", 262144)
        self.max_json_depth = constants.get("max_json_depth", 32)
        self.max_json_container_items = constants.get(
            "max_json_container_items", 100000
        )
        self._log_pipeline = log_pipeline

    def parse(
        self, raw_input: Union[IO[str], Iterable[str]]
    ) -> Iterable[Mapping[str, Any]]:
        """Orchestrate pipeline for stream-parsing JSONL input line by line.

        Steps:
        1. Validate input type (must be a text stream, not str/bytes).
        2. Iterate lines one-by-one from the stream.
        3. Check per-line memory limit.
        4. Safe deserialization of a single line.
        5. Structural validation (tree depth & containers).
        6. Type check and yield mapping.

        Args:
            raw_input: Open text stream or line iterator
                (e.g. ``gzip.open("feed.jsonl.gz", "rt")``).

        Returns:
            Generator yielding individual record mappings.
        """
        self._ensure_text_stream(raw_input)

        for i, line in enumerate(raw_input):
            if not line.strip():
                continue

            self._check_line_length(line, i)
            parsed_data = self._safe_deserialize_line(line, i)
            self._validate_tree_limits(parsed_data, i)

            record = self._extract_mapping(parsed_data, i)
            if record is not None:
                yield record

    def _ensure_text_stream(self, raw_input: Any) -> None:
        """Validate that input is a text stream, not an in-memory payload (Step 1).

        Strings are rejected: a plain str is an in-memory payload and belongs in
        JsonlAdapter. Bytes are rejected: the client must open the stream in text
        mode ("rt") to handle encoding before passing it here.

        Args:
            raw_input: The incoming data to validate.

        Raises:
            AdapterFormatError: If input is str, bytes, or not iterable.
        """
        if isinstance(raw_input, str):
            raise AdapterFormatError(
                "streaming_jsonl requires a text stream (IO[str] or Iterable[str]), "
                "not an in-memory string. Use JsonlAdapter for small in-memory payloads."
            )
        if isinstance(raw_input, bytes):
            raise AdapterFormatError(
                "streaming_jsonl requires a text stream (IO[str] or Iterable[str]), "
                "not bytes. Open the stream in text mode ('rt') before passing it here."
            )
        if not isinstance(raw_input, collections.abc.Iterable):
            raise AdapterFormatError(
                "streaming_jsonl requires an iterable text stream (IO[str] or Iterable[str])"
            )

    def _check_line_length(self, line: str, index: int) -> None:
        """Check a single line size against the per-line memory limit (Step 3).

        Args:
            line: A single JSONL line.
            index: The 0-based index of the line.

        Raises:
            AdapterFormatError: If the line exceeds max_line_bytes.
        """
        length = len(line.encode("utf-8", errors="ignore"))
        if length > self.max_line_bytes:
            raise AdapterFormatError(
                f"Line {index} length {length} bytes exceeds maximum limit of {self.max_line_bytes} bytes"
            )

    def _safe_deserialize_line(self, line: str, index: int) -> Any:
        """Parse a single JSON line safely, masking payload from errors (Step 4).

        Args:
            line: A single JSONL line.
            index: The 0-based index of the line.

        Returns:
            Deserialized JSON structure.

        Raises:
            AdapterFormatError: If the JSON payload cannot be decoded.
        """
        try:
            return json.loads(line)
        except Exception as e:
            # Mask the original line to avoid PII exposure in logs.
            self._log_pipeline.log_process(
                logging.ERROR,
                __name__,
                "Failed to decode JSONL line",
                exc_info=e,
                extra={"line_index": index},
            )
            raise AdapterFormatError(
                f"Failed to decode JSON payload at line {index}"
            ) from e

    def _validate_tree_limits(self, data: Any, index: int) -> None:
        """Validate parsed tree structure against depth and container limits (Step 5).

        Args:
            data: Deserialized JSON data for a single line.
            index: The 0-based index of the line.

        Raises:
            AdapterFormatError: If tree depth or container element limits are exceeded.
        """
        max_depth = self.max_json_depth
        max_items = self.max_json_container_items

        def _traverse(node: Any, current_depth: int) -> None:
            if current_depth > max_depth:
                raise AdapterFormatError(
                    f"JSON depth {current_depth} at line {index} exceeds maximum limit of {max_depth}"
                )
            if isinstance(node, dict):
                if len(node) > max_items:
                    raise AdapterFormatError(
                        f"JSON object item count {len(node)} at line {index} exceeds maximum limit of {max_items}"
                    )
                for val in node.values():
                    _traverse(val, current_depth + 1)
            elif isinstance(node, list):
                if len(node) > max_items:
                    raise AdapterFormatError(
                        f"JSON array item count {len(node)} at line {index} exceeds maximum limit of {max_items}"
                    )
                for item in node:
                    _traverse(item, current_depth + 1)

        try:
            _traverse(data, 1)
        except RecursionError as e:
            raise AdapterFormatError(
                f"JSON depth exceeds internal system limits (RecursionError) at line {index}"
            ) from e

    def _extract_mapping(self, data: Any, index: int) -> Optional[Mapping[str, Any]]:
        """Extract a single mapping record, ignoring scalars and lists at root (Step 6).

        Args:
            data: Fully validated JSON data structure.
            index: The 0-based index of the line.

        Returns:
            Mapping object if data is a dictionary, otherwise None.
        """
        if isinstance(data, Mapping):
            return dict(data)

        self._log_pipeline.log_process(
            logging.WARNING,
            __name__,
            "Skipped non-mapping jsonl line",
            extra={"line_index": index},
        )
        return None
