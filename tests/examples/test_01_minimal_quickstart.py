"""Tests for the 01_minimal_quickstart public example."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import runpy
from pathlib import Path
from types import ModuleType

from pfp_runtime.shell.factory import PFPFactory


def _load_example_run_module() -> ModuleType:
    """Load the example runner module from its file path.

    Returns:
        ModuleType: The loaded `run.py` module for example 01.
    """
    example_dir = (
        Path(__file__).resolve().parents[2] / "examples" / "01_minimal_quickstart"
    )
    module_path = example_dir / "run.py"
    spec = importlib.util.spec_from_file_location(
        "example_01_minimal_quickstart_run", module_path
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run = _load_example_run_module()


def test_example_worker_matches_expected_csv() -> None:
    """Verify that example 01 produces the expected CSV artifact bytes."""
    example_dir = Path(run.EXAMPLE_DIR)
    worker = PFPFactory().build_worker(infra_path=example_dir / "infra.yaml")

    report = worker.run((example_dir / "input" / "input.jsonl").read_bytes())

    assert report.status == "SUCCESS"
    assert len(report.artifacts) == 1

    actual = b"".join(report.artifacts[0].payload)
    expected = (example_dir / "expected" / "output.csv").read_bytes()
    assert actual == expected


def test_example_runner_prints_success_preview() -> None:
    """Verify that the example runner prints SUCCESS and the CSV preview."""
    stdout = io.StringIO()

    with contextlib.redirect_stdout(stdout):
        run.main()

    output = stdout.getvalue()
    assert "Status: SUCCESS" in output
    assert "Artifacts: 1" in output
    assert "id,title,description,link,availability" in output
    assert "SKU-1,Hello,World,https://example.com/sku-1,in_stock" in output


def test_example_script_entrypoint_prints_success_preview() -> None:
    """Verify that the script entrypoint executes and prints the CSV preview."""
    stdout = io.StringIO()
    run_file = run.__file__
    assert run_file is not None

    with contextlib.redirect_stdout(stdout):
        runpy.run_path(run_file, run_name="__main__")

    output = stdout.getvalue()
    assert "Status: SUCCESS" in output
    assert "Artifacts: 1" in output
    assert "id,title,description,link,availability" in output
