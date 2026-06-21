"""Run the complete repository validation suite."""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DIRECTORY = ROOT / "dist"

VALIDATION_COMMANDS: tuple[tuple[str, ...], ...] = (
    (sys.executable, "-m", "ruff", "format", "--check", "."),
    (sys.executable, "-m", "ruff", "check", "."),
    (sys.executable, "-m", "pyright"),
    (sys.executable, "-m", "pytest"),
)


def run(command: Sequence[str]) -> None:
    """Run one validation command and stop at the first failure."""
    printable_command = subprocess.list2cmdline(command)
    print(f"\n> {printable_command}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    """Validate formatting, linting, types, tests, and package build."""
    for command in VALIDATION_COMMANDS:
        run(command)

    shutil.rmtree(DIST_DIRECTORY, ignore_errors=True)
    run((sys.executable, "-m", "build", "--no-isolation", "--outdir", "dist"))


if __name__ == "__main__":
    main()
