"""Tests for enforceable package dependency boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.check_import_boundaries import (
    ALLOWED_DEPENDENCIES,
    DEFAULT_PACKAGE_ROOT,
    find_boundary_violations,
)


def _package_tree(tmp_path: Path) -> Path:
    package_root = tmp_path / "autonomous_trading"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    for package_name in ALLOWED_DEPENDENCIES:
        package_path = package_root / package_name
        package_path.mkdir()
        (package_path / "__init__.py").write_text("", encoding="utf-8")
    return package_root


def _write_module(package_root: Path, package_name: str, source: str) -> Path:
    module_path = package_root / package_name / "example.py"
    module_path.write_text(source, encoding="utf-8")
    return module_path


def test_repository_respects_package_boundaries() -> None:
    """The checked-in source tree satisfies the declared dependency policy."""
    assert find_boundary_violations(DEFAULT_PACKAGE_ROOT) == ()


@pytest.mark.parametrize(
    ("package_name", "source", "expected_message"),
    [
        (
            "strategy",
            "from autonomous_trading import execution\n",
            "'strategy' must not depend on 'execution'",
        ),
        (
            "risk",
            "from autonomous_trading import strategy\n",
            "'risk' must not depend on 'strategy'",
        ),
        (
            "validation",
            "from autonomous_trading import strategy\n",
            "'validation' must not depend on 'strategy'",
        ),
        (
            "strategy",
            "from .. import execution\n",
            "'strategy' must not depend on 'execution'",
        ),
        (
            "strategy",
            "from ... import execution\n",
            "relative import escapes the autonomous_trading package root",
        ),
    ],
)
def test_forbidden_dependencies_fail_closed(
    tmp_path: Path,
    package_name: str,
    source: str,
    expected_message: str,
) -> None:
    """Forbidden absolute and relative imports are rejected."""
    package_root = _package_tree(tmp_path)
    _write_module(package_root, package_name, source)

    violations = find_boundary_violations(package_root)

    assert len(violations) == 1
    assert expected_message in violations[0].message


def test_allowed_dependencies_use_public_package_interfaces(tmp_path: Path) -> None:
    """Allowed dependencies may import symbols exposed by the target package."""
    package_root = _package_tree(tmp_path)
    _write_module(
        package_root,
        "validation",
        "from autonomous_trading.experiment import ExperimentArtifact\n",
    )
    _write_module(
        package_root,
        "execution",
        "from autonomous_trading.risk import ApprovedPaperIntent\n",
    )

    assert find_boundary_violations(package_root) == ()


def test_cross_package_internal_import_is_rejected(tmp_path: Path) -> None:
    """A caller cannot couple itself to another package's implementation module."""
    package_root = _package_tree(tmp_path)
    _write_module(
        package_root,
        "validation",
        "from autonomous_trading.experiment.internal import ExperimentArtifact\n",
    )

    violations = find_boundary_violations(package_root)

    assert len(violations) == 1
    assert "through its public package interface" in violations[0].message


def test_undeclared_package_fails_closed(tmp_path: Path) -> None:
    """Adding a package without an explicit boundary rule is rejected."""
    package_root = _package_tree(tmp_path)
    unknown_package = package_root / "broker"
    unknown_package.mkdir()
    (unknown_package / "__init__.py").write_text("", encoding="utf-8")

    violations = find_boundary_violations(package_root)

    assert len(violations) == 1
    assert "has no declared dependency rule" in violations[0].message


def test_top_level_module_cannot_bypass_package_rules(tmp_path: Path) -> None:
    """A root module cannot create an undeclared cross-component boundary."""
    package_root = _package_tree(tmp_path)
    (package_root / "broker.py").write_text("", encoding="utf-8")

    violations = find_boundary_violations(package_root)

    assert len(violations) == 1
    assert "top-level modules are not package boundaries" in violations[0].message


def test_namespace_package_cannot_bypass_package_rules(tmp_path: Path) -> None:
    """A directory without ``__init__.py`` still requires an explicit boundary rule."""
    package_root = _package_tree(tmp_path)
    unknown_package = package_root / "broker"
    unknown_package.mkdir()
    (unknown_package / "adapter.py").write_text("", encoding="utf-8")

    violations = find_boundary_violations(package_root)

    assert len(violations) == 1
    assert "has no declared dependency rule" in violations[0].message
