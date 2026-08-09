"""Deterministic, local-only repository profile detection.

Detection reads the file tree only. It never runs the project, never installs
anything, and never contacts the network or the GitHub API, so the same tree
always yields the same profile.

Profiles are evaluated in a fixed order and the first match wins:

1. `python-docs`    documentation dominates a tree containing Python
2. `python-package` importable package plus packaging metadata
3. `python-app`     Python code without packaging metadata
4. `node-project`   a parseable `package.json`
5. `unknown`        none of the above

The order matters and is part of the contract: a repository that satisfies more
than one rule is reported as the first one it satisfies. Node is evaluated after
the Python rules so that a Python project which merely carries a `package.json`
for tooling is still audited as a Python project.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PYTHON_PACKAGE = "python-package"
PYTHON_APP = "python-app"
PYTHON_DOCS = "python-docs"
NODE_PROJECT = "node-project"
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

    if (root / "package.json").is_file():
        # Presence is enough. A malformed package.json is exactly the repository
        # that needs the Node checks to run and report it, so it must not fall
        # through to `unknown` and escape auditing.
        return Profile(NODE_PROJECT, "package.json present.")

    return Profile(UNKNOWN, "No Python files and no package.json.")


def read_package_json(root: Path) -> dict[str, Any] | None:
    """Return the parsed `package.json`, or None when absent or unparseable."""
    manifest = Path(root) / "package.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8", errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


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
