# BUB-9: Implement strategy lifecycle state machine

## Goal

Implement the first public `registry` package contract: an immutable, versioned strategy lifecycle
state machine that records legal strategy-state transitions from `PROPOSED` through `RETIRED`.

## Non-goals

- Strategy implementation, backtesting, validation, portfolio, risk, execution, reconciliation, or
  monitoring behaviour.
- Persistent database, filesystem, remote registry, broker, deployment, or credential integration.
- Granting live-trading authority, placing orders, enabling leverage, or approving real capital.
- Changing package dependency rules.

## Governing constraints

- `TRADING_MANDATE.md` permits only research, backtest, validation, and isolated paper simulation.
  Live-capital behaviour remains prohibited.
- `AGENTS.md` requires deterministic behaviour, typed versioned schemas, append-only attributable
  evidence, chronology preservation, and fail-closed safety controls.
- `ARCHITECTURE.md` assigns lifecycle and promotion evidence to the `registry` package, which may
  depend only on public `audit`, `configuration`, `experiment`, and `validation` interfaces.
- `SECURITY.md` prohibits secrets, broker credentials, public-network test dependencies, and
  permissive fallbacks.
- BUB-9 requires every lifecycle state, invalid-jump rejection, evidence-backed promotion,
  rejection of direct research-to-paper/live jumps, explicit approval and risk-envelope evidence
  for `LIMITED_LIVE`, deterministic append-only transitions, and property tests over all state
  pairs.

## Current state

The `registry` package is an empty public boundary. The `audit` package already provides immutable
event payloads, canonical serialization, integrity evidence, and append-only replay semantics.
There is no strategy lifecycle contract, transition validation, promotion evidence model, or
registry documentation.

## Proposed design

- Add dependency-free lifecycle value objects inside `autonomous_trading.registry`, using public
  `autonomous_trading.audit` symbols only when producing audit events.
- Define `StrategyLifecycleState` with exactly these repository lifecycle states:
  `PROPOSED`, `RESEARCH`, `BACKTESTED`, `VALIDATED`, `PAPER`, `LIVE_CANDIDATE`, `LIMITED_LIVE`,
  and `RETIRED`.
- Define a closed transition policy:
  - `PROPOSED -> RESEARCH`
  - `RESEARCH -> BACKTESTED`
  - `BACKTESTED -> VALIDATED`
  - `VALIDATED -> PAPER`
  - `PAPER -> LIVE_CANDIDATE`
  - `LIVE_CANDIDATE -> LIMITED_LIVE`
  - any non-retired state may transition to `RETIRED`
- Require non-empty machine-readable `EvidenceReference` values for all promotion transitions.
- Require an explicit `ApprovalRecord` and `RiskEnvelope` for `LIVE_CANDIDATE -> LIMITED_LIVE`.
  `LIMITED_LIVE` remains a record-only lifecycle state and does not enable live execution in this
  repository.
- Represent each transition as an immutable `StrategyLifecycleTransition` with caller-supplied IDs,
  actor, UTC timestamp, sequence number, evidence, and deterministic content digest.
- Represent lifecycle history as an immutable `StrategyLifecycle`; applying a transition returns a
  new lifecycle with appended history rather than mutating the existing lifecycle.
- Provide deterministic replay from a sequence of verified transitions and conversion of a
  transition to an `AuditEvent` payload for append-only registry audit evidence.

## Package and dependency impact

Only `autonomous_trading.registry` gains implementation and public exports. It may import
`autonomous_trading.audit` through the public package interface. No package-boundary rule changes
are required.

## Data, time, and determinism considerations

- Transition IDs, strategy IDs, evidence references, and actor identifiers are explicit inputs.
- Timestamps must be timezone-aware UTC datetimes; the registry will not read the wall clock.
- Digests use canonical JSON with sorted keys and compact separators.
- Decimal risk limits are represented canonically as exact strings in evidence payloads.
- Replaying the same transition sequence produces the same lifecycle state, history, and digest
  values.

## Safety and failure behaviour

- Unknown, malformed, duplicated, missing, non-UTC, non-canonical, or contradictory inputs fail
  closed with registry validation errors.
- Invalid state jumps fail closed before history is appended.
- Research cannot transition directly to paper, live-candidate, limited-live, or retired live-like
  operation.
- Promotions without evidence fail closed.
- `LIMITED_LIVE` without approval and risk-envelope evidence fails closed.
- Existing transition records are immutable; corrections require new append-only records.
- No lifecycle state performs deployment, broker communication, credential access, or live order
  activity.

## Test and evidence plan

- Unit tests for expected legal transitions and current-state advancement.
- Failure-path tests for illegal jumps, missing evidence, duplicate evidence, invalid timestamps,
  bad identifiers, and missing `LIMITED_LIVE` controls.
- Property tests over all source/target state pairs to prove the policy accepts only legal pairs.
- Immutability and append-only tests showing prior lifecycle instances and history snapshots do not
  mutate.
- Replay tests proving deterministic reconstruction and rejection of mismatched sequence/state
  records.
- Audit-event tests proving transition evidence can be rendered as a versioned audit payload without
  secrets or live authority.
- Full `uv sync --frozen --all-groups` and `uv run python scripts/validate.py`.

## Documentation updates

- Add registry lifecycle documentation covering states, legal transitions, required evidence,
  `LIMITED_LIVE` constraints, audit payloads, replay, and failure behaviour.
- Mark the registry public lifecycle contract implemented in `ARCHITECTURE.md`.
- Link the registry documentation and this plan from repository indexes.
- Update the README current-scope summary and documentation links.

## Rollback or recovery

The change introduces no external state or migration. Before merge, rollback is branch deletion.
After merge, reverting the commit removes the API. Existing serialized transition audit evidence
must remain append-only; any future incompatible lifecycle schema requires a new versioned contract
and reader.

## Open decisions

None for BUB-9. Durable registry storage, promotion-gate execution, paper-trading gates, and any
future live-capital authority remain separate tickets and require human review.
