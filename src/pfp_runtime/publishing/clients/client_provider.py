"""Resolves client class and IaC class by client_type from the registry."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Tuple, Type

_REGISTRY_FILE = "clients_registry.json"


class ClientRegistryError(ValueError):
    """Registry JSON is missing, malformed, or an import failed."""


class UnknownClientTypeError(ClientRegistryError):
    """Requested client_type is not found in the registry."""


def resolve_client(client_type: str) -> Tuple[Type[Any], Type[Any]]:
    """Return (client_class, iac_class) for the given client_type.

    Reads clients_registry.json next to this file.
    Both classes are imported dynamically from their dotted paths.

    Args:
        client_type: Registry key, e.g. "http", "http_streaming", "sftp", "noop".

    Returns:
        Tuple of (client_class, iac_class).

    Raises:
        UnknownClientTypeError: client_type not found in registry.
        ClientRegistryError: Registry missing/malformed or import failed.
    """
    registry = _load_registry()
    entry = _extract_entry(registry, client_type)
    client_class = _import_class(entry["class"])
    iac_class = _import_class(entry["iac_class"])
    return client_class, iac_class


def _load_registry() -> dict:
    """Load and validate clients_registry.json from the same directory as this file.

    Returns:
        Parsed registry dict with a top-level "clients" object.

    Raises:
        ClientRegistryError: If the file is missing, JSON is malformed, or the
            root structure is invalid.
    """
    registry_path = Path(__file__).parent / _REGISTRY_FILE
    if not registry_path.exists():
        raise ClientRegistryError(f"Registry file not found: {registry_path}")

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ClientRegistryError("Failed to parse registry JSON") from e

    if not isinstance(data, dict):
        raise ClientRegistryError("Registry root must be a JSON object")

    if "clients" not in data or not isinstance(data["clients"], dict):
        raise ClientRegistryError("Registry must contain 'clients' object")

    return data


def _extract_entry(registry: dict, client_type: str) -> dict:
    """Extract and normalise the registry entry for the given client_type.

    Args:
        registry: Parsed registry dict (must contain "clients" object).
        client_type: Requested client key; matched case-insensitively.

    Returns:
        Dict with normalised "class" and "iac_class" dotted import paths.

    Raises:
        UnknownClientTypeError: client_type is empty or not found in the registry.
        ClientRegistryError: Entry is not a dict or required fields are missing/empty.
    """
    if not client_type or not isinstance(client_type, str):
        raise UnknownClientTypeError("client_type must be a non-empty string")

    key = client_type.strip().lower()
    clients = registry["clients"]

    if key not in clients:
        raise UnknownClientTypeError(f"Unknown client_type in registry: {key}")

    entry = clients[key]
    if not isinstance(entry, dict):
        raise ClientRegistryError(
            f"Invalid schema: entry for '{key}' must be an object"
        )

    for field in ("class", "iac_class"):
        if (
            field not in entry
            or not isinstance(entry[field], str)
            or not entry[field].strip()
        ):
            raise ClientRegistryError(
                f"Missing or empty field '{field}' for client_type '{key}'"
            )

    return {
        "class": entry["class"].strip(),
        "iac_class": entry["iac_class"].strip(),
    }


def _import_class(dotted_path: str) -> Type[Any]:
    """Dynamically import a class from its dotted module path.

    Args:
        dotted_path: Full dotted path of the form "package.module.ClassName".

    Returns:
        The imported class object.

    Raises:
        ClientRegistryError: If the module cannot be imported, the attribute does
            not exist, or the resolved object is not a class.
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
    except Exception as e:
        raise ClientRegistryError(f"Failed to import: {dotted_path}") from e

    if not isinstance(cls, type):
        raise ClientRegistryError(f"Imported object '{dotted_path}' is not a class")

    return cls
