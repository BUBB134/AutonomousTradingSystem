# Documentation

Repository documentation is organised as follows:

- governing policy lives at the repository root:
  - [`TRADING_MANDATE.md`](../TRADING_MANDATE.md)
  - [`AGENTS.md`](../AGENTS.md)
  - [`ARCHITECTURE.md`](../ARCHITECTURE.md)
  - [`SECURITY.md`](../SECURITY.md)
  - [`QUALITY.md`](../QUALITY.md)
  - [`PLANS.md`](../PLANS.md)
- [`decisions/`](decisions/README.md) stores architecture decision records.
- [`plans/`](plans/README.md) stores version-controlled implementation plans.
- [`runbooks/`](runbooks/README.md) stores operator and recovery procedures.
- [`validation/`](validation/README.md) stores independent validation policy and report guidance.
- [`skills.md`](skills.md) explains the bounded repository skills and their update workflow.
- [`configuration.md`](configuration.md) documents the typed, fail-closed configuration boundary.

Documentation must distinguish current behaviour from intended future design. No document may
weaken `TRADING_MANDATE.md`.

Current architecture records:

- [ADR 0001: Enforce package dependency direction](decisions/0001-enforce-package-dependency-direction.md)
- [BUB-7 package-boundary implementation plan](plans/BUB-7-package-boundaries.md)
- [BUB-28 repository-skills implementation plan](plans/BUB-28-initial-repository-skills.md)
- [BUB-8 typed-configuration implementation plan](plans/BUB-8-typed-configuration.md)
