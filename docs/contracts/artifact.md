# Produced Artifact Contract

Этот документ описывает выходной artifact contract Product Feed Protocol.

## Scope

- `ProducedArtifact` как runtime output unit;
- `payload` contract;
- `ArtifactMetadata` fields и их смысл;
- различие между payload bytes и metadata;
- базовые invariants для artifact payload и metadata.

## Source Of Truth

- `src/pfp_core/contracts/produced_artifact.py`
- `src/pfp_core/contracts/artifact_metadata.py`
- artifact construction в `src/pfp_core/artifact_production/artifact_producer.py`
- `examples/01_minimal_quickstart/expected/output.csv`

## Contract Summary

На текущем этапе produced artifact в PFP выражается объектом `ProducedArtifact`, который объединяет:

1. `payload: Iterable[bytes]` — byte chunks итогового artifact payload;
2. `metadata: ArtifactMetadata` — identity и format descriptors для этого payload.

Иначе говоря, runtime contract на artifact состоит не только из «получившегося файла», но из пары payload + metadata. Эти две части нужно интерпретировать раздельно.

## ProducedArtifact

`ProducedArtifact` — dataclass-контейнер для одного сгенерированного feed artifact.

Его поля:

- `payload: Iterable[bytes]`
- `metadata: ArtifactMetadata`

Практический смысл:

- `payload` содержит сами байты artifact content;
- `metadata` описывает target, schema version, content type, encoding и identity-related context;
- artifact contract не смешивает payload bytes с validation diagnostics или run-level summary.

## Payload Contract

`ProducedArtifact.payload` документирован как `Iterable[bytes]`.

Это означает следующее:

- payload состоит из byte chunks, а не из строки, dict или path к файлу;
- runtime может выдавать payload streaming-образом;
- потребитель контракта должен быть готов итерировать chunks и собирать итоговое содержимое сам, если ему нужен один materialized blob;
- payload contract описывает содержимое artifact, но не место его публикации и не publish-time outcome.

Из docstring модели следует важная operational detail:

- до publish payload может быть generator-like iterable;
- после publish payload может быть materialized и re-iterable.

Следовательно, public contract нельзя описывать как «всегда один `bytes` object» или как «всегда путь к файлу на диске».

## Minimal Payload Example

Минимальный живой example artifact payload из `examples/01_minimal_quickstart/expected/output.csv`:

```text
id,title,description,link,availability
SKU-1,Hello,World,https://example.com/sku-1,in_stock
```

На уровне contract этот текст представляет собой сериализованный результат writer'а; в `ProducedArtifact.payload` он приходит как iterable byte chunks, а не как markdown/text abstraction.

## ArtifactMetadata

`ArtifactMetadata` — frozen dataclass с полями:

- `target: str`
- `schema_version: str`
- `generated_at: datetime`
- `content_type: str`
- `encoding: str`
- `artifact_profile: Optional[str]`
- `filename_hint: Optional[str]`

## Meaning Of Metadata Fields

### `target`

Идентификатор target system / target contract surface. Это не имя файла и не MIME type. Пример по коду: значения вроде `stripe.product`.

### `schema_version`

Точная версия schema contract, с которой был собран artifact. Это поле связывает artifact с конкретной schema identity, а не просто с writer format.

### `generated_at`

UTC timestamp генерации artifact. Это runtime timestamp создания artifact, а не publish timestamp внешней системы.

### `content_type`

MIME type payload, например `text/csv`. Это descriptor формата содержимого.

### `encoding`

Payload encoding, например `utf-8`. Это descriptor кодировки байтового содержимого.

### `artifact_profile`

Опциональный profile, с которым был собран artifact, например `catalog_snapshot`. Полезен для differentiation между различными artifact modes внутри одного target surface.

### `filename_hint`

Опциональная deterministic filename hint, которую runtime может сгенерировать для downstream publishing/archiving flows. Это hint, а не гарантия фактического publish location.

## Payload Vs Metadata

Различие между payload bytes и metadata принципиально:

- payload отвечает на вопрос «какое содержимое produced artifact получилось»;
- metadata отвечает на вопрос «как идентифицировать и интерпретировать этот artifact»;
- payload не должен дублировать metadata fields внутри себя по контракту;
- metadata не содержит самих payload bytes.

Практически это значит, что CSV content и поля вроде `target`, `schema_version`, `generated_at` принадлежат разным слоям одного artifact contract.

## Runtime Construction Semantics

По текущему `artifact_producer.py` metadata собирается из:

- `prepared.target_id` -> `target`;
- `prepared.schema_ref.schema_version` -> `schema_version`;
- `generated_at_utc` -> `generated_at`;
- writer spec -> `content_type` и file extension for `filename_hint`;
- prepared encoding -> `encoding`;
- compiled schema profile -> `artifact_profile`.

Следствие: artifact metadata не является произвольной пользовательской нагрузкой, а формируется как часть runtime contract из prepared schema + writer configuration.

## Invariants

- `ProducedArtifact` всегда состоит из `payload` и `metadata`.
- `payload` интерпретируется как iterable of byte chunks.
- `metadata` интерпретируется как format/identity descriptor, а не как publish result.
- `target`, `schema_version`, `generated_at`, `content_type`, `encoding` являются обязательными полями `ArtifactMetadata`.
- `artifact_profile` и `filename_hint` являются optional, но если присутствуют, должны относиться к текущему artifact, а не к внешнему transport state.
- Contract не обещает, что payload уже материализован в один `bytes` object.
- Contract не обещает, что artifact уже опубликован во внешнюю систему или сохранён на диск.

## Out Of Scope

- connector input semantics;
- aggregate validation report shape;
- per-diagnostic item contract;
- cross-cutting compatibility policy.