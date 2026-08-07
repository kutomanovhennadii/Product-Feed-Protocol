# Contributing to PFP

First off, thank you for considering contributing to the Product Feed Protocol (PFP) runtime! 

This document outlines the process for setting up a development environment, formatting your code, running tests, and proposing changes.

## 1. Development Environment Setup

You can set up a completely working local development environment in under 10 minutes.

### Prerequisites
* Python 3.10+
* Git

### Installation Steps
1. Fork and clone the repository.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install the package in editable mode with development dependencies:
   ```bash
   pip install -e .
   pip install pytest pytest-cov ruff black mypy build
   ```

You are now ready to develop! To verify your setup, run the smoke test:
```bash
python -c "from pfp_runtime import PFPFactory; print('Setup successful!')"
```

## 2. Code Style and Linting

PFP strictly enforces code quality to maintain a healthy codebase. We use `ruff` (for linting), `black` (for formatting), and `mypy` (for static type checking).

Before submitting a Pull Request, ensure your code passes all checks:

```bash
black src tests
ruff check --fix src tests
mypy src
```
CI will fail if any of these checks report issues.

## 3. Testing Requirements

Our testing pipeline is robust and split into categories to save developer time. 

### Fast Path (Local Development)
While developing, you only need to run Unit and Integration tests. This should execute very quickly:
```bash
pytest tests/ -m "not matrix and not e2e and not perf and not chaos"
```

### Full Pre-commit Validation
Before pushing a PR, please run the full suite (excluding destructive/chaos and heavy perf tests) to ensure you haven't broken the Golden Harness:
```bash
pytest tests/ -m "not perf and not chaos"
```
**Coverage Requirement:** PFP requires 100% line coverage for the `src` directory. You can verify this locally:
```bash
pytest tests/ -m "not perf and not chaos" --cov=src --cov-fail-under=100
```

## 4. Branching and Pull Requests

*   **Branch Naming:** Use descriptive branch names (e.g., `feat/add-shopify-connector`, `fix/schema-validation-error`).
*   **Conventional Commits:** We prefer commit messages following the [Conventional Commits](https://www.conventionalcommits.org/) specification (e.g., `feat: support XML inputs`, `fix(core): resolve parsing bug`).
*   **Draft PRs:** Feel free to open a Draft PR if you want early feedback.

## 5. Breaking Change Policy

PFP is built on strict data contracts (see `docs/contracts/compatibility.md`). 
If your PR introduces a breaking change to:
1. Public Python APIs (`PFPFactory`, `PFPWorker`)
2. Configuration schemas (`infra.yaml` or mappings)
3. The deterministic shape of the output artifact

You **must**:
* Add a `BREAKING CHANGE:` footer in your commit message.
* Clearly justify the breaking change in your PR description.
* Provide a migration path for existing users.
Major breaking changes will be batched into major semver releases and are rarely accepted without prior discussion via an Issue.