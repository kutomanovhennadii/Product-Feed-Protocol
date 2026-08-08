"""Stress perf regression with a large share of invalid realtime records."""

from __future__ import annotations

import pytest

from pfp_runtime.shell.factory import PFPFactory

from ._helpers import (
    build_realtime_payload,
    counter_int,
    csv_data_row_count,
    env_float,
    env_int,
    realtime_config_dir,
    realtime_infra_path,
    run_with_peak_memory,
)

pytestmark = [pytest.mark.perf, pytest.mark.timeout(300)]


def test_bad_record_stress_preserves_success_for_valid_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Half-invalid payloads must still succeed for the remaining valid records."""
    monkeypatch.chdir(realtime_config_dir())
    # Invalid records cost ~5 ms each (per-record warning logging), so 10k
    # half-invalid records keep the clean run near half of the 60 s SLA on
    # commodity CI runners. Scale up via the env knob in dedicated perf rigs.
    item_count = env_int("PFP_PERF_STRESS_ITEMS", 10_000)
    sla_seconds = env_float("PFP_PERF_STRESS_SLA_SECONDS", 60.0)
    peak_limit_mb = env_float("PFP_PERF_STRESS_PEAK_MB", 512.0)
    payload, valid_count, invalid_count = build_realtime_payload(
        total_records=item_count,
        invalid_every=2,
    )

    worker = PFPFactory().build_worker(infra_path=realtime_infra_path())
    report, peak_mb = run_with_peak_memory(worker, payload)

    assert invalid_count == item_count // 2
    assert report.status == "SUCCESS"
    assert report.timings["total"] < sla_seconds
    assert peak_mb < peak_limit_mb
    assert counter_int(report, "input_items_count") == valid_count
    assert counter_int(report, "processed") == valid_count
    assert counter_int(report, "artifacts_count") == 1
    assert csv_data_row_count(report) == valid_count
