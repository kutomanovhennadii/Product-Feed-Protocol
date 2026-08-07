# Example 07 — Streaming JSONL

## What this demonstrates

This example demonstrates the `streaming_jsonl` adapter on a larger JSONL fixture.
The runtime consumes the input as a text stream, processing one line at a time instead of materialising the full file in memory.

Because the current shell worker contract accepts in-memory bytes, this example uses the compiled manifest and `PipelineRunner` directly so it can pass an open text stream to the adapter.

## How to run

```bash
cd examples/07_streaming_jsonl
python run.py
```

## Expected output

The script prints `Status: SUCCESS`, `Artifacts: 1`, the processed record count, and a CSV preview.

The output artifact contains 50 product rows compiled from the streamed JSONL input.

## Files in this example

- `infra.yaml` — runtime wiring for `streaming_jsonl` input and noop publishing.
- `mapping.yaml` — maps top-level JSONL keys into Unified Model keys.
- `policies.yaml` — minimal valid policy bundle with `fail_on_error` strictness.
- `stripe.product_feed-1.0.0.yaml` — local schema for the generated CSV artifact.
- `archive.noop.yaml` — noop archiver config.
- `client.noop.yaml` — noop client config.
- `input/input.jsonl` — larger JSONL fixture with 50 records.
- `expected/output.csv` — expected CSV artifact bytes.
- `run.py` — launcher using `build_pipeline_manifest(...)` and `PipelineRunner`.

## Related documentation

- `../../config/docs/01_infra.md` — format of `infra.yaml`
- `../../config/docs/02_mapping.md` — format of `mapping.yaml`
- `../../config/docs/03_policies.md` — format of `policies.yaml`
- `../../config/docs/04_publishing.md` — noop archive/client configs
- `../../config/docs/05_schema.md` — schema YAML structure
- `../../src/pfp_runtime/connectors/connectors_registry.md` — streaming adapter contract
