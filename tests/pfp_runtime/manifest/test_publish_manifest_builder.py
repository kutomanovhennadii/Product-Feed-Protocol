"""Mirror unit tests for manifest.publish_manifest_builder."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.manifest import publish_manifest_builder
from pfp_runtime.manifest.pipeline_manifest import (
    ManifestBuildError,
    PublishManifest,
)
from pfp_runtime.publishing.contracts import Publisher
from pfp_runtime.publishing.contracts.publisher_errors import PublisherBuildError
from pfp_utils.logging import LogPipeline


def _make_infra() -> InfraConfig:
    """Build minimal canonical infra model for publish manifest tests."""
    python_root = Path(__file__).resolve().parents[3]
    return InfraConfig.model_validate(
        {
            "input": {
                "format": "csv",
                "config": {
                    "connector_mapping": "./mapping.yaml",
                },
            },
            "output": {
                "archive_type": "noop",
                "archive_config": str(python_root / "config" / "archive" / "noop.yaml"),
                "client_type": "noop",
                "client_config": str(python_root / "config" / "clients" / "noop.yaml"),
            },
            "producer": {
                "schema_file": "./schemas/product.yaml",
                "policy_file": "./config/policies.yaml",
            },
        }
    )


def test_build_publish_manifest_returns_ready_publisher() -> None:
    """Build PublishManifest with ready-to-use Publisher instance."""
    infra = _make_infra()
    log_pipeline = cast(LogPipeline, object())

    result = publish_manifest_builder.build_publish_manifest(
        infra,
        log_pipeline=log_pipeline,
    )

    assert isinstance(result, PublishManifest)
    assert isinstance(result.publisher, Publisher)
    assert not hasattr(result, "publishers")


def test_build_publish_manifest_wraps_publisher_build_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translate PublisherBuildError into ManifestBuildError."""
    infra = _make_infra()
    log_pipeline = cast(LogPipeline, object())

    def _failing_builder(
        output_config: dict[str, object], *, log_pipeline: LogPipeline
    ) -> Publisher:
        del output_config, log_pipeline
        raise PublisherBuildError("publisher build failed")

    monkeypatch.setattr(
        publish_manifest_builder,
        "build_publisher",
        _failing_builder,
    )

    with pytest.raises(ManifestBuildError, match="publisher build failed") as exc_info:
        publish_manifest_builder.build_publish_manifest(
            infra,
            log_pipeline=log_pipeline,
        )

    assert isinstance(exc_info.value.__cause__, PublisherBuildError)


def test_build_publish_manifest_passes_expected_output_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass exact output section mapping from infra to build_publisher."""
    infra = _make_infra()
    log_pipeline = cast(LogPipeline, object())
    captured: dict[str, Any] = {}
    publisher = cast(Publisher, object())

    def _capturing_builder(
        output_config: dict[str, object], *, log_pipeline: LogPipeline
    ) -> Publisher:
        captured["output_config"] = dict(output_config)
        captured["log_pipeline"] = log_pipeline
        return publisher

    monkeypatch.setattr(
        publish_manifest_builder,
        "build_publisher",
        _capturing_builder,
    )

    result = publish_manifest_builder.build_publish_manifest(
        infra,
        log_pipeline=log_pipeline,
    )

    assert result.publisher is publisher
    assert captured["output_config"] == {
        "archive_type": infra.output.archive_type,
        "archive_config": infra.output.archive_config,
        "client_type": infra.output.client_type,
        "client_config": infra.output.client_config,
    }
    assert captured["log_pipeline"] is log_pipeline
