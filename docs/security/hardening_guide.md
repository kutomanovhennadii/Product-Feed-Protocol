# Scope and Harding Guide

This document aggregates the requirements, operational bounds, and system hardening practices required to securely run the PFP framework.

## 1. Security Scope

PFP is considered an **Agentic Infrastructure Tool**. 
*   **In-Scope:** Data normalization integrity, memory bounds, deterministic behavior under hostile payloads, output path isolation.
*   **Out-of-Scope:** Host environment containerization, securing CI pipelines orchestrating PFP, external database IAM enforcement. PFP is not a firewall.

## 2. Secrets Management

*   **No Hardcoded Secrets:** PFP's `infra.yaml` format uses standard YAML explicit variables or Jinja-style env extraction.
*   **Secret Resolver:** Core components utilize `pfp_utils.security.secret_resolver` logic. Secrets resolve from the environment (`.env`) at runtime.
*   **Logging Guard:** By architectural mandate, variables mapped to `SecretStr` types in `pydantic` configurations are automatically redacted (`***`) when objects are dumped into diagnostics or logs.

## 3. General Hardening Requirements

When deploying `PFPWorker` into production, follow these principles:

1.  **Drop Privileges:** Even though PFP doesn't require root, do not run the Python process as root. Run as a restricted user mapping exactly to the local folders used for artifact consumption or generation.
2.  **Disable Debug Diagnostics in Prod:** Ensure error traces or detailed input diagnostic logs don't inadvertently write user PII into external logging services.
3.  **TLS Enforcement:** For `HTTP`, `S3`, and `SFTP` input/output configurations in `infra.yaml`, explicitly use `https://` / `sftp://`. PFP clients (e.g. `httpx`, `paramiko`) rely on TLS verification implicitly; do not pass explicit skip-verify flags unless executing inside isolated corporate networks.
4.  **Network Isolation:** PFP workers should reside in private subnets, fetching data from NAT gateways, isolating them from inbound internet connections.