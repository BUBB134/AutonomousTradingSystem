"""Validate the repository-local Codex skill set."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILLS_ROOT = ROOT / ".agents" / "skills"

EXPECTED_SKILLS: tuple[str, ...] = (
    "adversarial-strategy-validation",
    "architecture-decision",
    "data-quality-audit",
    "linear-issue-delivery",
    "risk-critical-change",
    "strategy-experiment",
)

COMMON_BODY_FRAGMENTS: tuple[str, ...] = (
    "TRADING_MANDATE.md",
    "AGENTS.md",
)

REQUIRED_BODY_FRAGMENTS: dict[str, tuple[str, ...]] = {
    "adversarial-strategy-validation": (
        "immutable, versioned experiment artifacts",
        "Do not depend on strategy implementation internals",
        "look-ahead leakage",
        "promotion",
    ),
    "architecture-decision": (
        "docs/decisions/",
        "status quo",
        "trust boundaries",
        "fails closed",
    ),
    "data-quality-audit": (
        "provenance",
        "timezone",
        "Never silently repair",
        "prevent downstream use",
    ),
    "linear-issue-delivery": (
        "BUB-46",
        "docs/plans/",
        "scripts/validate.py",
        "Review the complete diff",
        "Update Linear",
    ),
    "risk-critical-change": (
        "boundary tests",
        "failure-path tests",
        "property-based tests",
        "Never self-approve",
    ),
    "strategy-experiment": (
        "versioned historical data",
        "information availability",
        "typed signals",
        "independent validation",
    ),
}

SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class SkillViolation:
    """A deterministic repository-skill validation failure."""

    path: Path
    message: str


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("SKILL.md must start with YAML frontmatter")

    try:
        closing_index = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("SKILL.md frontmatter is not closed") from error

    fields: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"invalid frontmatter line: {line!r}")
        normalized_key = key.strip()
        if normalized_key in fields:
            raise ValueError(f"duplicate frontmatter field: {normalized_key!r}")
        fields[normalized_key] = value.strip()

    return fields, "\n".join(lines[closing_index + 1 :])


def _quoted_metadata_value(text: str, key: str) -> str | None:
    pattern = re.compile(rf'^\s*{re.escape(key)}:\s*"([^"]+)"\s*$', re.MULTILINE)
    match = pattern.search(text)
    return match.group(1) if match else None


def _validate_skill(skill_root: Path, skill_name: str) -> list[SkillViolation]:
    violations: list[SkillViolation] = []
    skill_file = skill_root / "SKILL.md"
    metadata_file = skill_root / "agents" / "openai.yaml"

    if not skill_file.is_file():
        violations.append(SkillViolation(skill_file, "required SKILL.md is missing"))
        return violations

    try:
        skill_text = skill_file.read_text(encoding="utf-8")
    except OSError as error:
        violations.append(SkillViolation(skill_file, f"cannot read SKILL.md: {error}"))
        return violations

    if "TODO" in skill_text:
        violations.append(SkillViolation(skill_file, "SKILL.md contains an unresolved TODO"))

    try:
        frontmatter, body = _parse_frontmatter(skill_text)
    except ValueError as error:
        violations.append(SkillViolation(skill_file, str(error)))
        frontmatter = {}
        body = ""

    if set(frontmatter) != {"description", "name"}:
        violations.append(
            SkillViolation(
                skill_file,
                "frontmatter must contain only the name and description fields",
            )
        )

    declared_name = frontmatter.get("name")
    if declared_name != skill_name:
        violations.append(
            SkillViolation(
                skill_file,
                f"frontmatter name must match the skill directory {skill_name!r}",
            )
        )
    if declared_name is not None and not SKILL_NAME_PATTERN.fullmatch(declared_name):
        violations.append(
            SkillViolation(skill_file, "frontmatter name must use lowercase hyphen-case")
        )

    description = frontmatter.get("description", "")
    if len(description) < 80 or "Use " not in description:
        violations.append(
            SkillViolation(
                skill_file,
                "description must precisely explain the capability and when to use it",
            )
        )

    for fragment in (*COMMON_BODY_FRAGMENTS, *REQUIRED_BODY_FRAGMENTS[skill_name]):
        if fragment not in body:
            violations.append(
                SkillViolation(skill_file, f"required workflow fragment is missing: {fragment!r}")
            )

    if not metadata_file.is_file():
        violations.append(SkillViolation(metadata_file, "agents/openai.yaml is missing"))
        return violations

    try:
        metadata_text = metadata_file.read_text(encoding="utf-8")
    except OSError as error:
        violations.append(SkillViolation(metadata_file, f"cannot read metadata: {error}"))
        return violations

    if "TODO" in metadata_text:
        violations.append(SkillViolation(metadata_file, "metadata contains an unresolved TODO"))
    if "interface:" not in metadata_text:
        violations.append(SkillViolation(metadata_file, "metadata interface section is missing"))

    display_name = _quoted_metadata_value(metadata_text, "display_name")
    short_description = _quoted_metadata_value(metadata_text, "short_description")
    default_prompt = _quoted_metadata_value(metadata_text, "default_prompt")
    if not display_name:
        violations.append(SkillViolation(metadata_file, "display_name must be a quoted string"))
    if short_description is None or not 25 <= len(short_description) <= 64:
        violations.append(
            SkillViolation(metadata_file, "short_description must contain 25 to 64 characters")
        )
    if default_prompt is None or f"${skill_name}" not in default_prompt:
        violations.append(
            SkillViolation(
                metadata_file,
                f"default_prompt must explicitly invoke ${skill_name}",
            )
        )

    return violations


def find_skill_violations(
    skills_root: Path = DEFAULT_SKILLS_ROOT,
) -> tuple[SkillViolation, ...]:
    """Return all repository-skill violations in deterministic order."""
    if not skills_root.is_dir():
        return (SkillViolation(skills_root, "repository skill root is missing"),)

    actual_skills = {path.name for path in skills_root.iterdir() if path.is_dir()}
    violations: list[SkillViolation] = []

    for missing_skill in sorted(set(EXPECTED_SKILLS) - actual_skills):
        violations.append(
            SkillViolation(skills_root / missing_skill, "required repository skill is missing")
        )
    for unexpected_skill in sorted(actual_skills - set(EXPECTED_SKILLS)):
        violations.append(
            SkillViolation(
                skills_root / unexpected_skill,
                "unexpected repository skill is not approved by BUB-28",
            )
        )

    for skill_name in EXPECTED_SKILLS:
        if skill_name in actual_skills:
            violations.extend(_validate_skill(skills_root / skill_name, skill_name))

    return tuple(
        sorted(violations, key=lambda violation: (violation.path.as_posix(), violation.message))
    )


def main() -> None:
    """Exit unsuccessfully when the repository skill set is invalid."""
    violations = find_skill_violations()
    if not violations:
        print(f"Validated {len(EXPECTED_SKILLS)} repository skills.")
        return

    print("Repository skill validation failed:", file=sys.stderr)
    for violation in violations:
        try:
            display_path = violation.path.relative_to(ROOT)
        except ValueError:
            display_path = violation.path
        print(f"- {display_path}: {violation.message}", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
