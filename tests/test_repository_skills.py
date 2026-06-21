"""Tests for repository-local Codex skill validation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from scripts.check_repository_skills import (
    DEFAULT_SKILLS_ROOT,
    EXPECTED_SKILLS,
    find_skill_violations,
)


@pytest.fixture
def skills_tree(tmp_path: Path) -> Path:
    """Copy the checked-in skill set for fail-closed mutation tests."""
    copied_root = tmp_path / "skills"
    shutil.copytree(DEFAULT_SKILLS_ROOT, copied_root)
    return copied_root


def test_repository_skills_are_valid() -> None:
    """The checked-in repository skill set satisfies the BUB-28 contract."""
    assert find_skill_violations() == ()


def test_missing_required_skill_fails_closed(skills_tree: Path) -> None:
    """Deleting an approved skill is reported."""
    missing_skill = EXPECTED_SKILLS[0]
    shutil.rmtree(skills_tree / missing_skill)

    violations = find_skill_violations(skills_tree)

    assert any(
        violation.path.name == missing_skill
        and violation.message == "required repository skill is missing"
        for violation in violations
    )


def test_unapproved_general_skill_fails_closed(skills_tree: Path) -> None:
    """An extra unrestricted skill cannot silently enter the approved set."""
    unexpected_skill = skills_tree / "general-autonomous-agent"
    unexpected_skill.mkdir()

    violations = find_skill_violations(skills_tree)

    assert any(
        violation.path == unexpected_skill and "not approved by BUB-28" in violation.message
        for violation in violations
    )


def test_skill_name_must_match_directory(skills_tree: Path) -> None:
    """Frontmatter cannot disguise a skill under another name."""
    skill_file = skills_tree / "linear-issue-delivery" / "SKILL.md"
    skill_file.write_text(
        skill_file.read_text(encoding="utf-8").replace(
            "name: linear-issue-delivery",
            "name: unrestricted-delivery",
        ),
        encoding="utf-8",
    )

    violations = find_skill_violations(skills_tree)

    assert any("must match the skill directory" in violation.message for violation in violations)


def test_frontmatter_fields_must_be_yaml_strings(skills_tree: Path) -> None:
    """YAML collections cannot masquerade as valid skill trigger descriptions."""
    skill_file = skills_tree / "architecture-decision" / "SKILL.md"
    skill_file.write_text(
        skill_file.read_text(encoding="utf-8")
        .replace(
            "description: Evaluate and record",
            "description: [Use this skill to evaluate and record",
            1,
        )
        .replace(
            "decisions. Use when",
            "decisions, Use when]",
            1,
        ),
        encoding="utf-8",
    )

    violations = find_skill_violations(skills_tree)

    assert any(
        violation.message == "frontmatter description must be a string" for violation in violations
    )


def test_unresolved_skill_template_fails_closed(skills_tree: Path) -> None:
    """Generated TODO placeholders cannot pass repository validation."""
    skill_file = skills_tree / "architecture-decision" / "SKILL.md"
    skill_file.write_text(
        f"{skill_file.read_text(encoding='utf-8')}\nTODO: choose an option\n",
        encoding="utf-8",
    )

    violations = find_skill_violations(skills_tree)

    assert any("unresolved TODO" in violation.message for violation in violations)


def test_risk_skill_requires_property_test_obligation(skills_tree: Path) -> None:
    """Risk-critical guidance must retain its broad invariant-test requirement."""
    skill_file = skills_tree / "risk-critical-change" / "SKILL.md"
    skill_file.write_text(
        skill_file.read_text(encoding="utf-8").replace(
            "property-based tests",
            "example tests",
        ),
        encoding="utf-8",
    )

    violations = find_skill_violations(skills_tree)

    assert any(
        "required workflow fragment is missing: 'property-based tests'" in violation.message
        for violation in violations
    )


def test_metadata_prompt_must_invoke_its_skill(skills_tree: Path) -> None:
    """UI metadata cannot point users at a different workflow."""
    metadata_file = skills_tree / "data-quality-audit" / "agents" / "openai.yaml"
    metadata_file.write_text(
        metadata_file.read_text(encoding="utf-8").replace(
            "$data-quality-audit",
            "$strategy-experiment",
        ),
        encoding="utf-8",
    )

    violations = find_skill_violations(skills_tree)

    assert any(
        "interface.default_prompt must explicitly invoke $data-quality-audit" in violation.message
        for violation in violations
    )


def test_metadata_fields_must_be_nested_under_interface(skills_tree: Path) -> None:
    """Top-level metadata fields cannot satisfy the required interface contract."""
    metadata_file = skills_tree / "strategy-experiment" / "agents" / "openai.yaml"
    metadata_file.write_text(
        metadata_file.read_text(encoding="utf-8")
        .replace(
            "interface:\n  display_name:",
            "interface: []\ndisplay_name:",
            1,
        )
        .replace(
            "\n  short_description:",
            "\nshort_description:",
            1,
        )
        .replace(
            "\n  default_prompt:",
            "\ndefault_prompt:",
            1,
        ),
        encoding="utf-8",
    )

    violations = find_skill_violations(skills_tree)

    assert any(
        violation.message == "metadata interface must be a YAML mapping" for violation in violations
    )
