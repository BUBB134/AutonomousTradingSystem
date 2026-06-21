# BUB-8: Implement typed configuration loading

## Goal

Implement a typed, versioned configuration boundary for research budgets, instrument universes,
promotion gates, isolated paper settings, disabled live settings, and reference-only secret
metadata.

## Non-goals

- Resolve or read secret values.
- Add broker, exchange, market-data, or production-service integrations.
- Add strategy, portfolio, execution, promotion, or deployment behaviour.
- Permit live trading, leverage, short selling, derivatives, or real-capital access.
- Add ambient environment-variable overrides or permissive fallback configuration.

## Governing constraints

- `TRADING_MANDATE.md` permits research, backtest, validation, and isolated paper modes only.
- Missing, malformed, contradictory, or unrecognised configuration must fail closed.
- `SECURITY.md` requires `TRADING_MODE` to default to research and live/broker settings to remain
  disabled.
- Configuration is the owning package and has no cross-package dependencies.
- The public boundary must be typed, versioned, deterministic, and suitable for later experiment
  provenance.

## Current state

The `autonomous_trading.configuration` package exists as an empty public boundary. It deliberately
exports no runtime symbols and documents BUB-8 as the ticket that will introduce its first public
API. The repository currently has no configuration parser, schema, examples, or configuration
tests.

## Proposed design

Add immutable dataclass schemas for:

- the operating environment;
- research budgets;
- the approved instrument universe;
- independent promotion-gate thresholds;
- isolated paper settings;
- disabled live settings;
- environment-variable secret references; and
- the root versioned configuration.

Add a strict TOML loader that:

- requires every documented field and rejects unknown fields at every level;
- requires the caller to provide the expected operating environment and rejects mismatches;
- accepts only the supported schema version;
- rejects unsafe live, leverage, or short-selling flags;
- validates types and value ranges without coercing strings or booleans into numbers;
- records secret reference names only and never reads secret values; and
- returns typed immutable objects or a single configuration-boundary exception.

Add a canonical JSON snapshot representation with sorted keys, normalized decimal strings, and a
SHA-256 digest. Secret references may appear in the snapshot, but secret values cannot because the
loader has no secret-resolution capability.

## Package and dependency impact

Implementation remains entirely inside `autonomous_trading.configuration` and the standard
library. The package public interface will export the schemas, loader functions, snapshot type, and
configuration error. No new dependency or cross-package import is required.

## Data, time, and determinism considerations

- TOML bytes and the expected environment are the only loader inputs.
- The loader does not read the wall clock, process environment, network, or global mutable state.
- Decimal configuration values are normalized from their textual numeric representation and
  serialized as strings in snapshots.
- Equivalent typed configurations produce byte-identical canonical snapshot JSON and the same
  SHA-256 digest.

## Safety and failure behaviour

- Unsupported schema versions, missing fields, unknown fields, malformed TOML, invalid types,
  duplicate instruments, invalid ranges, environment mismatches, and unsafe permission flags raise
  `ConfigurationError`.
- Paper mode must be explicit: paper settings are enabled only for the `paper` environment and are
  disabled for research, backtest, and validation.
- Live trading, leverage, and short selling are false-only fields in the initial schema.
- Secret entries contain a logical reference name and an environment-variable identifier only.
  Literal secret-value fields are unknown and therefore rejected.
- There is no fallback to defaults when a file is missing or invalid.

## Test and evidence plan

- Valid research and paper configurations load into the expected typed values.
- Every supported non-paper environment rejects enabled paper settings.
- Expected-environment mismatches fail closed.
- Unknown and missing fields fail at both root and nested levels.
- Invalid primitive types, numeric boundaries, duplicate instruments, malformed symbols, duplicate
  secret names, and malformed environment-variable identifiers fail closed.
- Any live, leverage, or short-selling permission set to true is rejected.
- Property-based tests cover the false-only permission invariant and snapshot determinism.
- Snapshot tests prove stable canonical content and digest changes when material configuration
  changes.
- The full repository validation command and CI provide final evidence.

## Documentation updates

- Add a configuration reference with schema, environment, failure, secret-reference, and snapshot
  semantics plus safe research and paper examples.
- Link the reference and this plan from the documentation indexes and README.
- Update the architecture package table to identify the configuration public contract as
  implemented.

## Rollback or recovery

Before downstream packages depend on this boundary, rollback is a normal revert of the BUB-8
commit. After adoption, schema changes must be additive through an explicit new schema version;
silently changing version 1 semantics is prohibited.

## Open decisions

None. Runtime secret resolution and any broker-facing configuration remain explicitly out of scope
and require separate approved tickets.
