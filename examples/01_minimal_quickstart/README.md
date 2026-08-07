# Example 01 — Minimal Quickstart

This example is the shortest first run in the canonical onboarding flow.
Use it after the root `README.md` when you want the smallest runnable path before moving to the API contract in `../../docs/api.md`, the failure guide in `../../docs/troubleshooting.md`, or richer example scenarios.

## What this demonstrates

This is the smallest happy-path example for the public PFP runtime.
It takes one JSONL record, maps it into the Unified Model, compiles it through the built-in `stripe.product_feed` schema, and produces one CSV row.

The example uses `archive_type: noop` and `client_type: noop`, so the run finishes with an in-memory artifact and a `SUCCESS` execution report.

## How to run

```bash
cd examples/01_minimal_quickstart
python run.py
```

## Expected output

The script prints `Status: SUCCESS`, `Artifacts: 1`, and then a CSV preview with one header row and one product row:

```text
id,title,description,link,availability
SKU-1,Hello,World,https://example.com/sku-1,in_stock
```

## Files in this example

- The YAML/config bundle in this directory is the minimal runnable footprint around the Python API.
- `infra.yaml` — minimal runtime wiring for `jsonl` input, built-in `stripe.product_feed` schema, and noop publishing.
- `mapping.yaml` — maps top-level JSON input keys into `product.*` and `inventory.*` fields.
- `policies.yaml` — minimal valid policy bundle with `fail_on_error` strictness.
- `stripe.product_feed-1.0.0.yaml` — local copy of the built-in `stripe.product_feed` schema to keep the example self-contained.
- `archive.noop.yaml` — noop archiver config.
- `client.noop.yaml` — noop client config.
- `input/input.jsonl` — one input record used by the example.
- `expected/output.csv` — expected CSV artifact for smoke verification.
- `run.py` — launcher using `PFPFactory().build_worker(...)`.

## Related documentation

- `../../docs/api.md` — current Python API contract and the role of the YAML bundle
- `../../docs/troubleshooting.md` — first-run operational failures and path/cwd troubleshooting
- `../../config/docs/01_infra.md` — format of `infra.yaml`
- `../../config/docs/02_mapping.md` — format of `mapping.yaml`
- `../../config/docs/03_policies.md` — format of `policies.yaml`
- `../../config/docs/04_publishing.md` — noop archive/client configs
- `../../config/docs/05_schema.md` — schema YAML structure
