# Flood Control Config

`observability.logging.flood_control_config` controls runtime suppression of noisy log records.

This is a deep-dive document for the semantics behind the `FloodControlConfig` subtree already introduced in `01_infra.md`.

Source of truth for this document:

- `src/pfp_runtime/config/infra_models.py`
- `src/pfp_utils/logging/filters/flood_control_filter/flood_control_filter.py`
- `src/pfp_utils/logging/filters/flood_control_filter/flood_control_filter_config_validation.py`
- `src/pfp_utils/logging/filters/flood_control_filter/flood_control_filter_strategies.py`

For the outer `observability` structure, see `01_infra.md`.

## What Flood Control Does

Flood control is a logging filter used to suppress repetitive records during item-level processing loops.

It is applied only to records that match both of these conditions:

- the record level is listed in `suppressed_levels`
- there is an active logging context that matches `context_keys`

Default behavior is:

- `enabled: true`
- `mode: context_info_suppression`
- `context_keys: ["item_ref"]`
- `suppressed_levels: ["INFO"]`

So the out-of-the-box behavior is: suppress `INFO` records when an active `LogContext` contains `item_ref`.

## Important Current Drift From The Plan

The runtime does not currently support literal mode token `allow_all`.

Current allow-all behavior is achieved by either of these runtime states:

- `enabled: false`
- `mode: off`

This document therefore uses term `allow-all semantics` for the behavior, while keeping the actual accepted mode values aligned with code.

## Fields

`FloodControlConfig` currently exposes 12 public fields.

| Field | Type | Required | Default | Effect |
|---|---|---|---|---|
| `enabled` | `bool` | no | `true` | Master on/off switch. When `false`, filter becomes allow-all regardless of `mode`. |
| `mode` | `str` | no | `context_info_suppression` | Runtime strategy selector. Accepted values are `off`, `context_info_suppression`, `rate_limit`, `deduplicate`. |
| `context_keys` | `list[str]` | no | `['item_ref']` | Context keys whose presence activates flood control. If empty, any active context activates it. |
| `suppressed_levels` | `list[str]` in infra model; normalized from strings or ints | no | `['INFO']` | Only records at these levels are candidates for suppression. |
| `force_log_attr` | `str` | no | `force_log` | Record attribute that bypasses suppression when truthy. |
| `key_fields` | `list[str]` | no | `['name', 'levelno', 'msg', 'item_ref']` | Fields used to build suppression identity for stateful modes and summaries. |
| `window_seconds` | `float` | no | `30.0` | Active time window for `rate_limit` and `deduplicate`. |
| `max_events_per_window` | `int` | no | `1` | Max allowed events per key per window in `rate_limit`. |
| `emit_summary` | `bool` | no | `false` | Enables periodic synthetic summary logs about suppressed records. |
| `summary_level` | `str` | no | `INFO` | Level used for summary records. Normalized through logging-level lookup. |
| `summary_interval_seconds` | `float` | no | `30.0` | Minimum interval before the next summary can be emitted for the same key. |
| `max_cache_size` | `int` | no | `10000` | Max number of unique keys kept in state caches; oldest keys are evicted first. |

## Validation Rules

Semantic validation is applied by `normalize_flood_control_config()` after the infra model layer.

Current enforced rules:

- `mode` must be one of `off`, `context_info_suppression`, `rate_limit`, `deduplicate`
- `context_keys` must be a sequence of non-empty strings
- `suppressed_levels` must be a sequence of strings or integers convertible to logging levels
- `force_log_attr` must be a non-empty string
- `key_fields` must be a sequence of non-empty strings
- `window_seconds` must be a positive number
- `max_events_per_window` must be a positive integer
- `emit_summary` must be boolean
- `summary_level` must resolve to a valid logging level
- `summary_interval_seconds` must be a positive number
- `max_cache_size` must be a positive integer
- in `deduplicate` mode, `key_fields` must not be empty

Missing keys are merged with defaults before validation.

## Activation Rules

Suppression does not run on every record automatically.

Current activation logic is:

1. If record has truthy attribute named by `force_log_attr`, allow it immediately.
2. If `enabled` is `false` or `mode` is `off`, allow everything.
3. If record level is not in `suppressed_levels`, allow it.
4. Read current `LogContext`.
5. If no active context key matches `context_keys`, allow it.
6. Otherwise apply the selected strategy.

If `context_keys` is an empty list, any active context is enough to activate suppression.

## Modes

### Allow-All Semantics

This is the effective "filter disabled" behavior.

Use either:

```yaml
flood_control_config:
  enabled: false
```

or:

```yaml
flood_control_config:
  mode: off
```

Effect:

- all records pass through
- no suppression state is tracked
- no summary emitter is used for filtering decisions

### `context_info_suppression`

This is the default mode.

Effect:

- if a record is suppressible and active context matches, the record is dropped immediately
- no per-key time window is checked
- summary emission can still work if `emit_summary: true`

This mode is the closest to the historic behavior described by the filter docstring: suppress noisy `INFO` logs inside active item context.

Example:

```yaml
flood_control_config:
  enabled: true
  mode: context_info_suppression
  context_keys:
    - item_ref
  suppressed_levels:
    - INFO
```

### `rate_limit`

This mode keeps up to `max_events_per_window` records per key inside each sliding `window_seconds` interval.

Effect:

- record key is built from `key_fields`
- timestamps are stored per key
- old timestamps older than `window_seconds` are dropped
- if the current key already reached the quota, record is suppressed
- otherwise record passes and its timestamp is appended

Example:

```yaml
flood_control_config:
  enabled: true
  mode: rate_limit
  context_keys:
    - item_ref
  suppressed_levels:
    - INFO
  key_fields:
    - name
    - levelno
    - message
    - item_ref
  window_seconds: 30
  max_events_per_window: 2
```

### `deduplicate`

This mode suppresses repeated records with the same key inside `window_seconds`.

Effect:

- first record for a key passes
- repeated records with the same key inside the active window are suppressed
- after the window expires, the next matching record passes again

`key_fields` is mandatory in practice here: semantic validation rejects empty `key_fields` when `mode: deduplicate`.

Example:

```yaml
flood_control_config:
  enabled: true
  mode: deduplicate
  context_keys:
    - item_ref
  suppressed_levels:
    - INFO
  key_fields:
    - name
    - message
    - item_ref
  window_seconds: 60
```

## `force_log` Semantics

By default, the bypass attribute name is `force_log`.

Current filter logic is:

- if `getattr(record, force_log_attr, False)` is truthy, the record always passes
- strategy logic is skipped completely

This is used both for caller-supplied critical records and for internally emitted summary records.

Example with custom attribute name:

```yaml
flood_control_config:
  force_log_attr: always_emit
```

Then records carrying `always_emit=True` bypass flood control.

## Summary Emitter

When `emit_summary: true`, suppressed events are counted per record key.

Current behavior:

- counts are tracked separately for each key
- first suppression for a key starts the counter and timestamp
- summary is emitted only after at least `summary_interval_seconds` have elapsed since the previous summary timestamp for that key
- emitted summary uses logger with the same `record.name`
- emitted summary level is `summary_level`
- emitted summary carries `extra={force_log_attr: True}` so it is not suppressed again

Current summary message template is:

- `Flood control suppressed {count} records in mode={mode} for key={key}`

Example:

```yaml
flood_control_config:
  enabled: true
  mode: rate_limit
  emit_summary: true
  summary_level: WARNING
  summary_interval_seconds: 60
```

## Key Construction

Stateful modes and summaries use a frozen key derived from `key_fields`.

Current key-building rules:

- if a field name exists in active context, context value wins
- special field name `message` uses `record.getMessage()`
- otherwise runtime reads `getattr(record, field_name, None)`
- non-hashable values are converted to `repr(value)` before key assembly

Default `key_fields` are:

- `name`
- `levelno`
- `msg`
- `item_ref`

Note the distinction:

- default list uses `msg`
- special handling exists only for literal field name `message`

So if you want the fully formatted message text in the key, set `message` explicitly in `key_fields`.

## Cache Behavior

`max_cache_size` limits in-memory state for unique suppression keys.

Current eviction policy in stateful code paths is:

- track `last_seen_at` per key
- when cache size exceeds limit, evict the oldest keys first

This affects:

- `rate_limit` event-window cache
- `deduplicate` seen-key cache
- summary emitter state cache

## Recommended Defaults

For most current pipelines, the safest choices are:

- keep default `context_info_suppression`
- keep `suppressed_levels: [INFO]`
- only enable summaries when you actively need observability into suppressed volume

Use `rate_limit` or `deduplicate` only when you need a more selective policy than "drop all matching INFO logs inside active context".

## Related Documents

- `01_infra.md` — outer `observability` structure and field placement inside `infra.yaml`