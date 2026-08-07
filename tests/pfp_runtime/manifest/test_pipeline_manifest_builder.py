"""Mirror unit tests for manifest.pipeline_manifest_builder."""

from __future__ import annotations

from typing import Any, cast

import pytest

from pfp_runtime.manifest import pipeline_manifest_builder
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    CoreManifest,
    ManifestBuildError,
    ObservabilityManifest,
    PipelineManifest,
    PublishManifest,
)


class _FakeArtifactProducer:
    """Test double used to satisfy ArtifactProducer contract in builder tests."""


def _valid_parts() -> tuple[
    ConnectorManifest,
    CoreManifest,
    PublishManifest,
    ObservabilityManifest,
]:
    """Build valid manifest parts used across positive and negative scenarios.

    Returns:
        Tuple with valid connector, core, publish, and observability sections.
    """
    connector = ConnectorManifest(connector=cast(Any, object()))
    core = CoreManifest(producer=cast(Any, _FakeArtifactProducer()))
    publish = PublishManifest(publisher=cast(Any, object()))
    observability = ObservabilityManifest(log_pipeline=cast(Any, object()))
    return connector, core, publish, observability


def test_build_pipeline_manifest_from_parts_returns_pipeline_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build PipelineManifest when all required manifest sections are valid."""
    connector, core, publish, observability = _valid_parts()
    monkeypatch.setattr(
        pipeline_manifest_builder, "ArtifactProducer", _FakeArtifactProducer
    )

    result = pipeline_manifest_builder.build_pipeline_manifest_from_parts(
        connector=connector,
        core=core,
        publish=publish,
        observability=observability,
    )

    assert isinstance(result, PipelineManifest)
    assert result.ingestion is connector
    assert result.core is core
    assert result.publish is publish
    assert result.observability is observability


def test_build_pipeline_manifest_from_parts_rejects_missing_connector() -> None:
    """Reject manifest parts when connector.connector is missing."""
    _, core, publish, observability = _valid_parts()

    with pytest.raises(
        ManifestBuildError,
        match=r"connector manifest\.connector is required",
    ):
        pipeline_manifest_builder.build_pipeline_manifest_from_parts(
            connector=ConnectorManifest(connector=None),  # type: ignore[arg-type]
            core=core,
            publish=publish,
            observability=observability,
        )


def test_build_pipeline_manifest_from_parts_rejects_missing_connector_section() -> None:
    """Reject manifest parts when connector section is missing entirely."""
    _, core, publish, observability = _valid_parts()

    with pytest.raises(ManifestBuildError, match=r"connector manifest is required"):
        pipeline_manifest_builder.build_pipeline_manifest_from_parts(
            connector=None,  # type: ignore[arg-type]
            core=core,
            publish=publish,
            observability=observability,
        )


def test_build_pipeline_manifest_from_parts_rejects_invalid_producer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject manifest parts when core.producer is not ArtifactProducer instance."""
    connector, _, publish, observability = _valid_parts()
    monkeypatch.setattr(
        pipeline_manifest_builder, "ArtifactProducer", _FakeArtifactProducer
    )

    with pytest.raises(ManifestBuildError, match=r"core\.producer is required"):
        pipeline_manifest_builder.build_pipeline_manifest_from_parts(
            connector=connector,
            core=CoreManifest(producer=cast(Any, object())),
            publish=publish,
            observability=observability,
        )


def test_build_pipeline_manifest_from_parts_rejects_missing_core() -> None:
    """Reject manifest parts when core section is missing entirely."""
    connector, _, publish, observability = _valid_parts()

    with pytest.raises(ManifestBuildError, match=r"manifest\.core is required"):
        pipeline_manifest_builder.build_pipeline_manifest_from_parts(
            connector=connector,
            core=None,  # type: ignore[arg-type]
            publish=publish,
            observability=observability,
        )


def test_build_pipeline_manifest_from_parts_rejects_missing_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject manifest parts when publish section is missing entirely."""
    connector, core, _, observability = _valid_parts()
    monkeypatch.setattr(
        pipeline_manifest_builder, "ArtifactProducer", _FakeArtifactProducer
    )

    with pytest.raises(ManifestBuildError, match=r"manifest\.publish is required"):
        pipeline_manifest_builder.build_pipeline_manifest_from_parts(
            connector=connector,
            core=core,
            publish=None,  # type: ignore[arg-type]
            observability=observability,
        )


def test_build_pipeline_manifest_from_parts_rejects_missing_publisher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject manifest parts when publish.publisher is missing."""
    connector, core, _, observability = _valid_parts()
    monkeypatch.setattr(
        pipeline_manifest_builder, "ArtifactProducer", _FakeArtifactProducer
    )

    with pytest.raises(
        ManifestBuildError,
        match=r"manifest\.publish\.publisher is required",
    ):
        pipeline_manifest_builder.build_pipeline_manifest_from_parts(
            connector=connector,
            core=core,
            publish=PublishManifest(publisher=None),  # type: ignore[arg-type]
            observability=observability,
        )


def test_build_pipeline_manifest_from_parts_rejects_missing_observability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject manifest parts when observability section is missing entirely."""
    connector, core, publish, _ = _valid_parts()
    monkeypatch.setattr(
        pipeline_manifest_builder, "ArtifactProducer", _FakeArtifactProducer
    )

    with pytest.raises(
        ManifestBuildError,
        match=r"manifest\.observability is required",
    ):
        pipeline_manifest_builder.build_pipeline_manifest_from_parts(
            connector=connector,
            core=core,
            publish=publish,
            observability=None,  # type: ignore[arg-type]
        )
