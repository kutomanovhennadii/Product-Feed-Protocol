"""Top-level orchestrator that assembles a Publisher from an infra output section."""

from __future__ import annotations

import logging
from typing import Any, List, Mapping

from pfp_runtime.publishing.archivers.archiver_builder import build_archiver
from pfp_runtime.publishing.clients.client_builder import build_client
from pfp_runtime.publishing.contracts.publisher_contract import Publisher
from pfp_runtime.publishing.contracts.publisher_errors import PublisherBuildError
from pfp_utils.logging import LogContext, LogPipeline

__all__: List[str] = ["build_publisher"]

_REQUIRED_KEYS = ("archive_type", "archive_config", "client_type", "client_config")


def build_publisher(
    output_config: Mapping[str, Any],
    *,
    log_pipeline: LogPipeline,
) -> Publisher:
    """Build and return a fully initialised Publisher from the output section of infra.yaml.

    Orchestrates the 3-step build chain:
      1. build_archiver(archive_type, archive_config) → Archiver
      2. build_client(client_type, client_config)     → DeliveryClient
      3. Publisher(archiver, client)                  → Publisher

    Validates all four required keys up front (Fail-Fast). No configuration
    errors are delegated to lower layers.

    Runs entirely under LogContext(stage="init", component="publisher_builder").
    On any failure, logs archive_type, archive_config, client_type, client_config
    values (these are paths and type keys — never secret values) and propagates
    PublisherBuildError.

    Args:
        output_config: Mapping with keys:
            - archive_type (str, required): Archiver registry key.
            - archive_config (str, required): Path to archiver IaC YAML.
            - client_type (str, required): Client registry key.
            - client_config (str, required): Path to client IaC YAML.
        log_pipeline: Runtime log pipeline propagated from manifest assembly.

    Returns:
        Fully initialised Publisher ready for publish() calls.

    Raises:
        PublisherBuildError: If required keys are missing or any build step fails.
    """
    with LogContext(stage="init", component="publisher_builder"):
        for key in _REQUIRED_KEYS:
            if key not in output_config:
                raise PublisherBuildError(
                    f"Missing required key in output_config: '{key}'"
                )

        archive_type: str = output_config["archive_type"]
        archive_config: str = output_config["archive_config"]
        client_type: str = output_config["client_type"]
        client_config: str = output_config["client_config"]

        try:
            archiver = build_archiver(
                archive_type,
                archive_config,
                log_pipeline=log_pipeline,
            )
            client = build_client(
                client_type,
                client_config,
                log_pipeline=log_pipeline,
            )
            return Publisher(archiver, client, log_pipeline=log_pipeline)
        except PublisherBuildError:
            raise
        except Exception as exc:
            log_pipeline.log_process(
                logging.ERROR,
                __name__,
                "publisher_builder failed: archive_type=%s archive_config=%s"
                " client_type=%s client_config=%s",
                archive_type,
                archive_config,
                client_type,
                client_config,
                exc_info=exc,
            )
            raise PublisherBuildError(f"Failed to build publisher: {exc}") from exc
