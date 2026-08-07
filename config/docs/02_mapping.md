# mapping.yaml

`mapping.yaml` defines how raw connector records are renamed into UM-space keys before they are passed further into the runtime pipeline.

This document reflects the actual contract implemented by:

- `src/pfp_runtime/connectors/connector_mapping/connector_mapping_loader.py`
- `src/pfp_runtime/connectors/connector_mapping/connector_mapping_config.py`
- `src/pfp_runtime/connectors/connector_mapping/connector_mapping_validator.py`
- `src/pfp_runtime/connectors/connector_mapping/connector_mapper.py`

## Where It Is Referenced

The mapping file path is configured in `infra.yaml` via `input.config.connector_mapping`:

```yaml
input:
  format: csv
  config:
    connector_mapping: ./mapping.yaml
```

Notes:

- The correct field name is `connector_mapping`, not `mapping`.
- At `InfraConfig` model level this field is optional, but the runtime connector builder requires it when constructing the standard source-connector pipeline.
- Path normalization for `connector_mapping` is described in `01_infra.md`.

## File Shape

```yaml
mappings:
  - source: "<raw field name>"
    target: "<um-space key>"
    required: true | false

continue_on_error: true | false
```

## Root Fields

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `mappings` | `list[object]` | yes | — | Must be a non-empty list. |
| `continue_on_error` | `bool` | no | `true` | Controls what happens when a required source field is missing. |

The YAML root must be a mapping. Unknown extra top-level keys are currently tolerated by the validator, but only `mappings` and `continue_on_error` participate in the typed runtime contract.

## `mappings[]`

Each item in `mappings` becomes one `ConnectorFieldMapping` entry.

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `source` | `str` | yes | — | Must be a non-empty string. The mapper treats it as an exact raw record key. |
| `target` | `str` | yes | — | Must be a non-empty string. The mapper uses it as the output UM-space key exactly as provided. |
| `required` | `bool` | no | `false` | If `true`, a missing source field becomes a record-level mapping failure. |

## Meaning Of `source`

`source` is an exact key lookup in the raw record produced by the chosen adapter.

Examples:

- CSV adapters: column name from the header row
- JSON / JSONL adapters: top-level key of the record object
- rows adapter: key already present in the in-memory dict

Important current limitation:

- the mapping layer does not parse source prefixes such as `column:`, `json:`, or other selector mini-languages
- the mapper checks only `if source_key in record`
- nested extraction, coercion, or transformation is not performed here

In other words, `source` must match the raw field name exactly.

## Meaning Of `target`

`target` is a UM-space key written into the output mapping exactly as a string.

Examples:

- `product.item_id`
- `product.title`
- `offer.price.amount`
- `inventory.inventory_quantity`

Important current limitation:

- the mapping validator only checks that `target` is a non-empty string
- the mapping layer does not validate a closed catalog of allowed target paths
- the mapper does not expand the dot path into nested objects; it emits a flat dict keyed by the target string

This means `target` should be treated as a contract with downstream producer/schema logic, not as something enforced by the connector mapping validator itself.

## `required` And `continue_on_error`

When a mapping item has `required: true`, the source key must be present in the incoming record.

Behavior depends on `continue_on_error`:

| `continue_on_error` | Behavior when a required source field is missing |
|---|---|
| `true` | Record is skipped and a `WARNING` is logged. Processing continues with the next record. |
| `false` | `ConnectorMappingValidationError` is raised and stream processing stops. |

When `required` is omitted, it defaults to `false`.

When a source field is optional and absent:

- no warning is emitted
- no output key is created for that mapping

## Runtime Behavior

The full runtime path is:

1. `load_yaml(mapping_path)`
2. `validate_mapping(raw_dict)`
3. `ConnectorMapper(config, log_pipeline=...)`
4. `apply_stream(records)`

What `ConnectorMapper` actually does per record:

- iterates over compiled `source -> target` rules
- copies matching values unchanged from raw record to output dict
- silently drops unmapped source fields
- enforces `required` according to `continue_on_error`

What it does not do:

- no type coercion
- no string-to-number conversion
- no nested source extraction
- no transforms
- no validation that target path belongs to a supported UM catalog

## Validation Rules

Validation currently enforced by `validate_mapping()`:

- YAML root must contain key `mappings`
- `mappings` must be a non-empty list
- every `mappings[i]` must be an object
- `mappings[i].source` must be a non-empty string
- `mappings[i].target` must be a non-empty string
- `mappings[i].required`, when present, must be a bool
- `continue_on_error`, when present, must be a bool

Validation currently not enforced:

- duplicate `source` keys
- duplicate `target` keys
- unknown extra keys inside `mappings[i]`
- target-path membership in a schema-defined catalog

One important runtime consequence of duplicate `source` keys:

- `ConnectorMapper` compiles rules into a dict `{m.source: m.target for m in config.mappings}`
- if the same `source` appears multiple times, the later rule wins for routing

Avoid duplicate `source` entries unless that overwrite behavior is intentional.

## Examples

### Minimal Example

```yaml
mappings:
  - source: "sku"
    target: "product.item_id"
    required: true
  - source: "name"
    target: "product.title"
    required: true

continue_on_error: true
```

### Typical Catalog Example

```yaml
mappings:
  - source: "sku"
    target: "product.item_id"
    required: true
  - source: "name"
    target: "product.title"
    required: true
  - source: "description"
    target: "product.description"
  - source: "url"
    target: "product.url"
  - source: "price"
    target: "offer.price.amount"
  - source: "currency"
    target: "offer.price.currency"
  - source: "availability"
    target: "inventory.availability"

continue_on_error: true
```

### Multi-Source Example

```yaml
mappings:
  - source: "id"
    target: "product.item_id"
    required: true
  - source: "title"
    target: "product.title"
    required: true
  - source: "vendor"
    target: "product.brand"
  - source: "inventoryQuantity"
    target: "inventory.inventory_quantity"
  - source: "compareAtPrice"
    target: "offer.sale_price"

continue_on_error: true
```

## Practical Guidance

- Keep `source` aligned with real adapter output keys, not with UI labels or guessed field names.
- Use `required: true` only for fields that must exist before downstream schema/policy processing can make sense.
- Treat target paths as downstream contract keys; if a path is misspelled, the mapping layer itself will not catch it.
- Prefer one `source` key per rule. Repeating the same source key is technically possible but easy to misread.

## Related Documents

- `01_infra.md` — how `connector_mapping` is referenced from `infra.yaml`
- `03_policies.md` — policy layer that runs after connector mapping
- `05_schema.md` — downstream schema contract that gives meaning to UM-space target keys