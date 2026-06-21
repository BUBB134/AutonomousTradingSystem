---
name: architecture-decision
description: Evaluate and record Autonomous Trading architecture, package-boundary, trust-boundary, schema-ownership, or dependency-direction decisions. Use when a ticket or design discussion requires an ADR, changes component responsibilities, introduces a new boundary, or compares structural alternatives before implementation.
---

# Architecture Decision

## Ground the decision

1. Read `../../../TRADING_MANDATE.md`, `../../../AGENTS.md`,
   `../../../ARCHITECTURE.md`, `../../../SECURITY.md`, and `../../../PLANS.md`.
2. Read the governing Linear ticket, relevant plans, existing records under
   `../../../docs/decisions/`, and nearest nested `AGENTS.md` files.
3. State the decision question, current facts, assumptions, constraints, and explicitly deferred
   work. Stop if the requested option would weaken the trading mandate.

## Evaluate options

1. Compare at least the status quo and credible alternatives.
2. Assess package direction, public interfaces, ownership, trust boundaries, failure behaviour,
   determinism, chronology, auditability, independent validation, and operational recovery.
3. Prefer the smallest design that preserves separation of responsibilities and fails closed.
4. Reject designs that give strategy code execution authority, let producers validate themselves,
   hide dependencies, introduce ambient state, or create a path to live trading.

## Record the outcome

1. Add or update a numbered ADR under `../../../docs/decisions/`.
2. Record context, decision, alternatives, consequences, safety properties, validation approach,
   and follow-up work.
3. Update `../../../docs/decisions/README.md`, `../../../ARCHITECTURE.md`, and any affected plan or
   package documentation.
4. Do not implement beyond the active ticket. Create separate Linear work for discovered follow-up
   changes.
5. Run the full repository validation command and leave acceptance and merge to human review.
