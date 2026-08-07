"""CSV adapter for SourceConnector orchestration.

Responsible for safe in-memory reading of CSV files.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Iterable, Mapping

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_utils.logging import LogPipeline


class CsvAdapter:
    """Parse CSV payload from raw strings or bytes into mapping records."""

    format_name = "csv"

    def __init__(
        self,
        constants: Mapping[str, Any],
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        """Initialize the adapter with security configuration.

        Args:
            constants: Mapping with limits. Can include 'max_input_bytes',
                'csv_field_size_limit', 'delimiter', 'has_header'.
        """
        self.constants = constants
        self.max_input_bytes = constants.get("max_input_bytes", 33554432)
        self.csv_field_size_limit = constants.get("csv_field_size_limit", 131072)
        self.delimiter = constants.get("delimiter", ",")
        self.has_header = constants.get("has_header", True)
        self._log_pipeline = log_pipeline

    def parse(self, raw_input: str | bytes) -> Iterable[Mapping[str, Any]]:
        """Parse raw input payload into generic records.

        Args:
            raw_input: Raw string or bytes containing CSV data.

        Returns:
            Iterable yielding dictionaries representing parsed CSV rows.

        Raises:
            AdapterFormatError: If input exceeds limit or fails to decode.
        """
        self._check_input_limits(raw_input)
        reader = self._init_safe_reader(raw_input)
        columns = self._process_headers(reader)
        yield from self._yield_records(reader, columns)

    def _check_input_limits(self, raw_input: str | bytes) -> None:
        """Validate input size limits (Memory / I/O bounds).

        Args:
            raw_input: Raw string or bytes to check.

        Raises:
            AdapterFormatError: If size exceeds max_input_bytes.
        """
        length = len(raw_input)
        if length > self.max_input_bytes:
            raise AdapterFormatError(
                f"Input size {length} exceeds maximum limit of {self.max_input_bytes}"
            )

    def _init_safe_reader(self, raw_input: str | bytes) -> csv.DictReader[str]:
        """Initialize safe in-memory CSV reader.

        Args:
            raw_input: Target data.

        Returns:
            Configured DictReader over string IO.

        Raises:
            AdapterFormatError: On decoding errors.
        """
        try:
            csv.field_size_limit(self.csv_field_size_limit)
        except Exception:
            self._log_pipeline.log_process(
                logging.DEBUG,
                __name__,
                "Fallback gracefully if system limits differ",
            )

        try:
            text_data = (
                raw_input.decode("utf-8")
                if isinstance(raw_input, bytes)
                else str(raw_input)
            )
        except UnicodeDecodeError as e:
            raise AdapterFormatError("Failed to decode raw_input as utf-8") from e

        # Strip optional UTF-8 BOM (Excel-exported CSVs often start with it).
        text_data = text_data.lstrip("﻿")

        text_io = io.StringIO(text_data)

        if not self.has_header:
            peek_reader = csv.reader(text_io, delimiter=self.delimiter)
            try:
                first_row = next(peek_reader)
                cols = [f"col_{i}" for i in range(len(first_row))]
                text_io.seek(0)
                return csv.DictReader(
                    text_io, fieldnames=cols, delimiter=self.delimiter
                )
            except StopIteration:
                text_io.seek(0)
                return csv.DictReader(text_io, delimiter=self.delimiter)
            except Exception as e:
                raise AdapterFormatError("Malformed CSV structure") from e
        else:
            return csv.DictReader(text_io, delimiter=self.delimiter)

    def _process_headers(self, reader: csv.DictReader[str]) -> list[str]:
        """Process and validate csv headers.

        Args:
            reader: Initialized DictReader.

        Returns:
            List of column strings.

        Raises:
            AdapterFormatError: On missing or empty headers when expected.
        """
        try:
            cols = reader.fieldnames
        except csv.Error as e:
            raise AdapterFormatError("Malformed CSV structure") from e

        if cols is None:
            return []

        columns_list = list(cols)

        if self.has_header:
            for col in columns_list:
                if col is None or not str(col).strip():
                    raise AdapterFormatError("CSV header contains empty column names.")

        return columns_list

    def _yield_records(
        self, reader: csv.DictReader[str], columns: list[str]
    ) -> Iterable[Mapping[str, Any]]:
        """Iterate records and stream mappings.

        Args:
            reader: Initialized DictReader.
            columns: Extracted column fields.

        Returns:
            Iterable yielding mapped records.
        """
        iterator = enumerate(reader)
        while True:
            try:
                i, row = next(iterator)
            except StopIteration:
                break
            except csv.Error as e:
                raise AdapterFormatError("Malformed CSV structure") from e

            record: dict[str | None, Any] = dict(row)

            if None in record or any(v is None for v in record.values()):
                self._log_pipeline.log_process(
                    logging.WARNING,
                    __name__,
                    "Row keys mismatch",
                    extra={"row_index": i},
                )
                if None in record:
                    del record[None]

            clean_record: dict[str, Any] = {str(k): v for k, v in record.items()}
            yield clean_record
