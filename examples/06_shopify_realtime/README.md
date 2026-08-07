# Example 06 — Shopify Realtime

## What this demonstrates

This example shows a realistic Shopify webhook-style payload compiled through the local `stripe.shopify_realtime` schema.
It demonstrates the full advanced bundle in one folder: `infra.yaml`, Shopify-specific `mapping.yaml`, `policies.yaml`, `tax_mapping_file`, the local schema copy, and a JSON fixture that produces a full catalog row.

The pipeline runs with `drop_invalid` strictness and local tax-code lookup, so it stays self-contained and reproducible without any external services.

## How to run

```bash
cd examples/06_shopify_realtime
python run.py
```

## Expected output

The script prints `Status: SUCCESS`, `Artifacts: 1`, and a CSV preview with realtime Shopify fields such as `brand`, `price`, `shipping`, and `stripe_product_tax_code`.

The generated artifact contains one row whose tax code is resolved from `shopify_to_stripe_ptc.json`.

## Files in this example

- `infra.yaml` — runtime wiring for JSON input, Shopify mapping, policy bundle, and tax mapping.
- `mapping.yaml` — maps Shopify realtime payload keys into Unified Model namespaces.
- `policies.yaml` — uses `drop_invalid` strictness and `SKIP_ITEM` fault isolation.
- `shopify_to_stripe_ptc.json` — local lookup table used by `map_tax_code`.
- `stripe.shopify_realtime-1.0.0.yaml` — local copy of the Shopify realtime schema.
- `archive.noop.yaml` — noop archiver config.
- `client.noop.yaml` — noop client config.
- `input/input.json` — one Shopify-style JSON array payload.
- `expected/output.csv` — expected CSV artifact bytes.
- `run.py` — launcher using `PFPFactory().build_worker(...)`.

## Related documentation

- `../../config/docs/01_infra.md` — format of `infra.yaml`
- `../../config/docs/02_mapping.md` — format of `mapping.yaml`
- `../../config/docs/03_policies.md` — format of `policies.yaml`
- `../../config/docs/04_publishing.md` — noop archive/client configs
- `../../config/docs/05_schema.md` — schema YAML structure
- `../../config/docs/06_advanced.md` — advanced bundle examples
