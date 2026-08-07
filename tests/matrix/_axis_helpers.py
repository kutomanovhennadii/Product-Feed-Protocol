"""Shared helpers for Phase 10 matrix axis tests.

Returns:
    None.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml

from tests.matrix.matrix_runner import MatrixCellResult

MATRIX_ROOT = Path(__file__).resolve().parent
EXPECTED_TIMING_KEYS = frozenset({"ingestion_extract", "core", "publish", "total"})


def read_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file into a mutable dictionary.

    Args:
        path: YAML file path.

    Returns:
        Parsed YAML mapping.
    """
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected mapping YAML at {path}, got {type(payload)!r}")
    return payload


def write_yaml(path: Path, payload: dict[str, Any]) -> Path:
    """Serialize a YAML mapping to disk.

    Args:
        path: Output path.
        payload: Mapping to serialize.

    Returns:
        The same output path for fluent call sites.
    """
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    return path


def clone_infra_with_overrides(
    tmp_path: Path,
    source_infra_path: Path,
    *,
    archive_config: Path | None = None,
    client_config: Path | None = None,
) -> Path:
    """Copy an infra YAML and replace output config paths when needed.

    Args:
        tmp_path: Temporary directory for the cloned infra file.
        source_infra_path: Original infra YAML path.
        archive_config: Optional replacement archive config path.
        client_config: Optional replacement client config path.

    Returns:
        Path to the cloned infra YAML.
    """
    infra_payload = read_yaml(source_infra_path)
    source_base_dir = source_infra_path.resolve().parent

    input_payload = infra_payload.setdefault("input", {})
    input_config = input_payload.get("config")
    if isinstance(input_config, dict) and "connector_mapping" in input_config:
        input_config["connector_mapping"] = str(
            (source_base_dir / str(input_config["connector_mapping"])).resolve()
        )

    producer_payload = infra_payload.setdefault("producer", {})
    for key in ("schema_file", "policy_file"):
        if key in producer_payload:
            producer_payload[key] = str(
                (source_base_dir / str(producer_payload[key])).resolve()
            )

    output_payload = infra_payload.setdefault("output", {})
    if archive_config is not None:
        output_payload["archive_config"] = str(archive_config)
    elif "archive_config" in output_payload:
        output_payload["archive_config"] = str(
            (source_base_dir / str(output_payload["archive_config"])).resolve()
        )
    if client_config is not None:
        output_payload["client_config"] = str(client_config)
    elif "client_config" in output_payload:
        output_payload["client_config"] = str(
            (source_base_dir / str(output_payload["client_config"])).resolve()
        )
    return write_yaml(tmp_path / source_infra_path.name, infra_payload)


def count_fixture_records(fixture_path: Path, input_format: str) -> int:
    """Count logical input rows for a matrix fixture.

    Args:
        fixture_path: Fixture payload path.
        input_format: Infra-declared input format for the fixture.

    Returns:
        Number of logical source records in the fixture.
    """
    normalized_format = input_format.strip().lower()
    raw_text = fixture_path.read_text(encoding="utf-8")

    if normalized_format in {"json", "rows", "streaming_json"}:
        payload = json.loads(raw_text)
        if not isinstance(payload, list):
            raise TypeError(
                f"Expected JSON array fixture for format {normalized_format!r}"
            )
        return len(payload)

    if normalized_format in {"jsonl", "streaming_jsonl"}:
        return sum(1 for line in raw_text.splitlines() if line.strip())

    if normalized_format in {"csv", "streaming_csv"}:
        rows = list(csv.reader(raw_text.splitlines()))
        return max(len(rows) - 1, 0)

    raise ValueError(f"Unsupported matrix fixture format: {input_format!r}")


def assert_success_baseline(
    result: MatrixCellResult,
    *,
    golden_path: Path,
    expected_target: str,
    expected_content_type: str,
    expected_input_count: int | None,
) -> None:
    """Assert the common success invariants shared by all matrix axes.

    Args:
        result: Runtime result returned by ``run_matrix_cell``.
        golden_path: Expected payload bytes committed in the repository.
        expected_target: Expected artifact target protocol id.
        expected_content_type: Expected artifact content type.
        expected_input_count: Number of logical source records in the fixture,
            or ``None`` when the axis only validates target/golden semantics.

    Returns:
        None.
    """
    report = result.report
    assert report.status == "SUCCESS"
    assert EXPECTED_TIMING_KEYS.issubset(report.timings)
    assert all(report.timings[key] >= 0 for key in EXPECTED_TIMING_KEYS)
    if expected_input_count is not None:
        assert report.counters["input_items_count"] == expected_input_count
    assert report.counters["artifacts_count"] == 1
    assert report.counters["error"] == 0

    artifact = report.artifacts[0]
    assert artifact.metadata.target == expected_target
    assert artifact.metadata.content_type == expected_content_type
    assert result.csv_payload == golden_path.read_bytes()
