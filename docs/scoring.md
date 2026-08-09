# Scoring

The v0.1 score is deterministic and category-based.

## Weights

- Identity: 15
- Public readiness: 20
- Python project health: 25
- Node project health: 25
- CI/readiness: 15
- Documentation: 15
- Safety: 10

A repository carries either the Python or the Node health category, never both,
so the weights in play always total 100. Both are listed because both are
configurable.

Each category contributes according to checklist completion.

### Overriding the weights

Weights can be overridden with a TOML file passed explicitly with `--config`:

```toml
[weights]
"Documentation" = 25
"Safety" = 20
```

Categories left out of the table keep their default weight, so the example above
changes two categories and nothing else. Category names must match the list
above exactly.

Weights express **relative** emphasis and are normalised to the 100-point scale
before scoring, so a table totalling 200 scores identically to the same
proportions totalling 100. Without that normalisation, weights summing above 100
would silently saturate every healthy repository at the maximum score.

Scoring is unchanged when no `--config` is supplied.

The config file is never discovered automatically inside the repository being
audited. This tool is meant to be pointed at repositories the operator may not
control, and a repository that could ship its own weights could raise its own
score. The path always comes from the command line.

These errors are reported with a message and exit code `2`, never a traceback:
a missing file, invalid TOML, a missing `[weights]` table, an unknown category
name, a non-numeric or boolean value, a negative value, or every weight set to
zero. Blockers subtract 5 points each and warnings subtract 2 points each; recommendations are actionable guidance and do not subtract points by themselves. Blockers always force the final verdict to `blocked`. Reports display the audited repository name instead of the local absolute path so versioned reports do not leak machine-specific paths.

## Verdicts

- 90-100: showcase-ready
- 85-89: public-ready
- 80-84: publishable
- 60-79: needs-work
- 0-59: not-ready
- Any blocker: blocked

