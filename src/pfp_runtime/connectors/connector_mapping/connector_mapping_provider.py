"""High-level Init Phase facade for building a ConnectorMapper from a file path."""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

from pfp_runtime.connectors.connector_mapping.connector_mapper import ConnectorMapper
from pfp_runtime.connectors.connector_mapping.connector_mapping_loader import load_yaml
from pfp_runtime.connectors.connector_mapping.connector_mapping_validator import (
    validate_mapping,
)
from pfp_utils.logging import LogPipeline


def provide_connector_mapper(
    mapping_path: Union[str, Path],
    *,
    log_pipeline: LogPipeline,
) -> ConnectorMapper:
    """Load, validate and build a ConnectorMapper from a mapping YAML file.

    Orchestrates the full Init Phase chain:
    ``load_yaml`` → ``validate_mapping`` → ``ConnectorMapper``

    Errors from lower layers are propagated unchanged — this function
    contains no error-handling logic of its own.

    Args:
        mapping_path: Path to the mapping YAML file (str or Path).

    Returns:
        A compiled ConnectorMapper ready for apply_stream calls.

    Raises:
        ConnectorMappingLoadError: Propagated from load_yaml if the file
            cannot be read or parsed.
        ConnectorMappingValidationError: Propagated from validate_mapping
            if the mapping structure is semantically invalid.
    """
    raw = load_yaml(mapping_path)
    config = validate_mapping(raw)
    return ConnectorMapper(config, log_pipeline=log_pipeline)


__all__: List[str] = ["provide_connector_mapper"]
