"""Shared runner helpers for Phase 10 matrix cells.

Returns:
    None.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ContextManager, Protocol

import yaml

from pfp_runtime.pipeline.execution_report import ExecutionReport
from pfp_runtime.shell.factory import PFPFactory


class SideEffectCapture(Protocol):
    """Protocol for axis-specific side effect capture.

    Returns:
        None.
    """

    def prepare(self) -> ContextManager[None]:
        """Return a context manager that installs the capture hooks.

        Returns:
            Context manager that activates the side-effect capture hooks.
        """

    def snapshot(self, report: ExecutionReport) -> Mapping[str, Any]:
        """Return collected side effects after pipeline execution.

        Args:
            report: Execution report produced by the completed pipeline run.

        Returns:
            Mapping with captured side-effect details.
        """


@dataclass(frozen=True)
class MatrixCellResult:
    """Result of one matrix cell execution.

    Attributes:
        report: Final execution report returned by the worker.
        csv_payload: Serialized artifact payload collected from the first artifact.
        side_effects: Captured side-effect metadata for the executed cell.
    """

    report: ExecutionReport
    csv_payload: bytes
    side_effects: Mapping[str, Any]


def run_matrix_cell(
    *,
    infra_path: Path,
    fixture_path: Path,
    side_effect_capture: SideEffectCapture | None = None,
) -> MatrixCellResult:
    """Execute one matrix cell using the user-facing PFP factory.

    Args:
        infra_path: Path to the infra YAML describing the matrix cell.
        fixture_path: Path to the input fixture consumed by the cell.
        side_effect_capture: Optional capture implementation for external effects.

    Returns:
        Result object containing the execution report, artifact payload and side effects.
    """

    resolved_infra_path = infra_path.resolve()
    resolved_fixture_path = fixture_path.resolve()
    input_format = _read_input_format(resolved_infra_path)
    capture_context = (
        side_effect_capture.prepare()
        if side_effect_capture is not None
        else nullcontext()
    )

    with _pushd(resolved_infra_path.parent), capture_context:
        worker = PFPFactory().build_worker(infra_path=resolved_infra_path)
        raw_input = _load_fixture_payload(resolved_fixture_path, input_format)
        report = worker.run(raw_input)

    artifact_payload = b""
    if report.artifacts:
        artifact_payload = b"".join(report.artifacts[0].payload)

    side_effects = (
        side_effect_capture.snapshot(report) if side_effect_capture is not None else {}
    )
    return MatrixCellResult(
        report=report,
        csv_payload=artifact_payload,
        side_effects=side_effects,
    )


def _read_input_format(infra_path: Path) -> str:
    """Read the declared input format from an infra file.

    Args:
        infra_path: Path to the infra YAML file.

    Returns:
        Normalized input format name, defaulting to ``jsonl`` when unspecified.
    """
    with infra_path.open("r", encoding="utf-8") as infra_file:
        infra_data = yaml.safe_load(infra_file) or {}
    input_section = infra_data.get("input") or {}
    return str(input_section.get("format", "jsonl")).strip().lower()


def _load_fixture_payload(fixture_path: Path, input_format: str) -> Any:
    """Load a fixture using the format declared by the matrix infra.

    Args:
        fixture_path: Path to the fixture file on disk.
        input_format: Normalized input format declared by the infra file.

    Returns:
        Bytes, text stream, binary stream, or parsed row collection for the fixture.
    """
    if input_format == "rows":
        content = fixture_path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        if content.startswith("["):
            return json.loads(content)

        records = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            records.append(json.loads(stripped))
        return records

    if input_format.startswith("streaming_"):
        if input_format in {"streaming_csv", "streaming_jsonl"}:
            return fixture_path.open("r", encoding="utf-8", newline="")
        return fixture_path.open("rb")

    return fixture_path.read_bytes()


@contextmanager
def _pushd(target_dir: Path) -> Iterator[None]:
    """Temporarily switch the working directory for fixture-relative execution.

    Args:
        target_dir: Directory to make current while the context is active.

    Yields:
        None while the working directory is switched.

    Returns:
        Iterator used by ``contextmanager`` to restore the previous directory.
    """
    previous_dir = Path.cwd()
    os.chdir(target_dir)
    try:
        yield
    finally:
        os.chdir(previous_dir)
