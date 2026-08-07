"""Integration tests for the pfp_runtime.connectors block."""

from __future__ import annotations

from pathlib import Path

import pytest

from pfp_runtime.config.infra_provider import InfraProvider
from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_runtime.manifest.connector_manifest_builder import build_connector_manifest
from pfp_utils.logging import build_log_pipeline


def _fixture_root() -> Path:
    """Return the manifest fixture root reused by runtime integration tests.

    Returns:
        Fixture directory containing runtime manifest assets.
    """

    return (
        Path(__file__).resolve().parents[1]
        / "manifest"
        / "fixtures"
        / "pipeline_manifest_provider"
    )


def test_connector_manifest_builds_extractable_source_connector() -> None:
    """Connector manifest builds a runtime connector that extracts unified items."""

    fixtures = _fixture_root()
    infra = InfraProvider().get_infra(str(fixtures / "infra.yaml"))
    manifest = build_connector_manifest(
        infra,
        log_pipeline=build_log_pipeline("INFO", "TEXT", {}),
    )

    extracted = list(
        manifest.connector.extract((fixtures / "input" / "items.csv").read_bytes())
    )

    assert extracted == [{"product": {"item_id": "SKU-1"}}]


def test_connector_manifest_returns_no_items_for_header_only_csv() -> None:
    """Connector manifest returns an empty stream for a CSV payload without rows."""

    fixtures = _fixture_root()
    infra = InfraProvider().get_infra(str(fixtures / "infra.yaml"))
    manifest = build_connector_manifest(
        infra,
        log_pipeline=build_log_pipeline("INFO", "TEXT", {}),
    )

    extracted = list(
        manifest.connector.extract(b"sku,name,description,url,availability\n")
    )

    assert extracted == []


def test_connector_manifest_surfaces_adapter_decode_errors() -> None:
    """Connector manifest propagates adapter format errors for invalid UTF-8 input."""

    fixtures = _fixture_root()
    infra = InfraProvider().get_infra(str(fixtures / "infra.yaml"))
    manifest = build_connector_manifest(
        infra,
        log_pipeline=build_log_pipeline("INFO", "TEXT", {}),
    )

    with pytest.raises(AdapterFormatError, match="Failed to decode raw_input as utf-8"):
        list(manifest.connector.extract(b"\x81invalid"))
