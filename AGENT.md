# PFP Agent Integration Pack

This document (`AGENT.md`) alongside `agent_contract.json` is designed for AI agents (GitHub Copilot, cursor, auto-gpt, etc.) to quickly understand the surface area of the Product Feed Processor (PFP) without parsing human-oriented paragraphs.

## 1. Source of Truth
* **Runtime exports:** `PFPFactory`, `PFPWorker`, `FactoryConfigError`, `get_pfp_factory`.
* **Factory input:** `PFPFactory().build_worker(infra_path=...)`.
* **Execution input:** `PFPWorker.run(input_data: bytes)`.
* **Reference Docs:**
  * For Python API and failure semantics: `docs/api.md`
  * For YAML schemas: `config/docs/README.md`
  * For output stability: `docs/determinism.md`
  * For a runnable scenario: `examples/01_minimal_quickstart/README.md`

## 2. Execution Outcome Model
`ExecutionReport.status` currently uses only two normalized status tokens:

* `SUCCESS`
* `FAILED`

Current failure-step tokens exposed by the runtime:

* `INGESTION_EXTRACT`
* `CORE_BUILD`
* `PUBLISH`
* `INTERNAL`

Current stable `reason_code` values exposed by the runtime:

* `INGESTION.EXTRACT_TIMEOUT`
* `INGESTION.EXTRACT_ERROR`
* `CORE.CONTRACT_ERROR`
* `CORE.VALIDATION_FAILED`
* `INTERNAL.ERROR`
* `PUBLISH.TIMEOUT`
* `PUBLISH.ERROR`

## 3. Integration Semantics (DIFF & Edits)
When generating configuration files for PFP:
* **Prefer Full Replacement:** Over writing complex regex/sed diffs for YAML, generate and replace the whole section or file to ensure Pydantic validation passes.
* **Determinism:** Comply with the rules in `docs/determinism.md` (e.g., inject `generated_at` when mocked, expect byte-for-byte identical output in tests).

## 4. Basic Validation Commands
Agents should run these commands to verify their setup:

* **Smoke Test (Install & Import):**
  ```bash
  pip install -e . && python -c "from pfp_runtime import PFPFactory"
  ```
* **Basic Run (Runnable Example):**
  ```bash
  cd examples/01_minimal_quickstart && python run.py
  ```
* **Contract Validation:**
  ```bash
  pytest tests/test_agent_contract.py -q
  ```
* **Fast Test Run (Unit & Integration only):**
  ```bash
  pytest tests/ -m "not matrix and not e2e and not perf and not chaos"
  ```

## 5. Troubleshooting
If Pydantic throws `ValidationError`, consult the schemas located in `config/docs/` to correct the output YAML generation. See `docs/troubleshooting.md` for common logging patterns and debugging traces.