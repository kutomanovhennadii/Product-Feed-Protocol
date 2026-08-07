# Example 02 — CSV Input

This example is the canonical CSV-input to CSV-output end-to-end path in the onboarding flow.
Use it after `01_minimal_quickstart` when you want the clearest runnable reference for a flat source format and a full artifact-producing configuration bundle.

## What this demonstrates

This example shows the same minimal happy-path pipeline as example 01, but with a CSV payload instead of JSONL.
The connector mapping renames CSV column headers into Unified Model keys before the schema compiler emits the CSV artifact.

The run uses `archive_type: noop` and `client_type: noop`, so the output stays in memory and the script finishes with a `SUCCESS` execution report.

## How to run

```bash
cd examples/02_csv_input
python run.py
```

## Expected output

The script prints `Status: SUCCESS`, `Artifacts: 1`, and then a preview of the generated CSV artifact:

```text
id,title,description,link,availability
SKU-2,CSV Starter,From CSV input,https://example.com/sku-2,in_stock
```

## Files in this example

- The YAML/config bundle in this directory is the canonical starter layout for a CSV-input e2e scenario.
- `infra.yaml` — runtime wiring for `csv` input, local mapping, schema, and noop publishing.
- `mapping.yaml` — maps CSV column names into Unified Model keys.
- `policies.yaml` — minimal valid policy bundle with `fail_on_error` strictness.
- `stripe.product_feed-1.0.0.yaml` — local copy of the minimal compile-safe schema.
- `archive.noop.yaml` — noop archiver config.
- `client.noop.yaml` — noop client config.
- `input/input.csv` — one CSV row with source column headers.
- `expected/output.csv` — expected output artifact bytes.
- `run.py` — launcher using `PFPFactory().build_worker(...)`.

## Related documentation

- `../../docs/api.md` — current Python API contract and the role of the YAML bundle
- `../../docs/troubleshooting.md` — first-run operational failures and path/cwd troubleshooting
- `../../config/docs/01_infra.md` — format of `infra.yaml`
- `../../config/docs/02_mapping.md` — format of `mapping.yaml`
- `../../config/docs/03_policies.md` — format of `policies.yaml`
- `../../config/docs/04_publishing.md` — noop archive/client configs
- `../../config/docs/05_schema.md` — schema YAML structure
