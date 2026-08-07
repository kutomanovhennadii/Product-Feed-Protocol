"""Run example 07_streaming_jsonl: larger JSONL fixture through a text stream."""

from pathlib import Path
from typing import Any, cast

from pfp_runtime.manifest.pipeline_manifest_provider import build_pipeline_manifest
from pfp_runtime.orchestration.pipeline_runner import PipelineRunner

EXAMPLE_DIR = Path(__file__).resolve().parent
INFRA_PATH = EXAMPLE_DIR / "infra.yaml"
INPUT_PATH = EXAMPLE_DIR / "input" / "input.jsonl"


def main() -> None:
    """Build the runtime manifest and stream the JSONL fixture once.

    Returns:
        None. The function prints the execution status, processed record count,
        and a CSV preview to stdout for manual inspection.
    """
    manifest = build_pipeline_manifest(str(INFRA_PATH))
    runner = PipelineRunner(manifest)

    with INPUT_PATH.open("r", encoding="utf-8") as input_stream:
        report = runner.run(cast(Any, input_stream))

    print(f"Status: {report.status}")
    print(f"Artifacts: {len(report.artifacts)}")
    print(f"Processed: {report.counters.get('processed', 0)}")
    if report.artifacts:
        payload = b"".join(report.artifacts[0].payload)
        print(f"--- Artifact preview ---\n{payload.decode('utf-8')[:500]}")


if __name__ == "__main__":
    main()
