"""Deterministic, local-only repository profile detection.

Detection reads the file tree only. It never runs the project, never installs
anything, and never contacts the network or the GitHub API, so the same tree
always yields the same profile.

Profiles are evaluated in a fixed order and the first match wins:

1. `python-docs`   documentation dominates the tree
2. `python-package` importable package plus packaging metadata
3. `python-app`     Python code without packaging metadata
4. `unknown`        no Python and not documentation-heavy

The order matters and is part of the contract: a repository that satisfies more
than one rule is reported as the first one it satisfies.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PYTHON_PACKAGE = "python-package"
PYTHON_APP = "python-app"
PYTHON_DOCS = "python-docs"
UNKNOWN = "unknown"

# A repository counts as documentation-heavy only when Markdown clearly
# dominates. The floor stops a three-file repository from qualifying by
# accident; the ratio stops an ordinary well-documented package from doing so.
DOCS_MIN_FILES = 5
DOCS_RATIO = 3

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "node_modules",
}


@dataclass(frozen=True)
class Profile:
    """The detected profile and the evidence that selected it."""

    name: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "reason": self.reason}


def detect_profile(target: str | Path) -> Profile:
    root = Path(target)
    python_files = _count_files(root, ".py")
    markdown_files = _count_files(root, ".md")

    if (
        python_files
        and markdown_files >= DOCS_MIN_FILES
        and markdown_files >= DOCS_RATIO * python_files
    ):
        return Profile(
            PYTHON_DOCS,
            f"{markdown_files} Markdown files against {python_files} Python files.",
        )

    has_package = _has_importable_package(root)
    if has_package and _has_packaging_metadata(root):
        return Profile(
            PYTHON_PACKAGE,
            "Importable package with packaging metadata in pyproject.toml.",
        )

    if python_files:
        if has_package:
            return Profile(
                PYTHON_APP,
                "Importable package without packaging metadata in pyproject.toml.",
            )
        return Profile(PYTHON_APP, f"{python_files} Python files without a package layout.")

    return Profile(UNKNOWN, "No Python files and not documentation-heavy.")


def _count_files(root: Path, suffix: str) -> int:
    return sum(1 for _ in _iter_files(root) if _.suffix == suffix)


def _iter_files(root: Path):
    if not root.is_dir():
        return
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def _has_importable_package(root: Path) -> bool:
    src = root / "src"
    if src.is_dir() and any(src.rglob("__init__.py")):
        return True
    if not root.is_dir():
        return False
    for child in root.iterdir():
        if child.name in SKIP_DIRS or child.name == "tests":
            continue
        if child.is_dir() and (child / "__init__.py").is_file():
            return True
    return False


def _has_packaging_metadata(root: Path) -> bool:
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        with pyproject.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError:
        # An unparseable pyproject.toml is already reported as a blocker by the
        # audit itself. For profiling it simply provides no metadata.
        return False
    return "project" in data or "build-system" in data
