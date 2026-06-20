# Public Repo Audit MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved Python-first v0.1 local CLI for public repository readiness audits.

**Architecture:** A small stdlib-only runtime package scans a local repository, produces typed report objects, computes deterministic scoring, and writes Markdown/JSON outputs. The CLI is a thin argparse wrapper over the audit and reporting modules.

**Tech Stack:** Python 3.11+, argparse, dataclasses, tomllib, json, subprocess, pytest, ruff.

## Global Constraints

- Command: `public-repo-audit <path>`.
- Runtime must make no network calls.
- No LLM/IA dependency.
- No GitHub API, issue/PR, stars/forks, dashboard, multi-language or AgentDesk implementation.
- Outputs: `report.md`, `report.json`, score, verdict, blockers, warnings, recommendations, checklist by category.
- Critical blockers: possible secret, missing README.md, missing LICENSE, invalid pyproject.toml, failing supplied test command, clearly invalid Python structure.

---

### Task 1: Core Audit Behavior

**Files:**
- Create: `src/public_repo_audit/models.py`
- Create: `src/public_repo_audit/audit.py`
- Test: `tests/test_audit.py`

**Interfaces:**
- Produces: `audit_repository(path: Path, test_command: str | None = None) -> AuditReport`.
- Produces: `AuditReport` with `score`, `verdict`, `blockers`, `warnings`, `recommendations`, `checklist`.

- [x] Write failing tests for complete repo, blockers and secret masking.
- [ ] Implement minimal models and scanner.
- [ ] Run `pytest tests/test_audit.py` until green.

### Task 2: Reports And CLI

**Files:**
- Create: `src/public_repo_audit/reporting.py`
- Create: `src/public_repo_audit/cli.py`
- Test: `tests/test_audit.py`

**Interfaces:**
- Produces: `write_markdown_report(report: AuditReport, path: Path) -> None`.
- Produces: `write_json_report(report: AuditReport, path: Path) -> None`.

- [x] Write failing tests for Markdown and JSON reports.
- [ ] Implement report writers.
- [ ] Implement CLI.
- [ ] Run `pytest` until green.

### Task 3: Documentation And Verification

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `CHANGELOG.md`
- Create: `.github/workflows/ci.yml`

- [ ] Write README quickstart.
- [ ] Generate self-audit `report.md` and `report.json`.
- [ ] Run `ruff check .`.
- [ ] Run `pytest`.
- [ ] Commit `feat: implement public repo audit MVP`.
