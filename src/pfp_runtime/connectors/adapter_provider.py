"""Mini-factory. Loads SSoT registry, extracts class, and initializes it with constants."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Mapping, Type

from pfp_runtime.connectors.adapters.adapter_contract import FormatAdapter
from pfp_utils.logging import LogPipeline

_DEFAULT_REGISTRY_FILE = "connectors_registry.json"


class AdapterRegistryError(ValueError):
    """Raised when the adapter registry JSON is missing, malformed, or violates its schema."""


class UnknownFormatError(AdapterRegistryError):
    """Raised when the requested format is not found or is disabled in the registry."""


def provide_adapter(
    format_name: str,
    config: Mapping[str, Any],
    *,
    log_pipeline: LogPipeline,
) -> FormatAdapter:
    """Provide fully initialized adapter for a given format from the registry.

    Loads the registry JSON, resolving aliases and formats, extracts canonical target
    options, dynamically imports the requested class and instantiates it.

    Args:
        format_name: Name of the connector format to resolve (e.g., "csv", "json").
        config: User configuration extracted from the infra.yaml mapping.

    Returns:
        Fully initialized FormatAdapter instance ready for data parsing.

    Raises:
        UnknownFormatError: If the specified format is missing or disabled.
        AdapterRegistryError: Built format cannot be instantiated or validation fails.
    """
    registry_path = _extract_registry_path(config)
    registry_data = _load_registry(registry_path)
    adapter_path, constants = _extract_and_validate_format_spec(
        registry_data, format_name
    )
    adapter_class = _import_adapter_class(adapter_path)
    return _initialize_adapter(adapter_class, constants, log_pipeline=log_pipeline)


def _extract_registry_path(config: Mapping[str, Any]) -> Path | None:
    """Extract optional registry path from configuration.

    Args:
        config: The user configuration mapping payload.

    Returns:
        Path to registry if present in config, None otherwise.
    """
    registry_path_str = config.get("connectors_registry_path")
    if registry_path_str:
        return Path(str(registry_path_str))
    return None


def _load_registry(path: Path | None) -> dict[str, Any]:
    """Load registry objects from disk.

    Args:
        path: Optional explicit path. Defaults to local connectors_registry.json.

    Returns:
        Structured mapping of the JSON configuration containing all formats.

    Raises:
        AdapterRegistryError: If registry is unreadable or malformed.
    """
    registry_path = path or Path(__file__).parent / _DEFAULT_REGISTRY_FILE
    if not registry_path.exists():
        raise AdapterRegistryError(f"Registry file not found: {registry_path}")

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise AdapterRegistryError("Failed to parse registry JSON") from e

    if not isinstance(data, dict):
        raise AdapterRegistryError("Registry root must be a JSON object")

    if "formats" not in data or not isinstance(data["formats"], dict):
        raise AdapterRegistryError("Registry must contain 'formats' object")

    return data


def _extract_and_validate_format_spec(
    registry: dict[str, Any], format_name: str
) -> tuple[str, dict[str, Any]]:
    """Extract and validate adapter import path and constants.

    Args:
        registry: The raw dictionary containing the parsed registry.
        format_name: The targeted format.

    Returns:
        Tuple of (adapter import path, extracted constants dictionary).

    Raises:
        UnknownFormatError: If missing, disabled, or not string.
        AdapterRegistryError: If payload schema is invalid.
    """
    if not format_name or not isinstance(format_name, str):
        raise UnknownFormatError("Format name must be a non-empty string")

    requested = format_name.strip().lower()
    formats = registry["formats"]

    if requested not in formats:
        raise UnknownFormatError(f"Unknown format in registry: {requested}")

    entry = formats[requested]
    if not isinstance(entry, dict):
        raise AdapterRegistryError(
            f"Invalid schema: format '{requested}' entry must be an object"
        )

    status = str(entry.get("status", "active")).strip().lower()
    if status != "active":
        raise UnknownFormatError(f"Format is disabled in registry: {requested}")

    if "adapter" not in entry:
        raise AdapterRegistryError(f"Missing adapter path for format '{requested}'")

    adapter_path = entry["adapter"]
    if not isinstance(adapter_path, str) or not adapter_path.strip():
        raise AdapterRegistryError(f"Invalid adapter path for format '{requested}'")

    constants = entry.get("constants", {})
    if not isinstance(constants, dict):
        raise AdapterRegistryError(
            f"Constants for format '{requested}' must be an object"
        )

    return adapter_path.strip(), constants


def _import_adapter_class(adapter_path: str) -> Type[FormatAdapter]:
    """Dynamically import the adapter class using its path string.

    Args:
        adapter_path: Import string using the structure module_import_path.ClassName.

    Returns:
        Type class implementing the FormatAdapter protocol.

    Raises:
        AdapterRegistryError: If the module is broken or the class doesn't exist.
    """
    try:
        module_path, class_name = adapter_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        adapter_class = getattr(module, class_name)
    except Exception as e:
        raise AdapterRegistryError(f"Failed to import adapter: {adapter_path}") from e

    if not isinstance(adapter_class, type):
        raise AdapterRegistryError(f"Imported object '{adapter_path}' is not a class")

    return adapter_class


def _initialize_adapter(
    adapter_class: Type[FormatAdapter],
    constants: dict[str, Any],
    *,
    log_pipeline: LogPipeline,
) -> FormatAdapter:
    """Initialize adapter class using extracted registry constants payload.

    Args:
        adapter_class: Class implementing FormatAdapter to establish.
        constants: Extracted bounds payload or other constraints.

    Returns:
        A healthy instance of FormatAdapter.

    Raises:
        AdapterRegistryError: If the class constructor raises exceptions.
    """
    try:
        return adapter_class(constants=constants, log_pipeline=log_pipeline)
    except Exception as e:
        raise AdapterRegistryError(
            f"Failed to initialize adapter class '{adapter_class.__name__}'"
        ) from e
