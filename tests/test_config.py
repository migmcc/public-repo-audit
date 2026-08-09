from __future__ import annotations

import pytest

from public_repo_audit.audit import audit_repository
from public_repo_audit.cli import run
from public_repo_audit.config import DEFAULT_CATEGORY_WEIGHTS, ConfigError, load_weights


def write_config(tmp_path, body: str):
    path = tmp_path / "audit.toml"
    path.write_text(body, encoding="utf-8")
    return path


def healthy_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "tests" / "test_smoke.py").write_text("def test_ok():\n    pass\n", encoding="utf-8")
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (repo / "README.md").write_text(
        "# demo\n\n## Quickstart\n\n## Usage\n\n```\ndemo\n```\n", encoding="utf-8"
    )
    (repo / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (repo / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    return repo


def weak_docs_repo(tmp_path):
    """Healthy except for the Documentation category."""
    repo = healthy_repo(tmp_path)
    (repo / "docs").rmdir()
    (repo / "README.md").write_text("# demo\n\n## Quickstart\n", encoding="utf-8")
    return repo


def test_defaults_are_used_when_no_config_is_supplied(tmp_path):
    repo = healthy_repo(tmp_path)

    assert audit_repository(repo).score == audit_repository(repo, weights=None).score


def test_explicit_default_weights_match_unconfigured_score(tmp_path):
    repo = weak_docs_repo(tmp_path)

    baseline = audit_repository(repo).score
    explicit = audit_repository(repo, weights=dict(DEFAULT_CATEGORY_WEIGHTS)).score

    assert baseline == explicit


def test_raising_a_weight_lowers_the_score_for_that_weak_category(tmp_path):
    repo = weak_docs_repo(tmp_path)

    baseline = audit_repository(repo).score
    stricter = audit_repository(repo, weights={**DEFAULT_CATEGORY_WEIGHTS, "Documentation": 40})

    assert stricter.score < baseline


def test_zeroing_a_weight_removes_its_penalty(tmp_path):
    repo = weak_docs_repo(tmp_path)

    baseline = audit_repository(repo).score
    softer = audit_repository(repo, weights={**DEFAULT_CATEGORY_WEIGHTS, "Documentation": 0})

    assert softer.score > baseline


def test_weights_are_normalised_so_large_totals_do_not_saturate(tmp_path):
    repo = weak_docs_repo(tmp_path)

    baseline = audit_repository(repo).score
    scaled = audit_repository(
        repo, weights={name: value * 10 for name, value in DEFAULT_CATEGORY_WEIGHTS.items()}
    )

    assert scaled.score == baseline


def test_partial_config_keeps_defaults_for_unlisted_categories(tmp_path):
    config = write_config(tmp_path, '[weights]\n"Safety" = 30\n')

    weights = load_weights(config)

    assert weights["Safety"] == 30
    assert weights["Identity"] == DEFAULT_CATEGORY_WEIGHTS["Identity"]


def test_missing_config_file_is_reported(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_weights(tmp_path / "absent.toml")


def test_invalid_toml_is_reported(tmp_path):
    config = write_config(tmp_path, "[weights\n")

    with pytest.raises(ConfigError, match="not valid TOML"):
        load_weights(config)


def test_missing_weights_table_is_reported(tmp_path):
    config = write_config(tmp_path, '[other]\nkey = "value"\n')

    with pytest.raises(ConfigError, match=r"no \[weights\] table"):
        load_weights(config)


def test_unknown_category_is_reported_with_the_known_names(tmp_path):
    config = write_config(tmp_path, '[weights]\n"Vibes" = 10\n')

    with pytest.raises(ConfigError, match="Unknown category 'Vibes'") as excinfo:
        load_weights(config)
    assert "Identity" in str(excinfo.value)


def test_non_numeric_weight_is_reported(tmp_path):
    config = write_config(tmp_path, '[weights]\n"Safety" = "high"\n')

    with pytest.raises(ConfigError, match="must be a number"):
        load_weights(config)


def test_boolean_weight_is_rejected_rather_than_treated_as_one(tmp_path):
    config = write_config(tmp_path, '[weights]\n"Safety" = true\n')

    with pytest.raises(ConfigError, match="must be a number"):
        load_weights(config)


def test_negative_weight_is_reported(tmp_path):
    config = write_config(tmp_path, '[weights]\n"Safety" = -1\n')

    with pytest.raises(ConfigError, match="must not be negative"):
        load_weights(config)


def test_all_zero_weights_are_reported(tmp_path):
    body = "[weights]\n" + "".join(
        f'"{name}" = 0\n' for name in DEFAULT_CATEGORY_WEIGHTS
    )
    config = write_config(tmp_path, body)

    with pytest.raises(ConfigError, match="greater than zero"):
        load_weights(config)


def test_cli_reports_config_errors_without_a_traceback(tmp_path, capsys):
    repo = healthy_repo(tmp_path)
    config = write_config(tmp_path, '[weights]\n"Vibes" = 10\n')

    exit_code = run(
        [
            str(repo),
            "--config",
            str(config),
            "--format",
            "json",
            "--json",
            str(tmp_path / "report.json"),
        ]
    )

    assert exit_code == 2
    assert "Configuration error" in capsys.readouterr().out
    assert not (tmp_path / "report.json").exists()
