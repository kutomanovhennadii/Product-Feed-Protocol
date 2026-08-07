"""Core manifest builder for init-phase manifest pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, cast

from pfp_core.artifact_production import prepare_artifact_producer_from_files
from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.manifest.pipeline_manifest import CoreManifest, ManifestBuildError
from pfp_utils.logging import LogPipeline


def build_core_manifest(
    infra: InfraConfig,
    *,
    log_pipeline: LogPipeline,
) -> CoreManifest:
    """Build core section of pipeline manifest from validated infra.

    Args:
        infra: Validated canonical infra configuration.
        log_pipeline: Runtime log pipeline propagated from observability builder.

    Returns:
        CoreManifest containing a ready-to-use ArtifactProducer.

    Raises:
        ManifestBuildError: If producer assembly fails.
    """
    try:
        tax_mapping = None
        if infra.producer.tax_mapping_file is not None:
            tax_mapping = _load_tax_mapping(infra.producer.tax_mapping_file)

        producer = prepare_artifact_producer_from_files(
            schema_file=infra.producer.schema_file,
            policy_file=infra.producer.policy_file,
            tax_mapping=tax_mapping,
            log_pipeline=log_pipeline,
        )
    except (OSError, ValueError) as exc:
        raise ManifestBuildError(str(exc)) from exc

    return CoreManifest(producer=producer)


def _load_tax_mapping(path_value: str) -> Mapping[str, Any]:
    """Load tax mapping JSON from an infra-supplied file path.

    Args:
        path_value: Path to the JSON file declared in infra producer config.

    Returns:
        Parsed JSON object as a mapping.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is invalid or lacks the required ``mappings`` key.
    """
    path = Path(path_value).expanduser().resolve()

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OSError(f"failed to read tax mapping JSON at {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"failed to parse tax mapping JSON at {path}: {exc}") from exc

    if not isinstance(loaded, dict):
        raise ValueError(f"tax mapping JSON at {path} must contain an object root")

    mappings = loaded.get("mappings")
    if not isinstance(mappings, dict):
        raise ValueError(f"tax mapping JSON at {path} must contain a 'mappings' object")

    return cast(Mapping[str, Any], loaded)


__all__ = ["build_core_manifest"]
