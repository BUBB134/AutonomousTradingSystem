# BUB-28: Add initial Codex repository skills

## Goal

Add six narrowly scoped repository skills that guide repeatable issue delivery, architecture
decisions, research experiments, data-quality audits, independent validation, and risk-critical
changes without granting live-trading or deployment authority.

## Non-goals

- Implement trading, data-ingestion, validation, risk, execution, or deployment behaviour.
- Add broker, market-data, credential, network, or production integrations.
- Create a general-purpose unrestricted autonomous-agent skill.
- Replace the governing repository documents with duplicated policy text.

## Governing constraints

- `TRADING_MANDATE.md` remains the highest authority.
- Root and nested `AGENTS.md` instructions remain authoritative for repository work.
- Strategy generation and independent validation remain separate.
- Missing evidence, configuration, or safety controls must fail closed.
- Every repository change requires human review and merge.

## Current state

The repository has governing documents and enforceable package boundaries, but it has no
repository-local Codex skills for applying those rules to recurring workflows.

## Proposed design

Create the following skills under `.agents/skills/`:

- `linear-issue-delivery`
- `architecture-decision`
- `strategy-experiment`
- `data-quality-audit`
- `adversarial-strategy-validation`
- `risk-critical-change`

Each skill will contain a concise `SKILL.md` and UI metadata. The instructions will point to
repository source-of-truth documents, define a bounded workflow, identify required evidence, and
state when to stop rather than broadening authority.

Add a deterministic repository check that validates the expected skill set, frontmatter, metadata,
required source-of-truth references, and key separation or testing obligations. Include this check
in the single repository-validation command and CI.

## Package and dependency impact

No Python package dependency changes are required. The validation check lives under `scripts/` and
does not import application packages.

## Data, time, and determinism considerations

The change does not process market data or depend on time. Skill discovery and validation use
sorted repository paths and fixed expected names so identical trees produce identical results.

## Safety and failure behaviour

Validation fails when a required skill is missing, incorrectly named, malformed, references no
governing source, weakens strategy-validation independence, or omits required risk-critical test
and authority guardrails.

The skills instruct Codex to stop on governing conflicts, missing blockers, missing evidence, or
scope that would require prohibited behaviour.

## Test and evidence plan

- Unit-test valid and invalid skill fixtures.
- Test the checked-in repository skill set.
- Test forbidden authority and missing workflow requirements fail closed.
- Run each skill through the skill-creator structural validator.
- Run `uv run python scripts/validate.py`.

## Documentation updates

Add a repository skills guide and link it from the README and documentation index. Update the
implementation-plan index and validation-command documentation when the new check is added.

## Rollback or recovery

Revert the skills, repository check, tests, CI step, and documentation together. Do not retain
documentation that claims unavailable skills or validation.

## Open decisions

Future changes to these skills must be delivered through reviewed tickets. BUB-45 will define the
controlled improvement loop; this ticket does not implement self-modification.
