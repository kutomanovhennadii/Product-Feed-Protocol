"""Mirror unit tests for manifest.pipeline_manifest contracts."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pfp_core.artifact_production.artifact_producer import ArtifactProducer
from pfp_runtime.connectors.contracts.source_connector import SourceConnector
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    CoreManifest,
    ManifestBuildError,
    ObservabilityManifest,
    PipelineManifest,
    PublishManifest,
    RunContext,
)
from pfp_runtime.publishing.contracts import Publisher
from pfp_utils.logging import LogPipeline
from pfp_utils.telemetry import NoOpTelemetryHandler


def test_manifest_models_are_frozen_dataclasses() -> None:
    """Ensure manifest dataclasses are immutable after construction."""
    connector = ConnectorManifest(connector=cast(SourceConnector, object()))
    core = CoreManifest(producer=cast(ArtifactProducer, object()))
    publish = PublishManifest(publisher=cast(Publisher, object()))
    run_context = RunContext(run_id="run-1")
    observability = ObservabilityManifest(log_pipeline=cast(LogPipeline, object()))
    manifest = PipelineManifest(
        ingestion=connector,
        core=core,
        publish=publish,
        observability=observability,
        run_context=run_context,
    )

    with pytest.raises(FrozenInstanceError):
        connector.raw_input = {"a": 1}  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        core.generated_at = None  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        publish.publisher = cast(Publisher, object())  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        run_context.run_id = "run-2"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        observability.log_pipeline = cast(LogPipeline, object())  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        manifest.core = core  # type: ignore[misc]


def test_core_manifest_requires_producer_argument() -> None:
    """Require producer argument in CoreManifest constructor."""
    with pytest.raises(TypeError):
        CoreManifest()  # type: ignore[call-arg]


def test_publish_manifest_has_publisher_and_no_publishers_field() -> None:
    """Expose only publisher field in PublishManifest model."""
    publish = PublishManifest(publisher=cast(Publisher, object()))

    assert hasattr(publish, "publisher")
    assert not hasattr(publish, "publishers")


def test_manifest_build_error_is_value_error() -> None:
    """Keep ManifestBuildError compatible with ValueError semantics."""
    assert issubclass(ManifestBuildError, ValueError)


def test_observability_manifest_requires_log_pipeline_argument() -> None:
    """Require log_pipeline argument in ObservabilityManifest constructor."""
    with pytest.raises(TypeError):
        ObservabilityManifest()  # type: ignore[call-arg]


def test_pipeline_manifest_requires_observability_argument() -> None:
    """Require observability argument in PipelineManifest constructor."""
    connector = ConnectorManifest(connector=cast(SourceConnector, object()))
    core = CoreManifest(producer=cast(ArtifactProducer, object()))
    publish = PublishManifest(publisher=cast(Publisher, object()))

    with pytest.raises(TypeError):
        PipelineManifest(  # type: ignore[call-arg]
            ingestion=connector,
            core=core,
            publish=publish,
        )


def test_observability_manifest_defaults_include_telemetry_provider() -> None:
    """Expose explicit telemetry provider and defaults on the new contract."""
    log_pipeline = cast(LogPipeline, object())
    observability = ObservabilityManifest(log_pipeline=log_pipeline)

    assert isinstance(observability.telemetry_handler, NoOpTelemetryHandler)
    assert observability.log_pipeline is log_pipeline
    assert observability.telemetry_enabled is False
    assert observability.telemetry_provider == "none"
