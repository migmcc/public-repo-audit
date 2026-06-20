from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

from public_repo_audit.models import (
    AuditReport,
    CategoryChecklist,
    ChecklistItem,
    Finding,
    Severity,
)

CATEGORY_WEIGHTS = {
    "Identity": 15,
    "Public readiness": 20,
    "Python project health": 25,
    "CI/readiness": 15,
    "Documentation": 15,
    "Safety": 10,
}

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

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*=\s*['\"]?[^\s'\"]{12,}"),
    re.compile(r"sk_(?:live|test|proj)?_[A-Za-z0-9_\-]{12,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
)

TEXT_SUFFIXES = {
    ".env",
    ".ini",
    ".cfg",
    ".conf",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def audit_repository(path: str | Path, test_command: str | None = None) -> AuditReport:
    target = Path(path).resolve()
    if not target.exists() or not target.is_dir():
        raise ValueError(f"Target must be an existing directory: {target}")

    findings: list[Finding] = []
    checklist = _build_checklist(target, findings)
    _scan_for_secrets(target, findings)
    if test_command:
        _run_test_command(target, test_command, findings)

    blockers = [item for item in findings if item.severity is Severity.BLOCKER]
    warnings = [item for item in findings if item.severity is Severity.WARNING]
    recommendations = [item for item in findings if item.severity is Severity.RECOMMENDATION]
    score = _score(checklist, blockers, warnings)
    verdict = _verdict(score, blockers)
    return AuditReport(
        target=target,
        score=score,
        verdict=verdict,
        blockers=blockers,
        warnings=warnings,
        recommendations=recommendations,
        checklist=checklist,
    )


def _build_checklist(target: Path, findings: list[Finding]) -> list[CategoryChecklist]:
    readme = target / "README.md"
    license_file = target / "LICENSE"
    pyproject = target / "pyproject.toml"
    has_docs = (target / "docs").is_dir() or (target / "examples").is_dir()
    has_tests = _has_tests(target)
    has_ci = (target / ".github" / "workflows" / "ci.yml").is_file()
    has_python_structure = _has_python_structure(target)
    pyproject_valid = _is_valid_pyproject(pyproject, findings)

    if not readme.is_file():
        findings.append(
            Finding(
                "MISSING_README",
                Severity.BLOCKER,
                "Identity",
                "README.md is required for a public repository.",
                "Add a README with purpose, quickstart and usage examples.",
                "README.md",
            )
        )
    if not license_file.is_file():
        findings.append(
            Finding(
                "MISSING_LICENSE",
                Severity.BLOCKER,
                "Public readiness",
                "LICENSE is required before publication.",
                "Add a project license file before publishing.",
                "LICENSE",
            )
        )
    if not pyproject.exists():
        findings.append(
            Finding(
                "MISSING_PYPROJECT",
                Severity.WARNING,
                "Python project health",
                "pyproject.toml is missing.",
                "Add pyproject.toml with project metadata and build configuration.",
                "pyproject.toml",
            )
        )
    if not has_python_structure:
        findings.append(
            Finding(
                "INVALID_PYTHON_STRUCTURE",
                Severity.BLOCKER,
                "Python project health",
                "No clear Python package/module structure was found.",
                "Add a src/<package>/ package or a top-level Python package/module.",
                "src/",
            )
        )
    if not has_tests:
        findings.append(
            Finding(
                "MISSING_TESTS",
                Severity.WARNING,
                "CI/readiness",
                "No tests were found.",
                "Add tests/ with at least one test file.",
                "tests/",
            )
        )
    if not has_ci:
        findings.append(
            Finding(
                "MISSING_CI",
                Severity.WARNING,
                "CI/readiness",
                "GitHub Actions CI workflow is missing.",
                "Add .github/workflows/ci.yml to run tests automatically.",
                ".github/workflows/ci.yml",
            )
        )
    if not (target / "CHANGELOG.md").is_file():
        findings.append(
            Finding(
                "MISSING_CHANGELOG",
                Severity.RECOMMENDATION,
                "Public readiness",
                "CHANGELOG.md is missing.",
                "Add a changelog so public users can understand project evolution.",
                "CHANGELOG.md",
            )
        )
    if not has_docs:
        findings.append(
            Finding(
                "MISSING_DOCS_OR_EXAMPLES",
                Severity.RECOMMENDATION,
                "Documentation",
                "No docs/ or examples/ directory was found.",
                "Add docs/ or examples/ to show how the project is used.",
                "docs/ or examples/",
            )
        )

    return [
        CategoryChecklist(
            "Identity",
            [
                ChecklistItem("README.md exists", readme.is_file(), "Public entry point."),
                ChecklistItem(
                    "README has quickstart", _readme_has_quickstart(readme), "Fast usage path."
                ),
            ],
        ),
        CategoryChecklist(
            "Public readiness",
            [
                ChecklistItem("LICENSE exists", license_file.is_file(), "Publication license."),
                ChecklistItem(
                    ".gitignore exists", (target / ".gitignore").is_file(), "Avoids noise."
                ),
                ChecklistItem(
                    "CHANGELOG.md exists", (target / "CHANGELOG.md").is_file(), "Tracks changes."
                ),
            ],
        ),
        CategoryChecklist(
            "Python project health",
            [
                ChecklistItem("pyproject.toml exists", pyproject.is_file(), "Python metadata."),
                ChecklistItem("pyproject.toml is valid", pyproject_valid, "Parseable TOML."),
                ChecklistItem(
                    "Python package structure exists", has_python_structure, "Importable code."
                ),
            ],
        ),
        CategoryChecklist(
            "CI/readiness",
            [
                ChecklistItem("tests/ exists", (target / "tests").is_dir(), "Test folder."),
                ChecklistItem("test files exist", has_tests, "Runnable tests."),
                ChecklistItem("GitHub Actions CI exists", has_ci, "Automated check."),
            ],
        ),
        CategoryChecklist(
            "Documentation",
            [
                ChecklistItem("docs/ or examples/ exists", has_docs, "Usage depth."),
                ChecklistItem(
                    "README has usage hints", _readme_has_usage(readme), "Practical instructions."
                ),
            ],
        ),
        CategoryChecklist(
            "Safety", [ChecklistItem("secret scan completed", True, "Local scan only.")]
        ),
    ]


def _is_valid_pyproject(path: Path, findings: list[Finding]) -> bool:
    if not path.exists():
        return False
    try:
        with path.open("rb") as handle:
            tomllib.load(handle)
    except tomllib.TOMLDecodeError:
        findings.append(
            Finding(
                "INVALID_PYPROJECT",
                Severity.BLOCKER,
                "Python project health",
                "pyproject.toml is not valid TOML.",
                "Fix pyproject.toml so Python tooling can parse it.",
                "pyproject.toml",
            )
        )
        return False
    return True


def _has_tests(target: Path) -> bool:
    tests_dir = target / "tests"
    return tests_dir.is_dir() and any(tests_dir.glob("test_*.py"))


def _has_python_structure(target: Path) -> bool:
    src = target / "src"
    if src.is_dir() and any(path.name == "__init__.py" for path in src.rglob("__init__.py")):
        return True
    for child in target.iterdir():
        if child.name in SKIP_DIRS or child.name == "tests":
            continue
        if child.is_dir() and (child / "__init__.py").is_file():
            return True
        if child.is_file() and child.suffix == ".py" and child.name not in {"setup.py"}:
            return True
    return False


def _readme_has_quickstart(path: Path) -> bool:
    text = _read_text(path).lower()
    return "quickstart" in text or "getting started" in text or "installation" in text


def _readme_has_usage(path: Path) -> bool:
    text = _read_text(path).lower()
    return "usage" in text or "quickstart" in text or "```" in text


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _scan_for_secrets(target: Path, findings: list[Finding]) -> None:
    for path in _iter_text_files(target):
        text = _read_text(path)
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            findings.append(
                Finding(
                    "POSSIBLE_SECRET",
                    Severity.BLOCKER,
                    "Safety",
                    "A possible secret was found. The value is intentionally hidden.",
                    "Remove the secret, rotate it if real, and keep secrets out of Git.",
                    str(path.relative_to(target)),
                )
            )


def _iter_text_files(target: Path):
    for path in target.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(target).parts):
            continue
        if not path.is_file() or path.stat().st_size > 512_000:
            continue
        if path.name == ".env" or path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def _run_test_command(target: Path, command: str, findings: list[Finding]) -> None:
    try:
        completed = subprocess.run(
            command,
            cwd=target,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            shell=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        findings.append(
            Finding(
                "TEST_COMMAND_FAILED",
                Severity.BLOCKER,
                "CI/readiness",
                f"Test command could not complete: {exc.__class__.__name__}.",
                "Fix the supplied test command or project test setup.",
                command,
            )
        )
        return
    if completed.returncode != 0:
        findings.append(
            Finding(
                "TEST_COMMAND_FAILED",
                Severity.BLOCKER,
                "CI/readiness",
                f"Test command exited with status {completed.returncode}.",
                "Fix failing tests before publishing.",
                command,
            )
        )


def _score(
    checklist: list[CategoryChecklist], blockers: list[Finding], warnings: list[Finding]
) -> int:
    score = 0.0
    for category in checklist:
        weight = CATEGORY_WEIGHTS[category.name]
        ratio = category.passed / category.total if category.total else 0
        score += weight * ratio
    score -= len(blockers) * 5
    score -= len(warnings) * 2
    return max(0, min(100, round(score)))


def _verdict(score: int, blockers: list[Finding]) -> str:
    if blockers:
        return "blocked"
    if score >= 90:
        return "showcase-ready"
    if score >= 85:
        return "public-ready"
    if score >= 80:
        return "publishable"
    if score >= 60:
        return "needs-work"
    return "not-ready"

