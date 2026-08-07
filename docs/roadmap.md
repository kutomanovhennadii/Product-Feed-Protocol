# PFP Public Roadmap

This document provides a high-level overview of the planned development phases for the Product Feed Protocol (PFP) runtime. It is a living document driven by pragmatic needs, an AI-first approach, and independent maintainer constraints.

## Current Status: Initial Open Source Release (Phase 15 equivalent)
Currently, PFP is focusing on stabilizing its public Git presence.
* **Goals:** Standalone repository structure, CI/CD normalization, Golden Harness determinism guarantees, and comprehensive YAML/API documentation.

---

## 1. Immediate Release Goals

### PyPI Distribution & Packaging
* Setup trusted publishing flows.
* Establish formal SemVer adherence.
* Publish the core package (`pfp-core`) to PyPI for standard `pip install pfp-core` usage.

### AI-Agent First Developer Experience
* We have explicitly chosen to **not** build a graphical UI/TUI for mapping generation. 
* Instead, we are standardizing an AI-first approach where AI agents generate configurations on the user's behalf.
* **Goal:** Finalize the `AGENT.md` standard to ensure autonomous and error-free mapping generation by LLM tools.

---

## 2. Strategic Integrations (Dogfooding)

### Shopify ↔ Stripe Bridge
* Develop a robust, production-ready reference implementation serving as a bridge between Shopify and Stripe.
* This will serve as the primary continuous stress test and real-world application of PFP.

### Agentic Commerce Protocol (ACP)
* Implement payment orchestration processes over ACP.
* This is a strict requirement for realizing the full potential of the Shopify/Stripe integration.

---

## 3. Community & Maintenance Operations

### Maintenance Expectations (Best-Effort SLA)
* PFP is maintained by an independent developer working 6 days a week on primary obligations.
* **Support:** Issues and PRs are reviewed on a *best-effort* basis. There is no commercial SLA or guaranteed response time for free usage.

### On-Demand User Customization
* Feature requests, custom adapters, and enhancements will be prioritized pragmatically based on actual use cases and direct developer requests.

### AI Cookbook & Templates
* Build out a rich library of Reference Configurations (Golden YAMLs).
* Provide extensive examples specifically tailored to be digested by the community's AI agents for zero-friction user onboarding.