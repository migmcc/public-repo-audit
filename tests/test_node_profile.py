from __future__ import annotations

import json

from public_repo_audit.audit import CATEGORY_WEIGHTS, audit_repository
from public_repo_audit.config import DEFAULT_CATEGORY_WEIGHTS, load_weights
from public_repo_audit.profiles import NODE_PROJECT, PYTHON_PACKAGE, detect_profile
from public_repo_audit.reporting import write_json_report, write_markdown_report


def python_repo(tmp_path):
    repo = tmp_path / "python-repo"
    (repo / "src" / "demo").mkdir(parents=True)
    (repo / "src" / "demo" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    return repo


def codes(report):
    return {finding.code for finding in report.blockers + report.warnings + report.recommendations}


def category(report, name):
    return next(item for item in report.checklist if item.name == name)


def healthy_node_repo(tmp_path):
    repo = tmp_path / "healthy-node"
    (repo / "src").mkdir(parents=True)
    (repo / "test").mkdir()
    (repo / "docs").mkdir()
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / "src" / "index.js").write_text("export const value = 1;\n", encoding="utf-8")
    (repo / "test" / "index.test.js").write_text("// test\n", encoding="utf-8")
    (repo / "docs" / "usage.md").write_text("# usage\n", encoding="utf-8")
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (repo / "package.json").write_text(
        json.dumps(
            {
                "name": "demo",
                "version": "1.0.0",
                "main": "src/index.js",
                "scripts": {"test": "vitest run"},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (repo / "package-lock.json").write_text('{"lockfileVersion": 3}\n', encoding="utf-8")
    (repo / "README.md").write_text(
        "# demo\n\n## Quickstart\n\n## Usage\n\n```\nnpm test\n```\n", encoding="utf-8"
    )
    (repo / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (repo / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    return repo


def weak_node_repo(tmp_path):
    """No lockfile, npm's placeholder test script, no CI, no docs, no license."""
    repo = tmp_path / "weak-node"
    repo.mkdir(parents=True)
    (repo / "index.js").write_text("console.log('hi');\n", encoding="utf-8")
    (repo / "package.json").write_text(
        json.dumps(
            {
                "name": "weak",
                "version": "0.0.1",
                "scripts": {"test": 'echo "Error: no test specified" && exit 1'},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (repo / "README.md").write_text("# weak\n", encoding="utf-8")
    return repo


def test_node_repository_is_detected(tmp_path):
    assert detect_profile(healthy_node_repo(tmp_path)).name == NODE_PROJECT


def test_healthy_node_repository_has_no_blockers(tmp_path):
    report = audit_repository(healthy_node_repo(tmp_path))

    assert report.profile == NODE_PROJECT
    assert report.blockers == []
    assert report.verdict != "blocked"
    assert report.score >= 90


def test_weak_node_repository_reports_each_gap(tmp_path):
    report = audit_repository(weak_node_repo(tmp_path))

    found = codes(report)
    assert "MISSING_LOCKFILE" in found
    assert "MISSING_TEST_SCRIPT" in found
    assert "MISSING_LICENSE" in found
    assert "MISSING_CI" in found
    assert "MISSING_DOCS_OR_EXAMPLES" in found
    assert report.score < 90


def test_npm_placeholder_test_script_does_not_count(tmp_path):
    repo = weak_node_repo(tmp_path)

    report = audit_repository(repo)

    assert "MISSING_TEST_SCRIPT" in codes(report)


def test_real_test_script_counts(tmp_path):
    repo = weak_node_repo(tmp_path)
    (repo / "package.json").write_text(
        json.dumps({"name": "weak", "scripts": {"test": "jest"}}, indent=2), encoding="utf-8"
    )

    assert "MISSING_TEST_SCRIPT" not in codes(audit_repository(repo))


def test_malformed_package_json_is_a_blocker_not_an_escape(tmp_path):
    repo = weak_node_repo(tmp_path)
    (repo / "package.json").write_text("{ not json\n", encoding="utf-8")

    report = audit_repository(repo)

    assert report.profile == NODE_PROJECT
    assert "INVALID_PACKAGE_JSON" in codes(report)
    assert report.verdict == "blocked"


def test_node_repository_is_not_asked_for_python_structure(tmp_path):
    report = audit_repository(healthy_node_repo(tmp_path))

    found = codes(report)
    assert "MISSING_PYPROJECT" not in found
    assert "INVALID_PYTHON_STRUCTURE" not in found
    assert category(report, "Node project health")


def test_any_supported_lockfile_satisfies_the_check(tmp_path):
    for name in ("yarn.lock", "pnpm-lock.yaml", "npm-shrinkwrap.json"):
        repo = healthy_node_repo(tmp_path / name)
        (repo / "package-lock.json").unlink()
        (repo / name).write_text("lock\n", encoding="utf-8")

        assert "MISSING_LOCKFILE" not in codes(audit_repository(repo)), name


def test_python_project_with_a_package_json_stays_python(tmp_path):
    """Python-first: tooling manifests must not reclassify a Python project."""
    repo = tmp_path / "py-with-node-tooling"
    (repo / "src" / "demo").mkdir(parents=True)
    (repo / "src" / "demo" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    (repo / "package.json").write_text('{"name": "docs-tooling"}\n', encoding="utf-8")
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")

    report = audit_repository(repo)

    assert report.profile == PYTHON_PACKAGE
    assert category(report, "Python project health")


def test_profile_is_stated_in_both_reports(tmp_path):
    repo = healthy_node_repo(tmp_path)
    report = audit_repository(repo)
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"

    write_json_report(report, json_path)
    write_markdown_report(report, markdown_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["profile"] == NODE_PROJECT
    assert f"Profile: {NODE_PROJECT}" in markdown_path.read_text(encoding="utf-8")


def test_every_emitted_category_has_a_weight(tmp_path):
    """The guard for the defect this stack introduced.

    Scoring looks each category up in DEFAULT_CATEGORY_WEIGHTS. A profile that
    emits a category missing from that table raises KeyError on every audit of
    that repository kind. This fails for any future profile with the same gap,
    not just for Node.
    """
    reports = [
        audit_repository(healthy_node_repo(tmp_path / "node")),
        audit_repository(weak_node_repo(tmp_path / "weak")),
        audit_repository(python_repo(tmp_path / "python")),
    ]

    emitted = {item.name for report in reports for item in report.checklist}

    assert emitted, "no categories were emitted"
    assert emitted <= set(DEFAULT_CATEGORY_WEIGHTS), (
        f"categories with no weight: {sorted(emitted - set(DEFAULT_CATEGORY_WEIGHTS))}"
    )


def test_the_weights_table_has_a_single_source_of_truth():
    """A second copy in audit.py is how the categories drifted apart."""
    assert CATEGORY_WEIGHTS is DEFAULT_CATEGORY_WEIGHTS


def test_the_node_category_weight_is_configurable(tmp_path):
    repo = healthy_node_repo(tmp_path)
    config = tmp_path / "audit.toml"
    config.write_text('[weights]\n"Node project health" = 40\n', encoding="utf-8")

    weights = load_weights(config)

    assert weights["Node project health"] == 40
    assert audit_repository(repo, weights=weights).score > 0


def test_node_modules_is_not_treated_as_project_source(tmp_path):
    repo = weak_node_repo(tmp_path)
    (repo / "index.js").unlink()
    vendored = repo / "node_modules" / "left-pad"
    vendored.mkdir(parents=True)
    (vendored / "index.js").write_text("module.exports = 1;\n", encoding="utf-8")

    assert "MISSING_NODE_SOURCE" in codes(audit_repository(repo))
