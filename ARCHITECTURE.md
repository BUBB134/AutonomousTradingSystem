# Architecture

## Purpose

This document defines the intended boundaries for the autonomous trading vertical slice. It is a
design constraint, not evidence that every component already exists.

The architecture must implement the safety rules in `TRADING_MANDATE.md` and the engineering rules
in `AGENTS.md`.

## System boundary

The initial system accepts versioned configuration and synthetic or explicitly approved historical
market data. It may produce research artifacts, backtest results, independent validation reports,
and simulated paper-trading records.

It has no live-broker boundary, no real-capital boundary, and no deployment authority.

## Intended flow

```text
versioned data + configuration
              |
              v
      strategy generation
              |
           signals
              |
              v
     target portfolio engine
              |
       proposed targets
              |
              v
      independent risk gate
              |
     approved paper intent
              |
              v
       paper broker simulator
              |
              v
   accounting + reconciliation
              |
              v
 audit, monitoring, and evidence
```

Independent validation consumes immutable experiment inputs and outputs through a separate path. It
does not trust strategy-authored claims and cannot be bypassed by the strategy pipeline.

## Planned component boundaries

| Area | Responsibility | Must not |
| --- | --- | --- |
| configuration | Load typed, versioned, fail-closed settings | Infer permissive defaults |
| audit | Record append-only domain and control events | Rewrite historical events |
| data | Represent and validate canonical market data | Hide timestamp or quality defects |
| strategy | Produce signals from information available at decision time | Approve itself or place orders |
| backtest | Run chronology-safe deterministic simulations | Read future data |
| portfolio | Convert signals into proposed target positions | Bypass risk controls |
| validation | Independently challenge experiments and promotion evidence | Depend on strategy approval logic |
| risk | Reject or constrain proposed paper actions | Be overridden by strategy code |
| execution | Simulate idempotent paper order lifecycles | Route to a live venue |
| reconciliation | Compare expected and observed simulated state | Continue activity after material mismatch |
| control plane | Expose read-only status and audited simulator controls | Enable live trading |

## Dependency direction

Domain schemas and deterministic utilities belong at the centre. Higher-level orchestration may
depend on lower-level domain interfaces, but domain code must not depend on UI, deployment, or
external adapters.

Strategy packages must not import execution adapters. Validation must operate through immutable
artifacts and stable interfaces rather than strategy internals. Risk and reconciliation must remain
independently invocable and testable.

Detailed package dependency rules will be defined by BUB-7. Until then, new packages must not
create circular dependencies or collapse the separation described here.

## Trust boundaries

Treat all external data, files, environment variables, serialized artifacts, and future service
responses as untrusted inputs. Validate them at the boundary before creating domain objects.

Promotion evidence crosses a trust boundary: the producer of a strategy result cannot be the sole
authority that validates or promotes it.

Any future credential-bearing or networked adapter is outside the current architecture and requires
an explicit owner-approved change to the mandate and security model.

## Determinism and state

Material computations must be reproducible from explicit inputs, versions, and seeds. Business
logic must not depend directly on the wall clock or ambient process state.

State transitions must be explicit, validated, idempotent where retries are possible, and recorded
in the audit trail. Invalid transitions fail closed.
