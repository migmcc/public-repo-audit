from __future__ import annotations

import argparse
from pathlib import Path

from public_repo_audit.audit import audit_repository
from public_repo_audit.reporting import write_json_report, write_markdown_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="public-repo-audit",
        description="Audit whether a local Python repository is ready to be public.",
    )
    parser.add_argument("path", help="Local repository path to audit.")
    parser.add_argument("--markdown", default="report.md", help="Markdown report path.")
    parser.add_argument("--json", default="report.json", help="JSON report path.")
    parser.add_argument(
        "--test-command", help="Optional test command to run inside the target path."
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = audit_repository(Path(args.path), test_command=args.test_command)
    write_markdown_report(report, args.markdown)
    write_json_report(report, args.json)
    print(f"Score: {report.score}/100")
    print(f"Verdict: {report.verdict}")
    print(f"Blockers: {len(report.blockers)}")
    print(f"Warnings: {len(report.warnings)}")
    print(f"Recommendations: {len(report.recommendations)}")
    return 1 if report.blockers else 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
