"""CSV writer implementation for schema-driven output."""

import csv
import io
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple, cast

from pfp_core.writers.writer_types import (
    MISSING,
    ArtifactMeta,
    BytesIterable,
    CsvRow,
    WriterConfig,
)


class CSVWriter:
    """Streaming CSV serializer producing deterministic bytes chunks."""

    writer_id = "csv"

    def __init__(
        self,
        writer_config: WriterConfig,
        artifact_meta: ArtifactMeta,
        columns: Optional[Tuple[str, ...]] = None,
    ) -> None:
        """Initialize CSV writer with deterministic serialization options.

        Args:
            writer_config: CSV writer configuration.
            artifact_meta: Artifact metadata describing output format.
            columns: Optional ordered column names from mapping plan.

        Returns:
            None.

        Raises:
            ValueError: If include_header is enabled without available columns.
        """
        self.content_type = str(artifact_meta.get("content_type", "text/csv"))
        self.file_extension = str(artifact_meta.get("file_extension", ".csv"))
        self.encoding = str(artifact_meta.get("encoding", "utf-8"))

        self._delimiter = str(writer_config.get("delimiter", ","))
        self._quotechar = str(writer_config.get("quotechar", '"'))
        escapechar_obj = writer_config.get("escapechar")
        self._escapechar = str(escapechar_obj) if escapechar_obj is not None else None
        self._line_terminator = str(writer_config.get("line_terminator", "\n"))
        self._include_header = bool(writer_config.get("include_header", False))
        self._missing_value_marker = self._read_marker(
            writer_config=writer_config,
            key="missing_value_marker",
        )
        self._null_value_marker = self._read_marker(
            writer_config=writer_config,
            key="null_value_marker",
        )

        config_columns = self._parse_columns(writer_config)
        self._columns = config_columns if config_columns is not None else columns

        if self._include_header and self._columns is None:
            raise ValueError("csv writer error: columns_required include_header=true")

    def write(self, records: Iterable[object]) -> BytesIterable:
        """Serialize CSV rows into lazy encoded line chunks.

        Args:
            records: Input iterable of runtime row objects.

        Returns:
            Lazy iterable of encoded CSV payload chunks.
        """

        return self._write_iter(records)

    def _write_iter(self, records: Iterable[object]) -> Iterator[bytes]:
        """Serialize records into per-line encoded chunks.

        Args:
            records: Input CSV rows.

        Returns:
            Iterator yielding encoded CSV chunks.

        Raises:
            ValueError: If row shape or marker rules violate writer contract.
        """
        buffer = io.StringIO()
        writer = csv.writer(
            buffer,
            delimiter=self._delimiter,
            quotechar=self._quotechar,
            escapechar=self._escapechar,
            lineterminator=self._line_terminator,
            quoting=csv.QUOTE_MINIMAL,
        )

        if self._include_header:
            columns = cast(Tuple[str, ...], self._columns)
            writer.writerow(list(columns))
            yield self._consume_buffer(buffer)

        saw_missing = False
        saw_none = False
        for row in records:
            csv_row = self._coerce_row(row)
            if self._columns is not None and len(csv_row) != len(self._columns):
                raise ValueError(
                    "csv writer error: row_size_mismatch expected="
                    + str(len(self._columns))
                    + " got="
                    + str(len(csv_row))
                )
            serialized, saw_missing, saw_none = self._serialize_row(
                row=csv_row,
                saw_missing=saw_missing,
                saw_none=saw_none,
            )
            writer.writerow(serialized)
            yield self._consume_buffer(buffer)

    def _consume_buffer(self, buffer: io.StringIO) -> bytes:
        """Read and reset one-row text buffer.

        Args:
            buffer: Mutable text buffer used by csv.writer.

        Returns:
            Encoded bytes currently written into the buffer.
        """
        payload = buffer.getvalue().encode(self.encoding)
        buffer.seek(0)
        buffer.truncate(0)
        return payload

    @staticmethod
    def _parse_columns(writer_config: WriterConfig) -> Optional[Tuple[str, ...]]:
        """Parse optional column list from writer configuration.

        Args:
            writer_config: CSV writer configuration mapping.

        Returns:
            Tuple of column names if configured, otherwise None.

        Raises:
            ValueError: If columns value is not a sequence of strings.
        """
        columns_obj = writer_config.get("columns")
        if columns_obj is None:
            return None
        if not isinstance(columns_obj, Sequence) or isinstance(columns_obj, str):
            raise ValueError("csv writer error: columns_type expected=sequence[str]")
        columns: List[str] = []
        for item in columns_obj:
            if not isinstance(item, str):
                raise ValueError("csv writer error: columns_value_type expected=str")
            columns.append(item)
        return tuple(columns)

    @staticmethod
    def _coerce_row(row: object) -> CsvRow:
        """Validate and cast runtime row value into CsvRow.

        Args:
            row: Runtime row candidate.

        Returns:
            Validated CsvRow tuple.

        Raises:
            ValueError: If row is not a tuple.
        """
        if not isinstance(row, tuple):
            raise ValueError("csv writer error: row_type expected=tuple")
        return tuple(row)

    @staticmethod
    def _read_marker(writer_config: WriterConfig, key: str) -> str:
        """Read marker configuration value as string.

        Args:
            writer_config: CSV writer configuration mapping.
            key: Marker key to read from config.

        Returns:
            Marker string.

        Raises:
            ValueError: If marker value is not a string.
        """
        marker = writer_config.get(key, "")
        if not isinstance(marker, str):
            raise ValueError(
                "csv writer error: marker_type key=" + key + " expected=str"
            )
        return marker

    def _serialize_row(
        self,
        row: CsvRow,
        saw_missing: bool,
        saw_none: bool,
    ) -> Tuple[List[str], bool, bool]:
        """Serialize one row while tracking Missing/None marker usage.

        Args:
            row: Input CSV row.
            saw_missing: Whether Missing was observed in earlier values.
            saw_none: Whether None was observed in earlier values.

        Returns:
            Tuple of serialized values and updated marker-observation flags.

        Raises:
            ValueError: If marker conflict is detected.
        """
        result: List[str] = []
        for value in row:
            if value is MISSING:
                saw_missing = True
            if value is None:
                saw_none = True
            self._validate_marker_distinction(
                saw_missing=saw_missing,
                saw_none=saw_none,
            )
            result.append(self._serialize_value(value))
        return result, saw_missing, saw_none

    def _validate_marker_distinction(self, saw_missing: bool, saw_none: bool) -> None:
        """Ensure Missing and None remain distinguishable when both are present.

        Args:
            saw_missing: Whether Missing marker was observed.
            saw_none: Whether None marker was observed.

        Returns:
            None.

        Raises:
            ValueError: If both values are present and markers are identical.
        """
        if (
            saw_missing
            and saw_none
            and self._missing_value_marker == self._null_value_marker
        ):
            raise ValueError(
                "csv writer error: marker_conflict missing_value_marker="
                + repr(self._missing_value_marker)
                + " null_value_marker="
                + repr(self._null_value_marker)
            )

    def _serialize_value(self, value: object) -> str:
        """Serialize one Python value into deterministic CSV field text.

        Args:
            value: Input value to serialize.

        Returns:
            Serialized field text.
        """
        if value is MISSING:
            return self._missing_value_marker
        if value is None:
            return self._null_value_marker
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)
