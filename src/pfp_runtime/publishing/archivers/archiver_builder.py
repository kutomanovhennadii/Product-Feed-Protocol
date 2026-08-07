"""Orchestrator for building a fully initialised Archiver from type + config path."""

from __future__ import annotations

import logging
from typing import Any, List

from pfp_runtime.publishing.archivers.archiver_config_loader import (
    ArchiverConfigLoadError,
    load_archiver_config,
)
from pfp_runtime.publishing.archivers.archiver_provider import (
    ArchiverRegistryError,
    resolve_archiver,
)
from pfp_runtime.publishing.contracts.publisher_errors import PublisherBuildError
from pfp_utils.logging import LogContext, LogPipeline

__all__: List[str] = ["build_archiver"]


def build_archiver(
    archive_type: str,
    config_path: str,
    *,
    log_pipeline: LogPipeline,
) -> Any:
    """Build and return a fully initialised Archiver for the given archive_type.

    Orchestrates the 4-step build chain:
      1. resolve_archiver(archive_type)     → archiver_class, iac_class
      2. load_archiver_config(config_path)  → raw dict
      3. iac_class.model_validate(raw_dict) → typed IaC
      4. archiver_class(iac)               → ready Archiver
         (the constructor resolves any SecretRef fields internally)

    Runs entirely under LogContext(stage="init", component="archiver_builder").
    On any failure, logs archive_type and config_path (never secret values) and
    raises PublisherBuildError.

    Args:
        archive_type: Registry key, e.g. "local", "s3", "s3_compat", "noop".
        config_path: Path to the archiver IaC YAML file.
        log_pipeline: Runtime log pipeline propagated from manifest assembly.

    Returns:
        Initialised Archiver instance ready for open/write_chunk/finalize calls.

    Raises:
        PublisherBuildError: If any step in the build chain fails.
    """
    with LogContext(stage="init", component="archiver_builder"):
        try:
            archiver_class, iac_class = resolve_archiver(archive_type)
            raw = load_archiver_config(config_path)
            try:
                iac = iac_class.model_validate(raw)
            except Exception as exc:
                raise PublisherBuildError(
                    f"IaC validation failed for archive_type '{archive_type}': {exc}"
                ) from exc
            return archiver_class(iac)
        except PublisherBuildError:
            raise
        except (ArchiverRegistryError, ArchiverConfigLoadError) as exc:
            log_pipeline.log_process(
                logging.ERROR,
                __name__,
                "archiver_builder failed: archive_type=%s config_path=%s",
                archive_type,
                config_path,
                exc_info=exc,
            )
            raise PublisherBuildError(str(exc)) from exc
        except Exception as exc:
            log_pipeline.log_process(
                logging.ERROR,
                __name__,
                "archiver_builder failed: archive_type=%s config_path=%s",
                archive_type,
                config_path,
                exc_info=exc,
            )
            raise PublisherBuildError(
                f"Failed to build archiver '{archive_type}': {exc}"
            ) from exc
