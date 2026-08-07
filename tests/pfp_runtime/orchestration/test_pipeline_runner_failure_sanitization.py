"""Failure-path sanitization tests for PipelineRunner catch blocks."""

from __future__ import annotations

from types import MethodType
from typing import Any, Iterable, cast

from pfp_core.contracts import BuildResult, ProducedArtifact
from pfp_runtime.manifest.pipeline_manifest import (
    CoreManifest,
    PipelineManifest,
    PublishManifest,
)
from pfp_runtime.orchestration.pipeline_runner import PipelineRunner
from pfp_utils.diagnostics.validation_report import ValidationReport

from .test_pipeline_runner import (
    _INPUT_DATA,
    _FakeConnector,
    _ingestion_manifest,
    _observability_manifest,
    _prepared_producer,
    _publish_manifest,
)


class _ExplodingExtractResult:
    """Extract result whose iterator fails with a secret-bearing message.

    Returns:
        Iterable-like object used to trigger ingestion iteration failure paths.
    """

    def __init__(self, message: str) -> None:
        """Store the iteration failure message.

        Args:
            message: Secret-bearing message raised during iteration.

        Returns:
            None.
        """
        self._message = message

    def __iter__(self) -> Iterable[Any]:
        """Raise the configured failure when the result is iterated.

        Returns:
            Iterable that raises on first consumption.
        """
        raise RuntimeError(self._message)
        yield  # pragma: no cover

    @property
    def diagnostics(self) -> tuple:
        """Expose empty diagnostics for the synthetic extract result.

        Returns:
            Empty diagnostics tuple.
        """
        return ()


class _FailingExtractConnector:
    """Connector that fails immediately during extract().

    Returns:
        Test connector that triggers the ingestion extract catch path.
    """

    def __init__(self, message: str) -> None:
        """Store the extract failure message.

        Args:
            message: Secret-bearing message raised by extract().

        Returns:
            None.
        """
        self._message = message

    def extract(self, raw_input: Any) -> Any:
        """Raise the configured extraction failure.

        Args:
            raw_input: Unused raw input payload.

        Returns:
            Never returns.
        """
        del raw_input
        raise RuntimeError(self._message)


class _IterationFailConnector:
    """Connector that succeeds on extract() but fails during iteration.

    Returns:
        Test connector that triggers the ingestion iteration catch path.
    """

    def __init__(self, message: str) -> None:
        """Store the iteration failure message.

        Args:
            message: Secret-bearing message raised during iteration.

        Returns:
            None.
        """
        self._message = message

    def extract(self, raw_input: Any) -> _ExplodingExtractResult:
        """Return an iterable that fails on consumption.

        Args:
            raw_input: Unused raw input payload.

        Returns:
            Extract result whose iterator fails on first use.
        """
        del raw_input
        return _ExplodingExtractResult(self._message)


class _FailingPublisher:
    """Publisher that fails with a configured secret-bearing message.

    Returns:
        Test publisher used for publish failure paths.
    """

    def __init__(
        self,
        message: str,
        *,
        error_type: type[Exception] = RuntimeError,
    ) -> None:
        """Store the publish failure message.

        Args:
            message: Secret-bearing message raised by publish().
            error_type: Exception type raised by publish().

        Returns:
            None.
        """
        self._message = message
        self._error_type = error_type

    def publish(self, artifact: ProducedArtifact) -> ProducedArtifact:
        """Raise the configured publish failure.

        Args:
            artifact: Produced artifact passed by PipelineRunner.

        Returns:
            Never returns.
        """
        del artifact
        raise self._error_type(self._message)


def _make_manifest(
    connector: Any,
    *,
    producer: Any | None = None,
    publisher: Any | None = None,
) -> PipelineManifest:
    """Build a runner manifest for failure-path sanitization tests.

    Args:
        connector: Connector instance used by the runner.
        producer: Optional producer override.
        publisher: Optional publisher override.

    Returns:
        PipelineManifest wired with the supplied test doubles.
    """
    resolved_producer = producer or _prepared_producer()
    resolved_publisher = publisher or _publish_manifest().publisher
    return PipelineManifest(
        ingestion=_ingestion_manifest(connector),
        core=CoreManifest(
            producer=resolved_producer,
            generated_at=None,
            fail_on_error_diagnostics=False,
        ),
        publish=PublishManifest(publisher=resolved_publisher),  # type: ignore[arg-type]
        observability=_observability_manifest(),
        run_context=None,
    )


def _assert_report_message_is_sanitized(
    report: Any,
    *,
    failed_step: str,
    reason_code: str,
    raw_secret: str = "secret123",
) -> None:
    """Assert that a failure report keeps the path semantics but masks secrets.

    Args:
        report: ExecutionReport produced by PipelineRunner.
        failed_step: Expected failed_step value.
        reason_code: Expected reason_code value.
        raw_secret: Raw secret fragment that must be absent from report.message.

    Returns:
        None.
    """
    assert report.status == "FAILED"
    assert report.failed_step == failed_step
    assert report.reason_code == reason_code
    assert "token=***" in report.message
    assert raw_secret not in report.message


def test_runner_sanitizes_ingestion_extract_failure_message() -> None:
    """Ingestion extract failure must be sanitized by the centralized report path.

    Returns:
        None.
    """
    runner = PipelineRunner(
        _make_manifest(_FailingExtractConnector("extract token=secret123"))
    )

    report = runner.run(_INPUT_DATA)

    _assert_report_message_is_sanitized(
        report,
        failed_step="INGESTION_EXTRACT",
        reason_code="INGESTION.EXTRACT_ERROR",
    )


def test_runner_sanitizes_core_contract_error_message() -> None:
    """Core contract failures must sanitize the final report message.

    Returns:
        None.
    """
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    producer = _prepared_producer()

    def _boom(self: Any, um: Any, *, generated_at: Any = None) -> Any:
        del self, um, generated_at
        raise ValueError("core token=secret123")

    cast(Any, producer).produce_artifacts = MethodType(_boom, producer)
    runner = PipelineRunner(_make_manifest(connector, producer=producer))

    report = runner.run(_INPUT_DATA)

    _assert_report_message_is_sanitized(
        report,
        failed_step="CORE_BUILD",
        reason_code="CORE.CONTRACT_ERROR",
    )


def test_runner_sanitizes_ingestion_iteration_failure_message() -> None:
    """Ingestion iteration failure must sanitize the final report message.

    Returns:
        None.
    """
    producer = _prepared_producer()

    def _consume_items(
        self: Any,
        um: Any,
        *,
        generated_at: Any = None,
    ) -> BuildResult:
        del self, generated_at
        list(um)
        return BuildResult(
            artifacts=(),
            validation_report=ValidationReport(target="stripe.product_feed"),
        )

    cast(Any, producer).produce_artifacts = MethodType(_consume_items, producer)
    runner = PipelineRunner(
        _make_manifest(
            _IterationFailConnector("iteration token=secret123"),
            producer=producer,
        )
    )

    report = runner.run(_INPUT_DATA)

    _assert_report_message_is_sanitized(
        report,
        failed_step="INGESTION_EXTRACT",
        reason_code="INGESTION.EXTRACT_ERROR",
    )


def test_runner_sanitizes_internal_core_error_message() -> None:
    """Generic core execution failures must sanitize the final report message.

    Returns:
        None.
    """
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    producer = _prepared_producer()

    def _boom(self: Any, um: Any, *, generated_at: Any = None) -> Any:
        del self, um, generated_at
        raise RuntimeError("internal token=secret123")

    cast(Any, producer).produce_artifacts = MethodType(_boom, producer)
    runner = PipelineRunner(_make_manifest(connector, producer=producer))

    report = runner.run(_INPUT_DATA)

    _assert_report_message_is_sanitized(
        report,
        failed_step="INTERNAL",
        reason_code="INTERNAL.ERROR",
    )


def test_runner_sanitizes_publish_error_message_from_publish_error_path() -> None:
    """PublishError catch path must sanitize the final report message.

    Returns:
        None.
    """
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    publisher = _FailingPublisher("publish token=secret123")
    runner = PipelineRunner(_make_manifest(connector, publisher=publisher))

    report = runner.run(_INPUT_DATA)

    _assert_report_message_is_sanitized(
        report,
        failed_step="PUBLISH",
        reason_code="PUBLISH.ERROR",
    )


def test_runner_maps_publish_timeout_to_timeout_reason_code() -> None:
    """Timeout publish failures must map to the timeout publish reason code.

    Returns:
        None.
    """
    connector = _FakeConnector(items=[{"item_id": "SKU-1"}])
    publisher = _FailingPublisher(
        "connection timed out to url?token=abc",
        error_type=TimeoutError,
    )
    runner = PipelineRunner(_make_manifest(connector, publisher=publisher))

    report = runner.run(_INPUT_DATA)

    _assert_report_message_is_sanitized(
        report,
        failed_step="PUBLISH",
        reason_code="PUBLISH.TIMEOUT",
        raw_secret="abc",
    )
