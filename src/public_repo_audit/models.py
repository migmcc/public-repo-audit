from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(Enum):
    BLOCKER = "blocker"
    WARNING = "warning"
    RECOMMENDATION = "recommendation"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    category: str
    message: str
    recommendation: str
    location: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


@dataclass(frozen=True)
class ChecklistItem:
    label: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CategoryChecklist:
    name: str
    items: list[ChecklistItem]

    @property
    def passed(self) -> int:
        return sum(1 for item in self.items if item.passed)

    @property
    def total(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "total": self.total,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True)
class AuditReport:
    target: Path
    score: int
    verdict: str
    blockers: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)
    recommendations: list[Finding] = field(default_factory=list)
    checklist: list[CategoryChecklist] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": str(self.target),
            "score": self.score,
            "verdict": self.verdict,
            "blockers": [finding.to_dict() for finding in self.blockers],
            "warnings": [finding.to_dict() for finding in self.warnings],
            "recommendations": [finding.to_dict() for finding in self.recommendations],
            "checklist": [category.to_dict() for category in self.checklist],
        }
