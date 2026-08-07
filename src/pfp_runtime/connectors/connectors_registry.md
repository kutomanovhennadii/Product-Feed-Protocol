# connectors_registry.json — developer reference

This document describes the contract of `connectors_registry.json` used by the runtime to resolve an input `format` to an adapter class and its initialization constants.

## Location

- `src/pfp_runtime/connectors/connectors_registry.json`

## High-level shape

The registry is a JSON object with a single top-level field:

```json
{
  "formats": {
    "<format_name>": {
      "adapter": "<python.module.path.ClassName>",
      "status": "active",
      "constants": { "<key>": "<value>" }
    }
  }
}
```

### Root fields

#### `formats`

- Type: `object`
- Required: yes
- Meaning: Mapping of `format_name` -> format specification.
- Constraints:
  - Keys should be lowercase strings (e.g., `"csv"`, `"json"`).
  - The runtime normalizes the requested format using `strip().lower()`.

## Per-format specification object

Each entry in `formats` is a JSON object with the fields below.

### `adapter`

- Type: `string`
- Required: yes
- Meaning: Fully-qualified import path to the adapter class.
- Format: `"<module_path>.<ClassName>"`
  - Example: `"pfp_runtime.connectors.adapters.json_adapter.JsonAdapter"`
- Runtime behavior:
  - The runtime imports `module_path`, then looks up `ClassName`.
  - The imported symbol must be a class.
  - The class must be instantiable as `AdapterClass(constants=<constants_object>)`.
  - The resulting instance is expected to implement a `parse(...)` method.

### `status`

- Type: `string`
- Required: no (defaults to `"active"`)
- Meaning: Whether the format is enabled.
- Supported values (current runtime behavior):
  - `"active"` — enabled
  - Any other value (e.g., `"disabled"`, `"deprecated"`) is treated as disabled.

### `constants`

- Type: `object`
- Required: no (defaults to `{}`)
- Meaning: Adapter-specific initialization parameters.
- Runtime behavior:
  - The object is passed verbatim into the adapter constructor as the `constants` argument.
  - Unknown keys are tolerated by the loader; whether they have any effect depends on the adapter implementation.

## Built-in formats and their `constants`

This section documents the known built-in formats currently present in the registry and the keys their adapters consume.

### `csv`

Adapter: `pfp_runtime.connectors.adapters.csv_adapter.CsvAdapter`

Consumed keys (as of Mar 2026):

- `max_input_bytes` (int, default `33554432`)
  - Maximum allowed size of the input payload (bytes).
- `csv_field_size_limit` (int, default `131072`)
  - Passed to `csv.field_size_limit(...)`.
- `delimiter` (string, default `","`)
  - CSV delimiter passed to the `csv.DictReader`.
- `has_header` (bool, default `true`)
  - If `false`, the adapter generates column names `col_0..col_N` from the first row.

Notes:
- Some keys may exist in the registry for historical/consistency reasons (e.g., `max_line_bytes`, `max_field_bytes`). If the adapter does not read them, they will have no effect.

### `json`

Adapter: `pfp_runtime.connectors.adapters.json_adapter.JsonAdapter`

Consumed keys:

- `max_input_bytes` (int, default `33554432`)
  - Maximum allowed size of the input payload (bytes).
- `max_json_depth` (int, default `32`)
  - Maximum nesting depth allowed during validation.
- `max_json_container_items` (int, default `100000`)
  - Maximum number of items allowed in any JSON `object` or `array` during validation.
- `items_path` (string, optional)
  - Dot-separated path used to locate an array of records within a decoded JSON object.
  - Example: `"data.products"`.
  - If omitted, the adapter expects the JSON root to be an array.

`items_path` semantics for `json`:
- The adapter treats `items_path` as `"key1.key2.key3"` and walks nested dictionaries.
- It does not support array indexing or wildcards.

### `jsonl`

Adapter: `pfp_runtime.connectors.adapters.jsonl_adapter.JsonlAdapter`

Consumed keys:

- `max_line_bytes` (int, default `262144`)
  - Maximum allowed size of a single line (bytes).
- `max_json_depth` (int, default `32`)
- `max_json_container_items` (int, default `100000`)

### `rows`

Adapter: `pfp_runtime.connectors.adapters.rows_adapter.RowsAdapter`

Registry notes:
- `rows` is intended for already-materialized records (iterable of mappings) supplied via config (`raw_rows`).
- The current adapter implementation does not consume `constants` keys.
- If a `constants` object is present in the registry, it will be passed to the adapter constructor by the loader, so the adapter must remain instantiable with `constants=...`.

### `streaming_json`

Adapter: `pfp_runtime.connectors.adapters.streaming_json_adapter.StreamingJsonAdapter`

Consumed keys:

- `items_path` (string, default `"item"`)
  - Prefix passed to `ijson.items(stream, items_path)`.
- `max_record_bytes` (int, default `1048576`)
  - Intended upper bound for an individual record size (bytes).

`items_path` semantics for `streaming_json`:

- This adapter uses `ijson.items(...)`, so `items_path` is an *ijson prefix*, not the same path resolver as in the in-memory `json` adapter.
- Common patterns:
  - `"item"` — stream elements of a top-level JSON array.
    - Example input: `[ {"id": 1}, {"id": 2} ]`
  - `"data.items.item"` — stream elements of a nested array at `data.items`.
    - Example input: `{ "data": { "items": [ {"id": 1} ] } }`
- Recommendation: Use a prefix ending with `.item` when you want to stream array elements one-by-one.

Notes:
- `streaming_json` requires a byte stream (`IO[bytes]`) or an `Iterable[bytes]`. In-memory `str`/`bytes` inputs are rejected by design.

### `streaming_jsonl`

Adapter: `pfp_runtime.connectors.adapters.streaming_jsonl_adapter.StreamingJsonlAdapter`

Consumed keys:

- `max_line_bytes` (int, default `262144`)
  - Maximum allowed size of a single line (bytes). Lines exceeding this limit raise `AdapterFormatError`.
- `max_json_depth` (int, default `32`)
  - Maximum nesting depth allowed in the JSON object on a single line.
- `max_json_container_items` (int, default `100000`)
  - Maximum number of items allowed in any JSON `object` or `array` on a single line.

Notes:
- `streaming_jsonl` requires a **text stream** (`IO[str]`) or a line iterator (`Iterable[str]`).
  In-memory `str`/`bytes` inputs are rejected by design — use `JsonlAdapter` for those.
- The typical client pattern is to open a (possibly compressed) file in text mode:
  ```python
  import gzip
  with gzip.open("feed.jsonl.gz", "rt", encoding="utf-8") as f:
      for record in connector.extract(f):
          ...
  ```
- Unlike `streaming_json`, this adapter does not require `ijson` — only the standard library.
- Peak memory usage is a single line plus its parsed dict, independent of file size.

### `streaming_csv`

Adapter: `pfp_runtime.connectors.adapters.streaming_csv_adapter.StreamingCsvAdapter`

Consumed keys:

- `csv_field_size_limit` (int, default `131072`)
  - Passed to `csv.field_size_limit(...)`. Limits the maximum size of a single CSV field (bytes).
    Rows containing a field exceeding this limit raise `AdapterFormatError`.
- `delimiter` (string, default `","`)
  - CSV delimiter passed to `csv.DictReader`.
- `has_header` (bool, default `true`)
  - If `false`, the adapter generates column names `col_0..col_N` from the first row,
    treating that row as data (not a header).

Notes:
- `streaming_csv` requires a **text stream** (`IO[str]`) or a line iterator (`Iterable[str]`).
  In-memory `str`/`bytes` inputs are rejected by design — use `CsvAdapter` for those.
- The typical client pattern is to open a (possibly compressed) file in text mode:
  ```python
  import gzip
  with gzip.open("feed.csv.gz", "rt", encoding="utf-8") as f:
      for record in connector.extract(f):
          ...
  ```
- Unlike `CsvAdapter`, this adapter does not accept `max_input_bytes` — the size of a streaming
  source is unknown upfront. Protection is provided by `csv_field_size_limit` at the field level.
- Does not require `ijson` or any third-party library — only the standard library.
- Peak memory usage is a single row plus its parsed dict, independent of file size.
- `has_header=False` is safe for non-seekable streams: the adapter uses `itertools.chain`
  to peek at the first row for column count detection without calling `.seek()`.

## Operational notes

- Disabling a format: set `status` to anything other than `"active"`.
- Adding a new format:
  1. Add a new entry under `formats`.
  2. Ensure the adapter can be imported and instantiated with `constants=<object>`.
  3. Keep `format_name` tokens stable because they are referenced from infra config (e.g., `input.format`).
