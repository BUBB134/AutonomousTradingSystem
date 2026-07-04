# Registry Lifecycle

The `autonomous_trading.registry` package currently implements the BUB-9 strategy lifecycle state
machine. It records immutable lifecycle transitions and promotion evidence. It does not implement
strategy logic, validation logic, paper execution, deployment, broker communication, or live-trading
authority.

## Public contract

The public interface is exported from `autonomous_trading.registry`:

- `StrategyLifecycleState`
- `StrategyLifecycle`
- `StrategyLifecycleTransition`
- `EvidenceReference`
- `ApprovalRecord`
- `RiskEnvelope`
- `is_legal_strategy_lifecycle_transition`

The schema version is `STRATEGY_LIFECYCLE_SCHEMA_VERSION = 1`.

## States

The lifecycle states are represented exactly once in `STRATEGY_LIFECYCLE_STATES`:

| State | Meaning |
| --- | --- |
| `PROPOSED` | A strategy idea exists but has not entered research. |
| `RESEARCH` | Research work may occur using approved offline inputs. |
| `BACKTESTED` | Backtest evidence exists by reference. |
| `VALIDATED` | Independent validation evidence exists by reference. |
| `PAPER` | The strategy is eligible for isolated paper-simulation work only. |
| `LIVE_CANDIDATE` | Evidence may support human consideration as a future live candidate. |
| `LIMITED_LIVE` | Record-only state requiring explicit approval and risk-envelope evidence. |
| `RETIRED` | No further lifecycle promotion is permitted. |

`LIMITED_LIVE` does not grant execution authority in this repository. The trading mandate still
prohibits live orders, broker connectivity, real capital, leverage, short selling, and production
deployment.

## Legal Transitions

The closed transition policy is:

| From | To |
| --- | --- |
| `PROPOSED` | `RESEARCH`, `RETIRED` |
| `RESEARCH` | `BACKTESTED`, `RETIRED` |
| `BACKTESTED` | `VALIDATED`, `RETIRED` |
| `VALIDATED` | `PAPER`, `RETIRED` |
| `PAPER` | `LIVE_CANDIDATE`, `RETIRED` |
| `LIVE_CANDIDATE` | `LIMITED_LIVE`, `RETIRED` |
| `LIMITED_LIVE` | `RETIRED` |
| `RETIRED` | none |

Invalid jumps fail closed before a transition is appended. In particular, `RESEARCH` cannot
transition directly to `PAPER`, `LIVE_CANDIDATE`, or `LIMITED_LIVE`.

## Evidence

Promotion transitions require at least one `EvidenceReference`:

- `RESEARCH -> BACKTESTED`
- `BACKTESTED -> VALIDATED`
- `VALIDATED -> PAPER`
- `PAPER -> LIVE_CANDIDATE`
- `LIVE_CANDIDATE -> LIMITED_LIVE`

Each evidence reference records a kind, URI, SHA-256 digest, schema name, and schema version.
Duplicate evidence references in the same transition are rejected.

`LIVE_CANDIDATE -> LIMITED_LIVE` also requires:

- an `ApprovalRecord` whose evidence kind is `owner_approval`; and
- a `RiskEnvelope` with explicit symbols, maximum gross exposure fraction, maximum single-position
  fraction, and UTC expiry timestamp.

Approval records and risk envelopes are rejected on all other transitions.

## Append-Only Semantics

`StrategyLifecycle` is immutable. Applying a transition returns a new lifecycle with one appended
`StrategyLifecycleTransition`; the prior lifecycle remains unchanged. Replayed history must match
strategy ID, sequence number, prior state, and unique transition IDs.

Transition timestamps must be explicit UTC datetimes. The registry never reads the wall clock,
generates hidden IDs, talks to external services, or falls back to a permissive state.

## Audit Evidence

`StrategyLifecycleTransition.to_audit_event()` renders a transition as a versioned audit event with:

- event type `registry.strategy_lifecycle.transition`; and
- payload schema `registry.strategy_lifecycle_transition`.

The audit event is returned to the caller. The registry does not persist it or mutate an audit log
as a side effect.

## Failure Behaviour

The registry raises `StrategyLifecycleValidationError` or `StrategyLifecycleIntegrityError` for
invalid, missing, duplicated, contradictory, or non-UTC inputs. Failures leave existing lifecycle
history unchanged.
