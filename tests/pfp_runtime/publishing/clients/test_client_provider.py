"""Tests for client_provider.resolve_client."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pfp_runtime.publishing.clients.client_provider import (
    ClientRegistryError,
    UnknownClientTypeError,
    resolve_client,
)
from pfp_runtime.publishing.clients.http_client import HttpClientIaC, HttpDeliveryClient
from pfp_runtime.publishing.clients.noop_client import NoopClient, NoopClientIaC
from pfp_runtime.publishing.clients.sftp_client import SftpClientIaC, SftpDeliveryClient
from pfp_runtime.publishing.clients.streaming_http_client import (
    StreamingHttpDeliveryClient,
)

# ---------------------------------------------------------------------------
# Happy path — real registry
# ---------------------------------------------------------------------------


def test_resolve_http():
    """resolve_client("http") returns (HttpDeliveryClient, HttpClientIaC)."""
    client_cls, iac_cls = resolve_client("http")
    assert client_cls is HttpDeliveryClient
    assert iac_cls is HttpClientIaC


def test_resolve_http_streaming():
    """resolve_client("http_streaming") returns StreamingHttpDeliveryClient with shared HttpClientIaC."""
    client_cls, iac_cls = resolve_client("http_streaming")
    assert client_cls is StreamingHttpDeliveryClient
    assert iac_cls is HttpClientIaC  # shared IaC model


def test_resolve_sftp():
    """resolve_client("sftp") returns (SftpDeliveryClient, SftpClientIaC)."""
    client_cls, iac_cls = resolve_client("sftp")
    assert client_cls is SftpDeliveryClient
    assert iac_cls is SftpClientIaC


def test_resolve_noop():
    """resolve_client("noop") returns (NoopClient, NoopClientIaC)."""
    client_cls, iac_cls = resolve_client("noop")
    assert client_cls is NoopClient
    assert iac_cls is NoopClientIaC


def test_resolve_case_insensitive():
    """client_type lookup is case-insensitive: "HTTP" resolves to HttpDeliveryClient."""
    client_cls, iac_cls = resolve_client("HTTP")
    assert client_cls is HttpDeliveryClient
    assert iac_cls is HttpClientIaC


# ---------------------------------------------------------------------------
# Unknown / empty type
# ---------------------------------------------------------------------------


def test_resolve_unknown_type_raises():
    """Unknown client_type raises UnknownClientTypeError with the type name in the message."""
    with pytest.raises(UnknownClientTypeError, match="unknown_xyz"):
        resolve_client("unknown_xyz")


def test_resolve_empty_type_raises():
    """Empty client_type raises UnknownClientTypeError."""
    with pytest.raises(UnknownClientTypeError):
        resolve_client("")


# ---------------------------------------------------------------------------
# Registry file errors (synthetic registry via monkeypatch)
# ---------------------------------------------------------------------------


def _patch_registry(tmp_path: Path, content: str):
    """Write synthetic registry and patch __file__ of client_provider."""
    registry = tmp_path / "clients_registry.json"
    registry.write_text(content, encoding="utf-8")
    return patch(
        "pfp_runtime.publishing.clients.client_provider.__file__",
        str(tmp_path / "client_provider.py"),
    )


def test_registry_file_missing(tmp_path):
    """Missing registry file raises ClientRegistryError with 'not found' in message."""
    with patch(
        "pfp_runtime.publishing.clients.client_provider.__file__",
        str(tmp_path / "client_provider.py"),
    ):
        with pytest.raises(ClientRegistryError, match="not found"):
            resolve_client("http")


def test_registry_invalid_json(tmp_path):
    """Malformed JSON in registry file raises ClientRegistryError with 'parse' in message."""
    with _patch_registry(tmp_path, "not valid json {{"):
        with pytest.raises(ClientRegistryError, match="parse"):
            resolve_client("http")


def test_registry_missing_clients_key(tmp_path):
    """Registry JSON without 'clients' key raises ClientRegistryError."""
    payload = json.dumps({"other": {}})
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ClientRegistryError, match="'clients'"):
            resolve_client("http")


def test_registry_root_not_dict(tmp_path):
    """Registry root is a JSON array, not an object — must raise ClientRegistryError."""
    with _patch_registry(tmp_path, "[1, 2, 3]"):
        with pytest.raises(ClientRegistryError, match="JSON object"):
            resolve_client("http")


def test_registry_entry_not_dict(tmp_path):
    """Registry entry is a string, not an object — must raise ClientRegistryError."""
    payload = json.dumps({"clients": {"http": "not-a-dict"}})
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ClientRegistryError, match="must be an object"):
            resolve_client("http")


def test_registry_entry_missing_class_field(tmp_path):
    """Registry entry without 'class' field raises ClientRegistryError."""
    payload = json.dumps(
        {
            "clients": {
                "http": {
                    "iac_class": "pfp_runtime.publishing.clients.http_client.HttpClientIaC"
                }
            }
        }
    )
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ClientRegistryError, match="'class'"):
            resolve_client("http")


def test_registry_entry_missing_iac_class_field(tmp_path):
    """Registry entry without 'iac_class' field raises ClientRegistryError."""
    payload = json.dumps(
        {
            "clients": {
                "http": {
                    "class": "pfp_runtime.publishing.clients.http_client.HttpDeliveryClient"
                }
            }
        }
    )
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ClientRegistryError, match="'iac_class'"):
            resolve_client("http")


def test_registry_entry_invalid_import_path(tmp_path):
    """Non-existent module in 'class' path raises ClientRegistryError with 'Failed to import'."""
    payload = json.dumps(
        {
            "clients": {
                "http": {
                    "class": "pfp_runtime.publishing.clients.nonexistent_module.SomeClass",
                    "iac_class": "pfp_runtime.publishing.clients.http_client.HttpClientIaC",
                }
            }
        }
    )
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ClientRegistryError, match="Failed to import"):
            resolve_client("http")


def test_import_non_class_object(tmp_path):
    """Imported path points to a module-level constant, not a class — must raise ClientRegistryError."""
    payload = json.dumps(
        {
            "clients": {
                "http": {
                    "class": "pfp_runtime.publishing.clients.client_provider._REGISTRY_FILE",
                    "iac_class": "pfp_runtime.publishing.clients.http_client.HttpClientIaC",
                }
            }
        }
    )
    with _patch_registry(tmp_path, payload):
        with pytest.raises(ClientRegistryError, match="is not a class"):
            resolve_client("http")
