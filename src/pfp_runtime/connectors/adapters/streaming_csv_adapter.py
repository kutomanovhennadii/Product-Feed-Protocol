"""Streaming CSV adapter for SourceConnector orchestration.

Responsible for memory-safe streaming of large CSV files.
Accepts a text stream (IO[str] or Iterable[str]) so each row is read and
processed individually — the full file is never loaded into RAM.

Use this adapter when the client opens a file handle (e.g. gzip.open in "rt" mode)
and passes it directly. Use CsvAdapter for small payloads already in memory.
"""

from __future__ import annotations

import collections.abc
import csv
import itertools
import logging
from typing import IO, Any, Iterable, List, Mapping, Union

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_utils.logging import LogPipeline


class StreamingCsvAdapter:
    """Parse extremely large CSV payloads from text streams into mapping records.

    Processes one row at a time — peak memory usage is a single row plus its
    parsed dict, independent of total file size.
    """

    format_name = "streaming_csv"

    def __init__(
        self,
        constants: Mapping[str, Any],
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        """Initialize adapter with format constants.

        Args:
            constants: Mapping of constants from the registry.
                Supports 'csv_field_size_limit', 'delimiter', 'has_header'.
        """
        self.constants = constants
        self.csv_field_size_limit = constants.get("csv_field_size_limit", 131072)
        self.delimiter = constants.get("delimiter", ",")
        self.has_header = constants.get("has_header", True)
        self._log_pipeline = log_pipeline

    def parse(
        self, raw_input: Union[IO[str], Iterable[str]]
    ) -> Iterable[Mapping[str, Any]]:
        """Orchestrate pipeline for stream-parsing CSV input row by row.

        Steps:
        1. Validate input type (must be a text stream, not str/bytes).
        2. Initialize safe DictReader directly over the stream.
        3. Process and validate header columns.
        4. Yield mapping records one at a time.

        Args:
            raw_input: Open text stream or line iterator
                (e.g. ``gzip.open("feed.csv.gz", "rt")``).

        Returns:
            Generator yielding individual record mappings.
        """
        self._ensure_text_stream(raw_input)
        reader = self._init_safe_reader(raw_input)
        columns = self._process_headers(reader)
        yield from self._yield_records(reader, columns)

    def _ensure_text_stream(self, raw_input: Any) -> None:
        """Validate that input is a text stream, not an in-memory payload (Step 1).

        Strings are rejected: a plain str is an in-memory payload and belongs in
        CsvAdapter. Bytes are rejected: the client must open the stream in text
        mode ("rt") to handle encoding before passing it here.

        Args:
            raw_input: The incoming data to validate.

        Raises:
            AdapterFormatError: If input is str, bytes, or not iterable.
        """
        if isinstance(raw_input, str):
            raise AdapterFormatError(
                "streaming_csv requires a text stream (IO[str] or Iterable[str]), "
                "not an in-memory string. Use CsvAdapter for small in-memory payloads."
            )
        if isinstance(raw_input, bytes):
            raise AdapterFormatError(
                "streaming_csv requires a text stream (IO[str] or Iterable[str]), "
                "not bytes. Open the stream in text mode ('rt') before passing it here."
            )
        if not isinstance(raw_input, collections.abc.Iterable):
            raise AdapterFormatError(
                "streaming_csv requires an iterable text stream (IO[str] or Iterable[str])"
            )

    def _init_safe_reader(
        self, raw_input: Union[IO[str], Iterable[str]]
    ) -> "csv.DictReader[str]":
        """Initialize safe streaming CSV reader directly over the input stream (Step 2).

        For has_header=True: passes the stream directly to DictReader, which reads
        the first line as column names lazily. For has_header=False: peeks at the
        first line to determine column count, generates col_0..col_N names, then
        uses itertools.chain to prepend the consumed line back into the stream.

        Args:
            raw_input: Open text stream or line iterator.

        Returns:
            Configured DictReader over the input stream.

        Raises:
            AdapterFormatError: If the CSV structure is malformed.
        """
        try:
            csv.field_size_limit(self.csv_field_size_limit)
        except Exception:
            self._log_pipeline.log_process(
                logging.DEBUG,
                __name__,
                "Fallback gracefully if system limits differ",
            )

        if self.has_header:
            return csv.DictReader(raw_input, delimiter=self.delimiter)

        # has_header=False: peek at the first line to count columns.
        # Cannot seek on non-seekable streams, so chain the line back via itertools.
        try:
            first_line = next(iter(raw_input))
        except StopIteration:
            return csv.DictReader(iter([]), delimiter=self.delimiter)

        try:
            first_row = next(csv.reader([first_line], delimiter=self.delimiter))
            cols = [f"col_{i}" for i in range(len(first_row))]
        except csv.Error as e:
            raise AdapterFormatError("Malformed CSV structure") from e

        combined: Iterable[str] = itertools.chain([first_line], raw_input)
        return csv.DictReader(combined, fieldnames=cols, delimiter=self.delimiter)

    def _process_headers(self, reader: "csv.DictReader[str]") -> List[str]:
        """Process and validate CSV column headers (Step 3).

        Args:
            reader: Initialized DictReader.

        Returns:
            List of column name strings.

        Raises:
            AdapterFormatError: If headers are missing or contain empty column names.
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
        self, reader: "csv.DictReader[str]", columns: List[str]
    ) -> Iterable[Mapping[str, Any]]:
        """Iterate DictReader and yield clean mapping records (Step 4).

        Handles row key mismatches: rows with extra values produce a None key
        (dropped with warning), rows with missing values produce None values
        (kept with warning).

        Args:
            reader: Initialized DictReader.
            columns: Extracted column fields.

        Returns:
            Generator yielding mapped records.

        Raises:
            AdapterFormatError: If the CSV structure is malformed.
        """
        iterator = enumerate(reader)
        while True:
            try:
                i, row = next(iterator)
            except StopIteration:
                break
            except csv.Error as e:
                raise AdapterFormatError("Malformed CSV structure") from e

            record: dict = dict(row)

            if None in record or any(v is None for v in record.values()):
                self._log_pipeline.log_process(
                    logging.WARNING,
                    __name__,
                    "Row keys mismatch",
                    extra={"row_index": i},
                )
                if None in record:
                    del record[None]

            clean_record: dict = {str(k): v for k, v in record.items()}
            yield clean_record
