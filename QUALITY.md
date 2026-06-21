# Quality Standard

## Quality objective

Quality means that a result is reproducible, chronology-safe, independently challengeable, and
unable to escape the repository's research and paper-simulation boundaries.

A green test suite is necessary but not sufficient. Claims about performance or safety require
evidence appropriate to the claim.

## Required validation

Set up the environment from the committed lockfile:

```bash
uv sync --frozen --all-groups
```

Run all repository checks:

```bash
uv run python scripts/validate.py
```

This covers formatting, linting, package-boundary enforcement, strict static types, tests, and
package build. CI must pass before merge. Tests must not require public-network access or external
services.

## Test expectations

- Unit tests cover domain rules and failure behaviour.
- Property-based tests cover invariants and broad input spaces where appropriate.
- Regression tests accompany defect fixes when practical.
- Integration tests cover component contracts without live external systems.
- Safety controls include negative tests proving missing or invalid evidence is rejected.
- Time-dependent tests use explicit clocks and timezone-aware timestamps.
- Randomised tests use recorded seeds or deterministic generators.
- Repeated identical inputs produce identical material outputs.

Do not reduce assertions, disable socket blocking, loosen types, or add broad ignores merely to
make validation green.

## Trading-specific evidence

Backtest or strategy work must address, as applicable:

- chronology and information availability;
- data quality and timestamp semantics;
- transaction costs and slippage;
- portfolio accounting reconciliation;
- benchmark comparison;
- parameter sensitivity;
- regime and concentration risk; and
- reproducibility from immutable inputs.

Strategy authorship is not independent validation. Validation code and reports must attempt to
falsify results and must be able to reject promotion.

## Review standard

Reviewers should be able to trace:

1. the ticket and intended behaviour;
2. the governing rule or architecture boundary;
3. the implementation;
4. the tests and evidence; and
5. the documentation and operational impact.

All review conversations must be resolved before merge. Human merge is required.

## Documentation standard

Documentation must describe current behaviour and clearly label future design. Commands must be
copyable. Safety limits and failure behaviour must be unambiguous.

Update architecture decisions, plans, runbooks, schemas, and examples in the same pull request as
the behaviour they describe.
