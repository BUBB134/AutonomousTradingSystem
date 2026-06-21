# Risk Package Instructions

These instructions apply to future files in this directory in addition to the root instructions.

- Risk controls are independent of strategy code and cannot be bypassed or weakened by strategy
  configuration.
- Evaluate proposed paper targets before execution simulation.
- Default to rejection when limits, prices, positions, freshness, or required state are unknown.
- Limits must be explicit, typed, versioned, deterministic, and covered by boundary tests.
- Record every approval, constraint, and rejection in the append-only audit trail.
- Changes require negative tests, documentation updates, focused human review, and human merge.

This package must not contain live-broker connectivity or real-capital behaviour.
