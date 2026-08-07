"""Tests for connector_mapping_loader.load_yaml."""

import sys
import unittest.mock
from pathlib import Path

import pytest

from pfp_runtime.connectors.connector_mapping.connector_mapping_config import (
    ConnectorMappingLoadError,
)
from pfp_runtime.connectors.connector_mapping.connector_mapping_loader import load_yaml

_VALID_YAML = """\
mappings:
  - source: "sku"
    target: "product.item_id"
    required: true
  - source: "name"
    target: "product.title"

continue_on_error: false
"""

_REAL_MAPPING_PATH = Path(__file__).resolve().parents[4] / "config" / "mapping.yaml"


def test_load_yaml_valid_file(tmp_path: Path) -> None:
    """Happy path: a well-formed YAML file is read and returns a dict with expected keys."""
    yaml_file = tmp_path / "mapping.yaml"
    yaml_file.write_text(_VALID_YAML, encoding="utf-8")

    result = load_yaml(yaml_file)

    assert isinstance(result, dict)
    assert "mappings" in result
    assert "continue_on_error" in result
    assert result["continue_on_error"] is False
    assert len(result["mappings"]) == 2


def test_load_yaml_file_not_found(tmp_path: Path) -> None:
    """Missing file raises ConnectorMappingLoadError with 'cannot read' in message."""
    missing = tmp_path / "nonexistent.yaml"

    with pytest.raises(ConnectorMappingLoadError, match="cannot read"):
        load_yaml(missing)


def test_load_yaml_unsupported_extension(tmp_path: Path) -> None:
    """Non-YAML extension raises ConnectorMappingLoadError with 'unsupported' in message."""
    json_file = tmp_path / "mapping.json"
    json_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ConnectorMappingLoadError, match="unsupported"):
        load_yaml(json_file)


def test_load_yaml_broken_syntax(tmp_path: Path) -> None:
    """Invalid YAML syntax raises ConnectorMappingLoadError with 'invalid YAML' in message."""
    broken = tmp_path / "mapping.yaml"
    broken.write_text("key: [unclosed", encoding="utf-8")

    with pytest.raises(ConnectorMappingLoadError, match="invalid YAML"):
        load_yaml(broken)


def test_load_yaml_root_is_list(tmp_path: Path) -> None:
    """YAML root being a list raises ConnectorMappingLoadError with 'root must be a mapping'."""
    list_file = tmp_path / "mapping.yaml"
    list_file.write_text("- item1\n- item2\n", encoding="utf-8")

    with pytest.raises(ConnectorMappingLoadError, match="root must be a mapping"):
        load_yaml(list_file)


def test_load_yaml_empty_file(tmp_path: Path) -> None:
    """Empty YAML file (safe_load returns None) raises ConnectorMappingLoadError."""
    empty = tmp_path / "mapping.yaml"
    empty.write_text("", encoding="utf-8")

    with pytest.raises(ConnectorMappingLoadError, match="root must be a mapping"):
        load_yaml(empty)


def test_load_yaml_yml_extension_accepted(tmp_path: Path) -> None:
    """The .yml extension is accepted and the file is loaded without error."""
    yml_file = tmp_path / "mapping.yml"
    yml_file.write_text(_VALID_YAML, encoding="utf-8")

    result = load_yaml(yml_file)

    assert isinstance(result, dict)
    assert "mappings" in result


def test_load_yaml_path_as_str(tmp_path: Path) -> None:
    """Passing path as a plain str (not Path) loads the file correctly."""
    yaml_file = tmp_path / "mapping.yaml"
    yaml_file.write_text(_VALID_YAML, encoding="utf-8")

    result = load_yaml(str(yaml_file))

    assert isinstance(result, dict)
    assert "mappings" in result


def test_load_yaml_pyyaml_unavailable(tmp_path: Path) -> None:
    """ConnectorMappingLoadError is raised when PyYAML cannot be imported."""
    yaml_file = tmp_path / "mapping.yaml"
    yaml_file.write_text(_VALID_YAML, encoding="utf-8")

    with unittest.mock.patch.dict(sys.modules, {"yaml": None}):
        with pytest.raises(ConnectorMappingLoadError, match="PyYAML is unavailable"):
            load_yaml(yaml_file)


def test_load_yaml_real_mapping_file() -> None:
    """Integration smoke test: the real project config/mapping.yaml loads as a non-empty dict."""
    result = load_yaml(_REAL_MAPPING_PATH)

    assert isinstance(result, dict)
    assert len(result) > 0
    assert "mappings" in result
