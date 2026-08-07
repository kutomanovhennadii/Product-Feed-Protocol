"""Mirror unit tests for manifest.connector_manifest_builder."""

from __future__ import annotations

from typing import Any, cast

import pytest

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.connectors.adapter_provider import AdapterRegistryError
from pfp_runtime.connectors.connector_builder import (
    ConnectorBuildError,
)
from pfp_runtime.connectors.contracts.source_connector import SourceConnector
from pfp_runtime.manifest import connector_manifest_builder
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    ManifestBuildError,
)
from pfp_utils.logging import LogPipeline


def _make_infra() -> InfraConfig:
    """Build minimal canonical infra model for connector manifest tests."""
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
                "archive_config": "./archive/noop.yaml",
                "client_type": "noop",
                "client_config": "./clients/noop.yaml",
            },
            "producer": {
                "schema_file": "./schemas/product.yaml",
                "policy_file": "./config/policies.yaml",
            },
        }
    )


def test_build_connector_manifest_builds_connector_from_input_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build ConnectorManifest from infra input using connector build resolver."""
    infra = _make_infra()
    connector = cast(SourceConnector, object())
    log_pipeline = cast(LogPipeline, object())
    captured: dict[str, Any] = {}

    def _fake_builder(
        *, format_name: str, config: dict[str, Any], log_pipeline: LogPipeline
    ) -> SourceConnector:
        captured["format_name"] = format_name
        captured["config"] = dict(config)
        captured["log_pipeline"] = log_pipeline
        return connector

    monkeypatch.setattr(
        connector_manifest_builder,
        "build_connector",
        _fake_builder,
    )

    result = connector_manifest_builder.build_connector_manifest(
        infra,
        log_pipeline=log_pipeline,
    )

    assert isinstance(result, ConnectorManifest)
    assert result.connector is connector
    assert captured["format_name"] == "csv"
    assert captured["config"] == {
        "connector_mapping": "./mapping.yaml",
        "format": "csv",
    }
    assert captured["log_pipeline"] is log_pipeline


def test_build_connector_manifest_wraps_connector_build_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translate ConnectorBuildError into ManifestBuildError."""
    infra = _make_infra()
    log_pipeline = cast(LogPipeline, object())

    def _failing_builder(
        *, format_name: str, config: dict[str, Any], log_pipeline: LogPipeline
    ) -> SourceConnector:
        del format_name, config, log_pipeline
        raise ConnectorBuildError("connector build failed")

    monkeypatch.setattr(
        connector_manifest_builder,
        "build_connector",
        _failing_builder,
    )

    with pytest.raises(ManifestBuildError, match="connector build failed") as exc_info:
        connector_manifest_builder.build_connector_manifest(
            infra,
            log_pipeline=log_pipeline,
        )

    assert isinstance(exc_info.value.__cause__, ConnectorBuildError)


def test_build_connector_manifest_wraps_adapter_registry_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translate AdapterRegistryError into ManifestBuildError."""
    infra = _make_infra()
    log_pipeline = cast(LogPipeline, object())

    def _failing_builder(
        *, format_name: str, config: dict[str, Any], log_pipeline: LogPipeline
    ) -> SourceConnector:
        del format_name, config, log_pipeline
        raise AdapterRegistryError("unknown format")

    monkeypatch.setattr(
        connector_manifest_builder,
        "build_connector",
        _failing_builder,
    )

    with pytest.raises(ManifestBuildError, match="unknown format") as exc_info:
        connector_manifest_builder.build_connector_manifest(
            infra,
            log_pipeline=log_pipeline,
        )

    assert isinstance(exc_info.value.__cause__, AdapterRegistryError)
