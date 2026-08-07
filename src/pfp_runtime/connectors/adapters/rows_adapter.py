"""Rows adapter for SourceConnector orchestration.

Responsible for passing pre-structured in-memory records through as-is,
with type validation and record count guards.
Used when the client has already performed I/O (SQL cursor, REST response)
and delivers ready-made mapping rows to PFP.
"""

from __future__ import annotations

import collections.abc
import logging
from typing import Any, Iterable, Mapping

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_utils.logging import LogPipeline


class RowsAdapter:
    """Pass pre-structured mapping records through with type validation and count guards."""

    format_name = "rows"

    def __init__(
        self,
        constants: Mapping[str, Any],
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        """Initialize adapter with format constants.

        Args:
            constants: Mapping of constants from the registry. Supports 'max_records'.
        """
        self.constants = constants
        self.max_records = constants.get("max_records", 50000)
        self._log_pipeline = log_pipeline

    def parse(self, raw_input: Any) -> Iterable[Mapping[str, Any]]:
        """Orchestrate pipeline for passing pre-structured rows.

        Steps:
        1. Validate input type (must be iterable, not str/bytes).
        2. Yield mapping records with count limit protection.

        Args:
            raw_input: Iterable of mapping records (e.g. from SQL cursor or REST response).

        Returns:
            Generator yielding individual record mappings.
        """
        self._check_input_type(raw_input)
        yield from self._yield_records(raw_input)

    def _check_input_type(self, raw_input: Any) -> None:
        """Validate that input is a proper iterable, not a raw text payload (Step 1).

        Args:
            raw_input: The incoming data to validate.

        Raises:
            AdapterFormatError: If input is str/bytes or is not iterable.
        """
        if isinstance(raw_input, (str, bytes)):
            raise AdapterFormatError(
                "rows format requires an iterable of mappings, not a string or bytes. "
                "Use json or csv adapters for raw text payloads."
            )
        if not isinstance(raw_input, collections.abc.Iterable):
            raise AdapterFormatError("rows format requires an iterable of mappings")

    def _yield_records(self, raw_input: Iterable[Any]) -> Iterable[Mapping[str, Any]]:
        """Iterate records, skip non-mapping items and enforce count limit (Step 2).

        Non-mapping items (scalars, lists) are logged as warnings and skipped.
        When the total number of iterated items reaches max_records, an error is raised.

        Args:
            raw_input: Validated iterable of arbitrary items.

        Returns:
            Generator yielding only mapping records.

        Raises:
            AdapterFormatError: If record count exceeds max_records.
        """
        for i, item in enumerate(raw_input):
            if i >= self.max_records:
                raise AdapterFormatError(
                    f"Record count exceeds maximum limit of {self.max_records}"
                )
            if isinstance(item, Mapping):
                yield dict(item)
            else:
                self._log_pipeline.log_process(
                    logging.WARNING,
                    __name__,
                    "Skipped non-mapping row",
                    extra={"row_index": i},
                )
