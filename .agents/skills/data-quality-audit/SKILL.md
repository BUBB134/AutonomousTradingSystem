---
name: data-quality-audit
description: Audit synthetic or approved historical market-data artifacts for schema validity, provenance, integrity, timestamp semantics, chronology, completeness, ordering, duplicates, and domain invariants. Use when reviewing a dataset, data adapter, fixture, ingestion result, or quality report before research, backtesting, or validation consumes it.
---

# Data Quality Audit

## Establish the evidence boundary

1. Read `../../../TRADING_MANDATE.md`, `../../../AGENTS.md`,
   `../../../ARCHITECTURE.md`, `../../../SECURITY.md`, `../../../QUALITY.md`, and the active ticket.
2. Identify the immutable input artifact, schema version, source approval, provenance, content
   digest, timezone, calendar, frequency, and expected coverage.
3. Stop when provenance, schema, approval, or time semantics are missing or contradictory. Do not
   infer a permissive default or fetch replacement data from the public network.

## Audit deterministically

1. Validate schema, types, ranges, nullability, identifiers, and version compatibility.
2. Check timestamp awareness, ordering, uniqueness, interval semantics, market-session assumptions,
   and information availability.
3. Check missing intervals, duplicate records, stale segments, unexpected revisions, and applicable
   price-volume invariants.
4. Distinguish source defects from transformations. Never silently repair, drop, reorder, or fill
   records in a way that hides the original evidence.
5. Emit stable, machine-readable findings with severity, affected records, rule identifiers, and
   artifact provenance.

## Verify failure behaviour

1. Add tests for valid data and malformed, duplicated, unordered, stale, timezone-naive,
   out-of-range, and provenance-missing inputs as applicable.
2. Prove severe or unclassified findings prevent downstream use.
3. Record corrections as new attributable artifacts that reference the rejected input.
4. Run `uv run python scripts/validate.py` and report unresolved findings without weakening checks.
