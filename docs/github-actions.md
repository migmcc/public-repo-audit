# GitHub Actions Readiness

`public-repo-audit` is local-first and does not need network access to scan a checked-out repository. In CI, use it after the normal Python quality gates so the generated reports describe the same state that was tested.

## Recommended Python Readiness Job

For a Python repository, run these checks in order:

```bash
ruff check .
pytest
public-repo-audit . --format both
```

This keeps lint, tests and public-readiness reporting separate. `ruff` and `pytest` decide whether the code is healthy; `public-repo-audit` writes `report.md` and `report.json` with the readiness score, verdict, blockers, warnings and recommendations.

## Output Format In CI

Use the default `--format both` when you want both a human-readable Markdown report and a machine-readable JSON report:

```bash
public-repo-audit . --format both
```

Use JSON-only mode when CI or later automation only needs structured data:

```bash
public-repo-audit . --format json
```

Use Markdown-only mode when you only want a report artifact for humans:

```bash
public-repo-audit . --format markdown
```

The scanner does not call the GitHub API, inspect issues or PRs, or require an LLM. It only reads the local checkout.

## Minimal Workflow

A copy-pasteable workflow is available at [`docs/examples/github-actions-public-repo-audit.yml`](examples/github-actions-public-repo-audit.yml).

The example installs the project under audit in editable mode, installs `public-repo-audit` from GitHub, runs `ruff`, runs `pytest`, runs the audit, and uploads `report.md` and `report.json` as artifacts.

## CI Badge

For this repository, the README badge points at `.github/workflows/ci.yml`:

```markdown
[![CI](https://github.com/migmcc/public-repo-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/migmcc/public-repo-audit/actions/workflows/ci.yml)
```

For another repository, replace `migmcc/public-repo-audit` and `ci.yml` with that repository and workflow file name.

