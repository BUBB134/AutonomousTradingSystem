# Execution Package Instructions

These instructions apply to future files in this directory in addition to the root instructions.

- Execution is restricted to the deterministic paper-broker simulator.
- Accept only instructions already approved by independent risk controls.
- Order commands and state transitions must be idempotent and safe under retries and restarts.
- Duplicate, stale, malformed, or unauthorised commands must fail closed and be audited.
- No adapter, configuration value, endpoint, or feature flag may route to a live venue.
- Changes require lifecycle and failure-mode tests, documentation updates, focused human review, and
  human merge.

If a task requests broker credentials or live order routing, stop and report a mandate conflict.
