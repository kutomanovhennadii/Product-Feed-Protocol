# Schemas — protocol schema documents (schema-doc)

This directory contains infrastructure schema documents that represent external provider protocols (Stripe/OpenAI/and future providers) in a machine-readable form. These schema-docs are the only inputs used by the schema-driven engine to assemble:
- ValidationPlan (validation Ext-modules + config)
- MappingPlan (mapping Ext-modules + config)
- WriterSpec (writer_id + writer_config)
and to produce deterministic artifacts (Artifact.payload as Iterable[bytes]) for the selected (protocol_id, schema_version, mode, generated_at).

Normative reference for the schema format and how to fill it:
- ../config/docs/05_schema.md

## 1. Directory layout

schemas/
  <protocol_id>/
    <protocol_id>-<schema_version>.yaml
    <protocol_id>-<schema_version>__notes.md          (optional)
    <protocol_id>-<schema_version>__migrations.md     (optional)

Examples:
- schemas/stripe.product_feed/stripe.product_feed-1.0.0.yaml
- schemas/openai.product_feed/openai.product_feed-1.0.0.yaml

Rules:
1) Directory name MUST equal header.protocol_id in the schema file.
2) File name MUST follow: <protocol_id>-<schema_version>.yaml
3) <protocol_id> in file name MUST equal header.protocol_id.
4) <schema_version> in file name MUST equal header.schema_version.
5) Schema files MUST be valid according to ../config/docs/05_schema.md.

## 2. What is protocol_id

protocol_id is a canonical identifier of the external protocol/target that the artifact conforms to.

Guidelines:
- Use lowercase.
- Use dot-separated names.
- Keep it stable: protocol_id changes are breaking.

Examples:
- stripe.product_feed
- stripe.inventory_price_feed
- openai.product_feed
- (future) gemini.product_feed
- (future) anthropic.product_feed
- (future) grok.product_feed

## 3. What is schema_version

schema_version identifies the version of the schema-doc (the internal representation of the external protocol). It is NOT the Core package version.

Recommended patterns (choose one project-wide):
- "1", "2", "3" (simple integer strings)
- "2026-02", "2026-03" (calendar-like)
- "v1", "v2" (explicit prefix)

Rules:
- schema_version MUST be a non-empty string.
- When external protocol changes in a way that affects output format/semantics, create a new schema_version.
- If backward compatibility is required, keep old schemas and select by schema_version.

## 4. Migration notes

When you introduce a new schema_version, add at least one of:
- <schema_version>__notes.md: what changed and why
- <schema_version>__migrations.md: how to migrate from previous version(s)

These notes reference the external protocol changes (source_protocol.url + source_protocol.revision).

## 5. Determinism and reproducibility

Schemas MUST be deterministic:
- No "now()", randomness, environment-dependent behavior.
- Any "generated_at" or timestamps used in artifacts MUST come from the API parameter `generated_at`, not from runtime clocks.

Writers MUST produce deterministic byte output under fixed parameters:
- stable field ordering (csv columns, json keys policy),
- stable line terminators,
- explicit encoding.

## 6. Minimal set of base schemas

The project maintains a minimal set of base schemas:
- stripe.product_feed v1
- openai.product_feed v1
- stripe.inventory_price_feed v1
Optionally (if enabled by the product roadmap):
- stripe.inventory_feed v1 (legacy/alias compatibility)
- stripe.price_feed v1 (legacy/alias compatibility)

These base schemas should remain as reference points for end-to-end baseline runs and golden comparisons.

## 7. Review checklist for a new schema

Before adding a schema file:
1) header.protocol_id and header.schema_version match the path.
2) source_protocol is filled with a stable reference (url + revision + retrieved_at).
3) modes.supported and presence semantics are explicitly defined.
4) output.writer_id and writer_config are explicit.
5) mapping fields cover the protocol required outputs.
6) validation rules cover required fields, types, and key cross-field dependencies.
7) no non-deterministic constructs exist.
8) if this is a new version, migration notes are added.

## 8. Ownership

Schemas represent external protocols and must be reviewed as contract artifacts:
- changes require a clear reference to external source changes,
- changes must update migration notes,
- changes must not break determinism expectations without a version bump.
