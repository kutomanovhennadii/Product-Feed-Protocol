"""Orchestrator for building a fully initialised DeliveryClient from type + config path."""

from __future__ import annotations

import logging
from typing import Any, List

from pfp_runtime.publishing.clients.client_config_loader import (
    ClientConfigLoadError,
    load_client_config,
)
from pfp_runtime.publishing.clients.client_provider import (
    ClientRegistryError,
    resolve_client,
)
from pfp_runtime.publishing.contracts.publisher_errors import PublisherBuildError
from pfp_utils.logging import LogContext, LogPipeline

__all__: List[str] = ["build_client"]


def build_client(
    client_type: str,
    config_path: str,
    *,
    log_pipeline: LogPipeline,
) -> Any:
    """Build and return a fully initialised DeliveryClient for the given client_type.

    Orchestrates the 4-step build chain:
      1. resolve_client(client_type)        → client_class, iac_class
      2. load_client_config(config_path)    → raw dict
      3. iac_class.model_validate(raw_dict) → typed IaC
      4. client_class(iac)                  → ready DeliveryClient
         (the constructor resolves any SecretRef fields internally)

    Runs entirely under LogContext(stage="init", component="client_builder").
    On any failure, logs client_type and config_path (never secret values) and
    raises PublisherBuildError.

    Args:
        client_type: Registry key, e.g. "http", "http_streaming", "sftp", "noop".
        config_path: Path to the client IaC YAML file.
        log_pipeline: Runtime log pipeline propagated from manifest assembly.

    Returns:
        Initialised DeliveryClient instance ready for open/send_chunk/finalize calls.

    Raises:
        PublisherBuildError: If any step in the build chain fails.
    """
    with LogContext(stage="init", component="client_builder"):
        try:
            client_class, iac_class = resolve_client(client_type)
            raw = load_client_config(config_path)
            try:
                iac = iac_class.model_validate(raw)
            except Exception as exc:
                raise PublisherBuildError(
                    f"IaC validation failed for client_type '{client_type}': {exc}"
                ) from exc
            return client_class(iac)
        except PublisherBuildError:
            raise
        except (ClientRegistryError, ClientConfigLoadError) as exc:
            log_pipeline.log_process(
                logging.ERROR,
                __name__,
                "client_builder failed: client_type=%s config_path=%s",
                client_type,
                config_path,
                exc_info=exc,
            )
            raise PublisherBuildError(str(exc)) from exc
        except Exception as exc:
            log_pipeline.log_process(
                logging.ERROR,
                __name__,
                "client_builder failed: client_type=%s config_path=%s",
                client_type,
                config_path,
                exc_info=exc,
            )
            raise PublisherBuildError(
                f"Failed to build client '{client_type}': {exc}"
            ) from exc
