"""I/O layer for archiver IaC YAML files.

Reads an archiver config file from disk and returns a raw, untrusted dict.
Pydantic validation and secret resolution are the responsibility of archiver_builder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


class ArchiverConfigLoadError(ValueError):
    """Raised when an archiver IaC config file cannot be read or parsed."""


def load_archiver_config(path: str) -> Dict[str, Any]:
    """Load an archiver IaC config from a YAML file and return the raw dict.

    Args:
        path: Absolute or relative path to an archiver IaC YAML file.

    Returns:
        Raw config dict (untrusted — pass to iac_class.model_validate before use).

    Raises:
        ArchiverConfigLoadError: If the extension is unsupported, the file cannot
            be read, PyYAML is unavailable, YAML syntax is invalid, or the root
            is not a mapping.
    """
    file_path = Path(path)

    suffix = file_path.suffix.lower()
    if suffix not in (".yaml", ".yml"):
        raise ArchiverConfigLoadError(
            "unsupported archiver config file extension: " + suffix
        )

    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ArchiverConfigLoadError(
            "cannot read archiver config file: " + str(file_path)
        ) from exc

    try:
        import yaml as _yaml  # noqa: PLC0415 — intentional lazy import
    except ImportError as exc:
        raise ArchiverConfigLoadError("PyYAML is unavailable: install pyyaml") from exc

    try:
        loaded = _yaml.safe_load(text)
    except _yaml.YAMLError as exc:
        raise ArchiverConfigLoadError(
            "invalid YAML in archiver config file: " + str(file_path)
        ) from exc

    if not isinstance(loaded, dict):
        raise ArchiverConfigLoadError(
            "archiver config root must be a mapping, got: " + type(loaded).__name__
        )

    return loaded


__all__: List[str] = ["ArchiverConfigLoadError", "load_archiver_config"]
