# Example 05 — Validation Report

## What this demonstrates

This example shows how the runtime surfaces validation diagnostics when a mixed fixture contains both a valid and an invalid record.
The policy bundle uses `drop_invalid`, so the invalid item is removed from the final artifact while the valid item is still emitted and the execution report remains runnable as a public example.

The script prints a short diagnostics summary from `report.validation_report` so you can see the emitted codes and severities directly.

## How to run

```bash
cd examples/05_validation_report
python run.py
```

## Expected output

The script prints `Status: SUCCESS`, `Artifacts: 1`, a diagnostics summary containing `STRIPE_TITLE_REQUIRED`, and then a CSV preview with only the valid product row:

```text
id,title,description,link,availability
SKU-5A,Valid Product,Included in the artifact,https://example.com/sku-5a,in_stock
```

## Files in this example

- `infra.yaml` — runtime wiring for `jsonl` input, local mapping, schema, and noop publishing.
- `mapping.yaml` — maps top-level JSON input keys into `product.*` and `inventory.*` fields while leaving `title` optional at the mapping layer.
- `policies.yaml` — uses `drop_invalid` strictness so invalid records produce diagnostics and are removed from the output.
- `stripe.product_feed-1.0.0.yaml` — local schema that enforces `title` as required.
- `archive.noop.yaml` — noop archiver config.
- `client.noop.yaml` — noop client config.
- `input/input.jsonl` — one valid and one invalid JSONL record.
- `expected/output.csv` — expected CSV artifact with only the valid row.
- `run.py` — launcher that prints diagnostics and artifact preview.

## Related documentation

- `../../config/docs/01_infra.md` — format of `infra.yaml`
- `../../config/docs/02_mapping.md` — format of `mapping.yaml`
- `../../config/docs/03_policies.md` — strictness strategies and diagnostics behavior
- `../../config/docs/04_publishing.md` — noop archive/client configs
- `../../config/docs/05_schema.md` — schema YAML structure
