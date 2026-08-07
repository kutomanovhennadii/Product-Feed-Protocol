# Unified Model Input Contract

This document describes the current input contract of Product Feed Protocol up to the stage of schema-bound artifact production.

## Scope

- raw source records at the connector/runtime input;
- mapping semantics in UM-space;
- expected target-path behavior;
- required-field handling and related invariants.

## Source Of Truth

- `src/pfp_runtime/connectors/connector_mapping/connector_mapping_config.py`
- `src/pfp_runtime/connectors/connector_mapping/connector_mapper.py`
- `examples/01_minimal_quickstart/input/input.jsonl`
- `examples/01_minimal_quickstart/mapping.yaml`

## Contract Summary

At the current stage, the PFP input contract is not defined by a separate canonical UM dataclass. The real input surface is composed of two parts:

1. adapter-level raw records arriving as dict-like objects with top-level string keys;
2. mapping configuration that routes those source keys into UM-space target paths.

In other words, the runtime does not expect a "ready-made Unified Model object", but a stream of raw records for which mapping rules have been described in advance.

## Raw Source Records

`ConnectorMapper.apply_stream(...)` accepts `Iterable[Mapping[str, Any]]`. This means the following:

- every record must behave as a mapping accessed by key;
- source lookup goes through top-level key membership (`source_key in record`);
- values are passed through without type coercion at the mapper layer;
- unmapped source keys are silently dropped and do not reach the output.

A minimal live example of raw input from `examples/01_minimal_quickstart/input/input.jsonl`:

```json
{"sku":"SKU-1","item_id":"SKU-1","title":"Hello","description":"World","url":"https://example.com/sku-1","availability":"in_stock"}
```

This payload is a source record, not a ready-made UM object.

## Mapping Rules

Each mapping rule is described by `ConnectorFieldMapping`:

- `source: str` — the field name in the raw input record;
- `target: str` — a dot-separated path in UM-space;
- `required: bool` — whether the source field is mandatory for the given record.

A minimal live example from `examples/01_minimal_quickstart/mapping.yaml`:

```yaml
mappings:
  - source: "sku"
    target: "product.item_id"
    required: true
  - source: "title"
    target: "title"
    required: true
  - source: "item_id"
    target: "item_id"
  - source: "description"
    target: "description"
  - source: "url"
    target: "url"
  - source: "availability"
    target: "inventory.availability"

continue_on_error: true
```

## UM-Space Target Paths

`ConnectorFieldMapping.target` is defined as a dot-separated path string. At the current stage this means:

- the target path lives in UM-space and is expressed as a string such as `product.item_id`;
- the mapper does not automatically materialize a nested object tree;
- the mapper output contains routed keys exactly as the configured target strings;
- interpretation of these target paths happens further down the pipeline, not at the `ConnectorMapper` layer.

In practice this means that `product.item_id` and `inventory.availability` must be read as schema/mapping-space identifiers, not as a guarantee that the mapper creates a nested dictionary of the form `{ "product": { "item_id": ... } }`.

## No Nested Source Query Language

The current mapping layer does not guarantee nested source traversal.

The current implementation implies that:

- source lookup only checks for the presence of an exact top-level key in the record;
- logic such as `source: product.id` as a nested-query language is not promised by this contract;
- dotted notation in `target` does not imply dotted lookup in `source`;
- documenting full nested extraction at this point would be incorrect.

If an input producer wants to use nested data, such behavior must be explicitly confirmed by another adapter/mapping layer. The current `ConnectorMapper` does not implement it on its own.

## Required Field Behavior

`ConnectorMappingConfig` holds an ordered tuple of mappings and a `continue_on_error` flag.

Required-field behavior is currently as follows:

- if a required source field is present, the mapper writes the value into the configured target;
- if a required source field is missing and `continue_on_error=true`, the record is skipped entirely and the runtime writes a warning into the log pipeline;
- if a required source field is missing and `continue_on_error=false`, a `ConnectorMappingValidationError` is raised and the stream stops;
- if an optional field is missing, it simply does not reach the output and no warning is produced.

Consequence for the input contract: mandatoriness is defined not by a schema file for the input record, but by the mapping configuration plus the `continue_on_error` policy.

## Output Of Mapping Layer

The mapping layer yields `Mapping[str, Any]`, where:

- keys correspond to the configured UM-space target paths;
- values remain the same as those that arrived from the source record;
- only mapped fields are present in the output;
- skipped records are not yielded at all.

## Invariants

- A raw input record must be dict-like and support top-level key lookup.
- `source` in mapping rules is interpreted as an exact source field name.
- `target` is interpreted as a UM-space identifier string.
- The current mapper does not promise nested source traversal.
- The current mapper does not promise nested object materialization along a dotted target path.
- Missing required field behavior depends entirely on `continue_on_error`.

## Out Of Scope

- artifact payload contract;
- aggregate validation outcome;
- diagnostic item schema;
- compatibility rules across all contract surfaces.
