"""Integration tests for PipelineRunner observability metrics."""

# ruff: noqa: E402

from datetime import datetime, timezone
from pathlib import Path
from types import MethodType
from typing import Any

import pytest

prometheus_client = pytest.importorskip(
    "prometheus_client", reason="prometheus extra not installed"
)

from pfp_core.artifact_production import prepare_artifact_producer_from_files
from pfp_core.contracts import Artifact, BuildResult
from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    CoreManifest,
    ObservabilityManifest,
    PipelineManifest,
    PublishManifest,
)
from pfp_runtime.orchestration.pipeline_runner import PipelineRunner
from pfp_runtime.publishing.publisher_builder import build_publisher
from pfp_utils.diagnostics.validation_report import ValidationReport
from pfp_utils.telemetry import PrometheusTelemetryHandler


class _LogPipelineStub:
    """Forwarding stub: routes log_process to stdlib so caplog can capture it."""

    def log_process(
        self, level: int, module_name: str, message: str, *_args: Any, **kwargs: Any
    ) -> None:
        import logging as _stdlib

        extra = kwargs.get("extra")
        _stdlib.getLogger(module_name).log(level, message, extra=extra)


_PYTHON_ROOT_PO = Path(__file__).resolve().parents[3]
_NOOP_OUTPUT_CONFIG_PO = {
    "archive_type": "noop",
    "archive_config": str(_PYTHON_ROOT_PO / "config" / "archive" / "noop.yaml"),
    "client_type": "noop",
    "client_config": str(_PYTHON_ROOT_PO / "config" / "clients" / "noop.yaml"),
}


class _ExtractResult:
    def __init__(self, items):
        self._items = items

    def __iter__(self):
        return iter(self._items)


class _Connector:
    def __init__(self, items):
        self._items = items

    def extract(self, raw_input: Any) -> _ExtractResult:
        del raw_input
        return _ExtractResult(self._items)


def _artifact() -> Artifact:
    return Artifact(
        payload=iter([b"x"]),
        metadata=ArtifactMetadata(
            target="stripe.product",
            artifact_profile="catalog_snapshot",
            schema_version="1.0.0",
            generated_at=datetime(2026, 2, 19, tzinfo=timezone.utc),
            content_type="text/csv",
            encoding="utf-8",
            filename_hint="stripe.product__FULL__v1.0.0.csv",
        ),
    )


def test_runner_emits_processed_counter_and_stage_histogram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep usage in the report while emitting only stage-duration telemetry."""
    registry = prometheus_client.CollectorRegistry()
    telemetry = PrometheusTelemetryHandler(registry=registry)

    producer = prepare_artifact_producer_from_files(
        schema_file=str(
            _PYTHON_ROOT_PO
            / "schemas"
            / "stripe.product_feed"
            / "stripe.product_feed-1.0.0.yaml"
        ),
        policy_file=str(_PYTHON_ROOT_PO / "config" / "policies.yaml"),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    manifest = PipelineManifest(
        ingestion=ConnectorManifest(
            connector=_Connector(items=[{"item_id": "SKU-1"}]),  # type: ignore[arg-type]
            raw_input=b"fake-data",
        ),
        core=CoreManifest(producer=producer),
        publish=PublishManifest(
            publisher=build_publisher(
                _NOOP_OUTPUT_CONFIG_PO, log_pipeline=_LogPipelineStub()  # type: ignore[arg-type]
            )
        ),
        observability=ObservabilityManifest(
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
            telemetry_enabled=True,
            telemetry_handler=telemetry,
        ),
    )

    runner = PipelineRunner(manifest)

    def fake_produce(self, um, *, generated_at=None):
        del self, generated_at
        assert list(um) == [{"item_id": "SKU-1"}]
        telemetry.observe_duration(
            "validation",
            0.05,
            {
                "target": "stripe.product_feed",
                "policy_name": "strict",
            },
        )
        return BuildResult(
            artifacts=(_artifact(),),
            validation_report=ValidationReport(target="stripe.product"),
        )

    monkeypatch.setattr(
        manifest.core.producer,
        "produce_artifacts",
        MethodType(fake_produce, manifest.core.producer),
    )

    report = runner.run(b"fake-data")

    assert report.status == "SUCCESS"
    assert report.usage.input_items_count == 1
    assert report.usage.processed == 1
    assert report.usage.artifacts_count == 1
    payload = prometheus_client.generate_latest(registry).decode("utf-8")
    assert 'target="stripe.product_feed"' in payload
    assert "pfp_stage_duration_seconds" in payload
    assert 'stage="validation"' in payload
    assert "policy_name" not in payload


def test_runner_processed_counter_for_schema_ref_with_non_sequence_iterable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Count processed items via the usage collector for schema-ref iterables."""
    registry = prometheus_client.CollectorRegistry()
    telemetry = PrometheusTelemetryHandler(registry=registry)

    def _items_iterable():
        yield {"item_id": "SKU-1"}

    producer = prepare_artifact_producer_from_files(
        schema_file=str(
            _PYTHON_ROOT_PO
            / "schemas"
            / "stripe.product_feed"
            / "stripe.product_feed-1.0.0.yaml"
        ),
        policy_file=str(_PYTHON_ROOT_PO / "config" / "policies.yaml"),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    manifest = PipelineManifest(
        ingestion=ConnectorManifest(
            connector=_Connector(items=_items_iterable()),  # type: ignore[arg-type]
            raw_input=b"fake-data",
        ),
        core=CoreManifest(producer=producer),
        publish=PublishManifest(
            publisher=build_publisher(
                _NOOP_OUTPUT_CONFIG_PO, log_pipeline=_LogPipelineStub()  # type: ignore[arg-type]
            )
        ),
        observability=ObservabilityManifest(
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
            telemetry_enabled=True,
            telemetry_handler=telemetry,
        ),
    )

    runner = PipelineRunner(manifest)

    def fake_produce(self, um, *, generated_at=None):
        del self, generated_at
        assert list(um) == [{"item_id": "SKU-1"}]
        telemetry.observe_duration(
            "validation",
            0.02,
            {
                "target": "stripe.product_feed",
            },
        )
        return BuildResult(
            artifacts=(_artifact(),),
            validation_report=ValidationReport(target="stripe.product"),
        )

    monkeypatch.setattr(
        manifest.core.producer,
        "produce_artifacts",
        MethodType(fake_produce, manifest.core.producer),
    )

    report = runner.run(b"fake-data")

    assert report.status == "SUCCESS"
    assert report.usage.input_items_count == 1
    assert report.usage.processed == 1
    payload = prometheus_client.generate_latest(registry).decode("utf-8")
    assert 'target="stripe.product_feed"' in payload
    assert "pfp_stage_duration_seconds" in payload
