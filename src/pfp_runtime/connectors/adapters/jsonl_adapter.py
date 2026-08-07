"""JSON Lines (JSONL) adapter for SourceConnector orchestration."""

from __future__ import annotations

import json
import logging
from typing import Any, Iterable, Mapping

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_utils.logging import LogPipeline


class JsonlAdapter:
    """Parse JSONL payload from raw input strings or bytes into mappings."""

    format_name = "jsonl"

    def __init__(
        self,
        constants: Mapping[str, Any],
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        """Initialize adapter with format constants.

        Args:
            constants: Must include 'max_line_bytes', 'max_json_depth', 'max_json_container_items'.
        """
        self.constants = constants
        self.max_line_bytes = constants.get("max_line_bytes", 262144)  # Default 256KB
        self.max_json_depth = constants.get("max_json_depth", 32)
        self.max_json_container_items = constants.get(
            "max_json_container_items", 100000
        )
        self._log_pipeline = log_pipeline

    def parse(self, raw_input: str | bytes) -> Iterable[Mapping[str, Any]]:
        """Orchestrate pipeline for parsing JSONL input to records line by line.

        Steps:
        1. Line streaming (iterator creation).
        2. Single line memory limit protection.
        3. Safe deserialization of a single line.
        4. Structural validation (tree depth & containers).
        5. Type check and yield mapping.

        Args:
            raw_input: Raw JSONL payload string or bytes.

        Returns:
            Generator yielding individual record mappings.
        """
        lines_iterator = self._iter_lines(raw_input)

        for i, line in enumerate(lines_iterator):
            if not line.strip():
                continue

            self._check_line_length(line, i)
            parsed_data = self._safe_deserialize_line(line, i)
            self._validate_tree_limits(parsed_data, i)

            record = self._extract_mapping(parsed_data, i)
            if record is not None:
                yield record

    def _iter_lines(self, raw_input: str | bytes) -> Iterable[str]:
        """Convert raw input into a line iterator (Step 1).

        Args:
            raw_input: Raw JSONL payload string or bytes.

        Returns:
            Iterable of individual lines.
        """
        text = raw_input if isinstance(raw_input, str) else raw_input.decode("utf-8")
        return text.splitlines()

    def _check_line_length(self, line: str, index: int) -> None:
        """Check a single line size against limits (Step 2).

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
        """Parse JSON line safely and hide payload from errors (Step 3).

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
            # Mask the original line to avoid PII exposure.
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
        """Validate parsed tree structure against depth and container limits (Step 4).

        Args:
            data: Deserialized JSON data for a single line.
            index: The 0-based index of the line.

        Raises:
            AdapterFormatError: If tree depth or container elements limits are exceeded.
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

    def _extract_mapping(self, data: Any, index: int) -> Mapping[str, Any] | None:
        """Extract a single mapping record, ignoring scalars/lists at root (Step 5).

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
