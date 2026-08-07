"""Mirror unit tests for manifest.pipeline_manifest_provider."""

from __future__ import annotations

from typing import Any, cast

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.connectors.contracts.source_connector import SourceConnector
from pfp_runtime.manifest import pipeline_manifest_provider
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    CoreManifest,
    ObservabilityManifest,
    PipelineManifest,
    PublishManifest,
)


def _infra_fixture() -> InfraConfig:
    """Build minimal canonical infra model for provider unit tests."""
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


def test_build_pipeline_manifest_composes_builders_in_order(
    monkeypatch,
) -> None:
    """Call provider and all builders in strict pipeline order."""
    infra = _infra_fixture()
    calls: list[str] = []

    connector_manifest = ConnectorManifest(connector=cast(SourceConnector, object()))
    core_manifest = CoreManifest(producer=object())  # type: ignore[arg-type]
    publish_manifest = PublishManifest(publisher=object())  # type: ignore[arg-type]
    observability_manifest = ObservabilityManifest(log_pipeline=cast(Any, object()))
    expected = PipelineManifest(
        ingestion=connector_manifest,
        core=core_manifest,
        publish=publish_manifest,
        observability=observability_manifest,
    )

    class _FakeInfraProvider:
        """Test double for InfraProvider dependency."""

        def get_infra(self, path: str) -> InfraConfig:
            """Return pre-built infra and assert requested path."""
            assert path == "./infra.yaml"
            calls.append("infra")
            return infra

    def _build_connector(value: InfraConfig, *, log_pipeline: Any) -> ConnectorManifest:
        calls.append("connector")
        assert value is infra
        assert log_pipeline is observability_manifest.log_pipeline
        return connector_manifest

    def _build_core(value: InfraConfig, *, log_pipeline: Any) -> CoreManifest:
        calls.append("core")
        assert value is infra
        assert log_pipeline is observability_manifest.log_pipeline
        return core_manifest

    def _build_publish(value: InfraConfig, *, log_pipeline: Any) -> PublishManifest:
        calls.append("publish")
        assert value is infra
        assert log_pipeline is observability_manifest.log_pipeline
        return publish_manifest

    def _build_observability(value: InfraConfig) -> Any:
        calls.append("observability")
        assert value is infra
        return observability_manifest

    def _assemble(
        *,
        connector: ConnectorManifest,
        core: CoreManifest,
        publish: PublishManifest,
        observability: Any,
    ) -> PipelineManifest:
        calls.append("assemble")
        assert connector is connector_manifest
        assert core is core_manifest
        assert publish is publish_manifest
        assert observability is observability_manifest
        return expected

    monkeypatch.setattr(pipeline_manifest_provider, "InfraProvider", _FakeInfraProvider)
    monkeypatch.setattr(
        pipeline_manifest_provider,
        "build_connector_manifest",
        _build_connector,
    )
    monkeypatch.setattr(
        pipeline_manifest_provider,
        "build_core_manifest",
        _build_core,
    )
    monkeypatch.setattr(
        pipeline_manifest_provider,
        "build_publish_manifest",
        _build_publish,
    )
    monkeypatch.setattr(
        pipeline_manifest_provider,
        "build_observability_manifest",
        _build_observability,
    )
    monkeypatch.setattr(
        pipeline_manifest_provider,
        "build_pipeline_manifest_from_parts",
        _assemble,
    )

    result = pipeline_manifest_provider.build_pipeline_manifest("./infra.yaml")

    assert result is expected
    assert calls == [
        "infra",
        "observability",
        "connector",
        "core",
        "publish",
        "assemble",
    ]
