from __future__ import annotations

import json
from pathlib import Path

from public_repo_audit.models import AuditReport, Finding


def write_json_report(report: AuditReport, path: str | Path) -> None:
    destination = Path(path)
    destination.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def write_markdown_report(report: AuditReport, path: str | Path) -> None:
    destination = Path(path)
    destination.write_text(_render_markdown(report), encoding="utf-8")


def _render_markdown(report: AuditReport) -> str:
    lines = [
        "# Public Repo Audit Report",
        "",
        "## Summary",
        f"Target: `{report.target}`",
        f"Score: {report.score}/100",
        f"Verdict: {report.verdict}",
        "",
        "## Blockers",
    ]
    lines.extend(_finding_lines(report.blockers, "No blockers found."))
    lines.extend(["", "## Warnings"])
    lines.extend(_finding_lines(report.warnings, "No warnings found."))
    lines.extend(["", "## Recommendations"])
    lines.extend(_finding_lines(report.recommendations, "No recommendations found."))
    lines.extend(["", "## Checklist"])
    for category in report.checklist:
        lines.append(f"### {category.name} ({category.passed}/{category.total})")
        for item in category.items:
            mark = "x" if item.passed else " "
            lines.append(f"- [{mark}] {item.label} - {item.detail}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _finding_lines(findings: list[Finding], empty: str) -> list[str]:
    if not findings:
        return [f"- {empty}"]
    return [
        f"- **{finding.code}** ({finding.category}) {finding.message} "
        f"Recommendation: {finding.recommendation}"
        + (f" Location: `{finding.location}`" if finding.location else "")
        for finding in findings
    ]
