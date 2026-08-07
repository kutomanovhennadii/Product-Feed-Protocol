"""Models for built-in schema manifest documents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

SCHEMA_MANIFEST_VERSION = 1


class SchemaManifestError(ValueError):
    """Raised when schema manifest generation or verification fails."""


@dataclass(frozen=True)
class SchemaManifestEntry:
    """One built-in schema integrity record.

    Args:
        path: Relative schema path inside the schemas root.
        protocol_id: Canonical protocol identifier from schema header.
        schema_version: Canonical schema version from schema header.
        sha256: SHA-256 digest for the schema file bytes.
    """

    path: str
    protocol_id: str
    schema_version: str
    sha256: str

    def to_dict(self) -> Dict[str, str]:
        """Convert entry to JSON-serializable mapping."""

        return {
            "path": self.path,
            "protocol_id": self.protocol_id,
            "schema_version": self.schema_version,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class SchemaManifestDocument:
    """Canonical manifest representation for built-in schemas."""

    version: int
    entries: Tuple[SchemaManifestEntry, ...]

    def to_dict(self) -> Dict[str, Any]:
        """Convert document to JSON-serializable mapping."""

        return {
            "version": self.version,
            "entries": [entry.to_dict() for entry in self.entries],
        }


def parse_manifest_document(data: Mapping[str, Any]) -> SchemaManifestDocument:
    """Validate and parse manifest mapping into a typed document."""

    version = data.get("version")
    if not isinstance(version, int):
        raise SchemaManifestError("Manifest field 'version' must be an integer.")

    entries_raw = data.get("entries")
    if not isinstance(entries_raw, list):
        raise SchemaManifestError("Manifest field 'entries' must be a list.")

    entries: List[SchemaManifestEntry] = []
    for index, item in enumerate(entries_raw):
        if not isinstance(item, Mapping):
            raise SchemaManifestError(
                "Manifest entry at index {0} must be an object.".format(index)
            )

        path = item.get("path")
        protocol_id = item.get("protocol_id")
        schema_version = item.get("schema_version")
        sha256 = item.get("sha256")

        if not isinstance(path, str) or not path:
            raise SchemaManifestError(
                "Manifest entry at index {0} has invalid 'path'.".format(index)
            )
        if not isinstance(protocol_id, str) or not protocol_id:
            raise SchemaManifestError(
                "Manifest entry at index {0} has invalid 'protocol_id'.".format(index)
            )
        if not isinstance(schema_version, str) or not schema_version:
            raise SchemaManifestError(
                "Manifest entry at index {0} has invalid 'schema_version'.".format(
                    index
                )
            )
        if not isinstance(sha256, str) or not sha256:
            raise SchemaManifestError(
                "Manifest entry at index {0} has invalid 'sha256'.".format(index)
            )

        entries.append(
            SchemaManifestEntry(
                path=path,
                protocol_id=protocol_id,
                schema_version=schema_version,
                sha256=sha256,
            )
        )

    return SchemaManifestDocument(version=version, entries=tuple(entries))
