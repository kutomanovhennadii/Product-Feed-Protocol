"""Adapter-axis matrix coverage for Phase 10.

Returns:
    None.
"""

from __future__ import annotations

import pytest

from pfp_runtime.publishing.contracts import PublishMetadata
from tests.matrix._axis_helpers import (
    MATRIX_ROOT,
    assert_success_baseline,
    count_fixture_records,
    read_yaml,
)
from tests.matrix.matrix_runner import run_matrix_cell

_ADAPTER_CASES = (
    pytest.param("infra_csv.yaml", "input.csv", id="csv"),
    pytest.param("infra_json.yaml", "input.json", id="json"),
    pytest.param("infra_jsonl.yaml", "input.jsonl", id="jsonl"),
    pytest.param("infra_rows.yaml", "input.rows.json", id="rows"),
    pytest.param("infra_streaming_csv.yaml", "input.streaming.csv", id="streaming-csv"),
    pytest.param(
        "infra_streaming_json.yaml", "input.streaming.json", id="streaming-json"
    ),
    pytest.param(
        "infra_streaming_jsonl.yaml", "input.streaming.jsonl", id="streaming-jsonl"
    ),
)


@pytest.mark.parametrize(("infra_name", "fixture_name"), _ADAPTER_CASES)
def test_adapter_axis_matches_expected_csv_golden(
    infra_name: str,
    fixture_name: str,
) -> None:
    """Each adapter input format must converge to the same published CSV.

    Args:
        infra_name: Matrix infra file that selects the adapter format.
        fixture_name: Fixture file consumed by the adapter case.

    Returns:
        None.
    """
    infra_path = MATRIX_ROOT / "infra" / "adapter" / infra_name
    fixture_path = MATRIX_ROOT / "fixtures" / "adapter" / fixture_name
    input_format = str(read_yaml(infra_path)["input"]["format"])

    result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)

    assert_success_baseline(
        result,
        golden_path=MATRIX_ROOT / "golden" / "adapter" / "expected.csv",
        expected_target="stripe.product_feed",
        expected_content_type="text/csv",
        expected_input_count=count_fixture_records(fixture_path, input_format),
    )

    metadata = result.report.artifacts[0].metadata
    assert isinstance(metadata, PublishMetadata)
    assert metadata.archive_skipped is True
    assert metadata.delivery_skipped is True
    assert metadata.delivery_status_code is None
