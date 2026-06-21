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

That command checks formatting, lint rules, static types, tests, and both source and wheel package
builds. Tests run with network sockets disabled.

The same checks can be run individually:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv run python -m build --sdist --wheel
```

GitHub Actions runs each validation stage independently on every pull request and every push to
`main`.

## Project layout

```text
.
|-- .github/workflows/ci.yml
|-- scripts/validate.py
|-- src/autonomous_trading/
|-- tests/
|-- pyproject.toml
`-- uv.lock
```

## Project management

- [Linear team board](https://linear.app/bubb134/team/BUB/overview)
- [Autonomous Trading Vertical Slice initiative](https://linear.app/bubb134/initiative/autonomous-trading-vertical-slice-fa5d8c010538)
- [BUB-5 — Bootstrap Python repository and deterministic CI](https://linear.app/bubb134/issue/BUB-5/bootstrap-python-repository-and-deterministic-ci)
