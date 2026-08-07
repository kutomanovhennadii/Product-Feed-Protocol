# Product Feed Protocol (PFP)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Repository](https://img.shields.io/badge/GitHub-Product--Feed--Protocol-181717?logo=github)](https://github.com/kutomanovhennadii/Product-Feed-Protocol)

Repository: [github.com/kutomanovhennadii/Product-Feed-Protocol](https://github.com/kutomanovhennadii/Product-Feed-Protocol)

Product Feed Protocol (PFP) is for teams that need to prepare a merchant catalog for external agentic-commerce platforms in a fast and predictable way. The project is built on top of the `Stripe Product catalog` and `Product Feed Spec` documents: they define the target protocol shape and constraints, while PFP provides the runtime that maps merchant product data into those external surfaces.

The practical value of PFP is not just feed conversion. It gives a team one controlled process for mapping, normalization, validation, artifact production, and delivery preparation. Instead of spreading this logic across ad hoc scripts, PFP compiles configuration into a runnable worker and returns a machine-readable `ExecutionReport` with outcome, diagnostics, and produced artifacts.

Shopify is the primary applied scenario at the current stage of the project. It is the most practical first route because a Shopify store already has a rich product catalog and a direct path into the broader agentic-commerce stack. At the same time, PFP is not limited to Shopify or to one store type. The core framing stays protocol-driven: adaptation to a specific merchant surface and publishing flow is defined by configuration rather than by a vendor-locked runtime.

For an engineering team, this means a library-first runtime that is assembled from configuration, started through a narrow Python API, and evaluated through `ExecutionReport` instead of informal logs or one-off output checks. The runtime supports structured logging, observability hooks, and optional Prometheus telemetry. It already includes a baseline data-protection model: secrets are resolved during initialization, diagnostics and logs go through redaction and sanitization, and the core remains stateless, with no built-in database and no persistent internal state between runs.

PFP is not a checkout server, payment orchestrator, or ACP host. Its role is to prepare correct product-feed artifacts and execution signals so that higher layers in the commerce and payment stack can safely work with catalog data and its updates.

## Installation

Clone the repository:

```bash
git clone https://github.com/kutomanovhennadii/Product-Feed-Protocol.git
cd Product-Feed-Protocol
```

Then, from the repository root:

```bash
pip install .
```

Optional dependency sets are available for richer transports and telemetry, including Prometheus, webhook delivery, S3, and SFTP.

## Minimal Quickstart

The canonical onboarding flow for PFP is intentionally split into distinct entry points:

- this root `README.md` explains what PFP is and where to start;
- [docs/api.md](docs/api.md) defines the current Python API contract and the minimum IaC bundle required to make that API runnable;
- [docs/troubleshooting.md](docs/troubleshooting.md) covers the first operational failures a new user is likely to hit;
- [examples/README.md](examples/README.md) helps you choose the right runnable scenario;
- [examples/01_minimal_quickstart/README.md](examples/01_minimal_quickstart/README.md) is the shortest first run;
- [examples/02_csv_input/README.md](examples/02_csv_input/README.md) is the canonical CSV-input to CSV-output end-to-end path.

The recommended first step is the runnable example in [examples/01_minimal_quickstart/README.md](examples/01_minimal_quickstart/README.md).

From the repository root:

```bash
cd examples/01_minimal_quickstart
python run.py
```

If you want to see the public Python API directly, the core usage path is:

```python
from pathlib import Path

from pfp_runtime import PFPFactory


factory = PFPFactory()
worker = factory.build_worker(infra_path=Path("examples/01_minimal_quickstart/infra.yaml"))

input_bytes = Path("examples/01_minimal_quickstart/input/input.jsonl").read_bytes()
report = worker.run(input_bytes)

print(report.status)
print(report.message)
print(len(report.artifacts))
```

The public runtime surface is intentionally narrow:

- `PFPFactory`
- `PFPWorker`
- `FactoryConfigError`
- `get_pfp_factory`

The main lifecycle is straightforward:

1. Describe the runtime through a small IaC bundle centered around `infra.yaml`.
2. Build a worker with `PFPFactory().build_worker(infra_path=...)`.
3. Execute one run with `worker.run(input_bytes)`.
4. Inspect the returned `ExecutionReport` for status, diagnostics, timings, and produced artifacts.

That first step is important: PFP is not a single-function runtime that works from Python code alone. A runnable setup needs configuration files such as `infra.yaml`, `mapping.yaml`, `policies.yaml`, a schema YAML, and publishing-related YAML files. Use [docs/api.md](docs/api.md) for the contract-level overview, [config/docs/README.md](config/docs/README.md) for the file-by-file YAML reference, and [docs/troubleshooting.md](docs/troubleshooting.md) when the first run does not behave as expected.

That final `ExecutionReport` is the real run contract. It gives you more than generated files alone, including:

- execution status;
- failure location and reason code;
- validation diagnostics;
- produced artifacts;
- timings and usage counters.

## What The Runtime Already Covers

PFP already covers a broader value chain than a single JSONL-to-CSV demo. The current staging package includes:

- input formats such as CSV, JSON, JSONL, and streaming variants;
- connector mapping into the unified model;
- policy-driven validation and diagnostics;
- schema-based artifact compilation;
- archive and delivery targets including local, S3-compatible, HTTP, and SFTP surfaces;
- observability integrations, including Prometheus-enabled scenarios.

This is why the project should be read as a configuration-first runtime for catalog transformation, not as a one-off converter.

## Where To Go Next

Use [docs/api.md](docs/api.md) when you want the contract of the Python API and the role of the required YAML files around it.

Use [docs/troubleshooting.md](docs/troubleshooting.md) when the first run fails or when cwd, relative paths, optional dependencies, or YAML bundle completeness are in doubt.

Start with [examples/README.md](examples/README.md) if you want a guided map of runnable scenarios, from minimal quickstart to Shopify realtime, streaming ingestion, and observability.

Use [config/docs/README.md](config/docs/README.md) as the source of truth for YAML configuration structure and file-by-file runtime setup.

Use [schemas/](schemas/) when you need to inspect the protocol schema files referenced by runtime configuration.

Use [tests/](tests/) when you want to inspect the currently exercised runtime behavior and contract boundaries.

## Scope Note

This README is meant to get a new user from clone to the first successful run and to explain why the project exists. It does not try to replace full configuration reference, scenario-specific walkthroughs, or future governance and release-management documentation.

The recommended entrypoint today is the Python API plus runnable examples. 