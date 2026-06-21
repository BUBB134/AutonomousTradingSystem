# Autonomous Trading System

A safety-first autonomous research, validation, and paper-trading system for systematic
strategies.

## Current scope

The first milestone is restricted to research, deterministic backtesting, independent
validation, and isolated paper simulation. Live trading, leverage, short selling, brokerage
connections, and real financial credentials are not permitted.

This bootstrap contains development infrastructure only. It intentionally contains no market
data integrations, strategies, broker SDKs, or trading logic.

## Requirements

- Python 3.14.4
- [`uv`](https://docs.astral.sh/uv/) 0.11.23 or a compatible newer release

The exact Python version is recorded in `.python-version`; project and development dependencies
are resolved in the committed `uv.lock`.

## Setup

Create the local environment from the committed lockfile:

```bash
uv sync --frozen --all-groups
```

## Validation

Run the complete repository validation suite with one command:

```bash
uv run python scripts/validate.py
```

That command checks formatting, lint rules, package dependency boundaries, static types, tests, and
a source distribution whose contents are then used to build the wheel. Tests run with network
sockets disabled.

The same checks can be run individually:

```bash
uv run ruff format --check .
uv run ruff check .
uv run python scripts/check_import_boundaries.py
uv run pyright
uv run pytest
uv run python -m build --no-isolation
```

GitHub Actions runs each validation stage independently on every pull request and every push to
`main`.

## Project layout

```text
.
|-- AGENTS.md
|-- ARCHITECTURE.md
|-- PLANS.md
|-- QUALITY.md
|-- SECURITY.md
|-- TRADING_MANDATE.md
|-- .github/workflows/ci.yml
|-- docs/
|-- scripts/check_import_boundaries.py
|-- scripts/validate.py
|-- src/autonomous_trading/
|-- tests/
|-- pyproject.toml
`-- uv.lock
```

## Governing documentation

Repository work is governed by the following documents:

- [Trading mandate](TRADING_MANDATE.md) — highest-level authority and prohibited behaviour
- [Repository instructions](AGENTS.md) — exact workflow, validation, test, and review rules
- [Architecture](ARCHITECTURE.md) — system boundaries and separation of responsibilities
- [Security policy](SECURITY.md) — secrets, network, supply-chain, and threat-model rules
- [Quality standard](QUALITY.md) — deterministic testing and evidence expectations
- [Plans](PLANS.md) — planning requirements and delivery source of truth
- [Documentation index](docs/README.md) — decisions, implementation plans, runbooks, and validation

All changes require human review and merge. No document or implementation may enable live trading
or access real financial credentials.

## Project management

- [Linear team board](https://linear.app/bubb134/team/BUB/overview)
- [Autonomous Trading Vertical Slice initiative](https://linear.app/bubb134/initiative/autonomous-trading-vertical-slice-fa5d8c010538)
- [BUB-46 — Backlog prioritization and execution sequencing](https://linear.app/bubb134/issue/BUB-46/track-autonomous-trading-backlog-prioritization-and-execution)
- [BUB-6 — Governing documents and repository instructions](https://linear.app/bubb134/issue/BUB-6/add-governing-documents-and-repository-instructions)
- [BUB-7 — Package boundaries and dependency rules](https://linear.app/bubb134/issue/BUB-7/define-package-boundaries-and-dependency-rules)
