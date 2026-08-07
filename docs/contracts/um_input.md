# Unified Model Input Contract

Этот документ описывает текущий входной contract Product Feed Protocol до стадии schema-bound artifact production.

## Scope

- raw source records на входе connector/runtime;
- mapping semantics в UM-space;
- expected target-path behavior;
- required-field handling и related invariants.

## Source Of Truth

- `src/pfp_runtime/connectors/connector_mapping/connector_mapping_config.py`
- `src/pfp_runtime/connectors/connector_mapping/connector_mapper.py`
- `examples/01_minimal_quickstart/input/input.jsonl`
- `examples/01_minimal_quickstart/mapping.yaml`

## Contract Summary

Входной contract PFP на текущем этапе не задаётся отдельным canonical UM dataclass. Реальный входной surface складывается из двух частей:

1. adapter-level raw records, приходящих как dict-like objects с top-level string keys;
2. mapping configuration, которая роутит эти source keys в UM-space target paths.

Иначе говоря, runtime ожидает не «готовый Unified Model object», а поток сырьевых records, для которых заранее описаны mapping rules.

## Raw Source Records

`ConnectorMapper.apply_stream(...)` принимает `Iterable[Mapping[str, Any]]`. Это означает следующее:

- каждый record должен вести себя как mapping по ключу;
- source lookup идёт по top-level key membership (`source_key in record`);
- значения прокидываются дальше без type coercion на слое mapper;
- unmapped source keys silently drop'аются и не попадают в output.

Минимальный живой пример raw input из `examples/01_minimal_quickstart/input/input.jsonl`:

```json
{"sku":"SKU-1","item_id":"SKU-1","title":"Hello","description":"World","url":"https://example.com/sku-1","availability":"in_stock"}
```

Этот payload является source record, а не готовым UM object.

## Mapping Rules

Каждое правило mapping описывается `ConnectorFieldMapping`:

- `source: str` — имя поля в raw input record;
- `target: str` — dot-separated path в UM-space;
- `required: bool` — обязательность source field для данного record.

Минимальный живой пример из `examples/01_minimal_quickstart/mapping.yaml`:

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

`ConnectorFieldMapping.target` задаётся как dot-separated path string. На текущем этапе это означает:

- target path живёт в UM-space и выражается строкой вроде `product.item_id`;
- mapper не материализует nested object tree автоматически;
- output mapper'а содержит routed keys exactly as configured target strings;
- interpretation этих target paths происходит дальше по pipeline, а не на слое `ConnectorMapper`.

Практически это значит, что `product.item_id` и `inventory.availability` нужно читать как schema/mapping-space identifiers, а не как гарантию, что mapper создаёт вложенный словарь вида `{ "product": { "item_id": ... } }`.

## No Nested Source Query Language

Current mapping layer не гарантирует nested source traversal.

Из текущей реализации следует:

- source lookup проверяет только наличие точного top-level ключа в record;
- логика вида `source: product.id` как nested-query language этим контрактом не обещается;
- dotted notation в `target` не означает dotted lookup в `source`;
- документировать полноценный nested extraction сейчас было бы неверно.

Если input producer хочет использовать nested data, такой behavior должен быть явно подтверждён другим adapter/mapping слоем. Текущий `ConnectorMapper` сам по себе этого не реализует.

## Required Field Behavior

`ConnectorMappingConfig` содержит ordered tuple mappings и флаг `continue_on_error`.

Поведение обязательных полей сейчас такое:

- если required source field присутствует, mapper записывает значение в configured target;
- если required source field отсутствует и `continue_on_error=true`, record skip'ается целиком, а runtime пишет warning в log pipeline;
- если required source field отсутствует и `continue_on_error=false`, выбрасывается `ConnectorMappingValidationError` и поток останавливается;
- если optional field отсутствует, оно просто не попадает в output и warning не создаётся.

Следствие для input contract: обязательность задаётся не schema-файлом input record, а mapping configuration plus `continue_on_error` policy.

## Output Of Mapping Layer

На выходе mapping layer yield'ится `Mapping[str, Any]`, где:

- keys соответствуют configured UM-space target paths;
- values остаются теми же, что пришли из source record;
- только mapped fields присутствуют в output;
- skipped records не yield'ятся вообще.

## Invariants

- Raw input record должен быть dict-like и поддерживать top-level key lookup.
- `source` в mapping rules интерпретируется как exact source field name.
- `target` интерпретируется как UM-space identifier string.
- Current mapper не обещает nested source traversal.
- Current mapper не обещает nested object materialization по dotted target path.
- Missing required field behavior полностью зависит от `continue_on_error`.

## Out Of Scope

- artifact payload contract;
- aggregate validation outcome;
- diagnostic item schema;
- compatibility rules между всеми contract surfaces.