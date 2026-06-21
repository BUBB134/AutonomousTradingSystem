# Deployment Package Instructions

These instructions apply to future files in this directory in addition to the root instructions.

- Deployment means deterministic assembly for research, backtest, validation, or isolated paper
  simulation only.
- No command, adapter, environment, workflow, or configuration may deploy live-trading behaviour.
- Composition must preserve independent validation, risk, execution, and reconciliation controls.
- Missing or contradictory configuration must fail closed before any simulated activity begins.
- Changes require boundary tests, failure-mode tests, documentation updates, focused human review,
  and human merge.

If a task requests production deployment, broker credentials, or real-capital access, stop and
report a mandate conflict.
