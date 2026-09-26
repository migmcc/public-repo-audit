# Repository profiles

The audit reports which kind of repository it believes it is looking at. The
profile is informational: it appears in both reports and in the terminal
output, and it does not change scoring or which checks run. Python-first
behaviour is unchanged.

Detection reads the file tree only. It never runs the project, never installs
anything, and never contacts the network or the GitHub API, so the same tree
always produces the same profile.

## Profiles

| Profile | Meaning |
|---|---|
| `python-package` | An importable package plus packaging metadata in `pyproject.toml` |
| `python-app` | Python code without packaging metadata, or without a package layout |
| `python-docs` | Markdown dominates a tree that contains Python |
| `node-project` | A `package.json` is present |
| `unknown` | None of the above |

## Order of evaluation

Rules are evaluated in a fixed order and the first match wins:

1. `python-docs`
2. `python-package`
3. `python-app`
4. `node-project`
5. `unknown`

The order is part of the contract. A repository that satisfies more than one
rule is reported as the first one it satisfies, so the result never depends on
filesystem iteration order.

Node is evaluated after every Python rule on purpose. Plenty of Python projects
carry a `package.json` for documentation tooling or a small front end, and
Python-first behaviour means those are still audited as Python projects.

## Node projects

The `node-project` profile replaces the **Python project health** category with
**Node project health**, carrying the same weight. A Node repository is never
asked for `pyproject.toml` or a Python package layout.

| Check | Detail |
|---|---|
| `package.json` exists | Presence of the manifest |
| `package.json` is valid | Parses as a JSON object |
| JavaScript/TypeScript source exists | The `main` entry point, or any `.js`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.jsx` file outside skip directories |
| Dependency lockfile exists | `package-lock.json`, `npm-shrinkwrap.json`, `yarn.lock` or `pnpm-lock.yaml` |
| Test script declared | A `scripts.test` entry that is not npm's placeholder |
| Test files exist | A `tests/`, `test/` or `__tests__/` directory, or any `*.test.*` / `*.spec.*` file |

The test-script check rejects the placeholder that `npm init` writes:

```json
{ "scripts": { "test": "echo \"Error: no test specified\" && exit 1" } }
```

That line exits non-zero and runs nothing, so treating it as a declared test
script would credit a repository for a suite it does not have.

A `package.json` that does not parse still selects the Node profile and is
reported as a blocker. Falling through to `unknown` would let the repository
that most needs the checks escape them.

Nothing is installed and no package manager is invoked. Detection and checks
read the file tree only.

## Thresholds

A repository is documentation-heavy when it contains **at least one** Python
file, **at least 5** Markdown files, and **at least 3 times** as many Markdown
files as Python files.

The Python requirement is what keeps the profile honest about its own name: a
repository of pure prose with no Python in it is not a documentation-heavy
Python project, and is reported as `unknown`.

The other two conditions exist for a reason. The floor stops a three-file repository
from qualifying by accident. The ratio stops an ordinary, well-documented
package from being reclassified as a documentation project just because it
takes its docs seriously — a package with 10 Python files would need 30
Markdown files to trip the rule.

Directories that are not part of the source tree are excluded from both counts:
`.git`, `.venv`, `venv`, `env`, `__pycache__`, `.pytest_cache`, `.ruff_cache`,
`dist`, `build`, `node_modules` and the other version-control directories.
Without that, a vendored dependency tree could decide the profile.

## Packaging metadata

`pyproject.toml` counts as packaging metadata when it parses and declares a
`[project]` or `[build-system]` table. A `pyproject.toml` that does not parse
provides no metadata for profiling purposes; the audit already reports it as a
blocker in its own right, so detection stays silent rather than reporting the
same problem twice.

## Reports

Both outputs carry the profile and the evidence that selected it:

```json
{
  "profile": "python-package",
  "profile_reason": "Importable package with packaging metadata in pyproject.toml."
}
```

```markdown
Profile: python-package (Importable package with packaging metadata in pyproject.toml.)
```

The reason is included so a surprising profile can be argued with instead of
merely disbelieved.
