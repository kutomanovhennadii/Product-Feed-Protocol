"""Typed in-memory representation of connector_mapping.yaml.

Contains frozen dataclass contracts and error types used by all
subsequent layers (loader, validator, mapper).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ConnectorFieldMapping:
    """Mapping rule for a single source field to a UM-space target path.

    Attributes:
        source: Field name in the raw input record (CSV column or JSON key).
        target: Dot-separated path in UM-space, e.g. ``"product.item_id"``.
        required: If True, records missing this field are dropped with a warning
            (or raise an error when ``continue_on_error=False``).
    """

    source: str
    target: str
    required: bool = False


@dataclass(frozen=True)
class ConnectorMappingConfig:
    """Validated, immutable mapping configuration for a connector.

    Attributes:
        mappings: Ordered tuple of field mapping rules.
        continue_on_error: If True, missing required fields produce a WARNING
            and the record is skipped. If False, the first missing required
            field raises an error and stops the stream.
    """

    mappings: Tuple[ConnectorFieldMapping, ...]
    continue_on_error: bool = True


class ConnectorMappingLoadError(Exception):
    """Raised when the mapping file cannot be read or its YAML syntax is broken."""


class ConnectorMappingValidationError(Exception):
    """Raised when the mapping structure is semantically invalid."""
