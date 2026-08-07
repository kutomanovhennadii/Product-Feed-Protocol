"""Common writer-layer type contracts.

This module centralizes shared types used by:
- `writer_base.py` for the writer protocol signatures,
- `writer_registry.py` for factory wiring and public APIs,
- `csv_writer.py` and `jsonl_writer.py` for concrete writer inputs/config.

`ArtifactMeta` defines the minimal artifact keys consumed by writer implementations.
All keys are optional because writers apply deterministic defaults.
"""

from typing import Iterable, Mapping, Tuple, Union

from typing_extensions import TypedDict

WriterId = str
BytesIterable = Iterable[bytes]
CsvRow = Tuple[object, ...]
JsonObject = Mapping[str, object]
WriterRecord = Union[CsvRow, JsonObject]
WriterConfig = Mapping[str, object]
MISSING = object()


class ArtifactMeta(TypedDict, total=False):
    """Minimal artifact metadata required by writer implementations."""

    encoding: str
    content_type: str
    file_extension: str
