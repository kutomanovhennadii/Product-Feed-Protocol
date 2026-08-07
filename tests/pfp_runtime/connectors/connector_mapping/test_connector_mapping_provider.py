"""Tests for connector_mapping_provider.provide_connector_mapper."""

from pathlib import Path
from typing import Any

import pytest

from pfp_runtime.connectors.connector_mapping.connector_mapper import ConnectorMapper
from pfp_runtime.connectors.connector_mapping.connector_mapping_config import (
    ConnectorMappingLoadError,
    ConnectorMappingValidationError,
)
from pfp_runtime.connectors.connector_mapping.connector_mapping_provider import (
    provide_connector_mapper,
)

_REAL_MAPPING_PATH = Path(__file__).resolve().parents[4] / "config" / "mapping.yaml"

_VALID_YAML = """\
mappings:
  - source: "sku"
    target: "product.item_id"
    required: true
  - source: "name"
    target: "product.title"
continue_on_error: true
"""

_NO_MAPPINGS_YAML = """\
continue_on_error: true
"""

_BROKEN_YAML = "key: [unclosed"


class _LogPipelineStub:
    def log_process(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def test_provide_connector_mapper_returns_connector_mapper(tmp_path: Path) -> None:
    """provide_connector_mapper returns a ConnectorMapper for a valid YAML file."""
    f = tmp_path / "mapping.yaml"
    f.write_text(_VALID_YAML, encoding="utf-8")

    result = provide_connector_mapper(
        f,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    assert isinstance(result, ConnectorMapper)


def test_provide_connector_mapper_lookup_structures_populated(tmp_path: Path) -> None:
    """The returned mapper has _source_to_target populated from the YAML file."""
    f = tmp_path / "mapping.yaml"
    f.write_text(_VALID_YAML, encoding="utf-8")

    mapper = provide_connector_mapper(
        f,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    assert len(mapper._source_to_target) > 0


def test_provide_connector_mapper_file_not_found_propagates() -> None:
    """ConnectorMappingLoadError is propagated when the file does not exist."""
    with pytest.raises(ConnectorMappingLoadError):
        provide_connector_mapper(
            "/nonexistent/path/mapping.yaml",
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_provide_connector_mapper_broken_yaml_propagates(tmp_path: Path) -> None:
    """ConnectorMappingLoadError is propagated for invalid YAML syntax."""
    f = tmp_path / "mapping.yaml"
    f.write_text(_BROKEN_YAML, encoding="utf-8")

    with pytest.raises(ConnectorMappingLoadError):
        provide_connector_mapper(
            f,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_provide_connector_mapper_invalid_structure_propagates(tmp_path: Path) -> None:
    """ConnectorMappingValidationError is propagated when mappings key is absent."""
    f = tmp_path / "mapping.yaml"
    f.write_text(_NO_MAPPINGS_YAML, encoding="utf-8")

    with pytest.raises(ConnectorMappingValidationError):
        provide_connector_mapper(
            f,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_provide_connector_mapper_integration_real_file() -> None:
    """Integration: provide_connector_mapper on the real config/mapping.yaml returns a working mapper."""
    mapper = provide_connector_mapper(
        _REAL_MAPPING_PATH,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    assert isinstance(mapper, ConnectorMapper)
    assert "sku" in mapper._source_to_target
    assert "name" in mapper._source_to_target

    result = list(
        mapper.apply_stream(
            [
                {
                    "sku": "X1",
                    "name": "Test Product",
                    "description": "desc",
                    "url": "http://x",
                }
            ]
        )
    )
    assert len(result) == 1
    assert result[0]["product.item_id"] == "X1"
    assert result[0]["product.title"] == "Test Product"
