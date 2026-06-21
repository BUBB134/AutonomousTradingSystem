"""Enforce top-level package dependency and public-interface boundaries."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_ROOT = REPOSITORY_ROOT / "src" / "autonomous_trading"
OUTSIDE_PACKAGE_ROOT = "<outside autonomous_trading>"

# A package may import itself and the packages listed here. Cross-package imports must target the
# dependency package's public ``__init__.py`` interface rather than an internal submodule.
ALLOWED_DEPENDENCIES: dict[str, frozenset[str]] = {
    "audit": frozenset(),
    "backtest": frozenset(
        {
            "audit",
            "configuration",
            "data",
            "execution",
            "portfolio",
            "reconciliation",
            "risk",
            "strategy",
        }
    ),
    "configuration": frozenset(),
    "control_plane": frozenset({"audit", "configuration", "monitoring"}),
    "data": frozenset(),
    "deployment": frozenset(
        {
            "audit",
            "backtest",
            "configuration",
            "control_plane",
            "data",
            "execution",
            "experiment",
            "monitoring",
            "portfolio",
            "reconciliation",
            "registry",
            "risk",
            "strategy",
            "validation",
        }
    ),
    "execution": frozenset({"audit", "configuration", "portfolio", "risk"}),
    "experiment": frozenset({"audit", "backtest", "configuration"}),
    "monitoring": frozenset(
        {
            "audit",
            "execution",
            "experiment",
            "reconciliation",
            "registry",
            "risk",
            "validation",
        }
    ),
    "portfolio": frozenset({"data", "strategy"}),
    "reconciliation": frozenset({"audit", "execution", "portfolio"}),
    "registry": frozenset({"audit", "configuration", "experiment", "validation"}),
    "risk": frozenset({"audit", "configuration", "data", "portfolio"}),
    "strategy": frozenset({"data"}),
    "validation": frozenset({"data", "experiment"}),
}


@dataclass(frozen=True, order=True)
class BoundaryViolation:
    """A deterministic package-boundary violation."""

    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        """Render the violation in a compiler-style format."""
        return f"{self.path}:{self.line}: {self.message}"


@dataclass(frozen=True)
class InternalImport:
    """An import resolved to a top-level autonomous-trading package."""

    target_package: str
    targets_internal_module: bool


def _source_package(path: Path, package_root: Path) -> str | None:
    relative_path = path.relative_to(package_root)
    if len(relative_path.parts) < 2:
        return None
    return relative_path.parts[0]


def _current_package_parts(path: Path, package_root: Path) -> tuple[str, ...]:
    relative_path = path.relative_to(package_root)
    return relative_path.parent.parts


def _absolute_internal_import(module_name: str) -> InternalImport | None:
    parts = module_name.split(".")
    if not parts or parts[0] != "autonomous_trading" or len(parts) == 1:
        return None
    return InternalImport(
        target_package=parts[1],
        targets_internal_module=len(parts) > 2,
    )


def _relative_internal_import(
    *,
    node: ast.ImportFrom,
    path: Path,
    package_root: Path,
) -> tuple[InternalImport, ...]:
    current_package = _current_package_parts(path, package_root)
    retained_parts = len(current_package) - (node.level - 1)
    if retained_parts < 0:
        return (
            InternalImport(
                target_package=OUTSIDE_PACKAGE_ROOT,
                targets_internal_module=False,
            ),
        )

    prefix = current_package[:retained_parts]
    module_parts = tuple(node.module.split(".")) if node.module else ()
    base_parts = prefix + module_parts

    if node.module:
        if not base_parts:
            return ()
        return (
            InternalImport(
                target_package=base_parts[0],
                targets_internal_module=len(base_parts) > 1,
            ),
        )

    imports: list[InternalImport] = []
    for alias in node.names:
        alias_parts = tuple(alias.name.split("."))
        resolved_parts = base_parts + alias_parts
        if resolved_parts:
            imports.append(
                InternalImport(
                    target_package=resolved_parts[0],
                    targets_internal_module=len(resolved_parts) > 1,
                )
            )
    return tuple(imports)


def _imports_from_node(
    node: ast.Import | ast.ImportFrom,
    *,
    path: Path,
    package_root: Path,
) -> tuple[InternalImport, ...]:
    if isinstance(node, ast.Import):
        return tuple(
            internal_import
            for alias in node.names
            if (internal_import := _absolute_internal_import(alias.name)) is not None
        )

    if node.level:
        return _relative_internal_import(node=node, path=path, package_root=package_root)

    if node.module == "autonomous_trading":
        return tuple(
            InternalImport(
                target_package=target_package,
                targets_internal_module="." in alias.name,
            )
            for alias in node.names
            if (target_package := alias.name.split(".")[0]) in ALLOWED_DEPENDENCIES
        )

    if node.module is None:
        return ()

    internal_import = _absolute_internal_import(node.module)
    return (internal_import,) if internal_import is not None else ()


def _policy_violations(package_root: Path) -> list[BoundaryViolation]:
    violations: list[BoundaryViolation] = []
    declared_packages = set(ALLOWED_DEPENDENCIES)
    initialized_packages = {
        path.parent.name for path in package_root.glob("*/__init__.py") if path.parent.is_dir()
    }
    source_directories = {
        path.name for path in package_root.iterdir() if path.is_dir() and any(path.rglob("*.py"))
    }

    for package in sorted(declared_packages - initialized_packages):
        violations.append(
            BoundaryViolation(
                path=package_root / package / "__init__.py",
                line=0,
                message=f"declared package {package!r} is missing",
            )
        )
    for package in sorted(source_directories - declared_packages):
        violations.append(
            BoundaryViolation(
                path=package_root / package / "__init__.py",
                line=0,
                message=f"package {package!r} has no declared dependency rule",
            )
        )

    for path in sorted(package_root.glob("*.py")):
        if path.name != "__init__.py":
            violations.append(
                BoundaryViolation(
                    path=path,
                    line=0,
                    message=(
                        "top-level modules are not package boundaries; "
                        "create a declared package instead"
                    ),
                )
            )

    for source_package, dependencies in sorted(ALLOWED_DEPENDENCIES.items()):
        unknown_dependencies = dependencies - declared_packages
        for target_package in sorted(unknown_dependencies):
            violations.append(
                BoundaryViolation(
                    path=Path(__file__),
                    line=0,
                    message=(
                        f"rule for {source_package!r} references unknown package {target_package!r}"
                    ),
                )
            )
        if source_package in dependencies:
            violations.append(
                BoundaryViolation(
                    path=Path(__file__),
                    line=0,
                    message=f"rule for {source_package!r} must not list itself",
                )
            )

    visited: set[str] = set()
    active_path: list[str] = []
    active_packages: set[str] = set()
    cycles: set[tuple[str, ...]] = set()

    def visit(package: str) -> None:
        active_path.append(package)
        active_packages.add(package)
        for dependency in sorted(ALLOWED_DEPENDENCIES[package]):
            if dependency not in declared_packages:
                continue
            if dependency in active_packages:
                cycle_start = active_path.index(dependency)
                cycles.add((*active_path[cycle_start:], dependency))
            elif dependency not in visited:
                visit(dependency)
        active_path.pop()
        active_packages.remove(package)
        visited.add(package)

    for package in sorted(declared_packages):
        if package not in visited:
            visit(package)

    for cycle in sorted(cycles):
        violations.append(
            BoundaryViolation(
                path=Path(__file__),
                line=0,
                message=f"dependency cycle declared: {' -> '.join(cycle)}",
            )
        )

    return violations


def find_boundary_violations(
    package_root: Path = DEFAULT_PACKAGE_ROOT,
) -> tuple[BoundaryViolation, ...]:
    """Return all package policy and import violations under ``package_root``."""
    if not package_root.is_dir():
        return (
            BoundaryViolation(
                path=package_root,
                line=0,
                message="package root is missing",
            ),
        )

    violations = _policy_violations(package_root)
    for path in sorted(package_root.rglob("*.py")):
        source_package = _source_package(path, package_root)
        if source_package is None:
            continue

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            violations.append(
                BoundaryViolation(
                    path=path,
                    line=getattr(error, "lineno", 0) or 0,
                    message=f"cannot inspect imports: {error}",
                )
            )
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Import | ast.ImportFrom):
                continue
            for internal_import in _imports_from_node(
                node,
                path=path,
                package_root=package_root,
            ):
                target_package = internal_import.target_package
                if target_package == OUTSIDE_PACKAGE_ROOT:
                    violations.append(
                        BoundaryViolation(
                            path=path,
                            line=node.lineno,
                            message=(
                                f"{source_package!r} relative import escapes the "
                                "autonomous_trading package root"
                            ),
                        )
                    )
                    continue
                if target_package == source_package:
                    continue
                if target_package not in ALLOWED_DEPENDENCIES:
                    violations.append(
                        BoundaryViolation(
                            path=path,
                            line=node.lineno,
                            message=(
                                f"{source_package!r} imports undeclared package {target_package!r}"
                            ),
                        )
                    )
                    continue
                if target_package not in ALLOWED_DEPENDENCIES[source_package]:
                    violations.append(
                        BoundaryViolation(
                            path=path,
                            line=node.lineno,
                            message=(f"{source_package!r} must not depend on {target_package!r}"),
                        )
                    )
                    continue
                if internal_import.targets_internal_module:
                    violations.append(
                        BoundaryViolation(
                            path=path,
                            line=node.lineno,
                            message=(
                                f"{source_package!r} must import {target_package!r} "
                                "through its public package interface"
                            ),
                        )
                    )

    return tuple(sorted(violations))


def main() -> None:
    """Exit non-zero when repository package boundaries are violated."""
    violations = find_boundary_violations()
    if violations:
        print("Package boundary violations:")
        for violation in violations:
            print(f"- {violation}")
        raise SystemExit(1)
    print("Package boundaries are valid.")


if __name__ == "__main__":
    main()
