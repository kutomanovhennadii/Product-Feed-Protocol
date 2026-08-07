"""JSON adapter for SourceConnector orchestration.

Responsible for safe reading of arbitrary nested JSON (within limits)
and extracting an array of records (via items_path) in streaming mode.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Iterable, Mapping

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_utils.logging import LogPipeline


class JsonAdapter:
    """Parses JSON payload from raw strings or bytes into mapping records."""

    format_name = "json"

    def __init__(
        self,
        constants: Mapping[str, Any],
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        """Initialize the adapter with security configuration.

        Args:
            constants: Mapping with limits. Must include 'max_input_bytes'. Optional: 'items_path'.
        """
        self.constants = constants
        self.max_input_bytes = constants.get(
            "max_input_bytes", 33554432
        )  # Default 32MB
        self.max_json_depth = constants.get("max_json_depth", 32)
        self.max_json_container_items = constants.get(
            "max_json_container_items", 100000
        )
        self.items_path = constants.get("items_path")
        self._log_pipeline = log_pipeline

    def parse(self, raw_input: str | bytes) -> Iterable[Mapping[str, Any]]:
        """Orchestrate pipeline for parsing JSON input records.

        Steps:
        1. Check memory limit.
        2. Safe deserialization.
        3. Validate structural limits (depth and container sizes).
        4. Locate target array via items_path.
        5. Yield streaming dictionaries.

        Args:
            raw_input: Raw JSON payload string or bytes.

        Returns:
            Generator yielding individual record mappings.
        """
        self._check_input_limits(raw_input)
        parsed_data = self._safe_deserialize(raw_input)
        self._validate_tree_limits(parsed_data)
        items_array = self._locate_items_array(parsed_data)
        yield from self._yield_record_mappings(items_array)

    def _check_input_limits(self, raw_input: str | bytes) -> None:
        """Check raw input data limits (Step 1).

        Args:
            raw_input: Raw JSON payload.

        Raises:
            AdapterFormatError: If input type is wrong or exceeds max_input_bytes.
        """
        if not isinstance(raw_input, (str, bytes)):
            raise AdapterFormatError("raw_input must be a string or bytes")

        length = (
            len(raw_input)
            if isinstance(raw_input, bytes)
            else len(raw_input.encode("utf-8", errors="ignore"))
        )

        if length > self.max_input_bytes:
            raise AdapterFormatError(
                f"Input size {length} bytes exceeds maximum limit of {self.max_input_bytes} bytes"
            )

    def _safe_deserialize(self, raw_input: str | bytes) -> Any:
        """Parse JSON safely masking payload from internal errors (Step 2).

        Args:
            raw_input: Raw JSON payload.

        Returns:
            Deserialized JSON structure.

        Raises:
            AdapterFormatError: If JSON decoding fails.
        """
        text = raw_input if isinstance(raw_input, str) else raw_input.decode("utf-8")
        try:
            return json.loads(text)
        except Exception as e:
            # Mask raw_input to avoid PII exposure.
            raise AdapterFormatError("Failed to decode JSON payload") from e

    def _validate_tree_limits(self, data: Any) -> None:
        """Validate structure against maximum tree depth and item counts limits (Step 3).

        Args:
            data: Deserialized JSON structure.

        Raises:
            AdapterFormatError: If tree depth or container constraints are exceeded.
        """
        max_depth = self.max_json_depth
        max_items = self.max_json_container_items

        def _traverse(node: Any, current_depth: int) -> None:
            if current_depth > max_depth:
                raise AdapterFormatError(
                    f"JSON depth {current_depth} exceeds maximum limit of {max_depth}"
                )

            if isinstance(node, dict):
                if len(node) > max_items:
                    raise AdapterFormatError(
                        f"JSON object item count {len(node)} exceeds maximum limit of {max_items}"
                    )
                for val in node.values():
                    _traverse(val, current_depth + 1)
            elif isinstance(node, list):
                if len(node) > max_items:
                    raise AdapterFormatError(
                        f"JSON array item count {len(node)} exceeds maximum limit of {max_items}"
                    )
                for item in node:
                    _traverse(item, current_depth + 1)

        try:
            _traverse(data, 1)
        except RecursionError as e:
            raise AdapterFormatError(
                "JSON depth exceeds internal system limits (RecursionError)"
            ) from e

    def _locate_items_array(self, parsed_data: Any) -> list[Any]:
        """Locate items array in the structure using items_path (Step 4).

        Args:
            parsed_data: Fully validated JSON structure.

        Returns:
            List of objects found at items_path or root.

        Raises:
            AdapterFormatError: If path is missing or does not resolve to a list.
        """
        target: Any = parsed_data

        if self.items_path:
            parts = self.items_path.split(".")
            for part in parts:
                if isinstance(target, dict) and part in target:
                    target = target[part]
                else:
                    raise AdapterFormatError(
                        f"Path '{self.items_path}' not found in JSON data"
                    )
        else:
            if isinstance(target, dict):
                return [target]

        if not isinstance(target, list):
            raise AdapterFormatError("Target items location does not contain an array")

        return target

    def _yield_record_mappings(
        self, items_array: list[Any]
    ) -> Iterable[Mapping[str, Any]]:
        """Yield mapping records and log skipping of invalid types (Step 5).

        Args:
            items_array: List of arbitrary JSON items.

        Returns:
            Generator yielding only items that are proper mappings.
        """
        for i, item in enumerate(items_array):
            if isinstance(item, Mapping):
                yield dict(item)
            else:
                self._log_pipeline.log_process(
                    logging.WARNING,
                    __name__,
                    "Skipped non-mapping item",
                    extra={"index": i},
                )
