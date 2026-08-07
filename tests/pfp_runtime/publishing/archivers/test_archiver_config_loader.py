"""Tests for archiver_config_loader.load_archiver_config."""

import sys
import unittest.mock
from pathlib import Path

import pytest

from pfp_runtime.publishing.archivers.archiver_config_loader import (
    ArchiverConfigLoadError,
    load_archiver_config,
)

_VALID_YAML = """\
bucket: my-feed-archive
key_prefix: sent/
transport:
  timeout_seconds: 60
"""

_REAL_ARCHIVER_CONFIG = (
    Path(__file__).resolve().parents[4] / "config" / "archive" / "local.yaml"
)


def test_load_valid_file(tmp_path: Path) -> None:
    """Happy path: a well-formed YAML file is read and returns a dict with expected keys."""
    yaml_file = tmp_path / "archiver.yaml"
    yaml_file.write_text(_VALID_YAML, encoding="utf-8")

    result = load_archiver_config(str(yaml_file))

    assert isinstance(result, dict)
    assert "bucket" in result
    assert "key_prefix" in result
    assert result["key_prefix"] == "sent/"


def test_file_not_found(tmp_path: Path) -> None:
    """Missing file raises ArchiverConfigLoadError with 'cannot read' in message."""
    missing = tmp_path / "nonexistent.yaml"

    with pytest.raises(ArchiverConfigLoadError, match="cannot read"):
        load_archiver_config(str(missing))


def test_unsupported_extension(tmp_path: Path) -> None:
    """Non-YAML extension raises ArchiverConfigLoadError with 'unsupported' in message."""
    json_file = tmp_path / "archiver.json"
    json_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ArchiverConfigLoadError, match="unsupported"):
        load_archiver_config(str(json_file))


def test_broken_yaml_syntax(tmp_path: Path) -> None:
    """Invalid YAML syntax raises ArchiverConfigLoadError with 'invalid YAML' in message."""
    broken = tmp_path / "archiver.yaml"
    broken.write_text("key: [unclosed", encoding="utf-8")

    with pytest.raises(ArchiverConfigLoadError, match="invalid YAML"):
        load_archiver_config(str(broken))


def test_root_is_list(tmp_path: Path) -> None:
    """YAML root being a list raises ArchiverConfigLoadError with 'root must be a mapping'."""
    list_file = tmp_path / "archiver.yaml"
    list_file.write_text("- item1\n- item2\n", encoding="utf-8")

    with pytest.raises(ArchiverConfigLoadError, match="root must be a mapping"):
        load_archiver_config(str(list_file))


def test_empty_file(tmp_path: Path) -> None:
    """Empty YAML file (safe_load returns None) raises ArchiverConfigLoadError."""
    empty = tmp_path / "archiver.yaml"
    empty.write_text("", encoding="utf-8")

    with pytest.raises(ArchiverConfigLoadError, match="root must be a mapping"):
        load_archiver_config(str(empty))


def test_yml_extension_accepted(tmp_path: Path) -> None:
    """The .yml extension is accepted and the file is loaded without error."""
    yml_file = tmp_path / "archiver.yml"
    yml_file.write_text(_VALID_YAML, encoding="utf-8")

    result = load_archiver_config(str(yml_file))

    assert isinstance(result, dict)
    assert "bucket" in result


def test_path_as_str(tmp_path: Path) -> None:
    """Passing path as a plain str loads the file correctly."""
    yaml_file = tmp_path / "archiver.yaml"
    yaml_file.write_text(_VALID_YAML, encoding="utf-8")

    result = load_archiver_config(str(yaml_file))

    assert isinstance(result, dict)


def test_pyyaml_unavailable(tmp_path: Path) -> None:
    """ArchiverConfigLoadError is raised when PyYAML cannot be imported."""
    yaml_file = tmp_path / "archiver.yaml"
    yaml_file.write_text(_VALID_YAML, encoding="utf-8")

    with unittest.mock.patch.dict(sys.modules, {"yaml": None}):
        with pytest.raises(ArchiverConfigLoadError, match="PyYAML is unavailable"):
            load_archiver_config(str(yaml_file))


def test_real_archiver_config_file() -> None:
    """Integration smoke: the real config/archive/local.yaml loads as a non-empty dict with output_dir."""
    result = load_archiver_config(str(_REAL_ARCHIVER_CONFIG))

    assert isinstance(result, dict)
    assert len(result) > 0
    assert "output_dir" in result
