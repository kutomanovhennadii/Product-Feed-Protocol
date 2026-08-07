"""Tests for connector builder dispatch facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pfp_runtime.connectors.adapter_provider import AdapterRegistryError
from pfp_runtime.connectors.connector_builder import (
    ConnectorBuildError,
    build_connector,
)
from pfp_runtime.connectors.contracts.source_connector import SourceConnector

_REAL_MAPPING_PATH = str(
    Path(__file__).resolve().parents[3] / "config" / "mapping.yaml"
)


class _LogPipelineStub:
    def log_process(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def test_build_connector_csv_returns_source_connector() -> None:
    """CSV format builds a valid SourceConnector."""
    connector = build_connector(
        format_name="csv",
        config={"connector_mapping": _REAL_MAPPING_PATH},
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    assert isinstance(connector, SourceConnector)


def test_build_connector_jsonl_returns_source_connector() -> None:
    """jsonl is a first-class format and builds a valid SourceConnector."""
    connector = build_connector(
        format_name="jsonl",
        config={"connector_mapping": _REAL_MAPPING_PATH},
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    assert isinstance(connector, SourceConnector)


def test_build_connector_unknown_format_fails_contract() -> None:
    """Unknown format names fail with registry contract error."""
    with pytest.raises(AdapterRegistryError, match="[Uu]nknown format"):
        build_connector(
            format_name="xml",
            config={"connector_mapping": _REAL_MAPPING_PATH},
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_build_connector_missing_connector_mapping_raises() -> None:
    """build_connector raises ConnectorBuildError when connector_mapping is absent."""
    with pytest.raises(ConnectorBuildError, match="connector_mapping is required"):
        build_connector(
            format_name="csv",
            config={},
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )
