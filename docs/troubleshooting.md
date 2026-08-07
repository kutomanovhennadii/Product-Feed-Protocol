# Troubleshooting

This document covers the first operational failures a new PFP user is most likely to hit.

It is intentionally practical. Each case is based on the current runtime and example behavior rather than on generic FAQ wording.

Use this document together with:

- [README.md](../README.md) for the repository entry point;
- [api.md](api.md) for the Python API contract and the minimum IaC bundle;
- [examples/README.md](../examples/README.md) for runnable scenario selection;
- [config/docs/README.md](../config/docs/README.md) for the YAML IaC reference.

## Wrong Working Directory When Running An Example

**Symptom**

- the example fails to find local YAML files or output paths;
- the same example works from its own directory but fails when launched from somewhere else;
- archive-related paths end up outside the example directory.

**Probable cause**

Some example layouts rely on the current working directory when resolving relative paths. This is not theoretical: `04_local_archive/run.py` explicitly switches into the example directory before building the worker and running the pipeline.

**How to check**

- print the current working directory before calling `PFPFactory().build_worker(...)`;
- compare your launch location with the example directory;
- if the scenario is archive-related, compare where relative archive paths are expected to land.

**What to fix**

- run the example from its own directory, for example `cd examples/04_local_archive` then `python run.py`;
- if you embed the example logic into your own launcher, either use absolute paths or switch the current working directory deliberately before execution;
- treat cwd-sensitive examples as configuration examples, not as proof that every relative path is resolved from `infra.yaml`.

## `infra.yaml` Is Not Found Or Relative Paths Break

**Symptom**

- worker creation fails before execution starts;
- the runtime cannot load configuration referenced from `infra.yaml`;
- files referenced by relative paths cannot be resolved.

**Probable cause**

The public API starts from `infra_path`, and that file is the entrypoint into the rest of the YAML bundle. If `infra_path` is wrong, empty, or points into a layout that does not match the expected local files, the runtime cannot assemble the manifest.

**How to check**

- confirm that `infra_path` is a real path to the intended `infra.yaml`;
- confirm that the neighboring YAML files referenced from that setup actually exist;
- compare your directory layout to `examples/01_minimal_quickstart` or `examples/02_csv_input`.

**What to fix**

- pass a real path to `PFPFactory().build_worker(infra_path=...)`;
- if you use relative paths, make sure they are valid from your actual launch context;
- when in doubt, start from a copied example directory and mutate it gradually instead of building a fresh layout from memory.

## Only `infra.yaml` Exists But The Rest Of The YAML Bundle Is Missing

**Symptom**

- the runtime starts from `infra.yaml` but fails during manifest assembly or later setup;
- the project “looks configured” because `infra.yaml` exists, but the example is still not runnable.

**Probable cause**

PFP is config-driven. `infra.yaml` is not a self-sufficient configuration universe. The starter examples rely on a minimum bundle that includes:

- `infra.yaml`
- `mapping.yaml`
- `policies.yaml`
- schema YAML
- archive config
- client config

In the two starter examples this is concretely represented by:

- `infra.yaml`
- `mapping.yaml`
- `policies.yaml`
- `stripe.product_feed-1.0.0.yaml`
- `archive.noop.yaml`
- `client.noop.yaml`

**How to check**

- compare your directory against `examples/01_minimal_quickstart` or `examples/02_csv_input`;
- verify that you have not created only `infra.yaml` while omitting the mapping, policy, schema, or publishing files;
- use [config/docs/README.md](../config/docs/README.md) as the authoritative checklist of configuration surfaces.

**What to fix**

- build a complete starter bundle instead of a single top-level YAML file;
- begin from a known-good example directory and edit one file at a time;
- use [api.md](api.md) for the contract-level overview and [config/docs/README.md](../config/docs/README.md) for file-by-file IaC details.

## JSONL Mapping Fails Because Nested Fields Are Not Routed

**Symptom**

- JSONL input looks structurally correct, but mapped output fields are empty or missing;
- a nested payload works in your head but not in the runtime;
- required mapping fields are reported as missing.

**Probable cause**

The current connector mapping layer performs exact key lookup against the source record. `ConnectorMapper` checks `if source_key in record` and does not traverse nested objects automatically. This is also reflected in `examples/03_jsonl_input`, which keeps nested objects for realism but mirrors the routed fields at the top level.

**How to check**

- inspect your source record and verify whether the mapped keys really exist at the top level;
- compare your mapping file to `examples/03_jsonl_input/mapping.yaml` and its fixture design;
- if your mapping expects something like a nested path selector, check whether the runtime actually supports it in the current example surface before assuming it does.

**What to fix**

- expose the fields required by the mapping at the top level of the input record;
- or adapt the source fixture so the connector mapping can see the expected keys directly;
- use `examples/03_jsonl_input` as the current reference for nested-looking payloads that still route through top-level keys.

## Local Archive Output Lands In The Wrong Place Or Fails On `output_dir`

**Symptom**

- the local archive example writes files into an unexpected directory;
- local archiving fails with an `output_dir does not exist or is not a directory` error;
- archive output appears to depend on where the process was launched.

**Probable cause**

`LocalArchiver` resolves `output_dir` with `Path(iac.output_dir).expanduser().resolve()` and requires that directory to exist before the run. It does not create the directory for you. Combined with relative path usage, this means launch context matters.

**How to check**

- inspect the configured `output_dir` in the local archive YAML config;
- verify that the destination directory already exists;
- compare your launch behavior with `examples/04_local_archive/run.py`, which changes cwd before execution.

**What to fix**

- create the target directory before running the pipeline if you use the local archiver;
- use an absolute `output_dir` if you need deterministic placement independent of cwd;
- if you keep relative paths, launch the example from the intended directory or align your custom runner with the example behavior.

## Prometheus Example Fails Before Running

**Symptom**

- `08_observability_prometheus` fails immediately before the pipeline run;
- the error asks you to install optional Prometheus dependencies.

**Probable cause**

The example imports `CollectorRegistry` and `generate_latest` from `prometheus_client`. In the current example code, missing that package raises a `RuntimeError` with the explicit message to install the optional Prometheus dependencies before running example 08.

**How to check**

- run `examples/08_observability_prometheus/run.py` and inspect the exception text;
- verify whether `prometheus_client` is available in your environment.

**What to fix**

- install the optional Prometheus dependency set in the environment where you run example 08;
- if you are validating only the base runtime, start with examples `01` through `05` instead of treating example 08 as part of the minimum install contract.

## How To Tell Config Problems From Input Problems

**Symptom**

- a run fails, but it is not obvious whether the issue is in your YAML bundle or in the payload bytes;
- you see validation issues and are not sure whether the runtime itself is misconfigured.

**Probable cause**

The runtime boundary is split in two:

- configuration assembly happens before or during worker construction and early pipeline setup;
- payload-specific problems appear during record processing and validation.

In practical terms, missing YAML files, broken relative paths, invalid archive destinations, or incomplete IaC bundles usually point to configuration issues. Record-level validation diagnostics and dropped items usually point to input issues.

**How to check**

- first verify that a known-good starter example runs unchanged in your environment;
- then compare your modified configuration bundle against that example;
- inspect `ExecutionReport.status`, `ExecutionReport.message`, `ExecutionReport.reason_code`, `ExecutionReport.validation_report`, and produced artifacts together instead of looking only at stdout.

**What to fix**

- if the known-good example fails unchanged, fix environment or configuration-path issues first;
- if the known-good example works but your modified payload fails, inspect mapping and validation expectations before changing runtime wiring;
- isolate one variable at a time: configuration layout, then mapping, then payload.

## Recommended Debug Order

When a first run fails, use this order:

1. Confirm you are starting from a known-good example directory.
2. Confirm cwd and `infra_path` point where you think they do.
3. Confirm the full YAML bundle exists, not just `infra.yaml`.
4. Confirm optional dependencies are installed for advanced examples.
5. Only then inspect payload-specific mapping and validation behavior.

This sequence matches the current runtime surface better than jumping directly into deep payload debugging.