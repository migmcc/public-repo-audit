# Scoring

The v0.1 score is deterministic and category-based.

## Weights

- Identity: 15
- Public readiness: 20
- Python project health: 25
- CI/readiness: 15
- Documentation: 15
- Safety: 10

Each category contributes according to checklist completion. Blockers subtract 5 points each and warnings subtract 2 points each, but blockers always force the final verdict to `blocked`.

## Verdicts

- 90-100: showcase-ready
- 85-89: public-ready
- 80-84: publishable
- 60-79: needs-work
- 0-59: not-ready
- Any blocker: blocked
