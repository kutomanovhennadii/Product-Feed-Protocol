"""Connector mapping subsystem.

Public API re-exported for convenient import:

    from pfp_runtime.connectors.connector_mapping import (
        ConnectorFieldMapping,
        ConnectorMappingConfig,
        ConnectorMappingLoadError,
        ConnectorMappingValidationError,
        ConnectorMapper,
        load_yaml,
        provide_connector_mapper,
        validate_mapping,
    )
"""

from typing import List

from pfp_runtime.connectors.connector_mapping.connector_mapper import ConnectorMapper
from pfp_runtime.connectors.connector_mapping.connector_mapping_config import (
    ConnectorFieldMapping,
    ConnectorMappingConfig,
    ConnectorMappingLoadError,
    ConnectorMappingValidationError,
)
from pfp_runtime.connectors.connector_mapping.connector_mapping_loader import load_yaml
from pfp_runtime.connectors.connector_mapping.connector_mapping_provider import (
    provide_connector_mapper,
)
from pfp_runtime.connectors.connector_mapping.connector_mapping_validator import (
    validate_mapping,
)

__all__: List[str] = [
    "ConnectorFieldMapping",
    "ConnectorMappingConfig",
    "ConnectorMappingLoadError",
    "ConnectorMappingValidationError",
    "ConnectorMapper",
    "load_yaml",
    "provide_connector_mapper",
    "validate_mapping",
]
