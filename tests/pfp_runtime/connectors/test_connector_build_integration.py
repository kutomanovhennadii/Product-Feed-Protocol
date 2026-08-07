"""Integration tests: full Init Phase + Runtime Phase connector chain."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, List

import pytest

from pfp_runtime.connectors.connector_builder import (
    ConnectorBuildError,
    build_connector,
)
from pfp_runtime.connectors.contracts.source_connector import SourceConnector


class _LogPipelineStub:
    """Forwarding stub: routes log_process to stdlib so caplog can capture it."""

    def log_process(
        self, level: int, module_name: str, message: str, *_args: Any, **kwargs: Any
    ) -> None:
        import logging as _stdlib

        extra = kwargs.get("extra")
        _stdlib.getLogger(module_name).log(level, message, extra=extra)


_REAL_MAPPING_PATH = str(
    Path(__file__).resolve().parents[3] / "config" / "mapping.yaml"
)

_CSV_ROW = "sku,name,description,url\nX1,Widget,A widget,http://example.com/widget\n"
_CSV_ROW_WITH_PRICE = (
    "sku,name,description,url,price,currency\n"
    "X1,Widget,A widget,http://example.com/widget,9.99,USD\n"
)


def test_build_connector_returns_source_connector() -> None:
    """Init Phase: build_connector with real mapping.yaml returns a SourceConnector."""
    connector = build_connector(
        format_name="csv",
        config={"path": "__bootstrap__.csv", "connector_mapping": _REAL_MAPPING_PATH},
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    assert isinstance(connector, SourceConnector)


def test_extract_yields_dict_record() -> None:
    """Runtime Phase: extract on a CSV string with required fields yields a dict record."""
    connector = build_connector(
        format_name="csv",
        config={"path": "__bootstrap__.csv", "connector_mapping": _REAL_MAPPING_PATH},
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    results: List[Mapping[str, Any]] = list(connector.extract(_CSV_ROW))

    assert len(results) == 1
    assert isinstance(results[0], Mapping)


def test_extract_maps_item_id_and_title() -> None:
    """Runtime Phase: sku → item_id and name → title are correctly mapped."""
    connector = build_connector(
        format_name="csv",
        config={"path": "__bootstrap__.csv", "connector_mapping": _REAL_MAPPING_PATH},
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    result = list(connector.extract(_CSV_ROW))[0]

    assert result["product"]["item_id"] == "X1"
    assert result["product"]["title"] == "Widget"


def test_extract_maps_offer_price() -> None:
    """Runtime Phase: price and currency fields are placed in nested offer.price dict."""
    connector = build_connector(
        format_name="csv",
        config={"path": "__bootstrap__.csv", "connector_mapping": _REAL_MAPPING_PATH},
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    result = list(connector.extract(_CSV_ROW_WITH_PRICE))[0]

    assert result["offer"]["price"]["amount"] == "9.99"
    assert result["offer"]["price"]["currency"] == "USD"


def test_build_connector_missing_connector_mapping_raises() -> None:
    """Init Phase: build_connector without connector_mapping raises ConnectorBuildError."""
    with pytest.raises(ConnectorBuildError, match="connector_mapping is required"):
        build_connector(
            format_name="csv",
            config={"path": "__bootstrap__.csv"},
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_build_connector_nonexistent_mapping_file_raises() -> None:
    """Init Phase: nonexistent mapping file path raises ConnectorBuildError."""
    with pytest.raises(ConnectorBuildError):
        build_connector(
            format_name="csv",
            config={
                "path": "__bootstrap__.csv",
                "connector_mapping": "/nonexistent/mapping.yaml",
            },
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )
