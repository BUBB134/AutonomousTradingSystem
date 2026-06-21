# BUB-7: Define package boundaries and dependency rules

## Goal

Create stable Python package homes for the planned vertical slice, document their ownership and
dependency direction, and make violations fail CI before business logic is added.

## Non-goals

- Implement trading strategies, schemas, backtesting, validation logic, or paper execution.
- Add broker, market-data, network, credential, or production-deployment integrations.
- Decide the concrete public classes that belong to later tickets.

## Governing constraints

- `TRADING_MANDATE.md` remains the highest authority.
- Strategy generation, independent validation, risk, execution, and reconciliation stay separate.
- Cross-package dependencies must be deterministic, acyclic, and visible.
- Missing package rules or imports that bypass a public package interface fail closed.

## Current state

The repository documents conceptual components, but most components do not yet have Python package
roots and no automated check prevents a future import from collapsing a safety boundary.

## Proposed design

Create top-level packages for configuration, audit, data, strategy, portfolio, risk, execution,
reconciliation, backtest, experiment, validation, registry, monitoring, control plane, and
deployment. Their `__init__.py` files are the only supported cross-package import surfaces.

Keep those public surfaces empty until the ticket responsible for a versioned interface implements
it. Add an AST-based repository check with an explicit allow-list of direct dependencies. Reject:

- undeclared top-level packages;
- imports outside the allowed dependency direction; and
- imports of another package's implementation submodules;
- component re-exports from the root package; and
- dynamic imports that bypass static dependency inspection.

## Package and dependency impact

The exact direct-import allow-list is defined in `scripts/check_import_boundaries.py` and explained
in `ARCHITECTURE.md`. The composition root is the only package allowed to depend broadly across the
system. Validation depends on immutable experiment interfaces, not strategy implementation.

## Data, time, and determinism considerations

The change does not process market data or time. The checker sorts files and violations so
identical source trees produce identical results.

## Safety and failure behaviour

The checker fails closed when the source root is missing, a declared package is absent, an
undeclared package appears, source cannot be parsed, or an import violates the dependency policy.
No permissive fallback is provided.

## Test and evidence plan

- Test the checked-in source tree.
- Test forbidden strategy-to-execution, risk-to-strategy, and validation-to-strategy imports.
- Test absolute and relative import forms.
- Test that allowed dependencies use public package interfaces.
- Test undeclared packages and internal cross-package imports fail closed.
- Run `uv run python scripts/validate.py`.

## Documentation updates

Update the architecture, quality, repository instructions, README, documentation index, and an ADR
describing the package-boundary decision.

## Rollback or recovery

Revert the package markers, checker, and documentation together. Do not retain package
implementations while removing their boundary rules.

## Open decisions

Concrete schemas and public symbols remain intentionally deferred to their owning Linear tickets.
