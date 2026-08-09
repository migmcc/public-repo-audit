from __future__ import annotations

import json

from public_repo_audit.audit import audit_repository
from public_repo_audit.profiles import (
    PYTHON_APP,
    PYTHON_DOCS,
    PYTHON_PACKAGE,
    UNKNOWN,
    detect_profile,
)
from public_repo_audit.reporting import write_json_report, write_markdown_report


def make_repo(tmp_path, name: str):
    repo = tmp_path / name
    repo.mkdir()
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    return repo


def package_fixture(tmp_path):
    """src layout, __init__.py, packaging metadata."""
    repo = make_repo(tmp_path, "package-repo")
    (repo / "src" / "demo").mkdir(parents=True)
    (repo / "src" / "demo" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "src" / "demo" / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    return repo


def app_fixture(tmp_path):
    """Python scripts, no package layout, no packaging metadata."""
    repo = make_repo(tmp_path, "app-repo")
    (repo / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (repo / "helpers.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    return repo


def docs_fixture(tmp_path):
    """Markdown dominates the tree."""
    repo = make_repo(tmp_path, "docs-repo")
    (repo / "docs").mkdir()
    for index in range(8):
        (repo / "docs" / f"page-{index}.md").write_text(f"# page {index}\n", encoding="utf-8")
    (repo / "build.py").write_text("print('build docs')\n", encoding="utf-8")
    return repo


def empty_fixture(tmp_path):
    repo = tmp_path / "empty-repo"
    repo.mkdir()
    (repo / "notes.txt").write_text("nothing here\n", encoding="utf-8")
    return repo


def test_python_package_is_detected(tmp_path):
    profile = detect_profile(package_fixture(tmp_path))

    assert profile.name == PYTHON_PACKAGE
    assert "packaging metadata" in profile.reason


def test_python_app_is_detected(tmp_path):
    profile = detect_profile(app_fixture(tmp_path))

    assert profile.name == PYTHON_APP


def test_documentation_heavy_project_is_detected(tmp_path):
    profile = detect_profile(docs_fixture(tmp_path))

    assert profile.name == PYTHON_DOCS
    assert "Markdown" in profile.reason


def test_repository_without_python_is_unknown(tmp_path):
    assert detect_profile(empty_fixture(tmp_path)).name == UNKNOWN


def test_package_without_packaging_metadata_is_an_app(tmp_path):
    repo = package_fixture(tmp_path)
    (repo / "pyproject.toml").unlink()

    assert detect_profile(repo).name == PYTHON_APP


def test_unparseable_pyproject_does_not_crash_detection(tmp_path):
    repo = package_fixture(tmp_path)
    (repo / "pyproject.toml").write_text("[project\n", encoding="utf-8")

    assert detect_profile(repo).name == PYTHON_APP


def test_well_documented_package_is_still_a_package(tmp_path):
    """The docs rule needs Markdown to dominate, not merely to be present."""
    repo = package_fixture(tmp_path)
    (repo / "docs").mkdir()
    for index in range(4):
        (repo / "docs" / f"guide-{index}.md").write_text("# guide\n", encoding="utf-8")

    assert detect_profile(repo).name == PYTHON_PACKAGE


def test_detection_ignores_skipped_directories(tmp_path):
    repo = package_fixture(tmp_path)
    noise = repo / "node_modules" / "pkg"
    noise.mkdir(parents=True)
    for index in range(30):
        (noise / f"doc-{index}.md").write_text("# vendored\n", encoding="utf-8")

    assert detect_profile(repo).name == PYTHON_PACKAGE


def test_detection_is_deterministic(tmp_path):
    repo = package_fixture(tmp_path)

    assert detect_profile(repo) == detect_profile(repo)


def test_profile_appears_in_the_json_report(tmp_path):
    repo = package_fixture(tmp_path)
    destination = tmp_path / "report.json"

    write_json_report(audit_repository(repo), destination)
    data = json.loads(destination.read_text(encoding="utf-8"))

    assert data["profile"] == PYTHON_PACKAGE
    assert data["profile_reason"]


def test_profile_appears_in_the_markdown_report(tmp_path):
    repo = package_fixture(tmp_path)
    destination = tmp_path / "report.md"

    write_markdown_report(audit_repository(repo), destination)

    assert f"Profile: {PYTHON_PACKAGE}" in destination.read_text(encoding="utf-8")


def test_profile_does_not_change_scoring(tmp_path):
    """Detection is informational in this change; Python-first behaviour stands."""
    package = audit_repository(package_fixture(tmp_path))
    app = audit_repository(app_fixture(tmp_path))

    assert package.profile != app.profile
    assert package.checklist[2].name == "Python project health"
    assert app.checklist[2].name == "Python project health"
