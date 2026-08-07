"""Build dispatch facade: format + config -> SourceConnector."""

from __future__ import annotations

import logging
from typing import Any, Mapping, cast

from pfp_runtime.connectors.adapter_provider import (
    AdapterRegistryError,
    provide_adapter,
)
from pfp_runtime.connectors.adapters.adapter_contract import FormatAdapter
from pfp_runtime.connectors.connector_mapping.connector_mapping_provider import (
    provide_connector_mapper,
)
from pfp_runtime.connectors.contracts import SourceConnector
from pfp_runtime.connectors.producers.product_producer import ProductProducer
from pfp_utils.logging import LogContext, LogPipeline
from pfp_utils.sanitization import sanitize_mapping


class ConnectorBuildError(ValueError):
    """Raised when connector config cannot be built for requested format."""


def build_connector(
    format_name: str,
    config: Mapping[str, Any],
    *,
    log_pipeline: LogPipeline,
) -> SourceConnector:
    """Build runtime connector instance for requested format."""
    with LogContext(stage="init", connector_format=str(format_name)):
        try:
            adapter = cast(
                FormatAdapter,
                provide_adapter(
                    format_name,
                    config,
                    log_pipeline=log_pipeline,
                ),
            )

            mapping_path = config.get("connector_mapping")
            if not mapping_path:
                raise ConnectorBuildError(
                    "connector_mapping is required in connector config"
                )

            mapper = provide_connector_mapper(mapping_path, log_pipeline=log_pipeline)
            producer = ProductProducer(log_pipeline=log_pipeline)

            log_pipeline.log_process(
                logging.DEBUG,
                __name__,
                "build_connector config",
                extra={"config": sanitize_mapping(config)},
            )

            return SourceConnector(adapter=adapter, mapper=mapper, producer=producer)
        except (AdapterRegistryError, ConnectorBuildError):
            raise
        except Exception as exc:
            log_pipeline.log_process(
                logging.ERROR,
                __name__,
                "Failed to build connector",
                exc_info=exc,
            )
            raise ConnectorBuildError(str(exc)) from exc
