"""Run example 03_jsonl_input: nested JSONL objects to one CSV row."""

from pathlib import Path

from pfp_runtime.shell.factory import PFPFactory

EXAMPLE_DIR = Path(__file__).resolve().parent
INFRA_PATH = EXAMPLE_DIR / "infra.yaml"
INPUT_PATH = EXAMPLE_DIR / "input" / "input.jsonl"


def main() -> None:
    """Build the worker and run the nested JSONL pipeline once.

    Returns:
        None. The function prints the execution status and a CSV preview
        to stdout for manual inspection.
    """
    worker = PFPFactory().build_worker(infra_path=INFRA_PATH)
    report = worker.run(INPUT_PATH.read_bytes())

    print(f"Status: {report.status}")
    print(f"Artifacts: {len(report.artifacts)}")
    if report.artifacts:
        payload = b"".join(report.artifacts[0].payload)
        print(f"--- Artifact preview ---\n{payload.decode('utf-8')[:500]}")


if __name__ == "__main__":
    main()
