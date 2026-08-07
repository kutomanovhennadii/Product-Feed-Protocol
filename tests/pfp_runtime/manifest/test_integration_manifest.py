"""Integration tests for runtime manifest assembly by block."""

from __future__ import annotations

import json
import logging
from collections.abc import Generator
from pathlib import Path

import pytest

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.manifest.core_manifest_builder import build_core_manifest
from pfp_runtime.manifest.pipeline_manifest import PipelineManifest
from pfp_runtime.manifest.pipeline_manifest_provider import build_pipeline_manifest
from pfp_utils.logging import build_log_pipeline


@pytest.fixture(autouse=True)
def restore_root_logger() -> Generator[None, None, None]:
    """Restore root logger handlers and level after each integration test.

    Returns:
        Generator that preserves and restores the root logger configuration.
    """

    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level

    root.handlers[:] = []

    try:
        yield
    finally:
        root.handlers[:] = []
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)


def _python_root() -> Path:
    """Return the project repository root for runtime integration fixtures.

    Returns:
        Repository root path for the Python workspace.
    """

    return Path(__file__).resolve().parents[3]


def _make_shopify_realtime_infra(*, tax_mapping_file: str | None) -> InfraConfig:
    """Build a canonical infra config for the realtime Shopify schema.

    Args:
        tax_mapping_file: Optional path to the tax mapping file to attach.

    Returns:
        Validated runtime infra configuration for manifest assembly.
    """

    root = _python_root()
    producer_config: dict[str, object] = {
        "schema_file": str(
            root
            / "schemas"
            / "stripe.shopify_realtime"
            / "stripe.shopify_realtime-1.0.0.yaml"
        ),
        "policy_file": str(
            root / "config" / "shopify_realtime" / "policies_shopify_realtime.yaml"
        ),
    }
    if tax_mapping_file is not None:
        producer_config["tax_mapping_file"] = tax_mapping_file

    return InfraConfig.model_validate(
        {
            "input": {
                "format": "csv",
                "config": {"connector_mapping": "./unused-mapping.yaml"},
            },
            "output": {
                "archive_type": "noop",
                "archive_config": "./archive/noop.yaml",
                "client_type": "noop",
                "client_config": "./clients/noop.yaml",
            },
            "producer": producer_config,
        }
    )


def test_build_pipeline_manifest_full_chain_from_infra_path() -> None:
    """Build PipelineManifest from fixture infra through the full manifest chain."""

    fixtures_root = (
        Path(__file__).resolve().parent / "fixtures" / "pipeline_manifest_provider"
    )
    infra_path = fixtures_root / "infra.yaml"

    manifest = build_pipeline_manifest(str(infra_path))

    assert isinstance(manifest, PipelineManifest)
    assert manifest.ingestion is not None
    assert manifest.ingestion.connector is not None
    assert manifest.core is not None
    assert manifest.core.producer is not None
    assert manifest.publish is not None
    assert manifest.publish.publisher is not None
    assert manifest.observability.telemetry_provider == "none"
    assert manifest.observability.labels == {}


def test_build_pipeline_manifest_full_chain_from_operational_infra_with_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build PipelineManifest from the operational config with its baseline tree.

    Args:
        monkeypatch: Pytest helper used to switch the current working directory.
    """

    project_root = _python_root()
    infra_path = project_root / "config" / "infra.yaml"
    sent_dir = project_root / "config" / "sent"
    sent_dir.mkdir(exist_ok=True)

    monkeypatch.chdir(project_root / "config")

    try:
        manifest = build_pipeline_manifest(str(infra_path))

        assert isinstance(manifest, PipelineManifest)
        assert manifest.ingestion is not None
        assert manifest.ingestion.connector is not None
        assert manifest.core is not None
        assert manifest.core.producer is not None
        assert manifest.publish is not None
        assert manifest.publish.publisher is not None
        assert manifest.observability.log_pipeline.level == "INFO"
        assert manifest.observability.log_pipeline.format_type == "TEXT"
        assert manifest.observability.telemetry_provider == "none"
        assert manifest.observability.labels == {
            "environment": "local",
            "pipeline": "product-feed",
        }
    finally:
        if sent_dir.exists() and not any(sent_dir.iterdir()):
            sent_dir.rmdir()


def test_build_core_manifest_loads_tax_mapping_for_shopify_schema(
    tmp_path: Path,
) -> None:
    """Core manifest builder loads infra-supplied tax mapping into the producer.

    Args:
        tmp_path: Temporary directory that stores the generated tax mapping file.
    """

    tax_mapping_path = tmp_path / "tax_mapping.json"
    tax_mapping_payload = {
        "mappings": {"Apparel & Accessories > Clothing": "txcd_20031000"},
        "default_taxable": "txcd_99999999",
        "default_exempt": "txcd_00000000",
    }
    tax_mapping_path.write_text(json.dumps(tax_mapping_payload), encoding="utf-8")

    manifest = build_core_manifest(
        _make_shopify_realtime_infra(tax_mapping_file=str(tax_mapping_path)),
        log_pipeline=build_log_pipeline("INFO", "TEXT", {}),
    )

    result = manifest.producer.produce_artifacts(
        [
            {
                "id": "SKU-1",
                "title": "Runner",
                "description": "Lightweight shoe",
                "slug": "runner",
                "price": "19.99",
                "currency": "USD",
                "tax_category": "Apparel & Accessories > Clothing > Activewear",
                "taxable": True,
            }
        ]
    )

    assert result.artifacts
    assert result.validation_report is not None
