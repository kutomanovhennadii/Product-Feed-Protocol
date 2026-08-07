"""JSONL writer implementation for schema-driven output."""

import json
from collections.abc import Mapping as MappingABC
from typing import Iterable, Iterator

from pfp_core.writers.writer_types import (
    MISSING,
    ArtifactMeta,
    BytesIterable,
    JsonObject,
    WriterConfig,
)


class JSONLWriter:
    """Streaming JSONL serializer producing deterministic bytes chunks."""

    writer_id = "jsonl"

    def __init__(
        self,
        writer_config: WriterConfig,
        artifact_meta: ArtifactMeta,
    ) -> None:
        """Initialize JSONL writer with deterministic serialization options.

        Args:
            writer_config: JSONL writer configuration mapping.
            artifact_meta: Artifact metadata describing output format.

        Returns:
            None.
        """
        self.content_type = str(
            artifact_meta.get("content_type", "application/x-ndjson")
        )
        self.file_extension = str(artifact_meta.get("file_extension", ".jsonl"))
        self.encoding = str(artifact_meta.get("encoding", "utf-8"))

        self._ensure_ascii = bool(writer_config.get("ensure_ascii", False))
        self._sort_keys = bool(writer_config.get("sort_keys", False))
        self._omit_nulls = bool(writer_config.get("omit_nulls", False))
        self._line_terminator = str(writer_config.get("line_terminator", "\n"))

    def write(self, records: Iterable[object]) -> BytesIterable:
        """Serialize mapping objects into lazy JSONL chunks.

        Args:
            records: Iterable of mapping objects prepared by mapping stage.

        Returns:
            Lazy iterable of encoded JSONL chunks.
        """

        return self._write_iter(records)

    def _write_iter(self, records: Iterable[object]) -> Iterator[bytes]:
        """Serialize records into one JSON object per output chunk.

        Args:
            records: Iterable of JSON-compatible mapping objects.

        Returns:
            Iterator yielding encoded JSONL lines.

        Raises:
            ValueError: If a record is not a mapping or JSON serialization fails.
        """
        for record in records:
            if not isinstance(record, MappingABC):
                raise ValueError("JSONLWriter record must be a mapping object.")

            filtered = self._filter_record(record)
            try:
                payload = json.dumps(
                    filtered,
                    ensure_ascii=self._ensure_ascii,
                    sort_keys=self._sort_keys,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            except ValueError as exc:
                raise ValueError("JSONL serialization failed: " + str(exc)) from exc
            yield (payload + self._line_terminator).encode(self.encoding)

    def _filter_record(self, record: JsonObject) -> JsonObject:
        """Filter one record according to Missing/null policy.

        Args:
            record: Input mapping object.

        Returns:
            Filtered mapping used for JSON serialization.

        Raises:
            ValueError: If record contains a non-string key.
        """
        output = {}
        for key, value in record.items():
            if not isinstance(key, str):
                raise ValueError("JSONLWriter object keys must be strings.")
            if value is MISSING:
                continue
            if self._omit_nulls and value is None:
                continue
            output[key] = value
        return output
