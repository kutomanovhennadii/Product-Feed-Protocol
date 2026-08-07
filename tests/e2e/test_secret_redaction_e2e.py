"""End-to-end regression test for secret redaction across runner outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, cast

import pytest

from pfp_core.artifact_production import prepare_artifact_producer_from_files
from pfp_core.contracts import ProducedArtifact
from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.manifest.observability_manifest_builder import (
    build_observability_manifest,
)
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    CoreManifest,
    PipelineManifest,
    PublishManifest,
)
from pfp_runtime.orchestration.pipeline_runner import PipelineRunner
from pfp_utils.diagnostics.diagnostic_models import Diagnostic, DiagnosticSeverity

_PYTHON_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_FILE = (
    _PYTHON_ROOT / "schemas" / "stripe.product_feed" / "stripe.product_feed-1.0.0.yaml"
)
_POLICY_FILE = _PYTHON_ROOT / "config" / "policies.yaml"

_API_KEY_SECRET = "E2E_SECRET_TOKEN"
_BEARER_SECRET = "E2E_SECRET_BEARER"
_SECRET_URL = f"https://example.local/catalog?api_key={_API_KEY_SECRET}"
_SECRET_AUTH = f"Authorization: Bearer {_BEARER_SECRET}"


class _ExtractResult:
    """Iterable extraction result carrying secret-bearing diagnostics.

    Returns:
        Iterable wrapper used by PipelineRunner ingestion flow.
    """

    def __init__(
        self,
        items: Iterable[Any],
        diagnostics: Iterable[Diagnostic],
    ) -> None:
        """Store extracted items and attached diagnostics.

        Args:
            items: Extracted UM items yielded into the core phase.
            diagnostics: Ingestion diagnostics attached to the extract result.

        Returns:
            None.
        """
        self._items = tuple(items)
        self._diagnostics = tuple(diagnostics)

    def __iter__(self) -> Iterable[Any]:
        """Yield extracted items for downstream processing.

        Returns:
            Iterator over extracted items.
        """
        return iter(self._items)

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """Expose extract diagnostics consumed by PipelineRunner.

        Returns:
            Tuple of ingestion diagnostics.
        """
        return self._diagnostics


class _SecretBearingConnector:
    """Connector that emits a valid item plus diagnostics with embedded secrets.

    Returns:
        Connector double for end-to-end redaction coverage.
    """

    def extract(self, raw_input: Any) -> _ExtractResult:
        """Return a valid ingest result plus secret-bearing diagnostics.

        Args:
            raw_input: Raw input payload supplied to the runner.

        Returns:
            Extract result with one valid item and one warning diagnostic.
        """
        del raw_input
        return _ExtractResult(
            items=({"item_id": "SKU-1"},),
            diagnostics=(
                Diagnostic(
                    severity=DiagnosticSeverity.WARN,
                    code="INGESTION.E2E_SECRET",
                    message=(
                        "Fetch warning for " f"{_SECRET_URL} using {_SECRET_AUTH}"
                    ),
                    metadata={
                        "request_url": _SECRET_URL,
                        "auth_header": _SECRET_AUTH,
                    },
                ),
            ),
        )


class _TimeoutPublisher:
    """Publisher that fails with secret-bearing timeout details.

    Returns:
        Publisher double used to exercise the publish failure path.
    """

    def publish(self, artifact: ProducedArtifact) -> ProducedArtifact:
        """Raise a timeout error containing URL and bearer secrets.

        Args:
            artifact: Produced artifact received from the core stage.

        Returns:
            Never returns.
        """
        del artifact
        raise TimeoutError(f"connection timed out to {_SECRET_URL}; {_SECRET_AUTH}")


def _make_infra() -> InfraConfig:
    """Build a minimal observability-enabled infra config for e2e logging.

    Returns:
        Valid InfraConfig with TEXT stdout logging and no telemetry backend.
    """
    return InfraConfig.model_validate(
        {
            "input": {
                "format": "csv",
                "config": {"connector_mapping": "./mapping.yaml"},
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
            "observability": {
                "log_format": "TEXT",
                "labels": {},
                "logging": {"level": "INFO"},
                "telemetry": {"provider": "none"},
            },
        }
    )


def _make_manifest() -> PipelineManifest:
    """Assemble a PipelineManifest with real logging and a failing publisher.

    Returns:
        PipelineManifest that exercises publish-time redaction end to end.
    """
    observability = build_observability_manifest(_make_infra())
    producer = prepare_artifact_producer_from_files(
        schema_file=str(_SCHEMA_FILE),
        policy_file=str(_POLICY_FILE),
        log_pipeline=observability.log_pipeline,
    )
    return PipelineManifest(
        ingestion=ConnectorManifest(
            connector=cast(Any, _SecretBearingConnector()),
            raw_input=b"e2e-input",
        ),
        core=CoreManifest(
            producer=producer,
            generated_at=None,
            fail_on_error_diagnostics=False,
        ),
        publish=PublishManifest(publisher=cast(Any, _TimeoutPublisher())),
        observability=observability,
        run_context=None,
    )


def _assert_secret_absent(text: str) -> None:
    """Assert that no raw e2e test secrets survive in ``text``.

    Args:
        text: Text surface that must not leak raw secrets.

    Returns:
        None.
    """
    assert _API_KEY_SECRET not in text
    assert _BEARER_SECRET not in text


def test_secret_redaction_e2e_masks_stdout_and_execution_report(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify stdout and ExecutionReport surfaces redact secrets end to end.

    Args:
        capsys: Pytest capture fixture used to inspect stdout output.

    Returns:
        None.
    """
    runner = PipelineRunner(_make_manifest())

    report = runner.run(b"e2e-input")
    stdout_text = capsys.readouterr().out
    validation_text = json.dumps(report.validation_report.to_dict(), sort_keys=True)

    assert report.status == "FAILED"
    assert report.failed_step == "PUBLISH"
    assert report.reason_code == "PUBLISH.TIMEOUT"
    assert report.error_type == "TimeoutError"

    _assert_secret_absent(stdout_text)
    _assert_secret_absent(report.message)
    _assert_secret_absent(validation_text)

    assert "***" in stdout_text
    assert "Publish failed" in stdout_text
    assert "***" in report.message
    assert "***" in validation_text
