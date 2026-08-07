"""I/O layer for connector mapping YAML files.

Reads a mapping YAML file from disk and returns a raw, untrusted dict.
Semantic validation is the responsibility of connector_mapping_validator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Union

from pfp_runtime.connectors.connector_mapping.connector_mapping_config import (
    ConnectorMappingLoadError,
)


def load_yaml(mapping_path: Union[str, Path]) -> Dict[str, Any]:
    """Load a connector mapping YAML file and return the raw config dict.

    Mirrors the pattern of ``infra_loader._parse_infra_config``:
    lazy PyYAML import, ``yaml.safe_load``, UTF-8 text read, root-type check.

    Args:
        mapping_path: Path to the mapping YAML file (str or Path).

    Returns:
        Raw mapping dict (untrusted — pass to validate_mapping before use).

    Raises:
        ConnectorMappingLoadError: If the file extension is unsupported, the file
            cannot be read, PyYAML is unavailable, the YAML syntax is invalid,
            or the root is not a mapping.
    """
    path = Path(mapping_path)

    suffix = path.suffix.lower()
    if suffix not in (".yaml", ".yml"):
        raise ConnectorMappingLoadError("unsupported mapping file extension: " + suffix)

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConnectorMappingLoadError(
            "cannot read mapping file: " + str(path)
        ) from exc

    try:
        import yaml as _yaml  # noqa: PLC0415 — intentional lazy import
    except ImportError as exc:
        raise ConnectorMappingLoadError(
            "PyYAML is unavailable: install pyyaml"
        ) from exc

    try:
        loaded = _yaml.safe_load(text)
    except _yaml.YAMLError as exc:
        raise ConnectorMappingLoadError(
            "invalid YAML in mapping file: " + str(path)
        ) from exc

    if not isinstance(loaded, dict):
        raise ConnectorMappingLoadError(
            "mapping file root must be a mapping, got: " + type(loaded).__name__
        )

    return loaded


__all__: List[str] = ["load_yaml"]
