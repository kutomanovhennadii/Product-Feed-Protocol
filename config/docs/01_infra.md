# infra.yaml

`infra.yaml` is the root runtime configuration file for a pipeline run. It wires together four concerns:

- input ingestion
- producer assembly
- artifact publishing
- runtime observability

This document is the source-of-truth guide for the canonical config-layer contract implemented by `InfraConfig` and related models in `src/pfp_runtime/config/infra_models.py`.

## Top-Level Shape

```yaml
input:
  format: <connector-format>
  config:
    connector_mapping: <optional path>

producer:
  schema_file: <path to schema yaml>
  policy_file: <path to policies yaml>
  tax_mapping_file: <optional path to tax mapping json>

output:
  archive_type: <archiver token>
  archive_config: <path to archiver yaml>
  client_type: <client token>
  client_config: <path to client yaml>

observability:  # optional
  log_format: TEXT | JSON
  labels:
    <key>: <value>
  logging:
    level: INFO
    flood_control_config: {}
  telemetry:
    provider: none | prometheus
```

## Root Fields

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `input` | `InputConfig` | yes | — | Required object. Unknown fields are rejected. |
| `producer` | `ProducerConfig` | yes | — | Required object. Unknown fields are rejected. |
| `output` | `OutputConfig` | yes | — | Required object. Unknown fields are rejected. |
| `observability` | `ObservabilityConfig \| null` | no | `null` | Optional object. When omitted, runtime observability uses component defaults. |

The root model uses `extra="forbid"`, so any undocumented top-level field is invalid.

## `input`

The `input` section declares how raw records are ingested.

### Fields

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `format` | `str` | yes | — | Trimmed and lowercased. Must be non-empty at model layer. Semantic validation then checks that the token exists in `connectors_registry.json`. |
| `config` | `InputSourceConfig` | yes | — | Required object. Unknown fields are rejected. |

### `input.format` values

Current active connector tokens from `src/pfp_runtime/connectors/connectors_registry.json`:

| Value | Adapter | Notes |
|---|---|---|
| `csv` | `CsvAdapter` | Eager CSV input. |
| `json` | `JsonAdapter` | Eager JSON input. |
| `jsonl` | `JsonlAdapter` | Eager JSON Lines input. |
| `rows` | `RowsAdapter` | In-memory row list input. |
| `streaming_csv` | `StreamingCsvAdapter` | Streaming CSV input. |
| `streaming_json` | `StreamingJsonAdapter` | Streaming JSON input. |
| `streaming_jsonl` | `StreamingJsonlAdapter` | Streaming JSON Lines input. |

### `input.config`

`InputSourceConfig` currently has one field:

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `connector_mapping` | `str \| null` | no | `null` | Trimmed when provided. Blank string is rejected. During normalization, relative paths are resolved against the directory of `infra.yaml`. |

Notes:

- `input.config` itself is required.
- `connector_mapping` is optional at the model layer.
- Mapping file structure is documented separately in `02_mapping.md`.

## `producer`

The `producer` section points to assembly-time inputs used by the schema/policy pipeline.

### Fields

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `schema_file` | `str` | yes | — | Trimmed at model layer. Blank string is rejected. Semantic validation requires a `.yaml` or `.yml` suffix and, when loaded through `InfraProvider`, an existing file. |
| `policy_file` | `str` | yes | — | Trimmed at model layer. Blank string is rejected. Semantic validation requires a `.yaml` or `.yml` suffix and, when loaded through `InfraProvider`, an existing file. |
| `tax_mapping_file` | `str \| null` | no | `null` | Trimmed when provided. Blank string is rejected. During normalization, relative paths use the same infra-dir then project-root fallback strategy as other producer file references. |

Notes:

- `ProducerConfig` uses `extra="forbid"`.
- `tax_mapping_file` is optional, but it is the supported way to enable tax-code lookup features in producer mapping logic.
- Tax mapping JSON structure is documented separately in `06_advanced.md`.

## `output`

The `output` section selects the publishing implementation and points to the corresponding IaC YAML files.

### Fields

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `archive_type` | `str` | yes | — | Trimmed and lowercased. Blank string is rejected. |
| `archive_config` | `str` | yes | — | Trimmed at model layer. Blank string is rejected. Semantic validation requires a `.yaml` or `.yml` suffix. During normalization, the path is resolved to an absolute path. |
| `client_type` | `str` | yes | — | Trimmed and lowercased. Blank string is rejected. |
| `client_config` | `str` | yes | — | Trimmed at model layer. Blank string is rejected. Semantic validation requires a `.yaml` or `.yml` suffix. During normalization, the path is resolved to an absolute path. |

Current publishing tokens used by runtime builders:

### `output.archive_type`

| Value | Meaning |
|---|---|
| `local` | Local filesystem archive copy. |
| `s3` | AWS S3 multipart archive. |
| `s3_compat` | S3-compatible object storage archive. |
| `noop` | Explicit no-op archive. |

### `output.client_type`

| Value | Meaning |
|---|---|
| `http` | Buffered HTTP POST delivery. |
| `http_streaming` | Streaming HTTP delivery using the same IaC schema as `http`. |
| `sftp` | SFTP delivery. |
| `noop` | Explicit no-op delivery. |

Notes:

- All four output fields are required.
- `archive_type` and `client_type` are normalized at model layer, but the detailed per-type IaC contracts live outside `InfraConfig`.
- Details of the referenced YAML files belong in `04_publishing.md`.
- Secrets must not be inlined in publishing YAML; use `SecretRef` fields in the referenced IaC files.

## `observability`

The `observability` section is optional. When present, it controls log formatting, runtime labels, logging behavior, and telemetry provider selection.

There is no `metrics` subtree in the canonical model.

### Fields

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `log_format` | `str` | no | `TEXT` | Trimmed and uppercased. Must be either `TEXT` or `JSON`. |
| `labels` | `dict[str, str]` | no | `{}` | Free-form string key/value labels attached to runtime events. |
| `logging` | `LoggingConfig` | no | default object | Nested runtime logging config. |
| `telemetry` | `TelemetryConfig` | no | default object | Nested telemetry provider config. |

### `observability.logging`

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `level` | `str` | no | `INFO` | Trimmed and uppercased. Blank string is rejected at model layer. Semantic validation then restricts the value to `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. |
| `flood_control_config` | `FloodControlConfig` | no | default object | Nested flood-control settings for noisy logs. Extra semantic validation is applied by `normalize_flood_control_config()`. |

### `observability.telemetry`

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `provider` | `str` | no | `none` | Trimmed and lowercased. Must be exactly `none` or `prometheus`. |

### `observability.logging.flood_control_config`

`FloodControlConfig` has 12 public fields:

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `enabled` | `bool` | no | `true` | Boolean flag for flood-control activation. |
| `mode` | `str` | no | `context_info_suppression` | Additional semantic validation accepts `off`, `context_info_suppression`, `rate_limit`, or `deduplicate`. |
| `context_keys` | `list[str]` | no | `['item_ref']` | Must be a sequence of non-empty strings in semantic validation. |
| `suppressed_levels` | `list[str]` | no | `['INFO']` | Semantic validation converts values to logging levels; invalid names are rejected. |
| `force_log_attr` | `str` | no | `force_log` | Must be a non-empty string in semantic validation. |
| `key_fields` | `list[str]` | no | `['name', 'levelno', 'msg', 'item_ref']` | Must be a sequence of non-empty strings; must not be empty when `mode: deduplicate`. |
| `window_seconds` | `float` | no | `30.0` | Must be a positive number in semantic validation. |
| `max_events_per_window` | `int` | no | `1` | Must be a positive integer in semantic validation. |
| `emit_summary` | `bool` | no | `false` | Boolean flag for summary emission. |
| `summary_level` | `str` | no | `INFO` | Semantic validation converts the value to a logging level and rejects invalid names. |
| `summary_interval_seconds` | `float` | no | `30.0` | Must be a positive number in semantic validation. |
| `max_cache_size` | `int` | no | `10000` | Must be a positive integer in semantic validation. |

Notes:

- In `01_infra.md`, flood control is described only as a subsection of `observability`.
- The dedicated deep-dive document for modes, runtime semantics, and examples is `07_flood_control.md`.

## Complete Example

The following example mirrors a real per-scenario bundle and includes all currently important optional fields:

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

observability:
  labels:
    environment: local
    pipeline: shopify-catalog-realtime
  logging:
    level: INFO
    flood_control_config: {}
  telemetry:
    provider: none
```

`flood_control_config: {}` means "use the full default flood-control configuration".

## Config Loading Pipeline

When infra is loaded through `InfraProvider.get_infra(path)`, the config layer applies three explicit steps.

### 1. Load

Implemented in `src/pfp_runtime/config/infra_loader.py`.

What happens:

- file extension must be `.yaml` or `.yml`
- file content is read from disk as UTF-8 text
- YAML is parsed with `yaml.safe_load`
- YAML root must be a mapping
- parsed payload is materialized into `InfraConfig` via `model_validate()`

Possible failures:

- unsupported extension
- file read error
- invalid YAML syntax
- root value is not a mapping
- Pydantic validation failure while materializing `InfraConfig`

### 2. Validate

Implemented in `src/pfp_runtime/config/infra_validator.py`.

Semantic validation adds cross-field checks that are not enforced directly by the Pydantic models:

- `input.format` must exist in `connectors_registry.json`
- `output.archive_config` and `output.client_config` must point to YAML files
- `producer.schema_file` and `producer.policy_file` must point to YAML files
- when `infra_path` is available, `producer.schema_file` and `producer.policy_file` must resolve to existing regular files
- `observability.logging.level` must be one of the supported Python logging levels
- `observability.logging.flood_control_config` is normalized and validated through `normalize_flood_control_config()`

### 3. Normalize

Implemented in `src/pfp_runtime/config/infra_normalizer.py`.

Relative paths are converted to absolute paths with the following rules:

- `producer.schema_file`, `producer.policy_file`, and `producer.tax_mapping_file`:
  resolve relative to the directory of `infra.yaml`; if the file is absent there, fall back to project root
- `output.archive_config` and `output.client_config`:
  resolve using the same infra-dir then project-root fallback strategy
- `input.config.connector_mapping`:
  resolve relative to the directory of `infra.yaml` only

### Entrypoint

`InfraProvider.get_infra(path)` performs the full sequence:

1. `load_infra_config(path)`
2. `validate_infra_config(infra, infra_path=path)`
3. `normalize_infra_paths(validated, infra_path=path)`

The result is a validated, path-normalized `InfraConfig` ready for downstream runtime compilation.

## Related Documents

- `02_mapping.md` — connector mapping file referenced by `input.config.connector_mapping`
- `03_policies.md` — policy bundle referenced by `producer.policy_file`
- `04_publishing.md` — YAML contracts referenced by `output.archive_config` and `output.client_config`
- `06_advanced.md` — tax mapping JSON and per-scenario bundles
- `07_flood_control.md` — deep-dive on `observability.logging.flood_control_config`