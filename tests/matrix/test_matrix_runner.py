"""Tests for the Phase 10 matrix runner helpers."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from tests.matrix import matrix_runner


class _DummyWorker:
    """Worker stub that records the raw input passed to ``run``.

    Attributes:
        report: Report object returned by ``run``.
        last_raw_input: Last payload received by the worker.
    """

    def __init__(self, report: Any) -> None:
        """Store the report object returned by the stub worker.

        Args:
            report: Report object to return from ``run``.

        Returns:
            None.
        """
        self.report = report
        self.last_raw_input: Any = None

    def run(self, raw_input: Any) -> Any:
        """Record the raw input and return the prepared report.

        Args:
            raw_input: Payload passed into the worker.

        Returns:
            Prepared report object.
        """
        self.last_raw_input = raw_input
        return self.report


class _DummyFactory:
    """Factory stub that returns a preconfigured worker.

    Attributes:
        worker: Worker returned from ``build_worker``.
        seen_infra_path: Last infra path received by the factory.
    """

    def __init__(self, worker: _DummyWorker) -> None:
        """Store the worker returned by the stub factory.

        Args:
            worker: Worker object returned by ``build_worker``.

        Returns:
            None.
        """
        self.worker = worker
        self.seen_infra_path: Path | None = None

    def build_worker(self, *, infra_path: Path) -> _DummyWorker:
        """Record the infra path and return the prepared worker.

        Args:
            infra_path: Resolved infra path supplied by the matrix runner.

        Returns:
            Prepared worker stub.
        """
        self.seen_infra_path = infra_path
        return self.worker


class _Capture:
    """Capture stub used to verify side-effect hooks.

    Attributes:
        prepared: Whether the prepare hook was invoked.
        snapped_report: Report passed into ``snapshot``.
    """

    def __init__(self) -> None:
        """Initialize capture state.

        Returns:
            None.
        """
        self.prepared = False
        self.snapped_report: Any = None

    def prepare(self):
        """Return a no-op context and record that prepare was called.

        Returns:
            No-op context manager.
        """
        self.prepared = True
        return nullcontext()

    def snapshot(self, report: Any) -> dict[str, str]:
        """Record the report and return a deterministic capture payload.

        Args:
            report: Report passed back from the executed worker.

        Returns:
            Deterministic capture payload for assertions.
        """
        self.snapped_report = report
        return {"published": "captured"}


def _write_infra(tmp_path: Path, input_format: str) -> Path:
    """Create a minimal infra file for input-format parsing tests.

    Args:
        tmp_path: Temporary directory root for the current test.
        input_format: Input format value written to the infra file.

    Returns:
        Path to the created infra YAML file.
    """
    infra_path = tmp_path / "infra.yaml"
    infra_path.write_text(
        yaml.safe_dump({"input": {"format": input_format}}),
        encoding="utf-8",
    )
    return infra_path


def test_read_input_format_defaults_to_jsonl(tmp_path: Path) -> None:
    """Reading infra without format must default to ``jsonl``.

    Args:
        tmp_path: Temporary directory root for the current test.

    Returns:
        None.
    """
    infra_path = tmp_path / "infra.yaml"
    infra_path.write_text("input: {}\n", encoding="utf-8")

    assert matrix_runner._read_input_format(infra_path) == "jsonl"


def test_load_fixture_payload_reads_rows_json_array(tmp_path: Path) -> None:
    """Rows fixtures must accept JSON arrays.

    Args:
        tmp_path: Temporary directory root for the current test.

    Returns:
        None.
    """
    fixture_path = tmp_path / "rows.json"
    fixture_path.write_text('[{"item_id": "SKU-1"}]', encoding="utf-8")

    assert matrix_runner._load_fixture_payload(fixture_path, "rows") == [
        {"item_id": "SKU-1"}
    ]


def test_load_fixture_payload_reads_rows_json_lines(tmp_path: Path) -> None:
    """Rows fixtures must accept line-delimited JSON objects.

    Args:
        tmp_path: Temporary directory root for the current test.

    Returns:
        None.
    """
    fixture_path = tmp_path / "rows.jsonl"
    fixture_path.write_text(
        '{"item_id": "SKU-1"}\n{"item_id": "SKU-2"}\n', encoding="utf-8"
    )

    assert matrix_runner._load_fixture_payload(fixture_path, "rows") == [
        {"item_id": "SKU-1"},
        {"item_id": "SKU-2"},
    ]


def test_load_fixture_payload_skips_blank_rows_json_lines(tmp_path: Path) -> None:
    """Rows fixtures must ignore blank lines between JSON objects.

    Args:
        tmp_path: Temporary directory root for the current test.

    Returns:
        None.
    """
    fixture_path = tmp_path / "rows.blank-lines.jsonl"
    fixture_path.write_text(
        '{"item_id": "SKU-1"}\n\n{"item_id": "SKU-2"}\n',
        encoding="utf-8",
    )

    assert matrix_runner._load_fixture_payload(fixture_path, "rows") == [
        {"item_id": "SKU-1"},
        {"item_id": "SKU-2"},
    ]


def test_load_fixture_payload_reads_empty_rows_as_empty_list(tmp_path: Path) -> None:
    """Empty rows fixtures must return an empty list.

    Args:
        tmp_path: Temporary directory root for the current test.

    Returns:
        None.
    """
    fixture_path = tmp_path / "rows.empty"
    fixture_path.write_text("\n", encoding="utf-8")

    assert matrix_runner._load_fixture_payload(fixture_path, "rows") == []


@pytest.mark.parametrize(
    ("input_format", "expected_mode", "expected_type"),
    [
        ("streaming_csv", "r", str),
        ("streaming_jsonl", "r", str),
        ("streaming_json", "rb", bytes),
    ],
)
def test_load_fixture_payload_opens_streaming_formats_with_expected_mode(
    tmp_path: Path,
    input_format: str,
    expected_mode: str,
    expected_type: type[Any],
) -> None:
    """Streaming formats must use text or binary streams expected by adapters.

    Args:
        tmp_path: Temporary directory root for the current test.
        input_format: Matrix input format to load.
        expected_mode: File mode expected on the opened stream.
        expected_type: Python value type returned by ``read`` on the stream.

    Returns:
        None.
    """
    fixture_path = tmp_path / f"fixture.{input_format}"
    fixture_path.write_text('{"item_id": "SKU-1"}\n', encoding="utf-8")

    stream = matrix_runner._load_fixture_payload(fixture_path, input_format)
    try:
        assert stream.mode == expected_mode
        assert isinstance(stream.read(), expected_type)
    finally:
        stream.close()


def test_load_fixture_payload_reads_non_streaming_formats_as_bytes(
    tmp_path: Path,
) -> None:
    """Non-streaming formats must be returned as raw bytes.

    Args:
        tmp_path: Temporary directory root for the current test.

    Returns:
        None.
    """
    fixture_path = tmp_path / "fixture.jsonl"
    fixture_path.write_bytes(b'{"item_id": "SKU-1"}\n')

    assert (
        matrix_runner._load_fixture_payload(fixture_path, "jsonl")
        == b'{"item_id": "SKU-1"}\n'
    )


def test_pushd_restores_previous_directory(tmp_path: Path) -> None:
    """Working directory helper must restore the previous directory after exit.

    Args:
        tmp_path: Temporary directory root for the current test.

    Returns:
        None.
    """
    original_dir = Path.cwd()

    with matrix_runner._pushd(tmp_path):
        assert Path.cwd() == tmp_path

    assert Path.cwd() == original_dir


def test_run_matrix_cell_executes_worker_and_collects_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Matrix cell execution must resolve inputs, run worker and capture artifacts.

    Args:
        tmp_path: Temporary directory root for the current test.
        monkeypatch: Pytest monkeypatch fixture for replacing runtime factory.

    Returns:
        None.
    """
    infra_path = _write_infra(tmp_path, "jsonl")
    fixture_path = tmp_path / "fixture.jsonl"
    fixture_path.write_bytes(b'{"item_id": "SKU-1"}\n')
    report = SimpleNamespace(
        artifacts=[SimpleNamespace(payload=[b"part-1", b"part-2"])],
    )
    worker = _DummyWorker(report)
    factory = _DummyFactory(worker)
    capture = _Capture()

    monkeypatch.setattr(matrix_runner, "PFPFactory", lambda: factory)

    result = matrix_runner.run_matrix_cell(
        infra_path=infra_path,
        fixture_path=fixture_path,
        side_effect_capture=capture,
    )

    assert factory.seen_infra_path == infra_path.resolve()
    assert worker.last_raw_input == b'{"item_id": "SKU-1"}\n'
    assert result.report is report
    assert result.csv_payload == b"part-1part-2"
    assert result.side_effects == {"published": "captured"}
    assert capture.prepared is True
    assert capture.snapped_report is report


def test_run_matrix_cell_returns_empty_payload_without_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Matrix cell execution must return empty payload when no artifacts are produced.

    Args:
        tmp_path: Temporary directory root for the current test.
        monkeypatch: Pytest monkeypatch fixture for replacing runtime factory.

    Returns:
        None.
    """
    infra_path = _write_infra(tmp_path, "jsonl")
    fixture_path = tmp_path / "fixture.jsonl"
    fixture_path.write_bytes(b'{"item_id": "SKU-1"}\n')
    report = SimpleNamespace(artifacts=[])
    worker = _DummyWorker(report)
    factory = _DummyFactory(worker)

    monkeypatch.setattr(matrix_runner, "PFPFactory", lambda: factory)

    result = matrix_runner.run_matrix_cell(
        infra_path=infra_path,
        fixture_path=fixture_path,
    )

    assert result.report is report
    assert result.csv_payload == b""
    assert result.side_effects == {}
