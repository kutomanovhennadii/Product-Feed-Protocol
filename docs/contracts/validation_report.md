# Validation Report Contract

This document describes the structure of the aggregate run validation outcome in the PFP runtime: `ValidationReport`.

## Purpose and Scope

`ValidationReport` represents the complete collection of diagnostic items produced during a single schema conversion or artifact generation run. It aggregates validation outcomes for the entire dataset or payload batch.

It differs from the final artifact payload: the artifact contains valid mapped records in bytes format, whereas the `ValidationReport` focuses only on the semantic and mapping issues encountered during the process.

## Contract Structure

The report structure is serialized as a dictionary/JSON object through the `to_dict()` method and consists of the following fields:

### Fields

*   **`target`** (`str | null`): The target schema endpoint identifier (e.g., `"stripe"` or `"my_target"`). Matches the `target` parameter of the mapping config.
*   **`artifact_profile`** (`str | null`): Optional identifier indicating the selected formatting profile used during execution.
*   **`diagnostics`** (`List[Diagnostic]`): The aggregated list of diagnostic items encountered.

## Deterministic Sorting

When serialized via `to_dict()`, the `diagnostics` array is always sorted deterministically to ensure reproducible output. The sorting rank is based on:
1.  **Severity Rank:** (`ERROR` = 0, `WARN` = 1, `INFO` = 2)
2.  **Diagnostic Code:** Lexicographical order of the `code` strings.
3.  **Item Reference (`item_ref`):** Lexicographical order of references, treating empty/null as the lowest string.
4.  **Path (`path`):** Lexicographical order of the target fields.

## Serialized Example

```json
{
  "target": "stripe",
  "artifact_profile": null,
  "diagnostics": [
    {
      "severity": "ERROR",
      "code": "MISSING_REQUIRED_FIELD",
      "message": "Field 'title' is missing but marked as required.",
      "path": "title",
      "item_ref": "RECORD-2",
      "metadata": {}
    },
    {
      "severity": "WARN",
      "code": "TYPE_COERCION",
      "message": "Value cast to string.",
      "path": "price",
      "item_ref": "RECORD-1",
      "metadata": {
        "original_type": "int"
      }
    }
  ]
}
```