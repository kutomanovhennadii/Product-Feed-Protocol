# Example 03 — Nested JSONL Input

## What this demonstrates

This example demonstrates a JSONL payload that contains nested `product` and `inventory` objects alongside explicit top-level routing keys.
The current connector mapping layer performs exact top-level key lookup only, so the example keeps the nested objects in the fixture for realism but routes the pipeline through the mirrored top-level keys that the runtime can consume today.

The run uses `archive_type: noop` and `client_type: noop`, so the output stays in memory and the script finishes with a `SUCCESS` execution report.

## How to run

```bash
cd examples/03_jsonl_input
python run.py
```

## Expected output

The script prints `Status: SUCCESS`, `Artifacts: 1`, and then a preview of the generated CSV artifact:

```text
id,title,description,link,availability
SKU-3,Nested JSONL Example,Uses nested product and inventory objects,https://example.com/sku-3,in_stock
```

## Files in this example

- `infra.yaml` — runtime wiring for `jsonl` input, local mapping, schema, and noop publishing.
- `mapping.yaml` — routes the top-level JSONL keys that mirror the nested product payload.
- `policies.yaml` — minimal valid policy bundle with `fail_on_error` strictness.
- `stripe.product_feed-1.0.0.yaml` — local schema for the generated CSV artifact.
- `archive.noop.yaml` — noop archiver config.
- `client.noop.yaml` — noop client config.
- `input/input.jsonl` — one nested JSONL record with mirrored top-level routing fields.
- `expected/output.csv` — expected output artifact bytes.
- `run.py` — launcher using `PFPFactory().build_worker(...)`.

## Related documentation

- `../../config/docs/01_infra.md` — format of `infra.yaml`
- `../../config/docs/02_mapping.md` — current connector mapping behavior
- `../../config/docs/03_policies.md` — format of `policies.yaml`
- `../../config/docs/04_publishing.md` — noop archive/client configs
- `../../config/docs/05_schema.md` — schema YAML structure
