"""Data Health Score -- decomposable, documented, and never presented as truth.

A single number is convenient and dishonest. This model reports independent
dimensions, keeps the formula visible, and states which findings moved each
one, so a reader can disagree with the weighting rather than having to accept
or reject the whole score.

The score answers "how healthy is this data?". It is a different question from
scan coverage, which answers "how much of the checking did we finish?", and the
two must never be conflated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .enums import IssueCategory, Severity

if TYPE_CHECKING:  # pragma: no cover
    from .issue import Issue

__all__ = ["Dimension", "DataHealthScore", "score_issues"]


#: Which categories count against which dimension. A category may appear in
#: more than one -- an invalid date is both a validity and a consistency
#: problem.
DIMENSION_CATEGORIES: dict[str, frozenset[IssueCategory]] = {
    "completeness": frozenset({IssueCategory.MISSINGNESS, IssueCategory.SUSPICIOUS_MISSINGNESS}),
    "validity": frozenset(
        {
            IssueCategory.INVALID_DATE,
            IssueCategory.RANGE_VIOLATION,
            IssueCategory.SENTINEL_CANDIDATE,
            IssueCategory.MIXED_PHYSICAL_TYPE,
        }
    ),
    "consistency": frozenset(
        {
            IssueCategory.STATE_CONTRADICTION,
            IssueCategory.FORMULA_VIOLATION,
            IssueCategory.GEOGRAPHIC_CONFLICT,
            IssueCategory.ACCOUNTING_IMPLAUSIBILITY,
            IssueCategory.IDENTIFIER_METADATA_MISMATCH,
        }
    ),
    "uniqueness": frozenset({IssueCategory.EXACT_DUPLICATE, IssueCategory.CONFLICTING_DUPLICATE}),
    "semantic_quality": frozenset(
        {
            IssueCategory.CATEGORY_VARIANT,
            IssueCategory.UNICODE_CONFUSABLE,
            IssueCategory.AMBIGUOUS_DATE,
            IssueCategory.CURRENCY_CONTEXT,
            IssueCategory.UNKNOWN_ENTITY,
        }
    ),
}

#: How much one finding costs its dimension, before scaling by prevalence.
#: Informational findings cost nothing: structural missingness is the data being
#: correct, and charging it would punish a dataset for being well modelled.
SEVERITY_WEIGHT: dict[Severity, float] = {
    Severity.INFO: 0.0,
    Severity.NOTICE: 2.0,
    Severity.WARNING: 6.0,
    Severity.HIGH_WARNING: 12.0,
    Severity.CRITICAL_REVIEW: 20.0,
    Severity.BLOCKING: 30.0,
}


@dataclass(frozen=True)
class Dimension:
    """One independently scored aspect of data health."""

    name: str
    score: float
    penalty: float
    contributing: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 1),
            "penalty": round(self.penalty, 1),
            "contributing_issues": list(self.contributing),
        }


@dataclass
class DataHealthScore:
    """Health across dimensions, plus the overall figure derived from them."""

    dimensions: dict[str, Dimension] = field(default_factory=dict)
    row_count: int = 0

    @property
    def overall(self) -> float:
        """Unweighted mean of the dimensions.

        Deliberately unweighted: any weighting would encode a judgement about
        which kind of wrongness matters most, and that depends on what the data
        is for. Callers who know their context should read the dimensions.
        """
        if not self.dimensions:
            return 100.0
        return sum(d.score for d in self.dimensions.values()) / len(self.dimensions)

    def get(self, name: str) -> float:
        return self.dimensions[name].score

    def delta(self, other: DataHealthScore) -> dict[str, float]:
        """Change per dimension, from ``other`` to ``self``."""
        return {
            name: round(dim.score - other.dimensions[name].score, 1)
            for name, dim in self.dimensions.items()
            if name in other.dimensions
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": round(self.overall, 1),
            "dimensions": {k: v.to_dict() for k, v in self.dimensions.items()},
            "note": (
                "Health measures the data. Scan coverage measures the checking. "
                "They are different numbers and neither implies the other."
            ),
        }

    def summary(self) -> str:
        lines = [f"Data health {self.overall:.0f}/100"]
        for name, dim in sorted(self.dimensions.items()):
            bar = "#" * int(dim.score / 5)
            lines.append(f"  {name:20s} {dim.score:5.1f}  {bar}")
        return "\n".join(lines)


def score_issues(issues: list[Issue], row_count: int) -> DataHealthScore:
    """Compute health from findings.

    A finding's cost scales with how much of the dataset it touches, so one bad
    row in a million is not treated like a systemic defect. The cost is capped
    per dimension so a single category cannot drive a score negative.
    """
    result = DataHealthScore(row_count=row_count)

    for name, categories in DIMENSION_CATEGORIES.items():
        penalty = 0.0
        contributing: list[str] = []
        for issue in issues:
            if issue.category not in categories:
                continue
            weight = SEVERITY_WEIGHT.get(issue.severity, 5.0)
            if weight == 0.0:
                continue
            prevalence = min(1.0, issue.affected_row_count / row_count) if row_count else 0.0
            # A finding always costs something once detected, plus more as it
            # spreads. Otherwise a single critical row would score as perfect.
            penalty += weight * (0.35 + 0.65 * prevalence)
            contributing.append(issue.id)

        penalty = min(penalty, 100.0)
        result.dimensions[name] = Dimension(
            name=name,
            score=max(0.0, 100.0 - penalty),
            penalty=penalty,
            contributing=tuple(contributing),
        )

    return result
