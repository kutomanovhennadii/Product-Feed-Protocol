# Supply Chain Security

This document details the dependencies and the supply chain properties of the PFP runtime environment.

## Python Dependency Tree

PFP minimizes its footprint to reduce supply chain attack surface. External dependencies are strictly categorized and constrained within `pyproject.toml`.

### Core Dependencies 
Required for baseline execution:
*   `PyYAML` - For parsing configurations and manifests.
*   `pydantic` - For strict data structure validation of schemas and configurations.
*   `ijson` - For memory-safe, iterative JSON parsing of large raw payloads.

*These packages undergo strict version pinpointing in deployment lockfiles and are commonly audited in the Python security ecosystem.*

### Optional / Extras Dependencies
These dependencies are only loaded if specific integration extras are activated via `pip install pfp-core[extra]`. If you do not use S3, you do not inherit `boto3` risks:
*   `boto3` (s3 extra)
*   `paramiko` (sftp extra)
*   `fastapi`, `uvicorn`, `httpx` (webhook extra)
*   `prometheus-client` (prometheus extra)

## Publishing and Provenance
*   PFP is versioned via `pyproject.toml`.
*   Continuous Integration checks leverage standard ecosystem tools (`ruff`, `black`, `mypy`) alongside `gitleaks` for accidental secret prevention.
*   Future PyPI distributions will employ trusted publishers (OIDC) to eliminate static repository credentials.