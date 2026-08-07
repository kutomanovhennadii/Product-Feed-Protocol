"""Resolves archiver class and IaC class by archive_type from the registry."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Tuple, Type

_REGISTRY_FILE = "archivers_registry.json"


class ArchiverRegistryError(ValueError):
    """Registry JSON is missing, malformed, or an import failed."""


class UnknownArchiverTypeError(ArchiverRegistryError):
    """Requested archive_type is not found in the registry."""


def resolve_archiver(archive_type: str) -> Tuple[Type[Any], Type[Any]]:
    """Return (archiver_class, iac_class) for the given archive_type.

    Reads archivers_registry.json next to this file.
    Both classes are imported dynamically from their dotted paths.

    Args:
        archive_type: Registry key, e.g. "local", "s3", "s3_compat", "noop".

    Returns:
        Tuple of (archiver_class, iac_class).

    Raises:
        UnknownArchiverTypeError: archive_type not found in registry.
        ArchiverRegistryError: Registry missing/malformed or import failed.
    """
    registry = _load_registry()
    entry = _extract_entry(registry, archive_type)
    archiver_class = _import_class(entry["class"])
    iac_class = _import_class(entry["iac_class"])
    return archiver_class, iac_class


def _load_registry() -> dict:
    """Load and validate archivers_registry.json from the same directory as this file.

    Returns:
        Parsed registry dict with a top-level "archivers" object.

    Raises:
        ArchiverRegistryError: If the file is missing, JSON is malformed, or the
            root structure is invalid.
    """
    registry_path = Path(__file__).parent / _REGISTRY_FILE
    if not registry_path.exists():
        raise ArchiverRegistryError(f"Registry file not found: {registry_path}")

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ArchiverRegistryError("Failed to parse registry JSON") from e

    if not isinstance(data, dict):
        raise ArchiverRegistryError("Registry root must be a JSON object")

    if "archivers" not in data or not isinstance(data["archivers"], dict):
        raise ArchiverRegistryError("Registry must contain 'archivers' object")

    return data


def _extract_entry(registry: dict, archive_type: str) -> dict:
    """Extract and normalise the registry entry for the given archive_type.

    Args:
        registry: Parsed registry dict (must contain "archivers" object).
        archive_type: Requested archiver key; matched case-insensitively.

    Returns:
        Dict with normalised "class" and "iac_class" dotted import paths.

    Raises:
        UnknownArchiverTypeError: archive_type is empty or not found in the registry.
        ArchiverRegistryError: Entry is not a dict or required fields are missing/empty.
    """
    if not archive_type or not isinstance(archive_type, str):
        raise UnknownArchiverTypeError("archive_type must be a non-empty string")

    key = archive_type.strip().lower()
    archivers = registry["archivers"]

    if key not in archivers:
        raise UnknownArchiverTypeError(f"Unknown archive_type in registry: {key}")

    entry = archivers[key]
    if not isinstance(entry, dict):
        raise ArchiverRegistryError(
            f"Invalid schema: entry for '{key}' must be an object"
        )

    for field in ("class", "iac_class"):
        if (
            field not in entry
            or not isinstance(entry[field], str)
            or not entry[field].strip()
        ):
            raise ArchiverRegistryError(
                f"Missing or empty field '{field}' for archive_type '{key}'"
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
        ArchiverRegistryError: If the module cannot be imported, the attribute does
            not exist, or the resolved object is not a class.
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
    except Exception as e:
        raise ArchiverRegistryError(f"Failed to import: {dotted_path}") from e

    if not isinstance(cls, type):
        raise ArchiverRegistryError(f"Imported object '{dotted_path}' is not a class")

    return cls
