"""Built-in schema manifest integrity API for schema layer and tooling."""

from typing import List

from pfp_core.schema.schema_manifest.manifest_builder import (
    build_manifest_document,
    collect_builtin_schema_files,
    compute_file_sha256,
)
from pfp_core.schema.schema_manifest.manifest_io import (
    SCHEMA_MANIFEST_FILENAME,
    dump_manifest_json,
    get_manifest_path,
    load_manifest_file,
    write_manifest_file,
)
from pfp_core.schema.schema_manifest.manifest_models import (
    SCHEMA_MANIFEST_VERSION,
    SchemaManifestDocument,
    SchemaManifestEntry,
    SchemaManifestError,
    parse_manifest_document,
)
from pfp_core.schema.schema_manifest.manifest_verifier import (
    STATUS_BUILT_IN_MODIFIED,
    STATUS_BUILT_IN_VERIFIED,
    STATUS_EXTERNAL_SCHEMA,
    SchemaIntegrityStatus,
    classify_schema_integrity,
    verify_builtin_schema_or_raise,
)

__all__: List[str] = [
    "SCHEMA_MANIFEST_FILENAME",
    "SCHEMA_MANIFEST_VERSION",
    "STATUS_BUILT_IN_MODIFIED",
    "STATUS_BUILT_IN_VERIFIED",
    "STATUS_EXTERNAL_SCHEMA",
    "SchemaIntegrityStatus",
    "SchemaManifestDocument",
    "SchemaManifestEntry",
    "SchemaManifestError",
    "build_manifest_document",
    "classify_schema_integrity",
    "collect_builtin_schema_files",
    "compute_file_sha256",
    "dump_manifest_json",
    "get_manifest_path",
    "load_manifest_file",
    "parse_manifest_document",
    "verify_builtin_schema_or_raise",
    "write_manifest_file",
]
