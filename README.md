# public-repo-audit

Audit whether a local Python repository is ready to be public on GitHub.

`public-repo-audit` is a deterministic, local-only CLI. It checks public readiness signals such as README, license, Python packaging metadata, tests, CI, documentation, examples and basic safety hygiene.

## Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
public-repo-audit .
```

Without installing the package, run it directly from a checkout:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m public_repo_audit.cli .
```

By default the command writes:

- `report.md`
- `report.json`

It also prints the final score and verdict in the terminal.

Example output:

```text
Score: 100/100
Verdict: showcase-ready
Blockers: 0
Warnings: 0
Recommendations: 0
```

## Usage

```powershell
public-repo-audit <path>
```

Custom output paths:

```powershell
public-repo-audit . --markdown reports/audit.md --json reports/audit.json
```

Run a local test command as part of the audit:

```powershell
public-repo-audit . --test-command "pytest"
```

If the supplied test command fails, the audit records a critical blocker.

## Verdicts

- `80+`: publishable
- `85+`: public-ready
- `90+`: showcase-ready
- Any critical blocker forces `blocked`, even with a high score.

## Categories

The MVP v0.1 checks these categories:

1. Identity
2. Public readiness
3. Python project health
4. CI/readiness
5. Documentation
6. Safety

## Critical Blockers

- Possible secret found.
- `README.md` absent.
- `LICENSE` absent.
- `pyproject.toml` invalid.
- Tests fail when a test command is supplied.
- Clearly invalid Python structure when applicable.

## Out Of Scope For v0.1

- GitHub API.
- Issue or PR analysis.
- Stars and forks.
- Web dashboard.
- Complete multi-language support.
- AI/LLM analysis.
- AgentDesk integration.

## Scoring

The score is deterministic and based on a fixed checklist. Category weights are documented in [`docs/scoring.md`](docs/scoring.md).

Recommendations are actionable guidance and do not subtract points by themselves. Critical blockers always force the final verdict to `blocked`.

## Release Status

Version `0.1.0` is prepared for public release review. No release tag has been created yet.

## Development

```powershell
.\.venv\Scripts\python -m pip install pytest ruff
ruff check .
pytest
```

The runtime implementation uses only the Python standard library.


