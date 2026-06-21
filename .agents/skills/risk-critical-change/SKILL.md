---
name: risk-critical-change
description: Plan, implement, and verify changes to safety controls, validation gates, risk, paper execution, reconciliation, control-plane actions, security, deployment composition, or governing policy with strengthened evidence and human review. Use whenever a repository change could weaken a trust boundary, permit unsafe simulated activity, alter promotion, or affect a risk-critical path.
---

# Risk-Critical Change

## Apply the strict instruction chain

1. Read `../../../TRADING_MANDATE.md`, `../../../AGENTS.md`,
   `../../../ARCHITECTURE.md`, `../../../SECURITY.md`, `../../../QUALITY.md`, the active ticket,
   approved plan, and every nearest nested `AGENTS.md`.
2. Stop on any conflict, missing human decision, prohibited live-capital implication, credential
   requirement, or attempt to weaken a governing rule.
3. Require a version-controlled plan under `../../../docs/plans/` before implementation.

## Define safety properties

1. Identify the trust boundary, authorised inputs and outputs, invariants, failure modes, restart
   behaviour, audit evidence, and independent control owner.
2. Make missing, invalid, stale, contradictory, duplicated, or unreconciled state fail closed.
3. Keep strategy, validation, risk, execution, reconciliation, and promotion responsibilities
   separate and independently invocable.
4. Preserve deterministic behaviour, explicit timezone-aware time, idempotency, append-only
   evidence, and typed versioned boundaries.

## Require stronger tests and evidence

1. Add boundary tests proving unauthorised components cannot bypass the control.
2. Add expected-path and failure-path tests for every material rejection or degraded state.
3. Add property-based tests for invariants and broad input spaces.
4. Add chronology, idempotency, replay, restart, reconciliation, audit, or regression tests when
   relevant to the change.
5. Verify failures stop or constrain activity rather than falling back permissively.

## Deliver for human review

1. Update governing documentation, schemas, runbooks, plans, and recovery instructions together
   with the implementation.
2. Run `uv run python scripts/validate.py` and review the complete diff for weakened controls,
   hidden authority, secrets, and scope expansion.
3. Require passing CI, focused human review, and resolved conversations.
4. Never self-approve, auto-merge, deploy, promote, or enable live trading.
