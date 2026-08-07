"""Run example 04_local_archive: JSONL input archived to a local CSV file."""

import os
from pathlib import Path

from pfp_runtime.shell.factory import PFPFactory

EXAMPLE_DIR = Path(__file__).resolve().parent
INFRA_PATH = EXAMPLE_DIR / "infra.yaml"
INPUT_PATH = EXAMPLE_DIR / "input" / "input.jsonl"


def main() -> None:
    """Build the worker and run the local archive pipeline once.

    Returns:
        None. The function prints the execution status, archived file path,
        and a CSV preview to stdout for manual inspection.
    """
    original_cwd = Path.cwd()
    try:
        os.chdir(EXAMPLE_DIR)
        worker = PFPFactory().build_worker(infra_path=INFRA_PATH)
        report = worker.run(INPUT_PATH.read_bytes())
    finally:
        os.chdir(original_cwd)

    print(f"Status: {report.status}")
    print(f"Artifacts: {len(report.artifacts)}")
    if report.artifacts:
        metadata = report.artifacts[0].metadata
        location = getattr(metadata, "location", None)
        print(f"Archive location: {location}")
        payload = b"".join(report.artifacts[0].payload)
        print(f"--- Artifact preview ---\n{payload.decode('utf-8')[:500]}")


if __name__ == "__main__":
    main()
