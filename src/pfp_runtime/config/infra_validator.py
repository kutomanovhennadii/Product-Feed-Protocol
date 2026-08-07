"""Semantic validation helpers for canonical infra config."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Mapping, Optional, Union

from pfp_runtime.config.infra_models import InfraConfig
from pfp_utils.logging.filters.flood_control_filter.flood_control_filter_config_validation import (
    normalize_flood_control_config,
)


class InfraConfigValidationError(ValueError):
    """Raised when canonical infra payload violates config-layer contract."""


def validate_infra_config(
    infra: InfraConfig,
    *,
    infra_path: Optional[Union[str, Path]] = None,
) -> InfraConfig:
    """Validate cross-field invariants for canonical infra models.

    Args:
        infra: Materialized canonical infra configuration.
        infra_path: Optional path to the infra YAML file. When provided, file-based
            producer references are resolved relative to this path and checked for
            existence.

    Returns:
        The same InfraConfig instance when validation succeeds.

    Raises:
        InfraConfigValidationError: If any semantic invariant is violated.
    """
    input_format = infra.input.format

    connectors_data = _load_registry(
        Path(__file__).resolve().parents[1] / "connectors" / "connectors_registry.json"
    )
    connectors_registry = connectors_data.get("formats", connectors_data)

    if input_format not in connectors_registry:
        raise InfraConfigValidationError(
            "input.format token '"
            + input_format
            + "' is missing in connectors registry"
        )

    archive_config_path = infra.output.archive_config
    client_config_path = infra.output.client_config

    if not archive_config_path.lower().endswith((".yaml", ".yml")):
        raise InfraConfigValidationError(
            "output.archive_config must point to a YAML file"
        )
    if not client_config_path.lower().endswith((".yaml", ".yml")):
        raise InfraConfigValidationError(
            "output.client_config must point to a YAML file"
        )

    if (
        infra.observability is not None
        and infra.observability.logging.level.upper()
        not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    ):
        raise InfraConfigValidationError("observability.logging.level is not supported")

    _validate_observability_logging(infra)

    _validate_producer_files(infra, infra_path=infra_path)

    return infra


def _validate_observability_logging(infra: InfraConfig) -> None:
    """Validate semantic invariants inside observability.logging subtree.

    Args:
        infra: Materialized canonical infra configuration.

    Returns:
        None.

    Raises:
        InfraConfigValidationError: If downstream flood-control validation fails.
    """
    if infra.observability is None:
        return

    try:
        normalize_flood_control_config(
            infra.observability.logging.flood_control_config.model_dump(
                exclude_none=True
            )
        )
    except ValueError as exc:
        raise InfraConfigValidationError(
            "observability.logging.flood_control_config: " + str(exc)
        ) from exc


def _validate_producer_files(
    infra: InfraConfig,
    *,
    infra_path: Optional[Union[str, Path]],
) -> None:
    """Validate producer file-based contract for schema/policy inputs.

    Args:
        infra: Materialized canonical infra configuration.
        infra_path: Optional infra YAML path used to resolve relative producer paths.

    Returns:
        None.

    Raises:
        InfraConfigValidationError: If the file paths are not YAML or, when infra_path
            is provided, referenced files are missing or not regular files.
    """
    schema_path = Path(infra.producer.schema_file)
    policy_path = Path(infra.producer.policy_file)

    if schema_path.suffix.lower() not in (".yaml", ".yml"):
        raise InfraConfigValidationError(
            "producer.schema_file must point to a YAML file"
        )
    if policy_path.suffix.lower() not in (".yaml", ".yml"):
        raise InfraConfigValidationError(
            "producer.policy_file must point to a YAML file"
        )

    if infra_path is None:
        return

    base_dir = Path(infra_path).expanduser().resolve().parent
    resolved_schema = (
        schema_path if schema_path.is_absolute() else (base_dir / schema_path)
    )
    resolved_policy = (
        policy_path if policy_path.is_absolute() else (base_dir / policy_path)
    )

    if not resolved_schema.exists():
        raise InfraConfigValidationError(
            "producer.schema_file does not exist: " + str(resolved_schema)
        )
    if not resolved_schema.is_file():
        raise InfraConfigValidationError(
            "producer.schema_file is not a file: " + str(resolved_schema)
        )
    if not resolved_policy.exists():
        raise InfraConfigValidationError(
            "producer.policy_file does not exist: " + str(resolved_policy)
        )
    if not resolved_policy.is_file():
        raise InfraConfigValidationError(
            "producer.policy_file is not a file: " + str(resolved_policy)
        )


def _load_registry(path: Path) -> Mapping[str, Any]:
    """Load a registry mapping from a JSON file.

    Args:
        path: Path to a JSON file containing an object mapping.

    Returns:
        Registry mapping.

    Raises:
        InfraConfigValidationError: If the file cannot be read, is invalid JSON, or
            the JSON root is not an object.
    """
    try:
        with path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except OSError as exc:
        raise InfraConfigValidationError(
            "cannot read registry file: " + str(path)
        ) from exc
    except json.JSONDecodeError as exc:
        raise InfraConfigValidationError("invalid registry JSON: " + str(path)) from exc

    if not isinstance(payload, dict):
        raise InfraConfigValidationError(
            "registry root must be a JSON object: " + str(path)
        )
    return payload


__all__: List[str] = [
    "InfraConfigValidationError",
    "validate_infra_config",
]
