"""Schema reference extraction utilities."""

from __future__ import annotations

import re
from pathlib import PurePath
from typing import Any, List, Mapping, Optional

from pfp_core.schema.schema_types import (
    SchemaDoc,
    SchemaErrorItem,
    SchemaFormatError,
    SchemaRef,
)
from pfp_core.schema.schema_utils import is_semver

_ALLOWED_FILE_EXTENSIONS = {"yaml", "yml", "json"}
_PROTOCOL_ID_PATTERN = re.compile(r"^[a-z0-9._]+$")


def extract_ref_from_doc(doc: SchemaDoc) -> SchemaRef:
    """Extract schema reference from ``header`` fields in a schema document.

    Args:
        doc: Schema document mapping.

    Returns:
        Extracted ``SchemaRef``.

    Raises:
        SchemaFormatError: If required header fields are missing or invalid.
    """

    items: List[SchemaErrorItem] = []
    header = _try_get_mapping(doc, "header", "header", items)

    protocol_id = _try_get_str(header, "protocol_id", "header.protocol_id", items)
    schema_version = _try_get_str(
        header, "schema_version", "header.schema_version", items
    )

    if items:
        raise SchemaFormatError(items, schema_ref=_try_extract_ref(doc))

    if protocol_id is None or schema_version is None:
        raise SchemaFormatError(items, schema_ref=_try_extract_ref(doc))

    return SchemaRef(protocol_id=protocol_id, schema_version=schema_version)


def extract_ref_from_filename(filename: str) -> SchemaRef:
    """Extract schema reference from a schema filename.

    Args:
        filename: Filename in ``<protocol_id>-<schema_version>.<ext>`` form.

    Returns:
        Extracted ``SchemaRef``.

    Raises:
        SchemaFormatError: If filename violates format, protocol_id, or SemVer rules.
    """

    items: List[SchemaErrorItem] = []
    basename = PurePath(filename).name
    stem: Optional[str] = None
    protocol_id: Optional[str] = None
    schema_version: Optional[str] = None

    if not basename or " " in basename:
        items.append(
            SchemaErrorItem(
                code="SCHEMA_FILENAME_INVALID",
                path="$",
                message="Filename must be non-empty and must not contain spaces.",
            )
        )

    if "." not in basename:
        items.append(
            SchemaErrorItem(
                code="SCHEMA_FILENAME_INVALID",
                path="$",
                message="Filename must include an extension.",
            )
        )
    else:
        stem, extension = basename.rsplit(".", 1)
        extension = extension.lower()
        if extension not in _ALLOWED_FILE_EXTENSIONS:
            items.append(
                SchemaErrorItem(
                    code="SCHEMA_FILENAME_INVALID",
                    path="$",
                    message=(
                        "Filename extension must be one of: "
                        + ", ".join(sorted(_ALLOWED_FILE_EXTENSIONS))
                        + "."
                    ),
                )
            )

    if stem is not None:
        if "-" not in stem:
            items.append(
                SchemaErrorItem(
                    code="SCHEMA_FILENAME_INVALID",
                    path="$",
                    message="Filename must match <protocol_id>-<schema_version>.<ext>.",
                )
            )
        else:
            protocol_id, schema_version = stem.rsplit("-", 1)

    if protocol_id is not None and not _PROTOCOL_ID_PATTERN.fullmatch(protocol_id):
        items.append(
            SchemaErrorItem(
                code="SCHEMA_PROTOCOL_ID_INVALID",
                path="filename.protocol_id",
                message=(
                    "protocol_id in filename must match [a-z0-9._]+ and must not contain '-'."
                ),
            )
        )

    if schema_version is not None and not is_semver(schema_version):
        items.append(
            SchemaErrorItem(
                code="SCHEMA_VERSION_INVALID",
                path="filename.schema_version",
                message="schema_version in filename must be SemVer MAJOR.MINOR.PATCH.",
            )
        )

    if items:
        raise SchemaFormatError(items, schema_ref=None, source=filename)

    if protocol_id is None or schema_version is None:
        raise SchemaFormatError(
            [
                SchemaErrorItem(
                    code="SCHEMA_FILENAME_INVALID",
                    path="$",
                    message="Filename must match <protocol_id>-<schema_version>.<ext>.",
                )
            ],
            schema_ref=None,
            source=filename,
        )

    return SchemaRef(protocol_id=protocol_id, schema_version=schema_version)


def _try_get_mapping(
    mapping_obj: Mapping[str, Any],
    key: str,
    path: str,
    items: List[SchemaErrorItem],
) -> Optional[Mapping[str, Any]]:
    value = mapping_obj.get(key)
    if value is None:
        items.append(
            SchemaErrorItem(
                code="SCHEMA_MISSING_FIELD",
                path=path,
                message=f"Missing required field '{path}'.",
            )
        )
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


def _try_get_str(
    mapping_obj: Optional[Mapping[str, Any]],
    key: str,
    path: str,
    items: List[SchemaErrorItem],
) -> Optional[str]:
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
    value = mapping_obj[key]
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


def _try_extract_ref(doc: Any) -> Optional[SchemaRef]:
    if not isinstance(doc, Mapping):
        return None
    header = doc.get("header")
    if not isinstance(header, Mapping):
        return None
    protocol_id = header.get("protocol_id")
    schema_version = header.get("schema_version")
    if isinstance(protocol_id, str) and isinstance(schema_version, str):
        return SchemaRef(protocol_id=protocol_id, schema_version=schema_version)
    return None


__all__: List[str] = ["extract_ref_from_doc", "extract_ref_from_filename"]
