"""Path normalization helpers for canonical infra config."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from pfp_runtime.config.infra_models import InfraConfig


def normalize_infra_paths(infra: InfraConfig, infra_path: str) -> InfraConfig:
    """Resolve relative infra file references to absolute paths.

    Producer and output config files are resolved with fallback strategy:
    1) relative to infra.yaml directory,
    2) fallback to project root when file is absent near infra.yaml.

    connector_mapping is resolved relative to infra.yaml directory when provided.

    Args:
        infra: Validated InfraConfig instance.
        infra_path: Path to infra YAML file.

    Returns:
        InfraConfig with normalized absolute file paths.
    """
    base_dir = Path(infra_path).expanduser().resolve().parent
    project_root = Path(__file__).resolve().parents[3]

    schema_path = _resolve_with_project_fallback(
        infra.producer.schema_file,
        base_dir=base_dir,
        project_root=project_root,
    )
    policy_path = _resolve_with_project_fallback(
        infra.producer.policy_file,
        base_dir=base_dir,
        project_root=project_root,
    )
    tax_mapping_path = None
    if infra.producer.tax_mapping_file is not None:
        tax_mapping_path = _resolve_with_project_fallback(
            infra.producer.tax_mapping_file,
            base_dir=base_dir,
            project_root=project_root,
        )
    archive_config_path = _resolve_with_project_fallback(
        infra.output.archive_config,
        base_dir=base_dir,
        project_root=project_root,
    )
    client_config_path = _resolve_with_project_fallback(
        infra.output.client_config,
        base_dir=base_dir,
        project_root=project_root,
    )

    input_config = infra.input.config
    input_config_updates: Dict[str, str] = {}
    if input_config.connector_mapping:
        input_config_updates["connector_mapping"] = str(
            _resolve_relative_to_base(
                input_config.connector_mapping,
                base_dir=base_dir,
            )
        )

    updates: Any = {
        "output": infra.output.model_copy(
            update={
                "archive_config": str(archive_config_path),
                "client_config": str(client_config_path),
            }
        ),
        "producer": infra.producer.model_copy(
            update={
                "schema_file": str(schema_path),
                "policy_file": str(policy_path),
                "tax_mapping_file": (
                    str(tax_mapping_path) if tax_mapping_path is not None else None
                ),
            }
        ),
    }
    if input_config_updates:
        updates["input"] = infra.input.model_copy(
            update={"config": input_config.model_copy(update=input_config_updates)}
        )

    return infra.model_copy(update=updates)


def _resolve_with_project_fallback(
    value: str,
    *,
    base_dir: Path,
    project_root: Path,
) -> Path:
    """Resolve a path with infra-dir first, then project-root fallback.

    Args:
        value: Raw path value from infra config.
        base_dir: Directory of infra YAML file.
        project_root: Project root directory used as fallback base.

    Returns:
        Absolute resolved path.
    """
    path = Path(value)
    if path.is_absolute():
        return path.expanduser().resolve()

    candidate = (base_dir / path).resolve()
    if candidate.exists():
        return candidate
    return (project_root / path).resolve()


def _resolve_relative_to_base(value: str, *, base_dir: Path) -> Path:
    """Resolve path against infra directory, preserving absolute inputs.

    Args:
        value: Raw path value from infra config.
        base_dir: Directory of infra YAML file.

    Returns:
        Absolute resolved path.
    """
    path = Path(value)
    if path.is_absolute():
        return path.expanduser().resolve()
    return (base_dir / path).resolve()


__all__: List[str] = ["normalize_infra_paths"]
