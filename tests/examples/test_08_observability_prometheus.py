"""Tests for the 08_observability_prometheus public example."""

from __future__ import annotations

import contextlib
import io
import runpy
import subprocess
import sys
from pathlib import Path

EXAMPLE_DIR = (
    Path(__file__).resolve().parents[2] / "examples" / "08_observability_prometheus"
)
RUN_FILE = EXAMPLE_DIR / "run.py"


def test_example_entrypoint_prints_expected_csv_and_metrics() -> None:
    """Verify that example 08 prints the expected CSV preview and metrics."""
    expected = (EXAMPLE_DIR / "expected" / "output.csv").read_text(encoding="utf-8")
    stdout = io.StringIO()

    with contextlib.redirect_stdout(stdout):
        runpy.run_path(str(RUN_FILE), run_name="__main__")

    output = stdout.getvalue()
    assert "Status: SUCCESS" in output
    assert "Artifacts: 1" in output
    assert expected.strip() in output
    assert "--- Metrics preview ---" in output
    assert "pfp_stage_duration_seconds" in output


def test_example_script_runs_in_fresh_process() -> None:
    """Verify that the script also succeeds when launched in a fresh process."""
    completed = subprocess.run(
        [sys.executable, str(RUN_FILE)],
        check=True,
        capture_output=True,
        text=True,
    )

    output = completed.stdout
    assert "Status: SUCCESS" in output
    assert "--- Metrics preview ---" in output
