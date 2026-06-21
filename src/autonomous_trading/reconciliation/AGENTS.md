# Reconciliation Package Instructions

These instructions apply to future files in this directory in addition to the root instructions.

- Reconciliation independently compares expected and observed paper-simulator state.
- A material mismatch must halt new simulated activity until explicitly resolved.
- Corrections are append-only records; never rewrite prior evidence to hide a mismatch.
- Repeated reconciliation over identical inputs must be deterministic and idempotent.
- Test missing records, duplicates, partial fills, restarts, stale state, and inconsistent balances.
- Changes require documentation updates, focused human review, and human merge.

This package must not reconcile or control live brokerage accounts.
