"""Tests for client_config_loader.load_client_config."""

import sys
import unittest.mock
from pathlib import Path

import pytest

from pfp_runtime.publishing.clients.client_config_loader import (
    ClientConfigLoadError,
    load_client_config,
)

_VALID_YAML = """\
endpoint: https://api.example.com/feed
transport:
  timeout_seconds: 30
"""

_REAL_CLIENT_CONFIG = (
    Path(__file__).resolve().parents[4] / "config" / "clients" / "http.yaml"
)


def test_load_valid_file(tmp_path: Path) -> None:
    """Happy path: a well-formed YAML file is read and returns a dict with expected keys."""
    yaml_file = tmp_path / "client.yaml"
    yaml_file.write_text(_VALID_YAML, encoding="utf-8")

    result = load_client_config(str(yaml_file))

    assert isinstance(result, dict)
    assert "endpoint" in result
    assert result["endpoint"] == "https://api.example.com/feed"


def test_file_not_found(tmp_path: Path) -> None:
    """Missing file raises ClientConfigLoadError with 'cannot read' in message."""
    missing = tmp_path / "nonexistent.yaml"

    with pytest.raises(ClientConfigLoadError, match="cannot read"):
        load_client_config(str(missing))


def test_unsupported_extension(tmp_path: Path) -> None:
    """Non-YAML extension raises ClientConfigLoadError with 'unsupported' in message."""
    json_file = tmp_path / "client.json"
    json_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ClientConfigLoadError, match="unsupported"):
        load_client_config(str(json_file))


def test_broken_yaml_syntax(tmp_path: Path) -> None:
    """Invalid YAML syntax raises ClientConfigLoadError with 'invalid YAML' in message."""
    broken = tmp_path / "client.yaml"
    broken.write_text("key: [unclosed", encoding="utf-8")

    with pytest.raises(ClientConfigLoadError, match="invalid YAML"):
        load_client_config(str(broken))


def test_root_is_list(tmp_path: Path) -> None:
    """YAML root being a list raises ClientConfigLoadError with 'root must be a mapping'."""
    list_file = tmp_path / "client.yaml"
    list_file.write_text("- item1\n- item2\n", encoding="utf-8")

    with pytest.raises(ClientConfigLoadError, match="root must be a mapping"):
        load_client_config(str(list_file))


def test_empty_file(tmp_path: Path) -> None:
    """Empty YAML file (safe_load returns None) raises ClientConfigLoadError."""
    empty = tmp_path / "client.yaml"
    empty.write_text("", encoding="utf-8")

    with pytest.raises(ClientConfigLoadError, match="root must be a mapping"):
        load_client_config(str(empty))


def test_yml_extension_accepted(tmp_path: Path) -> None:
    """The .yml extension is accepted and the file is loaded without error."""
    yml_file = tmp_path / "client.yml"
    yml_file.write_text(_VALID_YAML, encoding="utf-8")

    result = load_client_config(str(yml_file))

    assert isinstance(result, dict)
    assert "endpoint" in result


def test_path_as_str(tmp_path: Path) -> None:
    """Passing path as a plain str loads the file correctly."""
    yaml_file = tmp_path / "client.yaml"
    yaml_file.write_text(_VALID_YAML, encoding="utf-8")

    result = load_client_config(str(yaml_file))

    assert isinstance(result, dict)


def test_pyyaml_unavailable(tmp_path: Path) -> None:
    """ClientConfigLoadError is raised when PyYAML cannot be imported."""
    yaml_file = tmp_path / "client.yaml"
    yaml_file.write_text(_VALID_YAML, encoding="utf-8")

    with unittest.mock.patch.dict(sys.modules, {"yaml": None}):
        with pytest.raises(ClientConfigLoadError, match="PyYAML is unavailable"):
            load_client_config(str(yaml_file))


def test_real_client_config_file() -> None:
    """Integration smoke: the real config/clients/http.yaml loads as a non-empty dict with endpoint."""
    result = load_client_config(str(_REAL_CLIENT_CONFIG))

    assert isinstance(result, dict)
    assert len(result) > 0
    assert "endpoint" in result
