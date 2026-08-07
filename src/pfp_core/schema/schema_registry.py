"""In-memory schema registry with deterministic schema contract errors."""

from __future__ import annotations

from typing import Optional

from pfp_core.schema.schema_contract import validate_schema_doc_format
from pfp_core.schema.schema_refs import extract_ref_from_doc, extract_ref_from_filename
from pfp_core.schema.schema_types import (
    SchemaDoc,
    SchemaErrorItem,
    SchemaFormatError,
    SchemaNotFoundError,
    SchemaRef,
)


class SchemaRegistry:
    """Store schema documents indexed by ``(protocol_id, schema_version)``."""

    def __init__(self) -> None:
        """Initialize empty in-memory schema storage."""

        self._docs: dict[tuple[str, str], SchemaDoc] = {}
        self._versions: dict[str, set[str]] = {}

    def register(
        self,
        doc: SchemaDoc,
        *,
        source: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> None:
        """Validate and register a schema document in memory.

        Args:
            doc: Schema document mapping.
            source: Optional logical source identifier.
            filename: Optional filename used for reference extraction.

        Returns:
            None.

        Raises:
            SchemaFormatError: If format is invalid or key already exists.
        """

        expected_ref = extract_ref_from_filename(filename) if filename else None
        validate_schema_doc_format(doc, expected_ref=expected_ref)
        ref = extract_ref_from_doc(doc)
        key = (ref.protocol_id, ref.schema_version)

        if key in self._docs:
            raise SchemaFormatError(
                [
                    SchemaErrorItem(
                        code="SCHEMA_DUPLICATE",
                        path="$",
                        message=(
                            "Schema is already registered for "
                            f"protocol_id='{ref.protocol_id}', schema_version='{ref.schema_version}'."
                        ),
                    )
                ],
                schema_ref=ref,
                source=_build_error_source(source=source, filename=filename),
            )

        self._docs[key] = doc
        self._versions.setdefault(ref.protocol_id, set()).add(ref.schema_version)

    def list(self, protocol_id: str) -> list[str]:
        """List known versions for a protocol.

        Args:
            protocol_id: Canonical protocol identifier.

        Returns:
            Lexicographically sorted versions or an empty list when missing.
        """

        versions = self._versions.get(protocol_id)
        if not versions:
            return []
        # Lexicographic order is contract for now; SemVer order not required in Story 6b.2.
        return sorted(versions)

    def get(self, protocol_id: str, schema_version: str) -> SchemaDoc:
        """Return a registered schema document by key.

        Args:
            protocol_id: Canonical protocol identifier.
            schema_version: Schema version string.

        Returns:
            Registered schema document.

        Raises:
            SchemaNotFoundError: If no schema is registered for the key.
        """

        key = (protocol_id, schema_version)
        if key not in self._docs:
            raise SchemaNotFoundError(
                SchemaRef(protocol_id=protocol_id, schema_version=schema_version)
            )
        return self._docs[key]

    def validate(self, doc: SchemaDoc, *, filename: Optional[str] = None) -> None:
        """Validate schema document format without registering it.

        Args:
            doc: Schema document mapping.
            filename: Optional filename for header/filename consistency check.

        Returns:
            None.

        Raises:
            SchemaFormatError: If document format is invalid.
        """

        expected_ref = extract_ref_from_filename(filename) if filename else None
        validate_schema_doc_format(doc, expected_ref=expected_ref)


def _build_error_source(
    *, source: Optional[str], filename: Optional[str]
) -> Optional[str]:
    """Compose deterministic source context for error payload.

    Args:
        source: Logical source identifier.
        filename: Filename metadata.

    Returns:
        Combined source string when both values are provided, otherwise the
        single available value or ``None``.
    """

    if source and filename:
        return f"source={source}; filename={filename}"
    if source:
        return source
    return filename
