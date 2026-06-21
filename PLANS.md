# Plans

## Source of truth

Linear issue
[BUB-46](https://linear.app/bubb134/issue/BUB-46/track-autonomous-trading-backlog-prioritization-and-execution)
defines delivery order for the autonomous trading vertical slice. Linear blocker relationships
remain authoritative for dependency safety.

The current high-level sequence is:

1. repository and governance foundation;
2. data integrity and deterministic backtesting;
3. independent validation and promotion controls;
4. isolated paper-trading vertical slice;
5. live-candidate reporting without live execution; and
6. operator visibility and simulated emergency controls.

This sequence does not authorise live trading.

## When a repository plan is required

Create a version-controlled plan under `docs/plans/` for work that:

- spans multiple components or pull requests;
- changes a safety, trust, or package boundary;
- introduces a schema or migration;
- changes validation or promotion behaviour; or
- has meaningful rollback or operational risk.

Small, single-ticket changes may use the Linear issue as their plan when it contains sufficient
acceptance criteria and verification steps.

## Plan template

Each plan should include:

```text
# <ticket>: <title>

## Goal
## Non-goals
## Governing constraints
## Current state
## Proposed design
## Package and dependency impact
## Data, time, and determinism considerations
## Safety and failure behaviour
## Test and evidence plan
## Documentation updates
## Rollback or recovery
## Open decisions
```

Plans must separate facts from assumptions and label future work. Material discoveries that expand
scope should become separate Linear issues and be deliberately inserted into BUB-46 rather than
silently absorbed.

## Completion

A plan is complete only when its acceptance criteria, validation, documentation, and review
obligations are satisfied. Closing a plan or ticket does not grant merge, deployment, promotion, or
live-trading authority.
