# Independent Validation

Validation exists to challenge strategy and experiment claims, not to confirm the strategy
author's preferred conclusion.

Validation artifacts must be reproducible from immutable inputs and identify the code, data,
configuration, schema versions, and seeds used. Reports must show failed checks and contradictory
evidence as prominently as successful checks.

Promotion fails closed when evidence is missing, stale, internally inconsistent, or not independent
of the strategy implementation being evaluated.

Detailed validation implementation is future work. Path-specific repository instructions are
defined in `src/autonomous_trading/validation/AGENTS.md`.
