"""Tests for adapter_provider."""

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import pytest

from pfp_runtime.connectors.adapter_provider import (
    AdapterRegistryError,
    UnknownFormatError,
    provide_adapter,
)


class _LogPipelineStub:
    def log_process(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class MockAdapter:
    """Mock adapter for testing."""

    def __init__(
        self,
        constants: Mapping[str, Any],
        *,
        log_pipeline: Any,
    ) -> None:
        del log_pipeline
        self.constants = constants
        self.format_name = "mock_format"

    def parse(self, raw_input: Any) -> Iterable[Mapping[str, Any]]:
        yield {}


class FaultyAdapter:
    """Mock adapter that fails on initialization."""

    def __init__(
        self,
        constants: Mapping[str, Any],
        *,
        log_pipeline: Any,
    ) -> None:
        del constants, log_pipeline
        raise ValueError("Initialization failure")


def create_temp_registry(path: Path, config_data: dict) -> dict:
    path.write_text(json.dumps(config_data), encoding="utf-8")
    return {"connectors_registry_path": str(path)}


def test_provide_adapter_success(tmp_path: Path):
    """Test successful extraction, import, and initialization."""
    config_data = {
        "formats": {
            "good_format": {
                "adapter": "tests.pfp_runtime.connectors.test_adapter_provider.MockAdapter",
                "status": "active",
                "constants": {"mock_limit": 42},
            }
        }
    }
    config = create_temp_registry(tmp_path / "connectors_registry.json", config_data)

    adapter = provide_adapter(
        "good_format",
        config,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    assert adapter.__class__.__name__ == "MockAdapter"
    assert getattr(adapter, "constants", {}) == {"mock_limit": 42}


def test_provide_adapter_missing_format(tmp_path: Path):
    """Test that missing format raises UnknownFormatError."""
    config_data: dict[str, Any] = {"formats": {}}
    config = create_temp_registry(tmp_path / "connectors_registry.json", config_data)

    with pytest.raises(UnknownFormatError, match="Unknown format in registry"):
        provide_adapter(
            "missing_format",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_provide_adapter_disabled_format(tmp_path: Path):
    """Test that disabled format raises UnknownFormatError."""
    config_data = {
        "formats": {
            "disabled_format": {
                "adapter": "tests.pfp_runtime.connectors.test_adapter_provider.MockAdapter",
                "status": "disabled",
            }
        }
    }
    config = create_temp_registry(tmp_path / "connectors_registry.json", config_data)

    with pytest.raises(UnknownFormatError, match="Format is disabled"):
        provide_adapter(
            "disabled_format",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_invalid_registry_file(tmp_path: Path):
    """Test that missing or invalid registry file raises AdapterRegistryError."""
    missing_path = tmp_path / "nonexistent.json"
    config = {"connectors_registry_path": str(missing_path)}
    with pytest.raises(AdapterRegistryError, match="Registry file not found"):
        provide_adapter(
            "some_format",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )

    invalid_json_path = tmp_path / "invalid.json"
    invalid_json_path.write_text("invalid json")
    config = {"connectors_registry_path": str(invalid_json_path)}
    with pytest.raises(AdapterRegistryError, match="Failed to parse registry JSON"):
        provide_adapter(
            "some_format",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_invalid_format_entry(tmp_path: Path):
    """Test validation errors for bad schema in registry."""
    config_data = {
        "formats": {
            "no_adapter": {"status": "active"},
            "bad_constants": {
                "adapter": "tests.pfp_runtime.connectors.test_adapter_provider.MockAdapter",
                "constants": "not_a_dict",
            },
        }
    }
    config = create_temp_registry(tmp_path / "connectors_registry.json", config_data)

    with pytest.raises(AdapterRegistryError, match="Missing adapter path"):
        provide_adapter(
            "no_adapter",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )

    with pytest.raises(
        AdapterRegistryError,
        match="Constants for format 'bad_constants' must be an object",
    ):
        provide_adapter(
            "bad_constants",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_import_failure(tmp_path: Path):
    """Test failure when import path is malformed or missing."""
    config_data = {"formats": {"bad_import": {"adapter": "non.existent.Module"}}}
    config = create_temp_registry(tmp_path / "connectors_registry.json", config_data)

    with pytest.raises(AdapterRegistryError, match="Failed to import adapter"):
        provide_adapter(
            "bad_import",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_initialization_failure(tmp_path: Path):
    """Test failure when class raises error during init."""
    config_data = {
        "formats": {
            "faulty": {
                "adapter": "tests.pfp_runtime.connectors.test_adapter_provider.FaultyAdapter"
            }
        }
    }
    config = create_temp_registry(tmp_path / "connectors_registry.json", config_data)

    with pytest.raises(
        AdapterRegistryError, match="Failed to initialize adapter class"
    ):
        provide_adapter(
            "faulty",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_missing_registry_path_in_config(monkeypatch, tmp_path: Path):
    """Test that default registry path is used if not in config."""
    monkeypatch.setattr(
        "pfp_runtime.connectors.adapter_provider._DEFAULT_REGISTRY_FILE",
        "nonexistent_default.json",
    )
    config: dict[str, Any] = {}
    with pytest.raises(AdapterRegistryError, match="Registry file not found"):
        provide_adapter(
            "some_format",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_invalid_json_types(tmp_path: Path):
    """Test when registry JSON root is not dict, or formats is not dict."""
    config = {"connectors_registry_path": str(tmp_path / "reg1.json")}
    (tmp_path / "reg1.json").write_text("[]")
    with pytest.raises(
        AdapterRegistryError, match="Registry root must be a JSON object"
    ):
        provide_adapter(
            "some",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )

    config2 = {"connectors_registry_path": str(tmp_path / "reg2.json")}
    (tmp_path / "reg2.json").write_text('{"other": 1}')
    with pytest.raises(
        AdapterRegistryError, match="Registry must contain 'formats' object"
    ):
        provide_adapter(
            "some",
            config2,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_empty_format_name(tmp_path: Path):
    """Test providing empty or invalid format name."""
    config = create_temp_registry(
        tmp_path / "connectors_registry.json", {"formats": {}}
    )
    with pytest.raises(
        UnknownFormatError, match="Format name must be a non-empty string"
    ):
        provide_adapter(
            "",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )
    with pytest.raises(
        UnknownFormatError, match="Format name must be a non-empty string"
    ):
        provide_adapter(None, config, log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]


def test_invalid_format_entry_type(tmp_path: Path):
    """Test when the format entry itself is not a dict."""
    config = create_temp_registry(
        tmp_path / "connectors_registry.json", {"formats": {"bad": []}}
    )
    with pytest.raises(AdapterRegistryError, match="entry must be an object"):
        provide_adapter(
            "bad",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_invalid_adapter_path_type(tmp_path: Path):
    """Test adapter path empty or not a string."""
    config = create_temp_registry(
        tmp_path / "connectors_registry.json", {"formats": {"bad": {"adapter": ""}}}
    )
    with pytest.raises(AdapterRegistryError, match="Invalid adapter path"):
        provide_adapter(
            "bad",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_imported_object_not_class(tmp_path: Path):
    """Test when adapter string points to a function or variable instead of class."""
    config = create_temp_registry(
        tmp_path / "connectors_registry.json",
        {
            "formats": {
                "func": {
                    "adapter": "tests.pfp_runtime.connectors.test_adapter_provider.create_temp_registry"
                }
            }
        },
    )
    with pytest.raises(AdapterRegistryError, match="is not a class"):
        provide_adapter(
            "func",
            config,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )
