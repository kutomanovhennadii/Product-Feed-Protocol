# Diagnostics Contract

This document describes the individual diagnostic item contract in the PFP runtime: `Diagnostic`.

## Purpose and Scope

A `Diagnostic` explicitly defines a single evaluation finding, format coercion, or validation problem encountered during mapping or execution. It is machine-readable and designed both for structural aggregation and for developer understanding.

## Contract Structure

A diagnostic object serializes to a dictionary with the following attributes:

### Fields

*   **`severity`** (`str`): The severity level of the diagnostic. Must be one of the normalized values defined by `DiagnosticSeverity`.
*   **`code`** (`str`): A machine-readable string key identifying the nature of the issue (e.g., `"STRIPE_TITLE_REQUIRED"`, `"MISSING_REQUIRED_FIELD"`).
*   **`message`** (`str`): A human-readable description of the validation issue.
*   **`path`** (`str | null`): The associated UM-space property path or target field location where the problem occurred (e.g., `"title"`).
*   **`item_ref`** (`str | null`): An identifier for the specific source record or item that triggered the diagnostic (e.g., `"SKU-2"`).
*   **`metadata`** (`Dict[str, Any]`): An open dictionary containing additional contextual debugging information (e.g., original values, types, traceback details).

## Severity Normalization

The system recognizes exactly three normalized severity levels:
*   `ERROR`
*   `WARN`
*   `INFO`

**Alias Rules:** If a system emits `"WARNING"`, it is automatically normalized to `"WARN"`. Unknown severities raise structural errors during initialization.

## Serialized Example

```json
{
  "severity": "WARN",
  "code": "STRIPE_TITLE_REQUIRED",
  "message": "The property 'title' is absent. A fallback has been applied.",
  "path": "title",
  "item_ref": "SKU-404",
  "metadata": {
    "fallback_used": "Empty string"
  }
}
```