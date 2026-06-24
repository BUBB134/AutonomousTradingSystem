# Audit events

## Current scope

The `autonomous_trading.audit` package provides a dependency-free, versioned boundary for
immutable audit events and deterministic in-memory replay. It records evidence only; it does not
grant lifecycle, validation, risk, execution, deployment, or live-trading authority.

The current public contract exports:

- `AuditActor` and `ActorKind` for explicit attribution;
- `AuditPayload` for schema-owned canonical JSON payloads;
- `AuditEvent` for versioned event envelopes and integrity verification; and
- `InMemoryAuditLog` for append-only ordering, idempotency, and restart-replay semantics.

Durable storage, cryptographic signing, and domain-specific payload schemas are future work.

## Event schema

Audit event schema version 1 requires:

- a caller-supplied canonical UUID `event_id`;
- a caller-supplied timezone-aware UTC `occurred_at`;
- an actor kind and stable actor identifier;
- a constrained event type such as `experiment.created`;
- a caller-supplied canonical UUID `correlation_id`;
- a payload schema name and positive version;
- canonical JSON payload values and a payload SHA-256 digest; and
- an event SHA-256 digest covering the complete event body.

The package never reads the wall clock and never generates IDs. Callers must supply those explicit
inputs so repeated versioned inputs remain reproducible.

## Serialization and exact values

`AuditEvent.to_json()` produces canonical JSON with:

- sorted object keys;
- compact separators;
- ASCII escaping;
- canonical lowercase UUID strings; and
- UTC timestamps using fixed microseconds and `Z`.

Payloads accept strings, signed 64-bit integers, booleans, null, arrays, and objects with string
keys. Floating-point values are rejected. Exact decimal values must be represented by the owning
payload schema as strings or scaled integers.

`AuditEvent.from_json()` rejects malformed UTF-8 or JSON, duplicate keys, missing or unknown
fields, unsupported values, non-canonical representations, payload digest mismatches, and event
digest mismatches.

SHA-256 provides deterministic tamper evidence, not identity authentication. A future signing
design requires a separate ticket and must not place signing secrets in events or configuration.

## Sensitive values

Audit payloads must not contain credentials, passwords, tokens, authorization values, API keys,
private keys, or other secrets. Sensitive-looking keys are rejected unless their value is exactly:

```text
[REDACTED]
```

Prefer omitting the key entirely. The marker records that redaction occurred; it is not permission
to place a secret under a misleading key. Payload-schema owners remain responsible for ensuring
ordinary-looking fields do not contain sensitive values.

## Ordering and idempotency

`InMemoryAuditLog` uses first successful append order as the authoritative order. Event timestamps
are evidence and are not used to reorder the log, so clock skew or backfilled events cannot rewrite
history.

- A new event ID appends once.
- Replaying the same event ID with identical content is idempotent.
- Replaying the same event ID with different content raises `AuditIntegrityError`.
- A failed append does not alter existing events.
- `events()` and `serialize()` return immutable tuple snapshots.

Corrections must be new events with new event IDs. A correction payload may refer to the superseded
event, but the original event remains unchanged.

## Replay and recovery

After restart, rebuild an in-memory log with `InMemoryAuditLog.replay()` over canonical serialized
events in their persisted append order. Every event is parsed and integrity-checked before append.
Replay stops on corrupt, ambiguous, unsupported, or conflicting evidence; callers must not skip the
failure or silently continue with a partial trusted state.

The in-memory log is not a durable repository. A future persistence adapter must preserve these
ordering, verification, append-only, and fail-closed rules.
