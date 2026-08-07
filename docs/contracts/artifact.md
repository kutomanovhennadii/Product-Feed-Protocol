# Produced Artifact Contract

This document describes the output artifact contract of Product Feed Protocol.

## Scope

- `ProducedArtifact` as the runtime output unit;
- the `payload` contract;
- `ArtifactMetadata` fields and their meaning;
- the distinction between payload bytes and metadata;
- baseline invariants for artifact payload and metadata.

## Source Of Truth

- `src/pfp_core/contracts/produced_artifact.py`
- `src/pfp_core/contracts/artifact_metadata.py`
- artifact construction in `src/pfp_core/artifact_production/artifact_producer.py`
- `examples/01_minimal_quickstart/expected/output.csv`

## Contract Summary

At the current stage, a produced artifact in PFP is expressed by the `ProducedArtifact` object, which combines:

1. `payload: Iterable[bytes]` — byte chunks of the resulting artifact payload;
2. `metadata: ArtifactMetadata` — identity and format descriptors for that payload.

In other words, the runtime contract for an artifact consists not only of "the resulting file", but of a payload + metadata pair. These two parts must be interpreted separately.

## ProducedArtifact

`ProducedArtifact` is a dataclass container for a single generated feed artifact.

Its fields:

- `payload: Iterable[bytes]`
- `metadata: ArtifactMetadata`

Practical meaning:

- `payload` holds the bytes of the artifact content itself;
- `metadata` describes the target, schema version, content type, encoding, and identity-related context;
- the artifact contract does not mix payload bytes with validation diagnostics or run-level summary.

## Payload Contract

`ProducedArtifact.payload` is documented as `Iterable[bytes]`.

This means the following:

- the payload consists of byte chunks, not of a string, a dict, or a path to a file;
- the runtime may emit the payload in a streaming fashion;
- a consumer of the contract must be ready to iterate over chunks and assemble the final content itself if it needs a single materialized blob;
- the payload contract describes the content of the artifact, but not its publication location and not the publish-time outcome.

An important operational detail follows from the model docstring:

- before publish, the payload may be a generator-like iterable;
- after publish, the payload may be materialized and re-iterable.

Consequently, the public contract cannot be described as "always a single `bytes` object" or as "always a path to a file on disk".

## Minimal Payload Example

A minimal live example of an artifact payload from `examples/01_minimal_quickstart/expected/output.csv`:

```text
id,title,description,link,availability
SKU-1,Hello,World,https://example.com/sku-1,in_stock
```

At the contract level, this text is the serialized result of a writer; in `ProducedArtifact.payload` it arrives as iterable byte chunks, not as a markdown/text abstraction.

## ArtifactMetadata

`ArtifactMetadata` is a frozen dataclass with the following fields:

- `target: str`
- `schema_version: str`
- `generated_at: datetime`
- `content_type: str`
- `encoding: str`
- `artifact_profile: Optional[str]`
- `filename_hint: Optional[str]`

## Meaning Of Metadata Fields

### `target`

The identifier of the target system / target contract surface. This is not a file name and not a MIME type. Example from the code: values such as `stripe.product`.

### `schema_version`

The exact version of the schema contract the artifact was built against. This field ties the artifact to a specific schema identity, not merely to a writer format.

### `generated_at`

The UTC timestamp of artifact generation. This is the runtime timestamp of artifact creation, not the publish timestamp of an external system.

### `content_type`

The MIME type of the payload, for example `text/csv`. This is a descriptor of the content format.

### `encoding`

The payload encoding, for example `utf-8`. This is a descriptor of the byte content encoding.

### `artifact_profile`

The optional profile the artifact was built with, for example `catalog_snapshot`. Useful for differentiating between distinct artifact modes within a single target surface.

### `filename_hint`

An optional deterministic filename hint that the runtime may generate for downstream publishing/archiving flows. This is a hint, not a guarantee of the actual publish location.

## Payload Vs Metadata

The distinction between payload bytes and metadata is fundamental:

- the payload answers the question "what content did the produced artifact end up with";
- the metadata answers the question "how to identify and interpret this artifact";
- by contract, the payload should not duplicate metadata fields inside itself;
- the metadata does not contain the payload bytes themselves.

In practice this means that CSV content and fields such as `target`, `schema_version`, and `generated_at` belong to different layers of the same artifact contract.

## Runtime Construction Semantics

According to the current `artifact_producer.py`, metadata is assembled from:

- `prepared.target_id` -> `target`;
- `prepared.schema_ref.schema_version` -> `schema_version`;
- `generated_at_utc` -> `generated_at`;
- writer spec -> `content_type` and file extension for `filename_hint`;
- prepared encoding -> `encoding`;
- compiled schema profile -> `artifact_profile`.

Consequence: artifact metadata is not an arbitrary user-supplied payload; it is formed as part of the runtime contract from the prepared schema plus writer configuration.

## Invariants

- `ProducedArtifact` always consists of `payload` and `metadata`.
- `payload` is interpreted as an iterable of byte chunks.
- `metadata` is interpreted as a format/identity descriptor, not as a publish result.
- `target`, `schema_version`, `generated_at`, `content_type`, and `encoding` are required fields of `ArtifactMetadata`.
- `artifact_profile` and `filename_hint` are optional, but when present they must relate to the current artifact, not to external transport state.
- The contract does not promise that the payload is already materialized into a single `bytes` object.
- The contract does not promise that the artifact has already been published to an external system or saved to disk.

## Out Of Scope

- connector input semantics;
- aggregate validation report shape;
- per-diagnostic item contract;
- cross-cutting compatibility policy.
