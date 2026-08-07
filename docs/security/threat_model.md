# PFP Threat Model

This document outlines the threat model for the PFP runtime based on its offline / worker-centric architecture (`PFPFactory().build_worker()`).

## Architecture Context

PFP is designed as an agentic commerce processing runtime. It is **not** a persistent web server (FastAPI/Uvicorn are only used for optional webhook extensions or metrics, not core processing). It is typically invoked as a CLI execution, a scheduled Cron job, or a Kubernetes worker.

### Components
1. **Input Sources:** External raw data streams (HTTP, SFTP, S3, filesystem).
2. **PFP Worker (`PFPWorker`):** The core process that ingests mapped schemas, evaluates them, normalizes data, and produces an artifact.
3. **Artifact Destinations:** Output channels where the `ProducedArtifact` is published.

## Trust Boundaries

1.  **Operator / Process Boundary:** The entity invoking the PFP Python process is highly privileged. We assume the host OS boundary is secure via external means (e.g., containerization, IAM).
2.  **Configuration Boundary:** YAML configurations, schemas, and `infra.yaml` are considered **trusted** inputs. PFP trusts the mappings provided to it.
3.  **Payload Boundary:** The raw data payloads (e.g., JSONL, CSV rows from external feeds) are considered **untrusted, potentially hostile** environments.

## Core Threats

### 1. Payload Injection and Memory Exhaustion (Untrusted Payloads)
*   **Threat:** A malicious data provider submits malformed chunks (e.g., a multi-gigabyte JSON object without newlines) to exhaust memory or trigger regex back-tracking in normalizers.
*   **Mitigation:** `Iterable[bytes]` architecture. Files are processed via streaming (`ijson`, chunked iteration). PFP refuses to load entire source payloads into memory, relying instead on strict generator execution. 

### 2. Path Traversal
*   **Threat:** Output configurations or target names contain `../` leading to artifacts being published outside expected destination folders (e.g., writing to `/etc/artifact.csv`).
*   **Mitigation:** Built-in Path guards in the standard Local File Adapters prevent escaping the workspace target root.

### 3. Unexpected Server Side Request Forgery (SSRF)
*   **Threat:** A user tricks PFP into making internal network requests by using URLs as payload fields that auto-trigger API calls.
*   **Mitigation:** PFP pipeline runners operate strictly on pre-configured adapter endpoints defined in `infra.yaml`. The core mapping module *never* dynamically issues HTTP requests based on data embedded inside the payload `Iterable`.

## Out of Scope
*   Securing the environment where keys are stored. (PFP resolves secrets via `secret_resolver` but relies on the host OS / env vars to protect the actual values).
*   Man-in-the-middle (MITM) attacks if the operator explicitly configures insecure HTTP/FTP endpoints without TLS. PFP uses standard Python client security models (requests, boto3) which verify SSL by default, but operator overrides bypass this.