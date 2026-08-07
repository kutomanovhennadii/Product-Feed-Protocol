"""Soak perf regression for repeated runs through the same prepared worker."""

from __future__ import annotations

import gc
import tracemalloc

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
    soak_run_once,
)

pytestmark = [pytest.mark.perf, pytest.mark.timeout(300)]


def test_repeated_runs_reuse_worker_without_linear_memory_growth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sequential runs must reset counters and avoid obvious per-run memory growth."""
    monkeypatch.chdir(realtime_config_dir())
    run_count = env_int("PFP_PERF_SOAK_RUNS", 20)
    item_count = env_int("PFP_PERF_SOAK_ITEMS", 5_000)
    growth_limit_mb = env_float("PFP_PERF_SOAK_GROWTH_MB", 16.0)
    peak_limit_mb = env_float("PFP_PERF_SOAK_PEAK_MB", 256.0)
    payload, valid_count, invalid_count = build_realtime_payload(
        total_records=item_count
    )

    assert invalid_count == 0

    worker = PFPFactory().build_worker(infra_path=realtime_infra_path())
    current_samples: list[float] = []
    peak_samples: list[float] = []

    gc.collect()
    tracemalloc.start()
    try:
        for _ in range(run_count):
            report, current_mb, peak_mb = soak_run_once(worker, payload)
            current_samples.append(current_mb)
            peak_samples.append(peak_mb)
            tracemalloc.reset_peak()

            assert report.status == "SUCCESS"
            assert counter_int(report, "input_items_count") == valid_count
            assert counter_int(report, "processed") == valid_count
            assert counter_int(report, "artifacts_count") == 1
            assert csv_data_row_count(report) == valid_count
    finally:
        tracemalloc.stop()
        gc.collect()

    assert current_samples[-1] - current_samples[0] < growth_limit_mb
    assert max(peak_samples) < peak_limit_mb
