"""Run example 08_observability_prometheus: pipeline execution with Prometheus metrics."""

from dataclasses import replace
from pathlib import Path

from pfp_runtime.manifest.pipeline_manifest_provider import build_pipeline_manifest
from pfp_runtime.orchestration.pipeline_runner import PipelineRunner
from pfp_utils.telemetry.telemetry_handlers import PrometheusTelemetryHandler

try:
    from prometheus_client import CollectorRegistry, generate_latest
except (
    ImportError
) as exc:  # pragma: no cover - environment-specific optional dependency
    raise RuntimeError(
        "Install the optional prometheus dependencies before running example 08."
    ) from exc

EXAMPLE_DIR = Path(__file__).resolve().parent
INFRA_PATH = EXAMPLE_DIR / "infra.yaml"
INPUT_PATH = EXAMPLE_DIR / "input" / "input.jsonl"


def main() -> None:
    """Run the pipeline and print a deterministic Prometheus metrics preview.

    Returns:
        None. The function prints the execution status, a CSV artifact preview,
        and a subset of generated Prometheus metric lines.
    """
    registry = CollectorRegistry()
    manifest = build_pipeline_manifest(str(INFRA_PATH))
    observability = replace(
        manifest.observability,
        telemetry_handler=PrometheusTelemetryHandler(registry=registry),
        telemetry_enabled=True,
        telemetry_provider="prometheus",
    )
    runner = PipelineRunner(replace(manifest, observability=observability))
    report = runner.run(INPUT_PATH.read_bytes())

    print(f"Status: {report.status}")
    print(f"Artifacts: {len(report.artifacts)}")
    if report.artifacts:
        payload = b"".join(report.artifacts[0].payload)
        print(f"--- Artifact preview ---\n{payload.decode('utf-8')[:500]}")

    metric_lines = [
        line
        for line in generate_latest(registry).decode("utf-8").splitlines()
        if line.startswith("pfp_")
    ]
    print("--- Metrics preview ---")
    print("\n".join(metric_lines[:12]))


if __name__ == "__main__":
    main()
