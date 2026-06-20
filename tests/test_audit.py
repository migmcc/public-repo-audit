from __future__ import annotations

import json
from pathlib import Path

from public_repo_audit.audit import audit_repository
from public_repo_audit.models import Severity
from public_repo_audit.reporting import write_json_report, write_markdown_report


def write(path: Path, text: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_python_repo(root: Path) -> None:
    write(root / "README.md", "# Demo\n\n## Quickstart\n\n```bash\npython -m demo\n```\n")
    write(root / "LICENSE", "MIT License")
    write(root / ".gitignore", "__pycache__/\n")
    write(root / "pyproject.toml", '[project]\nname = "demo"\nversion = "0.1.0"\n')
    write(root / "CHANGELOG.md", "# Changelog\n")
    write(root / ".github" / "workflows" / "ci.yml", "name: CI\n")
    write(root / "tests" / "test_demo.py", "def test_demo():\n    assert True\n")
    write(root / "docs" / "index.md", "# Docs\n")
    write(root / "src" / "demo" / "__init__.py", "")


def test_complete_python_repo_is_public_ready(tmp_path: Path) -> None:
    make_python_repo(tmp_path)

    report = audit_repository(tmp_path)

    assert report.score >= 85
    assert report.verdict == "showcase-ready"
    assert report.blockers == []
    assert {category.name for category in report.checklist} == {
        "Identity",
        "Public readiness",
        "Python project health",
        "CI/readiness",
        "Documentation",
        "Safety",
    }


def test_missing_readme_license_and_invalid_pyproject_are_blockers(tmp_path: Path) -> None:
    write(tmp_path / "pyproject.toml", "[project\ninvalid")
    write(tmp_path / "src" / "demo" / "__init__.py", "")

    report = audit_repository(tmp_path)

    codes = {finding.code for finding in report.blockers}
    assert {"MISSING_README", "MISSING_LICENSE", "INVALID_PYPROJECT"} <= codes
    assert report.verdict == "blocked"
    assert all(finding.severity is Severity.BLOCKER for finding in report.blockers)


def test_possible_secret_is_reported_without_exposing_value(tmp_path: Path) -> None:
    make_python_repo(tmp_path)
    key_name = "API" + "_KEY"
    fake_value = "sk" + "_test_" + "1234567890abcdef"
    write(tmp_path / ".env", f"{key_name}={fake_value}\n")

    report = audit_repository(tmp_path)

    [finding] = [item for item in report.blockers if item.code == "POSSIBLE_SECRET"]
    assert ".env" in finding.location
    assert fake_value not in finding.message
    assert report.verdict == "blocked"


def test_reports_write_markdown_and_json(tmp_path: Path) -> None:
    make_python_repo(tmp_path)
    report = audit_repository(tmp_path)

    markdown_path = tmp_path / "report.md"
    json_path = tmp_path / "report.json"
    write_markdown_report(report, markdown_path)
    write_json_report(report, json_path)

    markdown = markdown_path.read_text(encoding="utf-8")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "# Public Repo Audit Report" in markdown
    assert "## Checklist" in markdown
    assert data["score"] == report.score
    assert data["verdict"] == report.verdict
    assert "blockers" in data
    assert "warnings" in data
    assert "recommendations" in data


def test_failed_supplied_test_command_is_blocker(tmp_path: Path) -> None:
    make_python_repo(tmp_path)

    report = audit_repository(tmp_path, test_command='python -c "raise SystemExit(2)"')

    codes = {finding.code for finding in report.blockers}
    assert "TEST_COMMAND_FAILED" in codes
    assert report.verdict == "blocked"


def test_cli_generates_default_reports(tmp_path: Path, capsys, monkeypatch) -> None:
    from public_repo_audit.cli import run

    target = tmp_path / "target"
    output_dir = tmp_path / "output"
    make_python_repo(target)
    output_dir.mkdir()
    monkeypatch.chdir(output_dir)
    exit_code = run([str(target)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Score:" in captured.out
    assert (Path.cwd() / "report.md").exists()
    assert (Path.cwd() / "report.json").exists()



def test_missing_changelog_is_actionable_recommendation(tmp_path: Path) -> None:
    make_python_repo(tmp_path)
    (tmp_path / "CHANGELOG.md").unlink()

    report = audit_repository(tmp_path)

    assert "MISSING_CHANGELOG" in {finding.code for finding in report.recommendations}


def test_reports_do_not_include_absolute_target_path(tmp_path: Path) -> None:
    make_python_repo(tmp_path)
    report = audit_repository(tmp_path)

    markdown_path = tmp_path / "report.md"
    json_path = tmp_path / "report.json"
    write_markdown_report(report, markdown_path)
    write_json_report(report, json_path)

    markdown = markdown_path.read_text(encoding="utf-8")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert str(tmp_path) not in markdown
    assert data["target"] == tmp_path.name


