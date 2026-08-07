"""Deterministic built-in schema manifest generation logic."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple

from pfp_core.schema.schema_manifest.manifest_models import (
    SCHEMA_MANIFEST_VERSION,
    SchemaManifestDocument,
    SchemaManifestEntry,
    SchemaManifestError,
)
from pfp_core.schema.schema_parser import parse_schema_text
from pfp_core.schema.schema_refs import extract_ref_from_doc


def collect_builtin_schema_files(schemas_root: Path) -> List[Path]:
    """Collect built-in schema files in deterministic order."""

    return sorted(schemas_root.rglob("*.yaml"), key=lambda path: path.as_posix())


def compute_file_sha256(file_path: Path) -> str:
    """Return SHA-256 digest for a file represented as lowercase hex."""

    digest = hashlib.sha256()
    digest.update(file_path.read_bytes())
    return digest.hexdigest()


def build_manifest_document(schemas_root: Path) -> SchemaManifestDocument:
    """Build typed manifest document from all built-in schema files."""

    schema_files = collect_builtin_schema_files(schemas_root)
    seen_identity: Set[Tuple[str, str]] = set()
    seen_paths: Set[str] = set()
    path_to_entry: Dict[str, SchemaManifestEntry] = {}

    for schema_file in schema_files:
        relative_path = schema_file.relative_to(schemas_root).as_posix()
        if relative_path in seen_paths:
            raise SchemaManifestError(
                "Duplicate built-in schema path in manifest source set: {0}".format(
                    relative_path
                )
            )
        seen_paths.add(relative_path)

        text = schema_file.read_text(encoding="utf-8")
        doc = parse_schema_text(text, format="yaml")
        schema_ref = extract_ref_from_doc(doc)

        identity = (schema_ref.protocol_id, schema_ref.schema_version)
        if identity in seen_identity:
            raise SchemaManifestError(
                "Duplicate schema identity for built-in schemas: protocol_id='{0}', schema_version='{1}'.".format(
                    schema_ref.protocol_id, schema_ref.schema_version
                )
            )
        seen_identity.add(identity)

        path_to_entry[relative_path] = SchemaManifestEntry(
            path=relative_path,
            protocol_id=schema_ref.protocol_id,
            schema_version=schema_ref.schema_version,
            sha256=compute_file_sha256(schema_file),
        )

    entries = tuple(path_to_entry[path] for path in sorted(path_to_entry.keys()))
    return SchemaManifestDocument(version=SCHEMA_MANIFEST_VERSION, entries=entries)
