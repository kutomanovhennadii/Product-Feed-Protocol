"""Semantic validation layer for raw connector mapping dicts.

Validates the raw dict produced by connector_mapping_loader and returns
a trusted, typed ConnectorMappingConfig. No I/O is performed here.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pfp_runtime.connectors.connector_mapping.connector_mapping_config import (
    ConnectorFieldMapping,
    ConnectorMappingConfig,
    ConnectorMappingValidationError,
)


def validate_mapping(raw_data: Dict[str, Any]) -> ConnectorMappingConfig:
    """Validate a raw mapping dict and return a typed ConnectorMappingConfig.

    Error messages include only field paths and expected types — never raw
    values from the dict. This prevents accidental leakage of API keys or
    PII that may appear in a mapping file.

    Args:
        raw_data: Raw dict returned by load_yaml.

    Returns:
        Validated, immutable ConnectorMappingConfig.

    Raises:
        ConnectorMappingValidationError: If the structure is semantically invalid.
    """
    if "mappings" not in raw_data:
        raise ConnectorMappingValidationError("missing required key: 'mappings'")

    raw_mappings = raw_data["mappings"]
    if not isinstance(raw_mappings, list) or len(raw_mappings) == 0:
        raise ConnectorMappingValidationError("'mappings' must be a non-empty list")

    field_mappings: List[ConnectorFieldMapping] = []

    for i, item in enumerate(raw_mappings):
        if not isinstance(item, dict):
            raise ConnectorMappingValidationError(
                "mappings["
                + str(i)
                + "]: expected a mapping, got "
                + type(item).__name__
            )

        source = item.get("source")
        if not isinstance(source, str) or source == "":
            raise ConnectorMappingValidationError(
                "mappings[" + str(i) + "]: missing or empty 'source'"
            )

        target = item.get("target")
        if not isinstance(target, str) or target == "":
            raise ConnectorMappingValidationError(
                "mappings[" + str(i) + "]: missing or empty 'target'"
            )

        required = item.get("required", False)
        if not isinstance(required, bool):
            raise ConnectorMappingValidationError(
                "mappings[" + str(i) + "]: 'required' must be a bool"
            )

        field_mappings.append(
            ConnectorFieldMapping(source=source, target=target, required=required)
        )

    continue_on_error = raw_data.get("continue_on_error", True)
    if not isinstance(continue_on_error, bool):
        raise ConnectorMappingValidationError("'continue_on_error' must be a bool")

    return ConnectorMappingConfig(
        mappings=tuple(field_mappings),
        continue_on_error=continue_on_error,
    )


__all__: List[str] = ["validate_mapping"]
