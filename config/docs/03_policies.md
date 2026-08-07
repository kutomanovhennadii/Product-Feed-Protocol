# policies.yaml

`policies.yaml` configures the core policy bundle used during artifact production.

This document reflects the actual contract implemented by:

- `src/pfp_core/policies/policy_config.py`
- `src/pfp_core/policies/policy_config_loader.py`
- `src/pfp_core/policies/policy_bundle_builder.py`
- `src/pfp_core/policies/domain/strictness.py`
- `src/pfp_core/policies/domain/eligibility.py`
- `src/pfp_core/policies/infra/fault_isolation_policy.py`

## What This File Controls

Current `policies.yaml` controls three policy areas that are actually wired into the runtime policy bundle:

- strictness policy
- eligibility policy
- fault isolation policy

Important current limitation:

- `logging` and `telemetry` policy classes exist in `pfp_core.policies.infra`, and `PolicyBundle` has optional slots for them
- but `PolicyConfig` and `build_policy_bundle()` do not currently load them from `policies.yaml`
- runtime logging and telemetry settings are configured through `infra.yaml` under `observability`, not through this file

## File Shape

```yaml
version: "1.0"

core:
  strictness:
    strategy: "fail_on_error"
  eligibility:
    checkout_requirements:
      merchant_fields:
        - "seller_tos"
        - "seller_privacy_policy"
  fault_isolation:
    strategy: "SKIP_ITEM"
```

## Root Fields

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `version` | `str` | yes | — | Required. `PolicyConfig` accepts only normalized version `1.0`. |
| `core` | `object` | yes | — | Required mapping. Unknown keys are rejected. |

Important current limitation:

- root keys other than `version` and `core` are rejected
- top-level `strictness`, `eligibility`, `logging`, and `telemetry` are not part of the current YAML contract
- top-level `infrastructure` is also not accepted from YAML, even though `PolicyConfig` exposes a derived `infrastructure` field in memory

## `core`

`core` contains the user-editable policy configuration.

Allowed keys:

- `strictness`
- `eligibility`
- `fault_isolation`

Unknown keys under `core` are rejected.

### `core.strictness`

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `strategy` | `str` | yes | — | Must normalize to one of `fail_on_error`, `drop_invalid`, `warn_only`. |

Supported strictness strategies:

| Value | Effect |
|---|---|
| `fail_on_error` | Keep diagnostics as-is. If any diagnostic has severity `ERROR`, strictness marks the item as failed. |
| `drop_invalid` | Keep diagnostics as-is. If any diagnostic has severity `ERROR`, the invalid item is dropped, but processing continues. |
| `warn_only` | Downgrade `ERROR` diagnostics to `WARN`. Processing continues without failing or dropping the item. |

### `core.eligibility`

`eligibility` is optional in practice. If omitted, it is parsed from an empty mapping and the resulting policy is effectively inactive.

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `checkout_requirements` | `object` | no | `{}` | Unknown keys are rejected. |

#### `core.eligibility.checkout_requirements`

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `merchant_fields` | `list[str]` | no | `[]` | Must be a list or tuple. Values are interpreted as required keys under `merchant`. |

Behavior:

- eligibility checks only run when the product record has `is_eligible_checkout` set
- when that flag is truthy, each listed `merchant_fields` entry must exist and be truthy under `merchant.<field>`
- missing fields produce diagnostics with code `ELIGIBILITY_CHECKOUT_MISSING_REQ`

### `core.fault_isolation`

`fault_isolation` is optional in practice. If omitted, it is parsed from an empty mapping.

| Field | Type | Required | Default | Validation / behavior |
|---|---|---|---|---|
| `strategy` | `str` | no | `SKIP_ITEM` | Value is uppercased and must be one of `SKIP_ITEM`, `FAIL_FAST`, `IGNORE`. |

Supported fault-isolation strategies:

| Value | Effect |
|---|---|
| `SKIP_ITEM` | Log the error and continue with the next item. |
| `FAIL_FAST` | Re-raise the error after logging. |
| `IGNORE` | Valid config token; policy keeps the strategy value, but the current `FaultIsolationPolicy.handle_error()` implementation has explicit branching only for `FAIL_FAST`, so non-`FAIL_FAST` behavior is effectively "log and continue". |

## Actual In-Memory Structure

`PolicyConfig` exposes:

- `version`
- `core`
- `infrastructure`

But only `version` and `core` are loaded from YAML.

Current behavior of `infrastructure`:

- it is derived automatically in `PolicyConfig.from_dict()`
- `infrastructure.fault_isolation.strategy` is copied from `core.fault_isolation.strategy`
- YAML users cannot configure `infrastructure.logging` or `infrastructure.telemetry` through `policies.yaml`

## Validation Rules

Current validation enforced by the loader/config layer:

- YAML root must be a mapping
- config must not be empty
- root must contain `version`
- root must contain `core`
- unknown root keys are rejected
- `version` must normalize to `1.0`
- `core.strictness.strategy` must be a string and one of the supported strictness strategies
- `core.eligibility.checkout_requirements`, when present, must be a mapping
- `core.eligibility.checkout_requirements.merchant_fields`, when present, must be a list or tuple
- `core.fault_isolation.strategy`, when present, must be a string and one of `SKIP_ITEM`, `FAIL_FAST`, `IGNORE`

## `fail_on_error_diagnostics` And `report.failed_step`

`fail_on_error_diagnostics` is not a field in `policies.yaml`.

Current runtime behavior:

- `policies.yaml` produces diagnostics through strictness, eligibility, and other core logic
- later, pipeline runtime decides whether accumulated `ERROR` diagnostics should fail the run
- that decision is controlled by `runner_manifest.core.fail_on_error_diagnostics`, not by `PolicyConfig`

When runtime has `fail_on_error_diagnostics=True` and the validation report contains `ERROR` diagnostics:

- `ctx.failed_step` is set to `CORE_BUILD`
- `ctx.reason_code` becomes `CORE.VALIDATION_FAILED`
- pipeline execution stops before publish

So the relationship is:

- `policies.yaml` influences which diagnostics are produced or downgraded
- `fail_on_error_diagnostics` influences whether those diagnostics become a run-level failure
- `report.failed_step` reflects that runtime decision, not a direct field from `policies.yaml`

## Complete Example

```yaml
version: "1.0"

core:
  strictness:
    strategy: "fail_on_error"

  eligibility:
    checkout_requirements:
      merchant_fields:
        - "seller_tos"
        - "seller_privacy_policy"

  fault_isolation:
    strategy: "SKIP_ITEM"
```

Minimal valid example:

```yaml
version: "1.0"
core:
  strictness:
    strategy: "drop_invalid"
```

## Related Documents

- `01_infra.md` — `producer.policy_file` reference from `infra.yaml`
- `05_schema.md` — schema-driven rules that later interact with policy decisions
