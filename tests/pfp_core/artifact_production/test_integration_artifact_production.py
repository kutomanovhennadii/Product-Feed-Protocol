"""Integration tests for the pfp_core.artifact_production block."""

from __future__ import annotations

from pathlib import Path

from pfp_core.artifact_production import prepare_artifact_producer_from_files
from pfp_utils.logging import build_log_pipeline


def _fixture_root() -> Path:
    """Return the project root for real schema and policy fixtures.

    Returns:
        Repository root path for the Python workspace.
    """

    return Path(__file__).resolve().parents[3]


def test_prepare_artifact_producer_from_files_builds_ready_producer() -> None:
    """File-based artifact producer preparation returns a runnable producer."""

    root = _fixture_root()
    producer = prepare_artifact_producer_from_files(
        schema_file=str(
            root / "schemas" / "stripe.product_feed" / "stripe.product_feed-1.0.0.yaml"
        ),
        policy_file=str(root / "config" / "policies.yaml"),
        log_pipeline=build_log_pipeline("INFO", "TEXT", {}),
    )

    result = producer.produce_artifacts(
        [
            {
                "item_id": "SKU-1",
                "title": "Runner",
                "description": "Lightweight shoe",
                "url": "https://example.test/products/sku-1",
                "inventory": {"availability": "IN_STOCK"},
            }
        ]
    )

    assert len(result.artifacts) == 1
    assert list(result.artifacts[0].payload) == [
        b"id,title,description,link,availability\n",
        b"SKU-1,Runner,Lightweight shoe,https://example.test/products/sku-1,in_stock\n",
    ]
    assert result.validation_report.target == "stripe.product_feed"
    assert result.validation_report.diagnostics == []


def test_prepare_artifact_producer_from_files_surfaces_empty_input_report() -> None:
    """Prepared producers still return a stable report for empty inputs."""

    root = _fixture_root()
    producer = prepare_artifact_producer_from_files(
        schema_file=str(
            root / "schemas" / "stripe.product_feed" / "stripe.product_feed-1.0.0.yaml"
        ),
        policy_file=str(root / "config" / "policies.yaml"),
        log_pipeline=build_log_pipeline("INFO", "TEXT", {}),
    )

    result = producer.produce_artifacts([])

    assert len(result.artifacts) == 1
    assert list(result.artifacts[0].payload) == [
        b"id,title,description,link,availability\n"
    ]
    assert result.validation_report.target == "stripe.product_feed"
    assert result.validation_report.diagnostics == []
