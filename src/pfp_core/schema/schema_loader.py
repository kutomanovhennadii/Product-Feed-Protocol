"""Built-in schema registry loader for library-managed schema documents."""

from __future__ import annotations

from pathlib import Path
from typing import List

from pfp_core.schema.schema_manifest import (
    SchemaManifestError,
    get_manifest_path,
    load_manifest_file,
    verify_builtin_schema_or_raise,
)
from pfp_core.schema.schema_parser import parse_schema_text
from pfp_core.schema.schema_registry import SchemaRegistry

# Root of the library-managed built-in schema catalog.
# Computed relative to this module so no user path is required.
_BUILTIN_SCHEMAS_ROOT: Path = Path(__file__).parent.parent.parent.parent / "schemas"


class BuiltinSchemaResolutionError(RuntimeError):
    """Raised when the expected built-in library schema cannot be resolved.

    This is a library contract error, not a user input error. It indicates
    that the built-in schema catalog shipped with the library is missing,
    damaged, or does not contain the expected canonical schema pair.
    """


def load_builtin_schema_registry() -> SchemaRegistry:
    """Load all built-in library schema documents into a SchemaRegistry.

    Scans the library-managed schemas directory in deterministic lexicographic
    order and registers each YAML schema document using the existing schema
    contract (parse -> validate -> register). No user-supplied path is
    accepted; the source of schema documents is controlled entirely by the
    library.

    Returns:
        Fully populated SchemaRegistry containing all built-in schema documents.

    Raises:
        BuiltinSchemaResolutionError: If the built-in schemas directory is
            missing.
        SchemaFormatError: If a built-in schema document violates the schema
            contract. Propagated as-is from the schema layer.
    """

    if not _BUILTIN_SCHEMAS_ROOT.is_dir():
        raise BuiltinSchemaResolutionError(
            "Built-in schemas directory not found: internal library contract broken."
        )

    manifest_path = get_manifest_path(_BUILTIN_SCHEMAS_ROOT)
    if not manifest_path.is_file():
        raise BuiltinSchemaResolutionError(
            "Built-in schema manifest file not found: " + str(manifest_path) + "."
        )

    try:
        manifest = load_manifest_file(manifest_path)
    except Exception as exc:
        raise BuiltinSchemaResolutionError(
            "Failed to load built-in schema manifest: " + str(manifest_path)
        ) from exc

    registry = SchemaRegistry()
    schema_files = sorted(_BUILTIN_SCHEMAS_ROOT.rglob("*.yaml"))

    for schema_file in schema_files:
        try:
            verify_builtin_schema_or_raise(
                schema_file,
                schemas_root=_BUILTIN_SCHEMAS_ROOT,
                manifest=manifest,
            )
        except SchemaManifestError as exc:
            raise BuiltinSchemaResolutionError(
                "Built-in schema integrity verification failed: " + str(exc)
            ) from exc

        text = schema_file.read_text(encoding="utf-8")
        doc = parse_schema_text(text, format="yaml")
        registry.register(doc, filename=schema_file.name, source="builtin")

    return registry


__all__: List[str] = [
    "BuiltinSchemaResolutionError",
    "load_builtin_schema_registry",
]
