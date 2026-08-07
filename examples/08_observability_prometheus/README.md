# Example 08 — Observability Prometheus

## What this demonstrates

This example demonstrates Prometheus telemetry integration for the local runtime.
It runs a small JSONL pipeline, replaces the default telemetry handler with a dedicated `CollectorRegistry`, and prints the generated `pfp_*` metrics to stdout.

The dedicated registry keeps the example deterministic and avoids polluting any global Prometheus state in the current Python process.

## How to run

```bash
cd examples/08_observability_prometheus
python run.py
```

If `prometheus-client` is not installed in the environment, install the optional dependency set for the public package before running the example.

## Expected output

The script prints `Status: SUCCESS`, `Artifacts: 1`, a CSV preview, and a metrics preview containing `pfp_stage_duration_seconds` and related `pfp_*` lines.

## Files in this example

- `infra.yaml` — runtime wiring for JSONL input and `telemetry.provider: prometheus`.
- `mapping.yaml` — maps top-level JSONL keys into Unified Model keys.
- `policies.yaml` — minimal valid policy bundle with `fail_on_error` strictness.
- `stripe.product_feed-1.0.0.yaml` — local schema for the generated CSV artifact.
- `archive.noop.yaml` — noop archiver config.
- `client.noop.yaml` — noop client config.
- `input/input.jsonl` — small valid JSONL fixture.
- `expected/output.csv` — expected CSV artifact bytes.
- `run.py` — launcher that injects a dedicated Prometheus registry.

## Related documentation

- `../../config/docs/01_infra.md` — format of `infra.yaml`
- `../../config/docs/02_mapping.md` — format of `mapping.yaml`
- `../../config/docs/03_policies.md` — format of `policies.yaml`
- `../../config/docs/05_schema.md` — schema YAML structure
- `../../src/pfp_utils/telemetry/telemetry_handlers.py` — Prometheus telemetry handler implementation
