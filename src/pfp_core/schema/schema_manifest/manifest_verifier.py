"""Runtime verification helpers for built-in schema manifest integrity."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from pfp_core.schema.schema_manifest.manifest_builder import compute_file_sha256
from pfp_core.schema.schema_manifest.manifest_models import (
    SchemaManifestDocument,
    SchemaManifestEntry,
    SchemaManifestError,
)

STATUS_BUILT_IN_VERIFIED = "built_in_verified"
STATUS_BUILT_IN_MODIFIED = "built_in_modified"
STATUS_EXTERNAL_SCHEMA = "external_schema"


@dataclass(frozen=True)
class SchemaIntegrityStatus:
    """Detailed integrity classification result for one schema file."""

    status: str
    relative_path: Optional[str]
    expected_sha256: Optional[str]
    actual_sha256: Optional[str]


def classify_schema_integrity(
    schema_file: Path,
    *,
    schemas_root: Path,
    manifest: SchemaManifestDocument,
) -> SchemaIntegrityStatus:
    """Classify schema file as built-in verified/modified/external."""

    schema_file_resolved = schema_file.resolve()
    schemas_root_resolved = schemas_root.resolve()

    try:
        relative_path = schema_file_resolved.relative_to(
            schemas_root_resolved
        ).as_posix()
    except ValueError:
        return SchemaIntegrityStatus(
            status=STATUS_EXTERNAL_SCHEMA,
            relative_path=None,
            expected_sha256=None,
            actual_sha256=None,
        )

    by_path: Dict[str, SchemaManifestEntry] = {
        entry.path: entry for entry in manifest.entries
    }
    entry = by_path.get(relative_path)
    actual_sha256 = compute_file_sha256(schema_file_resolved)

    if entry is None:
        return SchemaIntegrityStatus(
            status=STATUS_BUILT_IN_MODIFIED,
            relative_path=relative_path,
            expected_sha256=None,
            actual_sha256=actual_sha256,
        )

    if entry.sha256 != actual_sha256:
        return SchemaIntegrityStatus(
            status=STATUS_BUILT_IN_MODIFIED,
            relative_path=relative_path,
            expected_sha256=entry.sha256,
            actual_sha256=actual_sha256,
        )

    return SchemaIntegrityStatus(
        status=STATUS_BUILT_IN_VERIFIED,
        relative_path=relative_path,
        expected_sha256=entry.sha256,
        actual_sha256=actual_sha256,
    )


def verify_builtin_schema_or_raise(
    schema_file: Path,
    *,
    schemas_root: Path,
    manifest: SchemaManifestDocument,
) -> SchemaIntegrityStatus:
    """Fail fast when built-in schema does not match canonical manifest."""

    result = classify_schema_integrity(
        schema_file,
        schemas_root=schemas_root,
        manifest=manifest,
    )
    if result.status == STATUS_BUILT_IN_MODIFIED:
        raise SchemaManifestError(
            "Built-in schema manifest mismatch for '{0}'. expected_sha256={1}, actual_sha256={2}".format(
                result.relative_path,
                result.expected_sha256 or "<missing>",
                result.actual_sha256 or "<missing>",
            )
        )
    return result
