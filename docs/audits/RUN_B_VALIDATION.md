# Run B Validation

## Scope

Validated `public-repo-audit` against three real local Python repositories:

- `quality-docs-validator`
- `agent-desk`
- `agent-skill-quality-gate`

Reports are stored under `docs/audits/<repo>/report.md` and `docs/audits/<repo>/report.json`.

## Results

| Repository | Score | Verdict | Blockers | Warnings | Recommendations |
|---|---:|---|---:|---:|---:|
| quality-docs-validator | 100 | showcase-ready | 0 | 0 | 0 |
| agent-desk | 100 | showcase-ready | 0 | 0 | 0 |
| agent-skill-quality-gate | 93 | showcase-ready | 0 | 0 | 1 |

## Findings Review

### False Positives

None found in this run.

### Rules Too Rigid

None found. No repository was blocked incorrectly.

### Rules Too Easy

One issue was found: a missing `CHANGELOG.md` reduced the checklist score, but did not produce an actionable recommendation. This made the report less useful even though the score was deterministic.

### Recommendations Not Useful

Before adjustment, `agent-skill-quality-gate` had `Public readiness: 2/3` but zero recommendations. The missing changelog is now reported as `MISSING_CHANGELOG` with a concrete action.

### Versioned Report Privacy

Initial reports included local absolute target paths. Reports now display only the repository directory name, avoiding machine-specific or personal paths in versioned audit outputs.

## Rule Adjustments

- Added `MISSING_CHANGELOG` as a recommendation when `CHANGELOG.md` is absent.
- Changed report serialization/rendering to use the repository name instead of the absolute target path.
- Documented recommendation scoring and path sanitization in `docs/scoring.md`.

## Scope Check

No out-of-scope features were added:

- No GitHub API.
- No issue or PR analysis.
- No stars/forks analysis.
- No web dashboard.
- No multi-language expansion.
- No AI/LLM dependency.
- No AgentDesk integration.
