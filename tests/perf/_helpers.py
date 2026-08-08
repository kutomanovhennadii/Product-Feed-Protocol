"""Shared helpers for perf tests built on the current PFPFactory contract."""

from __future__ import annotations

import csv
import gc
import io
import json
import os
import tracemalloc
from pathlib import Path
from typing import Any, Final, Mapping, cast

from pfp_runtime.pipeline.execution_report import ExecutionReport
from pfp_runtime.shell.factory import PFPWorker

_MEBIBYTE: Final[float] = 1024.0 * 1024.0
_PYTHON_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_REALTIME_CONFIG_DIR: Final[Path] = _PYTHON_ROOT / "config" / "shopify_realtime"
_REALTIME_INFRA_PATH: Final[Path] = _REALTIME_CONFIG_DIR / "infra_shopify_realtime.yaml"
_REALTIME_FIXTURE_PATH: Final[Path] = (
    _PYTHON_ROOT / "tests" / "e2e" / "fixtures" / "shopify_realtime_input.json"
)


def realtime_config_dir() -> Path:
    """Return the config directory used by the perf runtime tests."""
    return _REALTIME_CONFIG_DIR


def realtime_infra_path() -> Path:
    """Return the infra path used by the perf runtime tests."""
    return _REALTIME_INFRA_PATH


def env_int(name: str, default: int, *, minimum: int = 1) -> int:
    """Read a positive integer from the environment."""
    raw_value = os.getenv(name)
    value = default if raw_value is None else int(raw_value)
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def env_float(name: str, default: float, *, minimum: float = 0.0) -> float:
    """Read a positive float from the environment."""
    raw_value = os.getenv(name)
    value = default if raw_value is None else float(raw_value)
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def build_realtime_payload(
    *,
    total_records: int,
    invalid_every: int | None = None,
) -> tuple[bytes, int, int]:
    """Build a synthetic Shopify Realtime payload for perf scenarios.

    Args:
        total_records: Number of records to generate.
        invalid_every: Every Nth record is generated without the required
            title field so the runtime skips it while preserving SUCCESS for
            the remaining valid items.

    Returns:
        Tuple of payload bytes, valid record count and invalid record count.
    """
    if total_records < 1:
        raise ValueError("total_records must be >= 1")
    if invalid_every is not None and invalid_every < 2:
        raise ValueError("invalid_every must be >= 2")

    records = []
    valid_count = 0
    invalid_count = 0
    valid_templates = _load_fixture_templates()[:3]

    for index in range(total_records):
        if invalid_every is not None and (index + 1) % invalid_every == 0:
            records.append(_make_invalid_record(index))
            invalid_count += 1
            continue

        template = valid_templates[index % len(valid_templates)]
        records.append(_make_valid_record(template, index))
        valid_count += 1

    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return payload, valid_count, invalid_count


def run_with_peak_memory(
    worker: PFPWorker,
    payload: bytes,
) -> tuple[ExecutionReport, float]:
    """Execute a clean SLA run, then a traced run measuring peak memory in MiB.

    The runs are separated on purpose: tracemalloc slows the pipeline roughly
    3x, so asserting ``report.timings`` from a traced run would measure the
    profiler, not the pipeline. The returned report comes from the clean run;
    the peak comes from a second run of the same payload under tracemalloc.
    """
    report = worker.run(payload)
    gc.collect()
    tracemalloc.start()
    try:
        worker.run(payload)
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        gc.collect()
    return report, peak_bytes / _MEBIBYTE


def soak_run_once(
    worker: PFPWorker, payload: bytes
) -> tuple[ExecutionReport, float, float]:
    """Execute one run inside an active tracemalloc session.

    Returns:
        Report, current traced memory in MiB and peak traced memory in MiB.
    """
    report = worker.run(payload)
    gc.collect()
    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    return report, current_bytes / _MEBIBYTE, peak_bytes / _MEBIBYTE


def counter_int(report: ExecutionReport, key: str) -> int:
    """Extract an integer counter from the legacy report view."""
    value = report.counters.get(key)
    if not isinstance(value, int):
        raise AssertionError(f"Expected integer counter for {key}, got {value!r}")
    return value


def csv_data_row_count(report: ExecutionReport) -> int:
    """Return the number of data rows in the first published CSV artifact."""
    artifact = report.artifacts[0]
    csv_text = b"".join(artifact.payload).decode(artifact.metadata.encoding)
    rows = list(csv.reader(io.StringIO(csv_text)))
    return max(len(rows) - 1, 0)


def _load_fixture_templates() -> list[Mapping[str, Any]]:
    """Load the existing realtime fixture as the canonical record template."""
    payload = json.loads(_REALTIME_FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise AssertionError("Expected realtime fixture to be a JSON array")
    return [cast(Mapping[str, Any], item) for item in payload]


def _make_valid_record(template: Mapping[str, Any], index: int) -> dict[str, Any]:
    """Clone a valid realtime record and assign stable unique identifiers."""
    record = dict(template)
    variant_id = 600_000 + index
    product_id = 700_000 + (index // 3)
    record["id"] = f"gid://shopify/ProductVariant/{variant_id}"
    record["__parentProductId"] = f"gid://shopify/Product/{product_id}"
    record["sku"] = f"SKU-{index:06d}"
    record["barcode"] = f"{9_000_000_000_000 + index:013d}"
    record["onlineStoreUrl"] = (
        f"https://example.myshopify.com/products/perf-{index:06d}"
    )
    record["title"] = f"Perf Catalog Item {index:06d}"
    record["__parentTitle"] = f"Perf Catalog Family {product_id}"
    return record


def _make_invalid_record(index: int) -> dict[str, Any]:
    """Create a record that matches the known realtime skip path."""
    record = _make_valid_record(_load_fixture_templates()[0], index)
    record.pop("title", None)
    record["descriptionHtml"] = "<p>Invalid perf record without title.</p>"
    return record


__all__ = [
    "build_realtime_payload",
    "counter_int",
    "csv_data_row_count",
    "env_float",
    "env_int",
    "realtime_config_dir",
    "realtime_infra_path",
    "run_with_peak_memory",
    "soak_run_once",
]
