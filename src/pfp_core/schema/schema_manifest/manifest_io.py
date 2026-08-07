"""I/O helpers for schema manifest files."""

from __future__ import annotations

import json
from pathlib import Path

from pfp_core.schema.schema_manifest.manifest_models import (
    SchemaManifestDocument,
    parse_manifest_document,
)

SCHEMA_MANIFEST_FILENAME = "schema_manifest.json"


def get_manifest_path(schemas_root: Path) -> Path:
    """Return canonical schema manifest path for a schemas root."""

    return schemas_root / SCHEMA_MANIFEST_FILENAME


def load_manifest_file(manifest_path: Path) -> SchemaManifestDocument:
    """Load manifest from JSON file and parse it into typed model."""

    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Manifest root JSON value must be an object.")
    return parse_manifest_document(raw)


def dump_manifest_json(document: SchemaManifestDocument) -> str:
    """Serialize manifest document into deterministic JSON representation."""

    return json.dumps(document.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def write_manifest_file(manifest_path: Path, document: SchemaManifestDocument) -> None:
    """Write manifest document to file in deterministic canonical format."""

    manifest_path.write_text(dump_manifest_json(document) + "\n", encoding="utf-8")
