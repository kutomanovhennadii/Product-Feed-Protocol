# PFP Governance

The Product Feed Protocol (PFP) follows a maintainer-led governance model. This document defines the roles, decision-making processes, and community expectations.

## Roles

### 1. Users
Anyone who uses PFP to process data. Users are encouraged to participate by opening issues, suggesting features, and helping others.

### 2. Contributors
Anyone who submits a Pull Request, participates in architectural discussions, or helps maintain documentation. Contributors must follow the guidelines in `CONTRIBUTING.md` and adhere to the project's Code of Conduct.

### 3. Maintainers
Core team members who hold write access to the repository. 
Maintainers are responsible for:
* Reviewing and merging Pull Requests.
* Triaging issues and defining the roadmap.
* Releasing new versions.
* Ensuring the security and stability of the project.

## Decision Making Process

* **Consensus-seeking:** Most decisions are made via lazy consensus on GitHub Issues or Pull Requests. If no maintainer objects within a reasonable timeframe (typically 72 hours for minor changes), the change is accepted.
* **RFCs (Request for Comments):** Significant architectural changes, breaking API changes, or major new features require opening an Issue tagged as an `RFC`. This allows the community and maintainers to discuss the design before code is written.
* **Final Authority:** In cases where consensus cannot be reached, the lead maintainer(s) hold the final say to prevent stagnation.

## Pull Request Approval
A Pull Request requires at least **one approved review** from a Maintainer before it can be merged, alongside passing all automated CI checks (100% coverage, linting, golden harness tests).