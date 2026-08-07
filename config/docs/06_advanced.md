# Advanced Config Topics

This document covers two advanced configuration surfaces that are referenced by the main YAML files but live outside the core `infra.yaml` / `mapping.yaml` / `policies.yaml` trio:

- `producer.tax_mapping_file`
- per-scenario bundles under `config/shopify_*/`

Source of truth for this document:

- `src/pfp_core/ext/mapping/module_mapping_map_tax_code.py`
- real bundle files under `config/shopify_*`

## Part A. `tax_mapping_file`

`tax_mapping_file` is an optional JSON file referenced from `infra.yaml`:

```yaml
producer:
  schema_file: ../../schemas/stripe.shopify_realtime/stripe.shopify_realtime-1.0.0.yaml
  policy_file: ./policies_shopify_realtime.yaml
  tax_mapping_file: ../../config/tax_mappings/shopify_to_stripe_ptc.json
```

It matters only when the loaded schema uses mapping op `map_tax_code`.

If a schema uses `map_tax_code` and producer context does not contain loaded tax mapping data, schema compilation fails with:

- `map_tax_code requires tax_mapping in producer context`

## JSON Shape

Current JSON structure used by `map_tax_code`:

| Field | Type | Required | Default in op | Meaning |
|---|---|---|---|---|
| `mappings` | `object[str, str]` | yes in practice | `{}` | Category-prefix lookup table. Keys are taxonomy prefixes, values are Stripe Product Tax Codes. |
| `default_taxable` | `str` | yes in practice | `txcd_99999999` | Fallback code when item is taxable and no override/category match exists. |
| `default_exempt` | `str` | yes in practice | `txcd_00000000` | Fallback code when item is explicitly non-taxable and no override/category match exists. |

Minimal valid example for human authors:

```json
{
  "mappings": {
    "Animals & Pet Supplies > Pet Supplies > Dog Food": "txcd_40040000"
  },
  "default_taxable": "txcd_99999999",
  "default_exempt": "txcd_00000000"
}
```

Living example:

- [config/tax_mappings/shopify_to_stripe_ptc.json](../tax_mappings/shopify_to_stripe_ptc.json)

That real-world file contains a large `mappings` table plus:

- `default_taxable: txcd_99999999`
- `default_exempt: txcd_00000000`

## Resolution Priority Chain

Current `map_tax_code` runtime behavior is exactly:

1. `tax_code_override` passthrough.
2. `tax_category` longest-prefix lookup in `mappings`.
3. `taxable` fallback to `default_exempt` or `default_taxable`.

The implementation sorts mapping keys by descending length before matching, so a more specific category prefix wins over a broad parent prefix.

### Priority 1. Override

By default the op reads field `tax_code_override` from the source value.

If it exists, is a non-empty string, and is not blank after trim, the op returns it immediately without consulting `mappings`.

### Priority 2. Category Lookup

By default the op reads field `tax_category` from the source value.

If it is a non-empty string, runtime checks `mappings` using longest-prefix match:

- every mapping key is treated as a prefix
- the longest matching prefix wins
- the mapped Stripe tax code is returned

This is why the JSON table can contain both broad taxonomy branches and more specific leaf overrides.

### Priority 3. Taxable Fallback

If no override and no category match are found, runtime inspects field `taxable`.

Current falsy handling for `default_exempt`:

- boolean `false`
- string `"false"`
- string `"no"`
- string `"0"`
- integer `0`

If one of those values is present, result is `default_exempt`.

Otherwise result is `default_taxable`.

## Optional Op Args

The JSON structure itself is fixed to `mappings` plus defaults, but schema authors can change which source keys are read by `map_tax_code`.

Current optional args on the schema op:

| Arg | Default | Meaning |
|---|---|---|
| `override_key` | `tax_code_override` | Source key for explicit Stripe tax-code override. |
| `category_key` | `tax_category` | Source key for category-prefix lookup. |
| `taxable_key` | `taxable` | Source key for taxable fallback logic. |

Those args live in schema YAML, not in the JSON mapping file.

## When To Use `tax_mapping_file`

Use `tax_mapping_file` when:

- schema contains `map_tax_code`
- source items carry category data but not final Stripe tax codes
- you want central lookup data shared across multiple scenario bundles

Do not add it just because the field exists in `ProducerConfig`. Several real scenario bundles do not need tax-code mapping and omit it.

## Part B. Per-Scenario Bundles

Per-scenario bundles are ready-made config folders under `config/shopify_*`.

Current directories include:

- `config/shopify_realtime/`
- `config/shopify_bulk/`
- `config/shopify_inventory/`
- `config/shopify_delete/`

Each bundle keeps scenario-local YAML files together and points to shared assets via relative paths.

## Typical Bundle Contents

Each current Shopify bundle contains three local files:

- `infra_<scenario>.yaml`
- `mapping_<scenario>.yaml`
- `policies_<scenario>.yaml`

Example bundle:

- [config/shopify_realtime/infra_shopify_realtime.yaml](../shopify_realtime/infra_shopify_realtime.yaml)
- [config/shopify_realtime/mapping_shopify_realtime.yaml](../shopify_realtime/mapping_shopify_realtime.yaml)
- [config/shopify_realtime/policies_shopify_realtime.yaml](../shopify_realtime/policies_shopify_realtime.yaml)

## How Bundle References Work

The scenario-local `infra_*.yaml` file is the hub. It points to:

- local mapping YAML in the same bundle directory
- local policies YAML in the same bundle directory
- shared schema YAML under `schemas/`
- shared archive/client YAML under `config/archive/` and `config/clients/`
- optional shared tax mapping JSON under `config/tax_mappings/`

From `config/shopify_realtime/infra_shopify_realtime.yaml`:

```yaml
input:
  format: json
  config:
    connector_mapping: ./mapping_shopify_realtime.yaml

producer:
  schema_file: ../../schemas/stripe.shopify_realtime/stripe.shopify_realtime-1.0.0.yaml
  policy_file: ./policies_shopify_realtime.yaml
  tax_mapping_file: ../../config/tax_mappings/shopify_to_stripe_ptc.json

output:
  archive_type: noop
  archive_config: ../archive/noop.yaml
  client_type: noop
  client_config: ../clients/noop.yaml
```

So the bundle pattern is:

- keep scenario-specific mapping and policy choices local
- reuse shared schemas and shared publishing configs by path
- optionally reuse shared tax-mapping data when the schema needs it

## Real Bundle Differences

Current real bundles are similar, but not identical:

| Bundle | Input format | Tax mapping | Shared schema |
|---|---|---|---|
| `shopify_realtime` | `json` | yes | `schemas/stripe.shopify_realtime/...` |
| `shopify_bulk` | `jsonl` | yes | `schemas/stripe.shopify_bulk/...` |
| `shopify_inventory` | `json` | no | `schemas/stripe.shopify_inventory/...` |
| `shopify_delete` | `json` | no | `schemas/stripe.shopify_delete/...` |

The presence or absence of `tax_mapping_file` is therefore scenario-driven, not mandatory for every bundle.

## Recommended Reading Order For Bundles

To understand a bundle, read files in this order:

1. `infra_<scenario>.yaml` — wiring and file references.
2. `mapping_<scenario>.yaml` — how source fields map into the Unified Model.
3. `policies_<scenario>.yaml` — scenario policy overrides.
4. shared schema YAML under `schemas/` — output contract and transforms.
5. optional shared tax mapping JSON if schema uses `map_tax_code`.

## Related Documents

- `01_infra.md` — root wiring for `producer.tax_mapping_file` and per-scenario infra files
- `02_mapping.md` — connector mapping YAML referenced from bundle infra files
- `03_policies.md` — policy YAML referenced from bundle infra files
- `05_schema.md` — schema YAML and `map_tax_code` usage from producer context
