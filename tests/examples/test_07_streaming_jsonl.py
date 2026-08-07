"""Tests for the 07_streaming_jsonl public example."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import runpy
from pathlib import Path
from types import ModuleType


def _load_example_run_module() -> ModuleType:
    """Load the example runner module from its file path.

    Returns:
        ModuleType: The loaded `run.py` module for example 07.
    """
    example_dir = (
        Path(__file__).resolve().parents[2] / "examples" / "07_streaming_jsonl"
    )
    module_path = example_dir / "run.py"
    spec = importlib.util.spec_from_file_location(
        "example_07_streaming_jsonl_run", module_path
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run = _load_example_run_module()


def test_example_runner_matches_expected_csv() -> None:
    """Verify that example 07 streams records and matches the expected CSV."""
    example_dir = Path(run.EXAMPLE_DIR)
    manifest = run.build_pipeline_manifest(str(example_dir / "infra.yaml"))
    runner = run.PipelineRunner(manifest)

    with (example_dir / "input" / "input.jsonl").open("r", encoding="utf-8") as stream:
        report = runner.run(run.cast(run.Any, stream))

    assert report.status == "SUCCESS"
    assert len(report.artifacts) == 1
    assert report.counters.get("processed", 0) == 50

    actual = b"".join(report.artifacts[0].payload)
    expected = (example_dir / "expected" / "output.csv").read_bytes()

    assert actual == expected


def test_example_runner_prints_success_preview() -> None:
    """Verify that the example runner prints SUCCESS, count, and preview."""
    stdout = io.StringIO()

    with contextlib.redirect_stdout(stdout):
        run.main()

    output = stdout.getvalue()
    assert "Status: SUCCESS" in output
    assert "Artifacts: 1" in output
    assert "Processed: 50" in output
    assert "Streaming Record 001" in output


def test_example_script_entrypoint_prints_success_preview() -> None:
    """Verify that the script entrypoint executes and prints the preview."""
    stdout = io.StringIO()
    run_file = run.__file__
    assert run_file is not None

    with contextlib.redirect_stdout(stdout):
        runpy.run_path(run_file, run_name="__main__")

    output = stdout.getvalue()
    assert "Status: SUCCESS" in output
    assert "Processed: 50" in output
