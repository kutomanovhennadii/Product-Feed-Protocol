# schema YAML

Schema YAML defines the target artifact contract used by the producer layer.

It is referenced from `infra.yaml` via `producer.schema_file` and loaded from the built-in schema catalog under `schemas/`.

Source of truth for this document:

- `src/pfp_core/schema/{schema_contract,schema_loader,schema_refs,schema_types}.py`
- `src/pfp_core/ext/mapping/mapping_contract.py`
- `src/pfp_core/ext/validation/validation_contract.py`
- `src/pfp_core/ext/ext_types.py`
- built-in examples under `schemas/`

## What The Schema File Does

A schema YAML describes:

- schema identity and source metadata
- Unified Model input contract description
- writer/output metadata
- field mapping plan and transforms
- validation rules executed against mapped values

## Where It Is Referenced

In `infra.yaml`:

```yaml
producer:
  schema_file: ../schemas/stripe.product_feed/stripe.product_feed-1.0.0.yaml
```

## File Naming And Versioning

Current filename rules from `schema_refs.py`:

- filename must match `<protocol_id>-<schema_version>.<ext>`
- allowed extensions: `.yaml`, `.yml`, `.json`
- `protocol_id` in filename must match `[a-z0-9._]+`
- `protocol_id` in filename must not contain `-`
- `schema_version` in filename must be SemVer `MAJOR.MINOR.PATCH`

Current header consistency rule from `schema_contract.py`:

- `header.protocol_id` and `header.schema_version` must match the filename reference when an expected ref is available

## Actual Top-Level Shape

Required top-level sections enforced by `validate_schema_doc_format()`:

- `header`
- `input`
- `output`
- `mapping`
- `validation`

Common additional section seen in built-in schemas:

- `modes`

Important current nuance:

- built-in schemas include `modes`, but the minimal format validator does not currently require it

## `header`

Required fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `protocol_id` | `str` | yes | Canonical protocol identifier. |
| `schema_version` | `str` | yes | Schema version string. |
| `artifact_profile` | `str` | yes | Artifact profile used by downstream runtime behavior. |
| `title` | `str` | yes | Human-readable schema title. |
| `source_protocol` | `object` | yes | Metadata describing the upstream protocol/source. |

Required `header.source_protocol` fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `provider` | `str` | yes | Source provider name. |
| `url` | `str` | yes | Reference URL for the source protocol/spec. |
| `revision` | `str` | yes | Revision or snapshot identifier. |
| `retrieved_at` | `str` | yes | Capture timestamp for the referenced source protocol. |

## `input`

Required field:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `um_contract` | `str` | yes | Human-readable description of the Unified Model input contract. |

## `modes`

Built-in schemas commonly include a `modes` section, for example presence semantics by mode.

Observed example structure:

```yaml
modes:
  presence_semantics:
    default: omit_missing
    per_mode:
      FULL: omit_missing
      DIFF: omit_missing
      DELETE: omit_missing
```

Important current nuance:

- `modes` is part of current built-in examples
- but minimal format validation does not enforce any specific structure for `modes`

## `output`

Required fields enforced by format validation:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `writer_id` | `str` | yes | Writer module identifier. |
| `artifact` | `object` | yes | Artifact metadata block. |

Required `output.artifact` fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `file_ext` | `str` | yes | File extension with dot. |
| `content_type` | `str` | yes | MIME type of the produced artifact. |

Observed optional fields in built-in schemas:

- `output_kind`
- `writer_config`
- `artifact.file_extension`
- `artifact.encoding`

Important current nuance:

- built-in examples use both `output.output_kind` and `mapping.output_kind`
- the format validator requires only `mapping.output_kind`
- semantic consistency between the two is not currently enforced by `schema_contract.py`

## `mapping`

Required field enforced by format validation:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `output_kind` | `str` | yes | Mapping/output type identifier. |

Common built-in structure:

```yaml
mapping:
  output_kind: csv_row
  delete_tombstone:
    enabled: true
    flag_path: delete
    id_field: id
  presence:
    default: omit_missing
    per_mode:
      DELETE: error_if_missing
  output_order:
    - id
    - title
  fields:
    id:
      source:
        path: item_id
        required: true
      transforms:
        - op: to_str
        - op: trim
```

### `mapping.fields`

Each entry under `mapping.fields` describes one output field.

Observed structure:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `source` | `object` | yes in examples | Source path and source-level required flag. |
| `transforms` | `list[object]` | no | Ordered mapping operations. |
| `presence` | `object` | no | Per-mode presence semantics. |

Observed `source` structure:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `path` | `str` | yes in examples | Dot-path into the Unified Model input item. |
| `required` | `bool` | no | Whether the source path must be present before transforms. |

Observed `presence` structure:

```yaml
presence:
  per_mode:
    DELETE: error_if_missing
```

Important current nuance:

- built-in examples use presence mode names like `FULL`, `DIFF`, `DELETE`
- minimal schema format validation does not enforce the allowed set of mode names here

### `delete_tombstone`

Observed structure:

| Field | Type | Meaning |
|---|---|---|
| `enabled` | `bool` | Whether tombstone emission is active. |
| `flag_path` | `str` | Source path used as deletion flag. |
| `id_field` | `str` | Output field used as delete identifier. |

### `output_order`

Observed as an ordered list of output field names, primarily for writer-friendly deterministic ordering.

## `transforms`

Each transform entry has the form:

```yaml
- op: to_str
  args:
    max_length: 100
```

Fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `op` | `str` | yes | Mapping operation id from `MAPPING_OP_REGISTRY`. |
| `args` | `object` | no | Operation-specific argument block. |

### Available Mapping Operations

Current sorted `MAPPING_OP_REGISTRY` ids:

| Op ID | Meaning |
|---|---|
| `bool_to_availability` | Convert boolean to availability enum. |
| `default_value` | Substitute default value when missing. |
| `emit_if_present` | Emit typed value/null/omit by presence. |
| `emit_null_if_missing` | Force NULL emission when missing. |
| `format_date` | Format date/datetime to string. |
| `format_datetime_utc` | Format datetime as UTC string. |
| `format_money` | Format value as money representation. |
| `format_price` | Combine amount and currency into price string. |
| `format_shipping` | Format shipping structure into string. |
| `get_path` | Extract nested value by dot-path. |
| `int_to_availability` | Convert quantity integer to availability enum. |
| `lower` | Lowercase string value. |
| `map_tax_code` | Resolve tax code from lookup table. |
| `normalize_whitespace` | Collapse repeated whitespace and trim. |
| `omit_if_missing` | Force OMIT emission when missing. |
| `parse_date` | Parse string/date into date value. |
| `regex_extract` | Extract regex capture from string. |
| `round_decimal` | Round numeric value to N decimals. |
| `strip_html` | Remove HTML tags and decode entities. |
| `strip_suffix` | Remove suffix by delimiter. |
| `to_bool` | Convert value to boolean. |
| `to_decimal` | Convert value to Decimal. |
| `to_int` | Convert value to integer. |
| `to_str` | Convert value to string. |
| `trim` | Trim leading and trailing whitespace. |
| `truncate` | Limit string length. |
| `upper` | Uppercase string value. |

## `validation`

Required field enforced by format validation:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `rules` | `list` | yes | Ordered list of validation rule entries. |

Observed rule shape:

```yaml
- id: stripe.title.required
  applies_to:
    field: title
  module_id: required
  config: {}
  on_fail:
    code: STRIPE_TITLE_REQUIRED
    message: title is required
    severity_hint: ERROR
```

Observed rule fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | `str` | yes in examples | Stable rule identifier. |
| `applies_to` | `object` | yes in examples | Target field selector block. |
| `module_id` | `str` | yes in examples | Validation module id from `VALIDATION_MODULE_REGISTRY`. |
| `config` | `object` | yes in examples | Module-specific configuration. |
| `on_fail` | `object` | yes in examples | Diagnostic emission metadata. |

Observed optional profile filters in code:

- `artifact_profile`
- `artifact_profiles`

These are used to restrict rule execution to one or more artifact profiles.

### Available Validation Modules

Current sorted `VALIDATION_MODULE_REGISTRY` ids:

| Module ID | Meaning |
|---|---|
| `enum` | Check value is in allowed list. |
| `range` | Check numeric value is within bounds. |
| `required` | Check value is present and not null. |
| `required_if_profile` | Require value only for specific artifact profiles. |
| `type` | Validate runtime value type. |

## ProducerContext And `map_tax_code`

Most mapping operations are pure data-to-data transforms.

One important exception is `map_tax_code`:

- its prepare step reads lookup data from `ProducerContext`
- current `ProducerContext` carries `tax_mapping`
- that lookup is populated from `infra.yaml -> producer.tax_mapping_file`

So if a schema uses `map_tax_code`, the matching infra configuration must provide `tax_mapping_file`.

## Built-In Schema Loading

The built-in library schema catalog is loaded from the repository `schemas/` directory through `load_builtin_schema_registry()`.

High-level flow:

1. locate built-in schemas root
2. load manifest
3. scan `*.yaml` schema files in deterministic order
4. parse schema text
5. validate schema contract
6. register schema by `(protocol_id, schema_version)`

This means users typically reference built-in schemas by path rather than inventing ad hoc file locations.

## Minimal Example

```yaml
header:
  protocol_id: "stripe.product_feed"
  schema_version: "1.0.0"
  artifact_profile: "catalog_delta"
  title: "Stripe Product Feed"
  source_protocol:
    provider: "stripe"
    url: "N/A"
    revision: "snapshot"
    retrieved_at: "2026-02-16"

input:
  um_contract: "Unified Model items as dict-like objects."

output:
  writer_id: "csv"
  artifact:
    file_ext: ".csv"
    content_type: "text/csv"

mapping:
  output_kind: "csv_row"
  fields:
    id:
      source:
        path: "item_id"
        required: true
      transforms:
        - op: "to_str"

validation:
  rules: []
```

For living examples, see built-in schemas under `schemas/`, for example:

- [schemas/stripe.product_feed/stripe.product_feed-1.0.0.yaml](../../schemas/stripe.product_feed/stripe.product_feed-1.0.0.yaml)
- [schemas/stripe.shopify_realtime/stripe.shopify_realtime-1.0.0.yaml](../../schemas/stripe.shopify_realtime/stripe.shopify_realtime-1.0.0.yaml)

## Related Documents

- `01_infra.md` — `producer.schema_file` reference from `infra.yaml`
- `06_advanced.md` — tax mapping JSON used by `map_tax_code`
