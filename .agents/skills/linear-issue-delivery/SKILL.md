---
name: linear-issue-delivery
description: Deliver an approved Linear BUB issue from dependency-safe selection through scoped implementation, repository validation, pull request publication, CI, and review feedback. Use when Codex is asked to pick up, implement, validate, publish, or shepherd an Autonomous Trading repository ticket to a human-merge-ready pull request.
---

# Linear Issue Delivery

## Establish authority and scope

1. Read `../../../TRADING_MANDATE.md`, `../../../AGENTS.md`, and the nearest nested
   `AGENTS.md` for every path that may change.
2. Read the full Linear ticket, its labels, comments, project context, blockers, and the sequence in
   BUB-46 when ticket selection is part of the request.
3. Stop and surface any conflict, prohibited behaviour, unresolved blocker, human decision, or
   missing authority. Do not reinterpret a lower-level instruction to weaken a higher-level rule.
4. Keep one ticket in scope. Record newly discovered work as a separate issue instead of expanding
   the current change.

## Plan the delivery

1. Inspect the clean checkout, current branch, remote default branch, and relevant implementation,
   tests, schemas, and documentation.
2. Create or update a version-controlled plan under `../../../docs/plans/` when required by
   `../../../PLANS.md`.
3. State the intended files, behaviour, failure modes, evidence, and documentation impact before
   implementation.
4. Move the Linear issue to the appropriate active state and leave a concise scope note.

## Implement and verify

1. Branch from the current remote default branch using a ticket-specific branch.
2. Make only the approved change. Preserve deterministic behaviour, chronology, typed boundaries,
   append-only evidence, and fail-closed controls.
3. Add expected-path and relevant failure-path tests. Add regression or property tests when the
   behaviour warrants them.
4. Update affected documentation, schemas, examples, plans, and validation evidence in the same
   change.
5. Run:

   ```bash
   uv sync --frozen --all-groups
   uv run python scripts/validate.py
   ```

6. Review the complete diff for scope, generated artifacts, secrets, prohibited authority,
   weakened checks, and accidental user changes.

## Publish and shepherd

1. Commit only ticket files, push the branch, and open a draft pull request linked to the Linear
   issue. Describe the change, reason, impact, and validation.
2. Keep auto-merge disabled. Never approve or merge the pull request.
3. Monitor every required CI check. Investigate failures from logs, apply focused fixes, rerun the
   full validation command, and push the correction.
4. Request review when authorised. Read all top-level and inline feedback, implement every
   applicable change, reply with evidence, and resolve only threads that are actually addressed.
5. Update Linear with the pull request and final validation state. Leave merge to a human.
