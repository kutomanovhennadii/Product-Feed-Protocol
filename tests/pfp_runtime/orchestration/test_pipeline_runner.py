from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import MethodType
from typing import Any, Dict, Iterable

import pytest

from pfp_core.artifact_production import prepare_artifact_producer_from_files
from pfp_core.contracts import Artifact, ArtifactMetadata, BuildResult, ProducedArtifact
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    CoreManifest,
    ObservabilityManifest,
    PipelineManifest,
    PublishManifest,
    RunContext,
)
from pfp_runtime.orchestration.pipeline_runner import (
    PipelineRunner,
    _has_error_diagnostics,
)
from pfp_runtime.publishing.publisher_builder import build_publisher
from pfp_utils.diagnostics import FeedUsageCollector
from pfp_utils.diagnostics.diagnostic_models import Diagnostic, DiagnosticSeverity
from pfp_utils.diagnostics.validation_report import ValidationReport

_PYTHON_ROOT = Path(__file__).resolve().parents[3]
_NOOP_ARCHIVE_YAML = str(_PYTHON_ROOT / "config" / "archive" / "noop.yaml")
_NOOP_CLIENT_YAML = str(_PYTHON_ROOT / "config" / "clients" / "noop.yaml")

_NOOP_OUTPUT_CONFIG: Dict[str, Any] = {
    "archive_type": "noop",
    "archive_config": _NOOP_ARCHIVE_YAML,
    "client_type": "noop",
    "client_config": _NOOP_CLIENT_YAML,
}


class _LogPipelineStub:
    def log_process(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _ExtractResult:
    def __init__(self, items: Iterable[Any], diagnostics: tuple = ()) -> None:
        self._items = items
        self._diagnostics = tuple(diagnostics)

    def __iter__(self) -> Any:
        return iter(self._items)

    @property
    def diagnostics(self) -> tuple:
        return self._diagnostics


class _FakeConnector:
    def __init__(
        self,
        *,
        items: Iterable[Any],
        fail_extract: bool = False,
    ) -> None:
        self._items = items
        self._fail_extract = fail_extract
        self.calls: list = []

    def extract(self, raw_input: Any) -> _ExtractResult:
        del raw_input
        self.calls.append("extract")
        if self._fail_extract:
            raise ValueError("extract failed")
        return _ExtractResult(
            self._items,
            diagnostics=(
                Diagnostic(
                    severity=DiagnosticSeverity.WARN,
                    code="INGESTION.TEST_WARN",
                    message="ingestion warning",
                ),
            ),
        )


class _SpyUsageCollector(FeedUsageCollector):
    """Collector spy used to verify manifest-provided usage accounting."""

    def __init__(self) -> None:
        """Initialize the spy collector with reset/build call counters.

        Returns:
            None.
        """
        super().__init__()
        self.reset_calls = 0
        self.build_calls = 0

    def reset(self) -> None:
        """Record reset usage and delegate to the base collector.

        Returns:
            None.
        """
        self.reset_calls += 1
        super().reset()

    def build(self):
        """Record snapshot builds and delegate to the base collector.

        Returns:
            Feed usage snapshot for the current collector state.
        """
        self.build_calls += 1
        return super().build()


def _prepared_producer() -> Any:
    return prepare_artifact_producer_from_files(
        schema_file=str(
            _PYTHON_ROOT
            / "schemas"
            / "stripe.product_feed"
            / "stripe.product_feed-1.0.0.yaml"
        ),
        policy_file=str(_PYTHON_ROOT / "config" / "policies.yaml"),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )


def _ingestion_manifest(connector: Any) -> ConnectorManifest:
    return ConnectorManifest(
        connector=connector,
        raw_input=b"fake-data",
    )


def _publish_manifest() -> PublishManifest:
    return PublishManifest(
        publisher=build_publisher(
            _NOOP_OUTPUT_CONFIG,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )
    )


def _observability_manifest(*, collector: Any = None) -> ObservabilityManifest:
    kwargs: Dict[str, Any] = {"log_pipeline": _LogPipelineStub()}
    if collector is not None:
        kwargs["usage_collector"] = collector
    return ObservabilityManifest(**kwargs)  # type: ignore[arg-type]


def _make_runner_manifest(
    connector: Any,
    *,
    producer: Any = None,
    observability: Any = None,
) -> PipelineManifest:
    if producer is None:
        producer = _prepared_producer()
    return PipelineManifest(
        ingestion=_ingestion_manifest(connector),
        core=CoreManifest(
            producer=producer,
            generated_at=None,
            fail_on_error_diagnostics=False,
        ),
        publish=_publish_manifest(),
        run_context=None,
        observability=observability or _observability_manifest(),
    )


_INPUT_DATA = b"fake-data"


def _artifact(target: str = "stripe.product") -> Artifact:
    return Artifact(
        payload=iter([b"x"]),
        metadata=ArtifactMetadata(
            target=target,
            artifact_profile="catalog_snapshot",
            schema_version="1.0.0",
            generated_at=datetime(2026, 2, 19, tzinfo=timezone.utc),
            content_type="text/csv",
            encoding="utf-8",
            filename_hint=target + "__FULL__v1.0.0.csv",
        ),
    )


def test_runner_success_flow_order_and_report() -> None:
    """Execute full pipeline and verify SUCCESS report with published artifacts."""
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    manifest = _make_runner_manifest(connector)
    runner = PipelineRunner(manifest)

    report = runner.run(_INPUT_DATA)

    assert report.status == "SUCCESS"
    assert connector.calls == ["extract"]
    assert len(report.artifacts) == 1
    assert report.artifacts[0].metadata.target == "stripe.product_feed"
    assert report.validation_report.artifact_profile == "catalog_delta"
    assert report.usage.input_items_count == 1
    assert report.usage.processed == 1
    assert report.usage.artifacts_count == 1
    assert report.usage.errors == 0
    expected_diagnostics = {"ERROR": 0, "WARN": 0, "INFO": 0}
    for diagnostic in report.validation_report.diagnostics:
        expected_diagnostics[
            str(DiagnosticSeverity.normalize(diagnostic.severity))
        ] += 1
    assert report.usage.diagnostics_count_by_severity == expected_diagnostics
    ingestion_diag = next(
        (
            diag
            for diag in report.validation_report.diagnostics
            if diag.code == "INGESTION.TEST_WARN"
        ),
        None,
    )
    assert ingestion_diag is not None


def test_runner_missing_connector_fails_manifest() -> None:
    """Raise ValueError when manifest has no connector."""
    manifest = PipelineManifest(
        ingestion=ConnectorManifest(connector=None, raw_input=b"data"),  # type: ignore[arg-type]
        core=CoreManifest(producer=_prepared_producer()),
        publish=_publish_manifest(),
        observability=_observability_manifest(),
    )

    with pytest.raises(ValueError, match="connector"):
        PipelineRunner(manifest)


def test_runner_requires_manifest_instance() -> None:
    """Raise ValueError when PipelineRunner is created without a manifest."""
    with pytest.raises(ValueError, match="manifest is required"):
        PipelineRunner(None)  # type: ignore[arg-type]


def test_runner_requires_ingestion_section() -> None:
    """Raise ValueError when manifest has no ingestion section."""
    manifest = PipelineManifest(
        ingestion=None,  # type: ignore[arg-type]
        core=CoreManifest(producer=_prepared_producer()),
        publish=_publish_manifest(),
        observability=_observability_manifest(),
    )

    with pytest.raises(ValueError, match=r"manifest\.ingestion"):
        PipelineRunner(manifest)


def test_runner_missing_core_producer_is_contract_error() -> None:
    """Raise ValueError when manifest has no core producer."""
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])

    manifest = PipelineManifest(
        ingestion=_ingestion_manifest(connector),
        core=CoreManifest(producer=None),  # type: ignore[arg-type]
        publish=_publish_manifest(),
        observability=_observability_manifest(),
    )

    with pytest.raises(ValueError, match="producer"):
        PipelineRunner(manifest)


def test_runner_requires_core_section() -> None:
    """Raise ValueError when manifest has no core section."""
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    manifest = PipelineManifest(
        ingestion=_ingestion_manifest(connector),
        core=None,  # type: ignore[arg-type]
        publish=_publish_manifest(),
        observability=_observability_manifest(),
    )

    with pytest.raises(ValueError, match=r"manifest\.core"):
        PipelineRunner(manifest)


def test_runner_extract_error_classified() -> None:
    """Classify connector extract failure as INGESTION_EXTRACT."""
    connector = _FakeConnector(items=[], fail_extract=True)
    manifest = _make_runner_manifest(connector)
    runner = PipelineRunner(manifest)

    report = runner.run(_INPUT_DATA)

    assert report.status == "FAILED"
    assert report.failed_step == "INGESTION_EXTRACT"
    assert report.usage.errors == 1


def test_runner_uses_manifest_usage_collector_when_present() -> None:
    """Use the manifest-provided usage collector for runtime accounting."""
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    collector = _SpyUsageCollector()
    manifest = _make_runner_manifest(
        connector,
        observability=_observability_manifest(collector=collector),
    )
    runner = PipelineRunner(manifest)

    report = runner.run(_INPUT_DATA)

    assert report.status == "SUCCESS"
    assert collector.reset_calls == 1
    assert collector.build_calls >= 1
    assert report.usage.input_items_count == 1
    assert report.usage.processed == 1


def test_runner_core_contract_error_classified() -> None:
    """Classify core producer ValueError as CORE_BUILD with CONTRACT_ERROR."""
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])

    producer = _prepared_producer()

    def _boom(self: Any, um: Any, *, generated_at: Any = None) -> Any:
        del self, um, generated_at
        raise ValueError("core contract error")

    producer.produce_artifacts = MethodType(_boom, producer)

    manifest = _make_runner_manifest(connector, producer=producer)
    runner = PipelineRunner(manifest)
    report = runner.run(_INPUT_DATA)

    assert report.status == "FAILED"
    assert report.failed_step == "CORE_BUILD"
    assert report.reason_code == "CORE.CONTRACT_ERROR"


def test_runner_uses_prepared_producer_when_present() -> None:
    """Invoke prepared producer exactly once during pipeline execution."""
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    observed: Dict[str, int] = {"producer_called": 0}

    producer = _prepared_producer()

    def _tracked(self: Any, um: Any, *, generated_at: Any = None) -> BuildResult:
        del self, generated_at
        observed["producer_called"] += 1
        assert list(um) == [{"item_id": "SKU-1"}]
        return BuildResult(
            artifacts=(_artifact(),),
            validation_report=ValidationReport(target="stripe.product"),
        )

    producer.produce_artifacts = MethodType(_tracked, producer)

    manifest = _make_runner_manifest(connector, producer=producer)
    runner = PipelineRunner(manifest)
    report = runner.run(_INPUT_DATA)

    assert report.status == "SUCCESS"
    assert observed["producer_called"] == 1


def test_runner_missing_publish_publisher_is_contract_error() -> None:
    """Raise ValueError when manifest has no publish publisher."""
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    manifest = PipelineManifest(
        ingestion=_ingestion_manifest(connector),
        core=CoreManifest(producer=_prepared_producer()),
        publish=PublishManifest(publisher=None),  # type: ignore[arg-type]
        observability=_observability_manifest(),
    )

    with pytest.raises(ValueError, match=r"publish\.publisher"):
        PipelineRunner(manifest)


def test_runner_requires_publish_section() -> None:
    """Raise ValueError when manifest has no publish section."""
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    manifest = PipelineManifest(
        ingestion=_ingestion_manifest(connector),
        core=CoreManifest(producer=_prepared_producer()),
        publish=None,  # type: ignore[arg-type]
        observability=_observability_manifest(),
    )

    with pytest.raises(ValueError, match=r"manifest\.publish"):
        PipelineRunner(manifest)


def test_runner_requires_observability_section() -> None:
    """Raise ValueError when manifest has no observability section."""
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    manifest = PipelineManifest(
        ingestion=_ingestion_manifest(connector),
        core=CoreManifest(producer=_prepared_producer()),
        publish=_publish_manifest(),
        observability=None,  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match=r"manifest\.observability"):
        PipelineRunner(manifest)


def test_runner_fails_on_error_diagnostics_before_publish() -> None:
    """Fail with CORE.VALIDATION_FAILED when error diagnostics are configured as fatal."""
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    producer = _prepared_producer()

    def _error_report(self: Any, um: Any, *, generated_at: Any = None) -> BuildResult:
        del self, generated_at
        assert list(um) == [{"item_id": "SKU-1"}]
        validation_report = ValidationReport(target="stripe.product_feed")
        validation_report.add(
            Diagnostic(
                severity=DiagnosticSeverity.ERROR,
                code="CORE.TEST_ERROR",
                message="fatal validation error",
            )
        )
        return BuildResult(
            artifacts=(_artifact(),),
            validation_report=validation_report,
        )

    producer.produce_artifacts = MethodType(_error_report, producer)
    manifest = PipelineManifest(
        ingestion=_ingestion_manifest(connector),
        core=CoreManifest(
            producer=producer,
            fail_on_error_diagnostics=True,
        ),
        publish=_publish_manifest(),
        run_context=RunContext(generated_at=datetime(2026, 2, 19, tzinfo=timezone.utc)),
        observability=_observability_manifest(),
    )
    runner = PipelineRunner(manifest)

    report = runner.run(_INPUT_DATA)

    assert report.status == "FAILED"
    assert report.failed_step == "CORE_BUILD"
    assert report.reason_code == "CORE.VALIDATION_FAILED"
    assert report.message == "Validation report contains ERROR diagnostics"
    assert report.artifacts == ()
    assert report.usage.errors == 1


def test_has_error_diagnostics_detects_error_entries() -> None:
    """Return True when the validation report contains an ERROR diagnostic."""
    report = ValidationReport(target="stripe.product_feed")
    report.add(
        Diagnostic(
            severity=DiagnosticSeverity.ERROR,
            code="CORE.TEST_ERROR",
            message="fatal validation error",
        )
    )

    assert _has_error_diagnostics(report) is True


def test_has_error_diagnostics_returns_false_without_errors() -> None:
    """Return False when the validation report has only non-error diagnostics."""
    report = ValidationReport(target="stripe.product_feed")
    report.add(
        Diagnostic(
            severity=DiagnosticSeverity.WARN,
            code="CORE.TEST_WARN",
            message="non-fatal validation warning",
        )
    )

    assert _has_error_diagnostics(report) is False


# ---------------------------------------------------------------------------
# Publish failure regression tests
# ---------------------------------------------------------------------------


class _FakePublisher:
    """Publisher that fails on a configurable call number."""

    def __init__(
        self,
        *,
        fail_on_call: int = 0,
        fail_message: str | None = None,
    ) -> None:
        self._fail_on_call = fail_on_call
        self._call_count = 0
        self._fail_message = fail_message

    def publish(self, artifact: ProducedArtifact) -> ProducedArtifact:
        self._call_count += 1
        if self._fail_on_call and self._call_count >= self._fail_on_call:
            if self._fail_message is not None:
                raise RuntimeError(self._fail_message)
            raise RuntimeError("publish failed on call %d" % self._call_count)
        return ProducedArtifact(
            payload=tuple(artifact.payload),
            metadata=artifact.metadata,
        )


def test_runner_publish_fail_produces_failure_report() -> None:
    """Publisher failure produces FAILED ExecutionReport with empty artifacts.

    Mirrors the scalar _publish contract: single artifact in, single artifact
    out; on failure PublishError is raised without any partial-progress state
    and the failure report contains no artifacts.
    """
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    publisher = _FakePublisher(fail_on_call=1)
    manifest = PipelineManifest(
        ingestion=_ingestion_manifest(connector),
        core=CoreManifest(
            producer=_prepared_producer(),
        ),
        publish=PublishManifest(publisher=publisher),  # type: ignore[arg-type]
        observability=_observability_manifest(),
    )
    runner = PipelineRunner(manifest)
    report = runner.run(_INPUT_DATA)

    assert report.status == "FAILED"
    assert report.failed_step == "PUBLISH"
    assert report.reason_code == "PUBLISH.ERROR"
    assert report.artifacts == ()


def test_runner_publish_fail_sanitizes_secret_in_failure_message() -> None:
    """Publish failure reports must sanitize secrets via the centralized report path."""
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    publisher = _FakePublisher(fail_on_call=1, fail_message="fail with token=secret123")
    manifest = PipelineManifest(
        ingestion=_ingestion_manifest(connector),
        core=CoreManifest(
            producer=_prepared_producer(),
        ),
        publish=PublishManifest(publisher=publisher),  # type: ignore[arg-type]
        observability=_observability_manifest(),
    )
    runner = PipelineRunner(manifest)

    report = runner.run(_INPUT_DATA)

    assert report.status == "FAILED"
    assert report.failed_step == "PUBLISH"
    assert report.reason_code == "PUBLISH.ERROR"
    assert "token=***" in report.message
    assert "secret123" not in report.message
