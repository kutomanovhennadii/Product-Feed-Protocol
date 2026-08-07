# Example 04 — Local Archive

## What this demonstrates

This example shows the same minimal JSONL pipeline as example 01, but with `archive_type: local` instead of `noop`.
The runtime writes the generated CSV artifact to a local directory and exposes the archived file path through `report.artifacts[0].metadata.location`.

The delivery client remains `noop`, so the example focuses only on local artifact persistence.

## How to run

```bash
cd examples/04_local_archive
python run.py
```

## Expected output

The script prints `Status: SUCCESS`, `Artifacts: 1`, the archived file location, and a CSV preview with one product row:

```text
id,title,description,link,availability
SKU-4,Local Archive Demo,Writes the generated artifact to disk,https://example.com/sku-4,in_stock
```

After the run, the `archive_output/` directory contains one timestamped CSV file whose bytes match `expected/output.csv`.

## Files in this example

- `infra.yaml` — runtime wiring for `jsonl` input, local schema, and local archiving.
- `mapping.yaml` — maps top-level JSON input keys into `product.*` and `inventory.*` fields.
- `policies.yaml` — minimal valid policy bundle with `fail_on_error` strictness.
- `stripe.product_feed-1.0.0.yaml` — local copy of the minimal compile-safe schema.
- `archive.local.yaml` — local archiver config pointing at `archive_output/`.
- `client.noop.yaml` — noop client config.
- `input/input.jsonl` — one JSONL record used by the example.
- `expected/output.csv` — expected CSV artifact bytes.
- `run.py` — launcher that also prints the archived file location.

## Related documentation

- `../../config/docs/01_infra.md` — format of `infra.yaml`
- `../../config/docs/02_mapping.md` — format of `mapping.yaml`
- `../../config/docs/03_policies.md` — format of `policies.yaml`
- `../../config/docs/04_publishing.md` — local archive/client configs
- `../../config/docs/05_schema.md` — schema YAML structure
