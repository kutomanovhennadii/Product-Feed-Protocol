"""Tests for archiver_provider.resolve_archiver."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pfp_runtime.publishing.archivers.archiver_provider import (
    ArchiverRegistryError,
    UnknownArchiverTypeError,
    resolve_archiver,
)
from pfp_runtime.publishing.archivers.local_archiver import (
    LocalArchiver,
    LocalArchiverIaC,
)
from pfp_runtime.publishing.archivers.noop_archiver import NoopArchiver, NoopArchiverIaC
from pfp_runtime.publishing.archivers.s3_archiver import S3Archiver, S3ArchiverIaC
from pfp_runtime.publishing.archivers.s3_compat_archiver import (
    S3CompatArchiver,
    S3CompatArchiverIaC,
)

# ---------------------------------------------------------------------------
# Happy path — real registry
# ---------------------------------------------------------------------------


def test_resolve_local():
    """resolve_archiver("local") returns (LocalArchiver, LocalArchiverIaC)."""
    archiver_cls, iac_cls = resolve_archiver("local")
    assert archiver_cls is LocalArchiver
    assert iac_cls is LocalArchiverIaC


def test_resolve_s3():
    """resolve_archiver("s3") returns (S3Archiver, S3ArchiverIaC)."""
    archiver_cls, iac_cls = resolve_archiver("s3")
    assert archiver_cls is S3Archiver
    assert iac_cls is S3ArchiverIaC


def test_resolve_s3_compat():
    """resolve_archiver("s3_compat") returns (S3CompatArchiver, S3CompatArchiverIaC)."""
    archiver_cls, iac_cls = resolve_archiver("s3_compat")
    assert archiver_cls is S3CompatArchiver
    assert iac_cls is S3CompatArchiverIaC


def test_resolve_noop():
    """resolve_archiver("noop") returns (NoopArchiver, NoopArchiverIaC)."""
    archiver_cls, iac_cls = resolve_archiver("noop")
    assert archiver_cls is NoopArchiver
    assert iac_cls is NoopArchiverIaC


def test_resolve_case_insensitive():
    """archive_type lookup is case-insensitive: "LOCAL" resolves to LocalArchiver."""
    archiver_cls, iac_cls = resolve_archiver("LOCAL")
    assert archiver_cls is LocalArchiver
    assert iac_cls is LocalArchiverIaC


# ---------------------------------------------------------------------------
# Unknown / empty type
# ---------------------------------------------------------------------------


def test_resolve_unknown_type_raises():
    """Unknown archive_type raises UnknownArchiverTypeError with the type name in the message."""
    with pytest.raises(UnknownArchiverTypeError, match="unknown_xyz"):
        resolve_archiver("unknown_xyz")


def test_resolve_empty_type_raises():
    """Empty archive_type raises UnknownArchiverTypeError."""
    with pytest.raises(UnknownArchiverTypeError):
        resolve_archiver("")


# ---------------------------------------------------------------------------
# Registry file errors (synthetic registry via monkeypatch)
# ---------------------------------------------------------------------------


def _patch_registry(tmp_path: Path, content: str):
    """Write synthetic registry and patch __file__ of archiver_provider."""
    registry = tmp_path / "archivers_registry.json"
    registry.write_text(content, encoding="utf-8")
    return patch(
        "pfp_runtime.publishing.archivers.archiver_provider.__file__",
        str(tmp_path / "archiver_provider.py"),
    )


def test_registry_file_missing(tmp_path):
    """Missing registry file raises ArchiverRegistryError with 'not found' in message."""
    with patch(
        "pfp_runtime.publishing.archivers.archiver_provider.__file__",
        str(tmp_path / "archiver_provider.py"),
    ):
        with pytest.raises(ArchiverRegistryError, match="not found"):
            resolve_archiver("local")


def test_registry_invalid_json(tmp_path):
    """Malformed JSON in registry file raises ArchiverRegistryError with 'parse' in message."""
    with _patch_registry(tmp_path, "not valid json {{"):
        with pytest.raises(ArchiverRegistryError, match="parse"):
            resolve_archiver("local")


def test_registry_missing_archivers_key(tmp_path):
    """Registry JSON without 'archivers' key raises ArchiverRegistryError."""
    payload = json.dumps({"other": {}})
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ArchiverRegistryError, match="'archivers'"):
            resolve_archiver("local")


def test_registry_root_not_dict(tmp_path):
    """Registry root is a JSON array, not an object — must raise ArchiverRegistryError."""
    with _patch_registry(tmp_path, "[1, 2, 3]"):
        with pytest.raises(ArchiverRegistryError, match="JSON object"):
            resolve_archiver("local")


def test_registry_entry_not_dict(tmp_path):
    """Registry entry is a string, not an object — must raise ArchiverRegistryError."""
    payload = json.dumps({"archivers": {"local": "not-a-dict"}})
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ArchiverRegistryError, match="must be an object"):
            resolve_archiver("local")


def test_registry_entry_missing_class_field(tmp_path):
    """Registry entry without 'class' field raises ArchiverRegistryError."""
    payload = json.dumps(
        {
            "archivers": {
                "local": {
                    "iac_class": "pfp_runtime.publishing.archivers.local_archiver.LocalArchiverIaC"
                }
            }
        }
    )
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ArchiverRegistryError, match="'class'"):
            resolve_archiver("local")


def test_registry_entry_missing_iac_class_field(tmp_path):
    """Registry entry without 'iac_class' field raises ArchiverRegistryError."""
    payload = json.dumps(
        {
            "archivers": {
                "local": {
                    "class": "pfp_runtime.publishing.archivers.local_archiver.LocalArchiver"
                }
            }
        }
    )
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ArchiverRegistryError, match="'iac_class'"):
            resolve_archiver("local")


def test_registry_entry_invalid_import_path(tmp_path):
    """Non-existent module in 'class' path raises ArchiverRegistryError with 'Failed to import'."""
    payload = json.dumps(
        {
            "archivers": {
                "local": {
                    "class": "pfp_runtime.publishing.archivers.nonexistent_module.SomeClass",
                    "iac_class": "pfp_runtime.publishing.archivers.local_archiver.LocalArchiverIaC",
                }
            }
        }
    )
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ArchiverRegistryError, match="Failed to import"):
            resolve_archiver("local")


def test_import_non_class_object(tmp_path):
    """Imported path points to a module-level constant, not a class — must raise ArchiverRegistryError."""
    payload = json.dumps(
        {
            "archivers": {
                "local": {
                    "class": "pfp_runtime.publishing.archivers.archiver_provider._REGISTRY_FILE",
                    "iac_class": "pfp_runtime.publishing.archivers.local_archiver.LocalArchiverIaC",
                }
            }
        }
    )
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ArchiverRegistryError, match="is not a class"):
            resolve_archiver("local")
