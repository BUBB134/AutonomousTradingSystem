# Validation Package Instructions

These instructions apply to future files in this directory in addition to the root instructions.

- Validation must be independent of strategy approval logic and must be able to reject promotion.
- Consume immutable experiment artifacts through stable schemas; do not trust strategy-authored
  summaries as evidence.
- Test leakage, chronology, costs, sensitivity, concentration, regime dependence, and benchmark
  comparisons when relevant.
- Missing, stale, malformed, or contradictory evidence must fail closed.
- Reports must preserve failed checks and provenance; do not suppress inconvenient results.
- Changes require tests, validation-documentation updates, focused human review, and human merge.

Do not implement strategy generation or execution behaviour in this package.
