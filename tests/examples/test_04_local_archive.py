"""Tests for the 04_local_archive public example."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import runpy
from pathlib import Path
from types import ModuleType

from pfp_runtime.shell.factory import PFPFactory


def _load_example_run_module() -> ModuleType:
    """Load the example runner module from its file path.

    Returns:
        ModuleType: The loaded `run.py` module for example 04.
    """
    example_dir = Path(__file__).resolve().parents[2] / "examples" / "04_local_archive"
    module_path = example_dir / "run.py"
    spec = importlib.util.spec_from_file_location(
        "example_04_local_archive_run", module_path
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run = _load_example_run_module()


def test_example_worker_matches_expected_csv_and_archive_path() -> None:
    """Verify that example 04 writes the expected CSV and archive location."""
    example_dir = Path(run.EXAMPLE_DIR)

    original_cwd = Path.cwd()
    try:
        os.chdir(example_dir)
        worker = PFPFactory().build_worker(infra_path=example_dir / "infra.yaml")
        report = worker.run((example_dir / "input" / "input.jsonl").read_bytes())
    finally:
        os.chdir(original_cwd)

    assert report.status == "SUCCESS"
    assert len(report.artifacts) == 1

    actual = b"".join(report.artifacts[0].payload)
    expected = (example_dir / "expected" / "output.csv").read_bytes()
    location = getattr(report.artifacts[0].metadata, "location", None)

    assert actual == expected
    assert location is not None
    assert Path(location).exists()


def test_example_runner_prints_success_preview_and_location() -> None:
    """Verify that the example runner prints SUCCESS, location, and CSV preview."""
    stdout = io.StringIO()

    with contextlib.redirect_stdout(stdout):
        run.main()

    output = stdout.getvalue()
    assert "Status: SUCCESS" in output
    assert "Artifacts: 1" in output
    assert "Archive location:" in output
    assert "id,title,description,link,availability" in output
    assert (
        "SKU-4,Local Archive Demo,Writes the generated artifact to disk,https://example.com/sku-4,in_stock"
        in output
    )


def test_example_script_entrypoint_prints_success_preview() -> None:
    """Verify that the script entrypoint executes and prints archive details."""
    stdout = io.StringIO()
    run_file = run.__file__
    assert run_file is not None

    with contextlib.redirect_stdout(stdout):
        runpy.run_path(run_file, run_name="__main__")

    output = stdout.getvalue()
    assert "Status: SUCCESS" in output
    assert "Artifacts: 1" in output
    assert "Archive location:" in output
