"""Telemetry-axis matrix coverage for Phase 10.

Returns:
    None.
"""

from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry, generate_latest

from pfp_runtime.publishing.contracts import PublishMetadata
from pfp_utils.telemetry import PrometheusTelemetryHandler
from tests.matrix._axis_helpers import (
    MATRIX_ROOT,
    assert_success_baseline,
    count_fixture_records,
    read_yaml,
)
from tests.matrix.matrix_runner import run_matrix_cell

_TELEMETRY_CASES = (
    pytest.param("infra_none.yaml", "none", id="none"),
    pytest.param("infra_prometheus.yaml", "prometheus", id="prometheus"),
)


@pytest.mark.parametrize(("infra_name", "provider"), _TELEMETRY_CASES)
def test_telemetry_axis_respects_provider_selection(
    infra_name: str,
    provider: str,
    monkeypatch: pytest.MonkeyPatch,
    prometheus_registry: CollectorRegistry,
) -> None:
    """Telemetry provider selection must match the runtime observability contract.

    Args:
        infra_name: Telemetry infra filename.
        provider: Expected telemetry provider token.
        monkeypatch: Pytest fixture used to replace telemetry constructor seams.
        prometheus_registry: Isolated Prometheus registry fixture.

    Returns:
        None.
    """
    infra_path = MATRIX_ROOT / "infra" / "telemetry" / infra_name
    fixture_path = MATRIX_ROOT / "fixtures" / "default.jsonl"
    input_format = str(read_yaml(infra_path)["input"]["format"])

    if provider == "prometheus":
        monkeypatch.setattr(
            "pfp_runtime.manifest.observability_manifest_builder.PrometheusTelemetryHandler",
            lambda *args, **kwargs: PrometheusTelemetryHandler(
                registry=prometheus_registry
            ),
        )
        result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)
    else:

        def _unexpected_prometheus_constructor(*args, **kwargs) -> object:
            raise AssertionError("provider=none must not build Prometheus telemetry")

        monkeypatch.setattr(
            "pfp_runtime.manifest.observability_manifest_builder.PrometheusTelemetryHandler",
            _unexpected_prometheus_constructor,
        )
        result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)

    assert_success_baseline(
        result,
        golden_path=MATRIX_ROOT / "golden" / "telemetry" / "expected.csv",
        expected_target="stripe.product_feed",
        expected_content_type="text/csv",
        expected_input_count=count_fixture_records(fixture_path, input_format),
    )

    metrics_text = generate_latest(prometheus_registry).decode("utf-8")
    if provider == "prometheus":
        assert "pfp_stage_duration_seconds" in metrics_text
        assert 'stage="validation"' in metrics_text
        assert 'stage="publish"' in metrics_text
        assert "pfp_items_processed_total" not in metrics_text
    else:
        assert "pfp_stage_duration_seconds" not in metrics_text

    metadata = result.report.artifacts[0].metadata
    assert isinstance(metadata, PublishMetadata)
    assert metadata.archive_skipped is True
    assert metadata.delivery_skipped is True
    assert metadata.delivery_status_code is None
