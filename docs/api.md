# Python API

This document explains the current user-facing Python API of the public PFP runtime.

Its role in the onboarding flow is intentionally narrow:

- the root [README.md](../README.md) explains what PFP is and where to start;
- this file explains the current Python API contract and the minimum YAML-based IaC bundle required to make that API runnable;
- [examples/README.md](../examples/README.md) helps choose a runnable scenario;
- [01_minimal_quickstart](../examples/01_minimal_quickstart/README.md) is the shortest first run;
- [02_csv_input](../examples/02_csv_input/README.md) is the canonical CSV-input to CSV-output end-to-end path.

This file does not replace the YAML reference in [config/docs](../config/docs/README.md), the data-contract documents planned for Story 4, or the troubleshooting document planned for the next Story 3 step.

## IaC Reference

The Python API in PFP is only one half of the runtime contract. The second half is the YAML-based IaC bundle described in [config/docs/README.md](../config/docs/README.md).

Use the IaC reference when you need to understand or author the configuration files around `infra_path`:

- [config/docs/README.md](../config/docs/README.md) for the full map of the configuration surface;
- [config/docs/01_infra.md](../config/docs/01_infra.md) for `infra.yaml` and path composition rules;
- [config/docs/02_mapping.md](../config/docs/02_mapping.md) for `mapping.yaml` and source-to-model routing;
- [config/docs/03_policies.md](../config/docs/03_policies.md) for `policies.yaml` and validation policy;
- [config/docs/04_publishing.md](../config/docs/04_publishing.md) for archive and client publishing configs;
- [config/docs/05_schema.md](../config/docs/05_schema.md) for schema YAML structure;
- [config/docs/06_advanced.md](../config/docs/06_advanced.md) for richer and more advanced runtime patterns.
- [config/docs/07_flood_control.md](../config/docs/07_flood_control.md) for flood-control configuration and rate-limiting related runtime behavior.

## What The User-Facing API Is

The public runtime surface is intentionally small:

- `PFPFactory`
- `PFPWorker`
- `FactoryConfigError`
- `get_pfp_factory`

The runtime is designed so that a caller assembles a worker from configuration and then executes one run against raw input bytes. The public API is therefore not an object graph for manually wiring internal subsystems. It is a narrow contract for turning a validated runtime configuration into a runnable worker.

In practice, most users only need `PFPFactory` and `PFPWorker`:

```python
from pathlib import Path

from pfp_runtime import PFPFactory


factory = PFPFactory()
worker = factory.build_worker(infra_path=Path("examples/01_minimal_quickstart/infra.yaml"))
report = worker.run(Path("examples/01_minimal_quickstart/input/input.jsonl").read_bytes())

print(report.status)
print(report.message)
print(len(report.artifacts))
```

`get_pfp_factory()` is only a convenience constructor for the same factory contract. It does not define a second runtime model.

## Minimal Lifecycle

The canonical lifecycle is:

1. Describe the runtime through a configuration bundle centered around `infra.yaml`.
2. Build a worker with `PFPFactory().build_worker(infra_path=...)`.
3. Execute one run with `worker.run(input_bytes)`.
4. Inspect the returned `ExecutionReport`.

This lifecycle is deliberately stable and compact. The main user decision is not which Python methods to chain, but which configuration files to provide to the runtime.

## `infra_path` Contract And `FactoryConfigError`

`build_worker` accepts one required keyword argument:

- `infra_path`: path to the top-level infrastructure YAML file.

At the public contract level, `infra_path` must be:

- a `str` or `pathlib.Path`;
- non-empty after trimming;
- a path to the runtime entry configuration that describes the rest of the bundle.

If this contract is violated, the factory raises `FactoryConfigError`.

At this layer, `FactoryConfigError` means the caller has not satisfied the user-facing factory contract. It is the boundary error for invalid factory input, not a generic wrapper for every downstream runtime failure.

## Why The API Is Config-Driven

PFP is not a pure in-code API where a caller passes a few Python objects and gets a feed artifact back. The runtime is configuration-driven by design.

That design matters because the runtime is responsible for more than one transformation step:

- mapping source fields into the runtime model;
- applying validation policy;
- compiling output artifacts through schema definitions;
- preparing archive and publishing behavior;
- producing a normalized `ExecutionReport` instead of ad hoc side effects.

Those responsibilities are intentionally described in YAML rather than spread across handwritten Python glue. The Python API is the narrow execution surface around that configuration.

So the honest quickstart is not “instantiate `PFPFactory` and call `run`”. The honest quickstart is “prepare a small configuration bundle, build a worker from `infra.yaml`, then execute one run against input bytes”.

## What You Must Prepare Before The First Run

Before a first successful run, the caller needs more than `input_bytes`. The caller must prepare a minimum IaC bundle around `infra.yaml`.

In the starter examples, that bundle is visible directly in:

- [01_minimal_quickstart](../examples/01_minimal_quickstart/README.md)
- [02_csv_input](../examples/02_csv_input/README.md)

The minimum quickstart bundle includes these file roles:

- `infra.yaml` for top-level runtime wiring and path composition;
- `mapping.yaml` for source-to-model mapping;
- `policies.yaml` for validation policy;
- schema YAML for artifact compilation;
- archive config for artifact handling;
- client config for delivery and publishing behavior.

In the two starter examples, this becomes a concrete file layout:

- `infra.yaml`
- `mapping.yaml`
- `policies.yaml`
- `stripe.product_feed-1.0.0.yaml`
- `archive.noop.yaml`
- `client.noop.yaml`

The examples also include input fixtures, expected output, and a `run.py` launcher. Richer examples extend the same pattern with more specialized payloads, adapters, and publishing behavior rather than replacing the model.

Use [config/docs/README.md](../config/docs/README.md) as the file-by-file YAML reference. This document only explains the role of the bundle in the public API contract.

## What `PFPWorker.run(...)` Returns

`PFPWorker.run(input_bytes)` returns an `ExecutionReport`.

At the public contract level, `ExecutionReport` is the machine-readable outcome of one runtime execution. It is the main object a caller should inspect after every run.

The report contains these important outcome categories:

- `status` for the final normalized execution status;
- `failed_step` for the pipeline stage where execution failed, or empty on success;
- `reason_code` for a stable machine-readable failure reason;
- `message` for a human-readable summary;
- `validation_report` for the run-level validation outcome;
- `artifacts` for produced artifacts;
- `timings` for per-step execution timings;
- `usage` for normalized run counters and usage data;
- optional runtime correlation fields such as `run_id`, `correlation_id`, and `error_type`.

For a first integration, the most important fields are usually:

- `status`
- `message`
- `artifacts`
- `validation_report`
- `reason_code`

This is why the runtime should be integrated against `ExecutionReport`, not against console output or assumptions about files alone.

## Execution Status And Failure Semantics

The current runtime normalizes `ExecutionReport.status` to exactly two tokens:

- `SUCCESS`
- `FAILED`

There are no public `ExecutionReport.status` values such as `VALIDATION_FAILED`, `RUNTIME_ERROR`, or `PARTIAL_SUCCESS`.

When a run succeeds, `failed_step` is empty and `reason_code` is empty.

When a run fails, the current runtime emits these `failed_step` tokens:

- `INGESTION_EXTRACT`
- `CORE_BUILD`
- `PUBLISH`
- `INTERNAL`

The current stable machine-readable `reason_code` values are:

- `INGESTION.EXTRACT_TIMEOUT`
- `INGESTION.EXTRACT_ERROR`
- `CORE.CONTRACT_ERROR`
- `CORE.VALIDATION_FAILED`
- `INTERNAL.ERROR`
- `PUBLISH.TIMEOUT`
- `PUBLISH.ERROR`

The validation-related failure path is therefore reported as `status="FAILED"` with `reason_code="CORE.VALIDATION_FAILED"`, not as a separate status token.

## What This Document Does Not Cover

This document intentionally does not include:

- the full YAML reference from [config/docs](../config/docs/README.md);
- full Unified Model or diagnostics structure details;
- determinism and golden-harness guarantees;
- CI, build, or install policy.

Those surfaces belong to other documents and other stories. Keeping this file narrow is part of the public API contract discipline.

## Where To Go Next

- Use [config/docs/README.md](../config/docs/README.md) for the YAML reference.
- Use [examples/README.md](../examples/README.md) for the runnable scenario map.
- Start with [01_minimal_quickstart](../examples/01_minimal_quickstart/README.md) for the shortest first run.
- Use [02_csv_input](../examples/02_csv_input/README.md) for the canonical CSV-input to CSV-output end-to-end path.
- Use the root [README.md](../README.md) when you need the product framing and repository entry point.