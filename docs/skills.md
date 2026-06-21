# Repository Skills

Repository-local Codex skills live under `.agents/skills/`. They provide bounded workflows for
recurring work while deferring authority to `TRADING_MANDATE.md`, root and nested `AGENTS.md`
files, the active Linear ticket, and approved plans.

## Available skills

| Skill | Invoke with | Purpose |
| --- | --- | --- |
| Linear issue delivery | `$linear-issue-delivery` | Deliver one approved BUB issue through planning, implementation, validation, pull request, CI, and review. |
| Architecture decision | `$architecture-decision` | Evaluate and record package, dependency, ownership, and trust-boundary decisions. |
| Strategy experiment | `$strategy-experiment` | Design reproducible research-only experiments without claiming independent validation. |
| Data quality audit | `$data-quality-audit` | Audit versioned market data, provenance, timestamps, chronology, and quality failures. |
| Adversarial strategy validation | `$adversarial-strategy-validation` | Independently attempt to falsify immutable strategy evidence. |
| Risk-critical change | `$risk-critical-change` | Apply strengthened planning, tests, evidence, and review to safety-sensitive paths. |

Invoke a skill explicitly in the task, for example:

```text
Use $data-quality-audit to assess this synthetic daily-bars fixture before backtesting.
```

Codex may also select a skill when its frontmatter description directly matches the requested
work. A skill narrows the workflow; it never grants broker access, live-trading authority,
deployment authority, approval authority, or merge authority.

## Updating skills

1. Use an approved Linear ticket and follow BUB-46 sequencing and blocker rules.
2. Read the governing documents and use the skill-creation workflow before editing.
3. Keep frontmatter limited to a precise `name` and trigger-focused `description`.
4. Reference repository source-of-truth documents rather than copying policy into the skill.
5. Update `agents/openai.yaml` whenever the skill name, purpose, or invocation changes.
6. Add or update fail-closed tests in `tests/test_repository_skills.py`.
7. Run the skill structural validator and the complete repository suite:

   ```bash
   uv run python scripts/check_repository_skills.py
   uv run python scripts/validate.py
   ```

8. Open a pull request, require passing CI and resolved review conversations, and leave merge to a
   human.

BUB-45 owns the future controlled skill-improvement loop. These skills must not modify themselves
or silently broaden their own authority.
