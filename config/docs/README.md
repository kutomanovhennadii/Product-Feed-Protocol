# YAML Config Docs

`config/docs/` is the centralized user-facing documentation set for runtime YAML and related config files under `config/`.

Use this directory as an entry point: start with the document that matches the file you are editing, then follow cross-links when one config references another.

## Read By Goal

If you want to configure the root pipeline file, read:

- `01_infra.md` — `infra.yaml`: `input`, `producer`, `output`, `observability`.

If you want to map source fields into the Unified Model, read:

- `02_mapping.md` — `mapping.yaml` / `connector_mapping`.

If you want to configure validation and error-handling policy, read:

- `03_policies.md` — `policies.yaml`.

If you want to configure archiving or delivery, read:

- `04_publishing.md` — archive/client configs: `local`, `s3`, `s3_compat`, `noop`, `http`, `http_streaming`, `sftp`.

If you want to understand or author schema YAML files, read:

- `05_schema.md` — schema YAML structure under `schemas/`.

If you want tax-code lookups or ready-made scenario bundles, read:

- `06_advanced.md` — `tax_mappings/*.json` and per-scenario bundles under `config/shopify_*/`.

If you want the full logging noise-suppression reference, read:

- `07_flood_control.md` — full reference for `observability.logging.flood_control_config`.

## Config Map

Main runtime files:

- `config/infra.yaml` and `config/<scenario>/infra_*.yaml` — root runtime config.
- `config/mapping.yaml` and `config/<scenario>/mapping_*.yaml` — connector field mapping.
- `config/policies.yaml` and `config/<scenario>/policies_*.yaml` — policy bundle config.

Publishing support files:

- `config/archive/*.yaml` — concrete archiver configs.
- `config/clients/*.yaml` — concrete delivery-client configs.

Templates:

- `config/archive/*.yaml.template`
- `config/clients/*.yaml.template`

These template files are starter examples with placeholder values for humans to copy and adapt. Runtime loads the concrete `.yaml` files referenced from `infra.yaml`, not the `.yaml.template` files directly.

Advanced/shared assets:

- `config/tax_mappings/*.json` — optional tax-code lookup data used by schema op `map_tax_code`.
- `schemas/*/*.yaml` — protocol schema files referenced by `producer.schema_file`.
- `config/shopify_*` — ready-made per-scenario bundles that point at shared schemas, tax mappings, archive configs, and client configs.

## How To Read The Docs

The intended reading order is:

1. Start with `01_infra.md`, because `infra.yaml` wires the whole runtime together.
2. Follow the referenced document for each file path inside `producer`, `output`, or `observability`.
3. Use `06_advanced.md` for shared lookup JSONs and scenario bundles.
4. Use `07_flood_control.md` only when you need the deep runtime behavior behind `flood_control_config`.

## Notes

- The documentation in `config/docs/` is written from the current code contracts, not copied from legacy MD files.
- Per-scenario bundles stay in their current folders; this directory centralizes the explanation, not the runtime assets.