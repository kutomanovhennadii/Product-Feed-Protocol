"""Load-style perf regression for a large realtime catalog."""

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


def test_large_catalog_runtime_satisfies_sla(monkeypatch: pytest.MonkeyPatch) -> None:
    """A large synthetic catalog must stay within runtime and memory budgets."""
    monkeypatch.chdir(realtime_config_dir())
    # 20k records ≈ 16 MB payload — half of the 32 MiB max_input_bytes limit
    # declared in connectors_registry.json. Larger defaults would be rejected
    # by the adapter contract before any performance is measured; scale up via
    # the env knob only together with a config that raises the input limit.
    item_count = env_int("PFP_PERF_LARGE_CATALOG_ITEMS", 20_000)
    sla_seconds = env_float("PFP_PERF_LARGE_CATALOG_SLA_SECONDS", 60.0)
    peak_limit_mb = env_float("PFP_PERF_LARGE_CATALOG_PEAK_MB", 512.0)
    payload, valid_count, invalid_count = build_realtime_payload(
        total_records=item_count
    )

    assert invalid_count == 0

    worker = PFPFactory().build_worker(infra_path=realtime_infra_path())
    report, peak_mb = run_with_peak_memory(worker, payload)

    assert report.status == "SUCCESS"
    assert report.timings["total"] < sla_seconds
    assert peak_mb < peak_limit_mb
    assert counter_int(report, "input_items_count") == valid_count
    assert counter_int(report, "processed") == valid_count
    assert counter_int(report, "artifacts_count") == 1
    assert csv_data_row_count(report) == valid_count
