# Security Policy

## Supported Versions
Only the latest major version of the PFP runtime is actively supported for security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of the Product Feed Protocol (PFP) runtime very seriously. 

If you discover a security vulnerability within PFP, please do NOT report it by creating a public GitHub issue in [the repository](https://github.com/kutomanovhennadii/Product-Feed-Protocol). Instead, please follow the process below:

1. Send an email to [kutomanov.hennadii@gmail.com](mailto:kutomanov.hennadii@gmail.com).
2. Include a detailed description of the vulnerability, including steps to reproduce.
3. Include the version of PFP you are using and your Python environment details.

Security reports are reviewed on a best-effort basis. If the vulnerability is accepted, we will coordinate with you to publish a fix and, when appropriate, a security advisory.

## Scope

Vulnerabilities within the scope of this responsible disclosure include:
- Remote Code Execution (RCE) via malicious schemas or payloads.
- Secret exposure or leakage in logs/artifacts.
- File system escapes (Path Traversal) during local I/O handling.

Issues related to the specific external infrastructure you deploy PFP on (e.g., your own proxy configurations, cloud IAM roles) are outside of PFP's threat model scope unless they are caused by PFP mishandling valid configurations.