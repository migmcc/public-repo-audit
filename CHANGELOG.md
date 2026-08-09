# Changelog

## Unreleased

- Add GitHub Actions readiness guidance and a copy-pasteable workflow example.
- Add CLI `--format` option to write Markdown, JSON, or both report outputs.
- Detect and report a repository profile (`python-package`, `python-app`,
  `python-docs`, `unknown`). Detection is deterministic and local-only, appears
  in both reports and in the terminal output, and does not change scoring.
- Add CLI `--config` option to override category scoring weights from a TOML
  file. Scoring is unchanged without it, weights are normalised to the
  100-point scale, and the file is never auto-discovered inside the audited
  repository.

## 0.1.0 - 2026-06-20

- Initial Python-first MVP.
- Local CLI audit command.
- Deterministic scoring and verdicts.
- Markdown and JSON report output.
- Critical blockers, warnings and recommendations.
- Public release metadata prepared.
- CI configured for Python 3.12 and 3.13.
