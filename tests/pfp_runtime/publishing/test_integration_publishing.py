"""Integration tests for the pfp_runtime.publishing block."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.config.infra_provider import InfraProvider
from pfp_runtime.manifest.pipeline_manifest import ManifestBuildError
from pfp_runtime.manifest.publish_manifest_builder import build_publish_manifest
from pfp_runtime.pipeline.publish_guard import publish_step
from pfp_runtime.publishing.contracts.publish_metadata import PublishMetadata
from pfp_utils.logging import build_log_pipeline
from tests.pfp_runtime._integration_helpers import python_root


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


def _artifact(*, payload: tuple[bytes, ...] = (b"payload\n",)) -> ProducedArtifact:
    """Build a minimal produced artifact reused by publishing integration tests.

    Args:
        payload: Materialized payload chunks to stream through the publisher.

    Returns:
        ProducedArtifact instance with deterministic metadata.
    """

    return ProducedArtifact(
        payload=iter(payload),
        metadata=ArtifactMetadata(
            target="stripe.product_feed",
            schema_version="1.0.0",
            generated_at=datetime.now(timezone.utc),
            content_type="text/csv",
            encoding="utf-8",
            artifact_profile="catalog_delta",
            filename_hint="stripe.csv",
        ),
    )


def _make_local_publish_infra(tmp_path: Path) -> InfraConfig:
    """Build infra that uses the real local archiver and noop delivery client.

    Args:
        tmp_path: Temporary directory that hosts the local archive config and output dir.

    Returns:
        InfraConfig pointing at local archive and noop delivery assets.
    """

    root = python_root()
    output_dir = tmp_path / "sent"
    output_dir.mkdir()
    archive_config = tmp_path / "archive.local.yaml"
    archive_config.write_text(
        f"output_dir: {output_dir.as_posix()}\nfilename_base: integration_feed\n",
        encoding="utf-8",
    )

    return InfraConfig.model_validate(
        {
            "input": {
                "format": "csv",
                "config": {"connector_mapping": "./unused-mapping.yaml"},
            },
            "output": {
                "archive_type": "local",
                "archive_config": str(archive_config),
                "client_type": "noop",
                "client_config": str(root / "config" / "clients" / "noop.yaml"),
            },
            "producer": {
                "schema_file": str(
                    root
                    / "schemas"
                    / "stripe.product_feed"
                    / "stripe.product_feed-1.0.0.yaml"
                ),
                "policy_file": str(root / "config" / "policies.yaml"),
            },
        }
    )


def test_publish_manifest_builds_noop_publisher_and_materializes_payload() -> None:
    """Publishing block builds a publisher and returns publish metadata."""

    fixtures = _fixture_root()
    infra = InfraProvider().get_infra(str(fixtures / "infra.yaml"))
    manifest = build_publish_manifest(
        infra, log_pipeline=build_log_pipeline("INFO", "TEXT", {})
    )
    published = publish_step(_artifact(), manifest)

    assert published.payload == (b"payload\n",)
    assert isinstance(published.metadata, PublishMetadata)
    assert published.metadata.archive_skipped is True
    assert published.metadata.delivery_skipped is True


def test_publish_manifest_writes_payload_through_local_archiver(
    tmp_path: Path,
) -> None:
    """Publishing block supports the real local archiver without mocking the publisher.

    Args:
        tmp_path: Temporary directory that hosts the local archive config and output dir.
    """

    manifest = build_publish_manifest(
        _make_local_publish_infra(tmp_path),
        log_pipeline=build_log_pipeline("INFO", "TEXT", {}),
    )

    published = publish_step(_artifact(payload=(b"first\n", b"second\n")), manifest)

    assert isinstance(published.metadata, PublishMetadata)
    assert published.metadata.archive_skipped is False
    assert published.metadata.delivery_skipped is True
    assert published.metadata.location is not None
    archived_path = Path(published.metadata.location)
    assert archived_path.is_file()
    assert archived_path.read_bytes() == b"first\nsecond\n"


def test_publish_manifest_wraps_unknown_client_type() -> None:
    """Publishing block reports manifest build errors for unknown delivery clients."""

    root = python_root()
    infra = InfraConfig.model_validate(
        {
            "input": {
                "format": "csv",
                "config": {"connector_mapping": "./unused-mapping.yaml"},
            },
            "output": {
                "archive_type": "noop",
                "archive_config": str(root / "config" / "archive" / "noop.yaml"),
                "client_type": "missing_client",
                "client_config": str(root / "config" / "clients" / "noop.yaml"),
            },
            "producer": {
                "schema_file": str(
                    root
                    / "schemas"
                    / "stripe.product_feed"
                    / "stripe.product_feed-1.0.0.yaml"
                ),
                "policy_file": str(root / "config" / "policies.yaml"),
            },
        }
    )

    with pytest.raises(ManifestBuildError, match="missing_client"):
        build_publish_manifest(
            infra,
            log_pipeline=build_log_pipeline("INFO", "TEXT", {}),
        )
