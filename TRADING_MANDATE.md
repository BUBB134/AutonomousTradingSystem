# Trading Mandate

## Authority

This mandate is the highest-level repository policy. Every design, plan, instruction,
implementation, test, review, and operational action must comply with it.

If another repository document or local instruction conflicts with this mandate, follow this
mandate and stop to surface the conflict. Only the repository owner may approve a change to this
mandate, and every such change requires human review and merge.

## Mission

Build a safe, reproducible system for:

1. systematic trading research;
2. chronology-safe backtesting;
3. independent strategy validation;
4. isolated paper-trading simulation; and
5. evidence-based reporting for a possible future live candidate.

The system exists to test and challenge trading ideas. It does not have authority to place live
orders, move capital, or decide that a strategy may trade real money.

## Permitted operating scope

Repository work may support only these modes:

- `research`: offline development, synthetic data, approved historical data, and deterministic
  experiments;
- `backtest`: deterministic simulation over versioned inputs;
- `validation`: independent attempts to falsify strategy results and promotion evidence; and
- `paper`: isolated simulation with no route to a real broker or real capital.

The default mode is `research`. Missing, malformed, contradictory, or unrecognised configuration
must fail closed.

## Prohibited behaviour

The repository must not:

- place, route, stage, or schedule a live order;
- connect to a live or sandbox brokerage account unless a later owner-approved mandate explicitly
  permits a narrowly scoped simulator integration;
- contain broker credentials, exchange keys, personal financial credentials, or production
  secrets;
- enable live trading through configuration, environment variables, feature flags, hidden
  endpoints, or runtime overrides;
- transfer money, request withdrawals, or modify custody settings;
- use leverage, short selling, derivatives, or margin in the initial vertical slice;
- bypass risk, validation, reconciliation, audit, or promotion controls;
- treat a successful backtest as approval for paper or live operation;
- download unapproved market data during tests or require public-network access for validation;
- silently relax safety limits, data-quality rules, chronology checks, or evidence requirements;
- auto-merge, auto-deploy, or self-approve a risk-sensitive change; or
- modify its own governing rules without an explicit, separately reviewed owner decision.

If a requested task requires any prohibited behaviour, stop and report the conflict.

## Separation of responsibilities

Strategy generation and strategy approval are separate responsibilities.

- Strategy code may transform approved historical information into signals.
- Portfolio construction may transform signals into proposed targets.
- Independent risk controls may reject or constrain proposed targets.
- Execution simulation may act only on approved paper instructions.
- Reconciliation must independently compare expected and observed simulated state.
- Validation must attempt to disprove results using leakage checks, stress tests, robustness tests,
  and benchmark comparisons.
- Promotion gates must fail closed when evidence is missing, stale, contradictory, or produced by
  the component being evaluated.

No strategy component may approve itself, bypass a downstream control, or write validation
evidence on behalf of an independent validator.

## Reproducibility and provenance

Every material result must be reproducible from versioned code, configuration, input data, and
random seeds. Experiment and validation artifacts must identify their schema version and
provenance. Timestamps must be explicit and chronology must be preserved.

Audit records are append-only. Corrections are new records that reference prior records; existing
records are not rewritten to make outcomes look better.

## Human authority

Human review and merge are required for all repository changes. The repository owner retains sole
authority over:

- changes to this mandate or other governing policies;
- strategy promotion decisions;
- credentials and external service access;
- deployment;
- any future brokerage integration; and
- any future decision involving real capital.

Completion of paper trading may produce a recommendation or evidence package only. It must not
enable live trading.
