# Repository Instructions

## Instruction order

Follow instructions in this order:

1. `TRADING_MANDATE.md`;
2. this root `AGENTS.md`;
3. the nearest nested `AGENTS.md` for the files being changed; and
4. the active Linear ticket and approved implementation plan.

Stop and surface any conflict. Never reinterpret a lower-level instruction to weaken a higher-level
safety rule.

## Repository scope

This repository is research-only. Work may support deterministic research, backtesting,
independent validation, and isolated paper simulation. Live orders, broker credentials, real
capital, leverage, short selling, and production deployment are prohibited by
`TRADING_MANDATE.md`.

Default to fail-closed behaviour. Do not add a permissive fallback when configuration, evidence,
data, state, or a safety control is missing or invalid.

## Setup and validation

Use the pinned Python version and the committed dependency lock:

```bash
uv sync --frozen --all-groups
```

Run the complete repository validation suite:

```bash
uv run python scripts/validate.py
```

The equivalent individual commands are:

```bash
uv run ruff format --check .
uv run ruff check .
uv run python scripts/check_import_boundaries.py
uv run pyright
uv run pytest
uv run python -m build --no-isolation
```

Tests must pass without public-network access or external services. Do not weaken socket blocking
to make a test pass.

## Change workflow

For every ticket:

1. read the ticket, its blockers, and the relevant governing documents;
2. keep the change within the ticket's scope;
3. add or update tests for behaviour changes;
4. update affected documentation, schemas, examples, and plans;
5. run the complete validation command;
6. open a pull request linked to the Linear ticket;
7. ensure CI passes and all review conversations are resolved; and
8. leave merge to a human.

Do not combine unrelated cleanup with ticket work. Record newly discovered work as a separate
ticket rather than silently expanding scope.

## Engineering rules

- Keep business behaviour deterministic for identical versioned inputs.
- Use explicit, timezone-aware timestamps and documented market-time semantics.
- Preserve chronology; future information must never influence an earlier decision.
- Use typed, versioned schemas at system boundaries.
- Keep audit and experiment records append-only and attributable.
- Keep strategy generation separate from independent validation.
- Keep strategy code unable to call execution or broker-facing interfaces directly.
- Import other top-level packages only through their public package interfaces and only in the
  direction permitted by `scripts/check_import_boundaries.py`.
- Keep risk, execution, and reconciliation controls independently testable.
- Avoid hidden global state, wall-clock dependencies, and uncontrolled randomness.
- Never log credentials, tokens, personal financial data, or unredacted secret values.
- Do not add broker or market-data SDKs unless an approved ticket explicitly requires one.

## Tests and documentation

Behaviour changes require tests that cover the expected path and relevant failure modes. Safety
controls require tests proving they fail closed. Fixes require a regression test when practical.

Update documentation in the same pull request when changing:

- public interfaces or configuration;
- architecture or package dependencies;
- operating procedures or validation evidence;
- safety limits, promotion rules, or failure behaviour; or
- setup and validation commands.

Documentation-only changes still require the full validation command because documentation is
packaged and reviewed with the repository.

## Reviews and merge

All changes require human merge. Risk, validation, execution, reconciliation, security, deployment,
and governing-document changes require especially careful human review. Codex may implement review
feedback and resolve addressed conversations, but must not approve or merge its own pull request.

Generated artifacts such as `dist/`, caches, and virtual environments must not be committed.
