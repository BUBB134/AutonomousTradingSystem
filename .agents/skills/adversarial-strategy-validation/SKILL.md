---
name: adversarial-strategy-validation
description: Independently challenge immutable strategy and experiment evidence through leakage checks, benchmark comparison, robustness tests, parameter sensitivity, cost stress, regime analysis, and fail-closed promotion assessment. Use when validating or attempting to falsify a backtest, experiment, strategy claim, validation report, or promotion evidence.
---

# Adversarial Strategy Validation

## Preserve independence

1. Read `../../../TRADING_MANDATE.md`, `../../../AGENTS.md`,
   `../../../ARCHITECTURE.md`, `../../../QUALITY.md`, the active ticket, and
   `../../../src/autonomous_trading/validation/AGENTS.md`.
2. Accept only immutable, versioned experiment artifacts through validation's public interfaces.
   Do not depend on strategy implementation internals or strategy-authored approval logic.
3. Record validator identity, code version, configuration, input digests, timestamps, and seeds.
4. Treat missing, stale, contradictory, mutable, or producer-only evidence as a validation failure.

## Attempt to falsify the claim

1. Reconstruct the claimed result from recorded inputs.
2. Test timestamp semantics, look-ahead leakage, survivorship and selection effects, duplicates,
   revisions, and information availability.
3. Compare declared benchmarks and stress costs, slippage, parameters, windows, seeds, regimes,
   concentration, and hidden exposures as applicable.
4. Include deliberately fragile or leaking controls where useful to prove the validator rejects
   them.
5. Prefer rejection or inconclusive status over unsupported confidence.

## Produce independent evidence

1. Emit an immutable machine-readable report containing checks, evidence references, findings,
   severity, and a deterministic outcome.
2. Do not repair the strategy, rewrite its artifacts, grant paper authority, self-approve, or merge
   a promotion decision.
3. Add expected-path, failure-path, leakage, robustness, and reproducibility tests.
4. Run `uv run python scripts/validate.py` and hand the report to a separate fail-closed promotion
   gate.
