"""Schema document parsing utilities."""

from __future__ import annotations

import json
from typing import Any, List, Literal, Mapping

import yaml  # type: ignore[import-untyped]

from pfp_core.schema.schema_types import SchemaDoc, SchemaErrorItem, SchemaFormatError


def parse_schema_text(text: str, *, format: Literal["yaml", "json"]) -> SchemaDoc:
    """Parse schema text into a mapping document.

    Args:
        text: Raw schema text content.
        format: Input format, either ``"yaml"`` or ``"json"``.

    Returns:
        Parsed schema document as a mapping.

    Raises:
        SchemaFormatError: If parsing fails or root value is not a mapping.
    """

    if format not in {"yaml", "json"}:
        raise SchemaFormatError(
            [
                SchemaErrorItem(
                    code="SCHEMA_PARSE_ERROR",
                    path="$",
                    message=(
                        "Unsupported schema format: "
                        + repr(format)
                        + ". Supported formats are: yaml, json."
                    ),
                )
            ]
        )

    try:
        if format == "json":
            parsed: Any = json.loads(text)
        else:
            parsed = yaml.safe_load(text)
    except Exception as exc:  # pragma: no cover - exact parser errors vary
        raise SchemaFormatError(
            [
                SchemaErrorItem(
                    code="SCHEMA_PARSE_ERROR",
                    path="$",
                    message=(
                        f"Failed to parse schema text as {format}: "
                        f"{type(exc).__name__}"
                    ),
                )
            ]
        ) from exc

    if not isinstance(parsed, Mapping):
        raise SchemaFormatError(
            [
                SchemaErrorItem(
                    code="SCHEMA_INVALID_TYPE",
                    path="$",
                    message="Schema document root must be a mapping.",
                )
            ]
        )
    return parsed


__all__: List[str] = ["parse_schema_text"]
