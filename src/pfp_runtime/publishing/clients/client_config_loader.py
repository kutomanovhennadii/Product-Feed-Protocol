"""I/O layer for delivery client IaC YAML files.

Reads a client config file from disk and returns a raw, untrusted dict.
Pydantic validation and secret resolution are the responsibility of client_builder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


class ClientConfigLoadError(ValueError):
    """Raised when a client IaC config file cannot be read or parsed."""


def load_client_config(path: str) -> Dict[str, Any]:
    """Load a delivery client IaC config from a YAML file and return the raw dict.

    Args:
        path: Absolute or relative path to a client IaC YAML file.

    Returns:
        Raw config dict (untrusted — pass to iac_class.model_validate before use).

    Raises:
        ClientConfigLoadError: If the extension is unsupported, the file cannot
            be read, PyYAML is unavailable, YAML syntax is invalid, or the root
            is not a mapping.
    """
    file_path = Path(path)

    suffix = file_path.suffix.lower()
    if suffix not in (".yaml", ".yml"):
        raise ClientConfigLoadError(
            "unsupported client config file extension: " + suffix
        )

    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ClientConfigLoadError(
            "cannot read client config file: " + str(file_path)
        ) from exc

    try:
        import yaml as _yaml  # noqa: PLC0415 — intentional lazy import
    except ImportError as exc:
        raise ClientConfigLoadError("PyYAML is unavailable: install pyyaml") from exc

    try:
        loaded = _yaml.safe_load(text)
    except _yaml.YAMLError as exc:
        raise ClientConfigLoadError(
            "invalid YAML in client config file: " + str(file_path)
        ) from exc

    if not isinstance(loaded, dict):
        raise ClientConfigLoadError(
            "client config root must be a mapping, got: " + type(loaded).__name__
        )

    return loaded


__all__: List[str] = ["ClientConfigLoadError", "load_client_config"]
