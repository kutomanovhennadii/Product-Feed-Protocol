"""Canonical infra config loader for runtime config layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Mapping

from pydantic import ValidationError

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.config.infra_validator import InfraConfigValidationError


class InfraConfigError(ValueError):
    """Base configuration contract error for canonical infra config."""


class InfraConfigParseError(InfraConfigError):
    """Raised when infra config cannot be read or parsed."""


def load_infra_config(path: str) -> InfraConfig:
    """Load canonical infra config from a YAML file path.

    Args:
        path: Absolute or relative path to an infra YAML file.

    Returns:
        Materialized canonical infra configuration.

    Raises:
        InfraConfigParseError: If the file extension is not YAML, the file cannot be
            read, or the YAML config cannot be parsed.
        InfraConfigValidationError: If the parsed YAML root is not a mapping or the
            config cannot be materialized into canonical models.
    """
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix not in (".yaml", ".yml"):
        raise InfraConfigParseError("unsupported infra file extension: " + suffix)

    try:
        config = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InfraConfigParseError(
            "cannot read infra config file: " + str(file_path)
        ) from exc

    parsed = _parse_infra_config(config)
    return _validate_infra_config(parsed)


def _parse_infra_config(config: str) -> Mapping[str, Any]:
    """Parse infra YAML text into a mapping.

    Args:
        config: Raw YAML text.

    Returns:
        Parsed mapping config.

    Raises:
        InfraConfigParseError: If YAML support is unavailable or YAML parsing fails.
        InfraConfigValidationError: If the YAML root is not a mapping.
    """
    try:
        import yaml as _yaml
    except ImportError as exc:
        raise InfraConfigParseError(
            "YAML support is unavailable: missing PyYAML"
        ) from exc

    try:
        loaded = _yaml.safe_load(config)
    except _yaml.YAMLError as exc:
        raise InfraConfigParseError("invalid YAML config") from exc

    if not isinstance(loaded, Mapping):
        raise InfraConfigValidationError("infra config root must be a mapping")
    return loaded


def _validate_infra_config(config: Mapping[str, Any]) -> InfraConfig:
    """Materialize a parsed mapping into canonical infra models.

    Args:
        config: Parsed YAML root config.

    Returns:
        Materialized canonical infra configuration.

    Raises:
        InfraConfigValidationError: If the config fails Pydantic validation.
    """
    try:
        return InfraConfig.model_validate(config)  # type: ignore[attr-defined]
    except ValidationError as exc:
        raise InfraConfigValidationError(_format_validation_error(exc)) from exc


def _format_validation_error(exc: ValidationError) -> str:
    """Build a safe validation error message from Pydantic details.

    The returned message is a compact summary that includes field locations and
    reasons without embedding any input values.

    Args:
        exc: Pydantic validation error.

    Returns:
        Sanitized, stable error message suitable for user-facing errors.
    """
    lines: List[str] = []
    for item in exc.errors():
        raw_loc = item.get("loc", ())
        if isinstance(raw_loc, tuple):
            loc_path = ".".join(str(segment) for segment in raw_loc)
        else:
            loc_path = str(raw_loc)
        message = str(item.get("msg", "validation error"))
        if loc_path:
            lines.append(loc_path + ": " + message)
        else:
            lines.append(message)

    if not lines:
        return "infra config validation failed"
    return "; ".join(lines)


__all__: List[str] = [
    "InfraConfigError",
    "InfraConfigParseError",
    "InfraConfigValidationError",
    "load_infra_config",
]
