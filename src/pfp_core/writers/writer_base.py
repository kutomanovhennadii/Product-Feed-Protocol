"""Writer interface definitions."""

from typing import Iterable, Protocol

from pfp_core.writers.writer_types import BytesIterable


class Writer(Protocol):
    """Protocol for schema-selected writer modules.

    Attributes:
        writer_id: Stable writer identifier.
        content_type: MIME type for the produced artifact.
        file_extension: File extension for the produced artifact.
        encoding: Text encoding used for byte serialization.
    """

    writer_id: str
    content_type: str
    file_extension: str
    encoding: str

    def write(self, records: Iterable[object]) -> BytesIterable:
        """Serialize prepared records into lazy bytes chunks.

        Args:
            records: Prepared records ready for output serialization.

        Returns:
            Lazy iterable of encoded bytes chunks.
        """
        ...
