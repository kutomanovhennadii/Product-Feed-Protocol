# Examples

This file is the runnable-scenarios index in the canonical onboarding flow.

- The root `README.md` explains what PFP is and where to start.
- `../docs/api.md` explains the Python API contract and the minimum YAML bundle around it.
- `../docs/troubleshooting.md` covers the first operational failures and environment-sensitive pitfalls.
- This file helps choose the runnable scenario.
- `01_minimal_quickstart` is the shortest first run.
- `02_csv_input` is the canonical CSV-input to CSV-output end-to-end path.

## Why this directory exists

This directory is the public entry point for runnable PFP examples.
Each numbered example is self-contained: it keeps its own `README.md`, `infra.yaml`, `mapping.yaml`, `policies.yaml`, input fixtures, expected CSV output, and `run.py` launcher inside the example folder.

The examples are ordered from the smallest happy-path flow to more advanced scenarios such as Shopify realtime mapping, streaming ingestion, and Prometheus telemetry.

## Example index

| # | Directory | What it demonstrates | Typical time |
|---|---|---|---|
| 01 | `01_minimal_quickstart` | Minimal JSONL happy-path: one record in, one CSV row out, noop publishing. | ~5 min |
| 02 | `02_csv_input` | CSV input format with `connector_mapping` from flat columns into the Unified Model. | ~5 min |
| 03 | `03_jsonl_input` | JSONL input with realistic nested payload shape and top-level routing keys for mapping. | ~5 min |
| 04 | `04_local_archive` | Local archiver flow that writes the generated CSV artifact to disk. | ~5 min |
| 05 | `05_validation_report` | Mixed valid and invalid records with diagnostics and dropped invalid rows. | ~5 min |
| 06 | `06_shopify_realtime` | Shopify webhook-style payload compiled through `stripe.shopify_realtime` with local tax mapping. | ~10 min |
| 07 | `07_streaming_jsonl` | `streaming_jsonl` adapter for larger JSONL fixtures and low-memory processing. | ~5 min |
| 08 | `08_observability_prometheus` | Prometheus telemetry with a dedicated registry and printed `pfp_*` metrics. | ~10 min |

## How to run any example

From the package root:

```bash
cd examples/01_minimal_quickstart
python run.py
```

Replace `01_minimal_quickstart` with any numbered example directory from the table above.

Each `run.py` prints at least:

- `Status: SUCCESS` when the pipeline finishes successfully.
- `Artifacts: <n>` showing how many artifacts were produced.
- A short preview of the generated CSV artifact.

Some examples print extra information:

- `04_local_archive` also prints the archive location on disk.
- `05_validation_report` also prints validation diagnostics.
- `07_streaming_jsonl` also prints the processed record count.
- `08_observability_prometheus` also prints a metrics preview with `pfp_*` lines.

## How to choose an example

- Start with `01_minimal_quickstart` if you want the smallest end-to-end reference.
- Move to `02_csv_input` if you want the canonical CSV-input -> CSV-output end-to-end path.
- Move to `03_jsonl_input` if you are adapting a nested JSONL source format.
- Use `04_local_archive` if you need to inspect real artifact files on disk.
- Use `05_validation_report` if you need to understand diagnostics and invalid-row handling.
- Use `06_shopify_realtime`, `07_streaming_jsonl`, and `08_observability_prometheus` for advanced runtime features.

## Documentation map

- `../config/docs/01_infra.md` — runtime infrastructure format and path rules for `infra.yaml`.
- `../config/docs/02_mapping.md` — connector mapping structure and source-to-UM routing.
- `../config/docs/03_policies.md` — policy bundle structure and strictness settings.
- `../config/docs/04_publishing.md` — noop and local publishing configuration.
- `../config/docs/05_schema.md` — schema YAML structure and output mapping rules.
- `../config/docs/06_advanced.md` — advanced configuration patterns used by the richer examples.

## Notes

- These examples are intended to be read and run from the numbered example directories listed above.
- The minimal runnable setup always includes a small YAML bundle around `infra.yaml`; inspect `01_minimal_quickstart` and `02_csv_input` for the canonical starter layout.
- The per-example `README.md` files are the source of truth for scenario-specific input, expected output, and caveats.
- If a starter example does not behave as expected, use `../docs/troubleshooting.md` before changing the runtime wiring blindly.
- `08_observability_prometheus` may require the optional Prometheus dependency set in environments where `prometheus-client` is not already installed.
