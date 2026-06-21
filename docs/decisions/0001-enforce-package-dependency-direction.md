# ADR 0001: Enforce package dependency direction

## Status

Accepted for BUB-7.

## Context

The vertical slice requires strategy generation, independent validation, risk, paper execution,
and reconciliation to remain separate. Documentation alone cannot prevent a future import from
coupling those responsibilities or bypassing a control.

The repository is small and has no runtime dependencies, so a deterministic source-level check is
preferable to adding a third-party architecture framework.

## Decision

Each planned component has a top-level package under `autonomous_trading`. Direct dependencies are
declared in `scripts/check_import_boundaries.py`.

Cross-package imports:

1. must follow the declared dependency direction; and
2. must use symbols exported by the dependency package's `__init__.py`.

The checker runs in the repository validation command and as a dedicated CI job. New top-level
packages fail validation until their boundary is deliberately reviewed and declared.

Validation may consume the public `experiment` artifact interface but may not import strategy
implementation. Risk may consume proposed portfolio targets but may not import strategy. Strategy
may consume canonical data but may not import risk or execution.

## Alternatives considered

- Documentation only: rejected because violations would rely on reviewer memory.
- A third-party import-linter dependency: deferred because the current rule set is small and can be
  enforced with Python's standard-library AST parser.
- One large domain package: rejected because it would erase independent control boundaries.

## Safety consequences

The decision makes boundary changes explicit and reviewable. It does not prove semantic
independence, so later tickets still require contract, negative, and end-to-end tests.

The deployment package remains a research and isolated-paper composition root only. Its broad
imports grant no production, broker, credential, or live-trading authority.
