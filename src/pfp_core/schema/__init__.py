from typing import List

from pfp_core.schema.schema_contract import validate_schema_doc_format
from pfp_core.schema.schema_loader import (
    BuiltinSchemaResolutionError,
    load_builtin_schema_registry,
)
from pfp_core.schema.schema_manifest import (
    STATUS_BUILT_IN_MODIFIED,
    STATUS_BUILT_IN_VERIFIED,
    STATUS_EXTERNAL_SCHEMA,
    SchemaIntegrityStatus,
    classify_schema_integrity,
)
from pfp_core.schema.schema_parser import parse_schema_text
from pfp_core.schema.schema_refs import extract_ref_from_doc, extract_ref_from_filename
from pfp_core.schema.schema_registry import SchemaRegistry
from pfp_core.schema.schema_types import (
    SchemaDoc,
    SchemaError,
    SchemaErrorItem,
    SchemaFormatError,
    SchemaNotFoundError,
    SchemaRef,
    SchemaRegistryError,
    SchemaValidationError,
    SchemaVersionError,
    sort_schema_error_items,
)

__all__: List[str] = [
    "BuiltinSchemaResolutionError",
    "SchemaDoc",
    "SchemaError",
    "SchemaErrorItem",
    "SchemaFormatError",
    "SchemaNotFoundError",
    "SchemaRegistryError",
    "SchemaRef",
    "SchemaValidationError",
    "SchemaVersionError",
    "SchemaIntegrityStatus",
    "SchemaRegistry",
    "STATUS_BUILT_IN_MODIFIED",
    "STATUS_BUILT_IN_VERIFIED",
    "STATUS_EXTERNAL_SCHEMA",
    "classify_schema_integrity",
    "extract_ref_from_doc",
    "extract_ref_from_filename",
    "load_builtin_schema_registry",
    "parse_schema_text",
    "sort_schema_error_items",
    "validate_schema_doc_format",
]
