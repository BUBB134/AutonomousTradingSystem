# Security Policy

## Supported scope

Security work in the initial vertical slice protects research artifacts, source code, configuration,
historical data, and the isolated paper simulator. This repository is not authorised to connect to
live brokerage or real-capital systems.

Report suspected vulnerabilities privately to the repository owner. Do not open a public issue that
contains credentials, exploit details, personal financial information, or other sensitive data.

## Security invariants

- `TRADING_MODE` defaults to `research`.
- `BROKER_ENABLED` and `LIVE_TRADING_ENABLED` remain false and must not activate live behaviour.
- Missing or invalid security-sensitive configuration fails closed.
- Tests and repository validation require no public-network access.
- Secrets are never committed, printed, placed in fixtures, or copied into issue or pull-request
  text.
- Human review and merge are required for every change.

## Secrets and credentials

Do not add broker keys, exchange keys, personal financial credentials, production cloud
credentials, database-administrator credentials, or real account identifiers.

Use obviously fake values in documentation. If a secret is discovered:

1. stop using and exposing it;
2. notify the owner through a private channel;
3. rotate or revoke it outside the repository;
4. remove it from current files and, when necessary, repository history; and
5. document the incident without reproducing the secret.

Adding a `.env` file to source control is prohibited. Adding a secret to `.gitignore` after it has
been committed does not remediate exposure.

## Network and external inputs

Tests must keep socket blocking enabled. External data and future service responses are untrusted
until their schema, provenance, timestamps, range constraints, and integrity checks pass.

Do not download market data or dependencies at runtime inside tests. Dependency installation occurs
through the committed `uv.lock`; CI installs from that lock before network-isolated validation.

## Supply chain

- Pin the Python version and commit the dependency lock.
- Review dependency additions for necessity, maintenance, licence, and transitive risk.
- Do not add broker or market-data SDKs without an approved ticket.
- Build source and wheel distributions in CI.
- Do not execute scripts from untrusted artifacts or pull requests with privileged credentials.

## Threat model

Important threats include:

- look-ahead leakage or tampered timestamps that produce false performance;
- poisoned, stale, malformed, or substituted market data;
- configuration that silently enables a less safe operating mode;
- a strategy bypassing risk, validation, execution, or reconciliation controls;
- duplicate or replayed simulated orders;
- mutation of audit or experiment evidence;
- secrets exposed in logs or artifacts; and
- compromised dependencies or CI workflows.

Controls for these threats must be explicit, testable, fail closed, and independently reviewable.

## Risk-sensitive paths

Changes under future validation, risk, execution, reconciliation, control-plane, CI, deployment, or
governance paths require focused human review. Nested `AGENTS.md` files add path-specific rules but
cannot weaken this policy or `TRADING_MANDATE.md`.
