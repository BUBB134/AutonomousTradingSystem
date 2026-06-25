# BUB-10: Implement append-only audit event schema

## Goal

Implement the first public `audit` package contract: immutable, versioned, attributable audit
events with deterministic serialization, integrity verification, and append-only replay semantics.

## Non-goals

- Persistent database, filesystem, or remote audit adapters.
- Lifecycle, experiment, risk, execution, reconciliation, or operator-control behaviour.
- Event signing, credential management, network access, or deployment.
- Any live-trading, brokerage, leverage, short-selling, or real-capital authority.

## Governing constraints

- `TRADING_MANDATE.md` requires append-only, attributable audit records and corrections as new
  records.
- `AGENTS.md` requires typed versioned boundaries, deterministic behaviour, explicit UTC time, and
  fail-closed safety controls.
- `ARCHITECTURE.md` assigns audit integrity to the dependency-free `audit` package.
- `SECURITY.md` prohibits credentials and unredacted secret values in logs and artifacts.
- BUB-10 requires stable IDs, UTC timestamps, actors, versions, correlation IDs, payload schemas,
  serialization, ordering and idempotency rules, round-trip tests, and tamper detection.

## Current state

The `audit` package is an empty public boundary. Downstream packages may import it through
`autonomous_trading.audit`, but no audit symbols or persistence behaviour exist.

## Proposed design

- Add immutable `AuditActor`, `AuditPayload`, and `AuditEvent` value objects.
- Require callers to provide event IDs, correlation IDs, actors, event types, and UTC timestamps;
  the domain must not read the wall clock or generate uncontrolled identifiers.
- Store payloads as canonical JSON with an explicit payload schema name and version.
- Reject unsupported payload types, non-string keys, duplicate JSON keys, and unredacted values
  under sensitive key names.
- Serialize events as canonical JSON and attach a SHA-256 digest over the complete event body.
- Parse serialized events through a strict boundary that reconstructs typed values and verifies
  the digest before returning an event.
- Add an in-memory append-only log for domain semantics and tests. First append order is
  authoritative. Replaying identical event content is idempotent; reusing an event ID with
  different content fails closed.

## Package and dependency impact

Only the dependency-free `autonomous_trading.audit` package gains implementation. Its public
`__init__.py` exports the versioned contract. No dependency direction changes are required.

## Data, time, and determinism considerations

- Event and correlation IDs use caller-supplied UUID values.
- Timestamps must be timezone-aware with a zero UTC offset and are canonicalized to `Z`.
- JSON uses sorted keys, ASCII escaping, and compact separators.
- Floating-point payload values are rejected; exact decimal values must cross the boundary as
  strings or scaled integers under an owning payload schema.
- Repeated identical typed inputs produce byte-identical serialized events and digests.

## Safety and failure behaviour

- Missing, unknown, malformed, duplicated, non-canonical, or unsupported fields fail closed.
- Sensitive-looking keys may contain only the explicit redaction marker.
- A digest mismatch rejects an event before it can be replayed.
- Existing records are immutable; corrections must use a new event ID and may refer to the prior
  event in their payload.
- Conflicting event-ID replay raises an integrity error and does not alter the log.
- Replay after restart rebuilds append order from verified serialized events; no ambient state is
  trusted.

## Test and evidence plan

- Expected-path construction, canonical serialization, and round-trip tests.
- Boundary tests for IDs, actor and schema identifiers, UTC timestamps, payload types, unknown
  fields, duplicate keys, and sensitive values.
- Tamper tests for event fields, payloads, and digests.
- Immutability and append-only tests, including tuple snapshots and mutation attempts.
- Idempotent identical replay and fail-closed conflicting replay tests.
- Property-based tests for deterministic round trips and payload tamper detection over broad input
  spaces.
- Full `uv sync --frozen --all-groups` and `uv run python scripts/validate.py`.

## Documentation updates

- Add current audit schema, ordering, idempotency, redaction, replay, and recovery documentation.
- Mark the audit public contract implemented in `ARCHITECTURE.md`.
- Link the audit documentation and this plan from repository indexes.
- Update the README current-scope summary.

## Rollback or recovery

The change introduces no migration or external state. Before merge, rollback is branch deletion.
After merge, reverting the commit removes the API. Serialized version-1 events remain evidence and
must not be rewritten; any future incompatible schema requires a new version and explicit reader.

## Open decisions

None. Durable storage, cryptographic signing, and domain-specific payload schemas remain future
ticket work.
