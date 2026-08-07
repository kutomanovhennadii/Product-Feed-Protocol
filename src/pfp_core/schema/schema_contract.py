"""Schema contract validation utilities."""

from __future__ import annotations

from typing import Any, List, Mapping, Optional

from pfp_core.schema.schema_types import (
    SchemaDoc,
    SchemaErrorItem,
    SchemaFormatError,
    SchemaRef,
)


def validate_schema_doc_format(
    doc: SchemaDoc, *, expected_ref: Optional[SchemaRef] = None
) -> None:
    """Validate minimal schema document structure and key field types.

    Args:
        doc: Schema document mapping.
        expected_ref: Optional reference expected from filename metadata.

    Returns:
        None.

    Raises:
        SchemaFormatError: If one or more format violations are detected.
    """

    items: List[SchemaErrorItem] = []

    if not isinstance(doc, Mapping):
        items.append(
            SchemaErrorItem(
                code="SCHEMA_INVALID_TYPE",
                path="$",
                message="Schema document root must be a mapping.",
            )
        )
        raise SchemaFormatError(items, schema_ref=_try_extract_ref(doc))

    required_sections = ("header", "input", "output", "mapping", "validation")
    for section in required_sections:
        _get_required_dict(doc, section, section, items)

    header = _get_required_dict(doc, "header", "header", items)
    header_protocol_id = _get_required_string(
        header, "protocol_id", "header.protocol_id", items
    )
    header_schema_version = _get_required_string(
        header, "schema_version", "header.schema_version", items
    )
    _get_required_string(header, "artifact_profile", "header.artifact_profile", items)
    _get_required_string(header, "title", "header.title", items)
    source_protocol = _get_required_dict(
        header, "source_protocol", "header.source_protocol", items
    )
    _get_required_string(
        source_protocol, "provider", "header.source_protocol.provider", items
    )
    _get_required_string(source_protocol, "url", "header.source_protocol.url", items)
    _get_required_string(
        source_protocol, "revision", "header.source_protocol.revision", items
    )
    _get_required_string(
        source_protocol,
        "retrieved_at",
        "header.source_protocol.retrieved_at",
        items,
    )

    input_section = _get_required_dict(doc, "input", "input", items)
    _get_required_string(input_section, "um_contract", "input.um_contract", items)

    output_section = _get_required_dict(doc, "output", "output", items)
    _get_required_string(output_section, "writer_id", "output.writer_id", items)
    artifact = _get_required_dict(output_section, "artifact", "output.artifact", items)
    _get_required_string(artifact, "file_ext", "output.artifact.file_ext", items)
    _get_required_string(
        artifact, "content_type", "output.artifact.content_type", items
    )

    mapping_section = _get_required_dict(doc, "mapping", "mapping", items)
    _get_required_string(mapping_section, "output_kind", "mapping.output_kind", items)

    validation_section = _get_required_dict(doc, "validation", "validation", items)
    rules = _get_required_field(validation_section, "rules", "validation.rules", items)
    if rules is not None and not isinstance(rules, list):
        items.append(
            SchemaErrorItem(
                code="SCHEMA_INVALID_TYPE",
                path="validation.rules",
                message="validation.rules must be a list.",
            )
        )

    if (
        expected_ref
        and isinstance(header_protocol_id, str)
        and isinstance(header_schema_version, str)
    ):
        if (
            header_protocol_id != expected_ref.protocol_id
            or header_schema_version != expected_ref.schema_version
        ):
            items.append(
                SchemaErrorItem(
                    code="SCHEMA_HEADER_FILENAME_MISMATCH",
                    path="header",
                    message=(
                        "header.protocol_id/header.schema_version must match filename reference."
                    ),
                )
            )

    if items:
        raise SchemaFormatError(items, schema_ref=_try_extract_ref(doc))


def _get_required_dict(
    mapping_obj: Optional[Mapping[str, Any]],
    key: str,
    path: str,
    items: List[SchemaErrorItem],
) -> Optional[Mapping[str, Any]]:
    value = _get_required_field(mapping_obj, key, path, items)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        items.append(
            SchemaErrorItem(
                code="SCHEMA_INVALID_TYPE",
                path=path,
                message=f"{path} must be an object.",
            )
        )
        return None
    return value


def _get_required_string(
    mapping_obj: Optional[Mapping[str, Any]],
    key: str,
    path: str,
    items: List[SchemaErrorItem],
) -> Optional[str]:
    value = _get_required_field(mapping_obj, key, path, items)
    if value is None:
        return None
    if not isinstance(value, str):
        items.append(
            SchemaErrorItem(
                code="SCHEMA_INVALID_TYPE",
                path=path,
                message=f"{path} must be a string.",
            )
        )
        return None
    return value


def _get_required_field(
    mapping_obj: Optional[Mapping[str, Any]],
    key: str,
    path: str,
    items: List[SchemaErrorItem],
) -> Any:
    if mapping_obj is None:
        return None
    if key not in mapping_obj:
        items.append(
            SchemaErrorItem(
                code="SCHEMA_MISSING_FIELD",
                path=path,
                message=f"Missing required field '{path}'.",
            )
        )
        return None
    return mapping_obj[key]


def _try_get_mapping(
    mapping_obj: Optional[Mapping[str, Any]],
    key: str,
) -> Optional[Mapping[str, Any]]:
    if mapping_obj is None:
        return None
    value = mapping_obj.get(key)
    if isinstance(value, Mapping):
        return value
    return None


def _try_get_str(
    mapping_obj: Optional[Mapping[str, Any]],
    key: str,
) -> Optional[str]:
    if mapping_obj is None:
        return None
    value = mapping_obj.get(key)
    if isinstance(value, str):
        return value
    return None


def _try_get_field(mapping_obj: Optional[Mapping[str, Any]], key: str) -> Any:
    if mapping_obj is None:
        return None
    return mapping_obj.get(key)


def _try_extract_ref(doc: Any) -> Optional[SchemaRef]:
    header = _try_get_mapping(doc, "header") if isinstance(doc, Mapping) else None
    protocol_id = _try_get_str(header, "protocol_id")
    schema_version = _try_get_str(header, "schema_version")
    if isinstance(protocol_id, str) and isinstance(schema_version, str):
        return SchemaRef(protocol_id=protocol_id, schema_version=schema_version)
    return None


__all__: List[str] = ["validate_schema_doc_format"]
