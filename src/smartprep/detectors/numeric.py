"""Numeric quality: declared-range violations and sentinel codes.

A sentinel is not an outlier. ``999999`` employees is not a very large company;
it is a placeholder wearing a number's clothes. Feeding it to an IQR rule gets
the arithmetic right and the meaning wrong.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ..core.enums import (
    DomainSensitivity,
    InformationLossRisk,
    IssueCategory,
    Reversibility,
    RuleSource,
    Severity,
    StatisticalImpact,
)
from ..core.issue import Evidence, Issue, TreatmentCandidate
from .base import numeric_series, register

__all__ = ["RangeConstraint", "RangeViolationDetector", "SentinelDetector", "DEFAULT_RANGES"]


@dataclass(frozen=True)
class RangeConstraint:
    """A hard domain bound, distinct from a soft statistical expectation."""

    column: str
    minimum: float | None = None
    maximum: float | None = None
    allow_zero: bool = True
    rationale: str = ""


#: Constraints implied by the fixture's data dictionary. In production these are
#: read from a contract, not hard-coded -- the source is what makes them "hard".
DEFAULT_RANGES: tuple[RangeConstraint, ...] = (
    RangeConstraint(
        "quantity", minimum=1, rationale="an invoice line cannot bill zero or fewer units"
    ),
    RangeConstraint("discount_pct", minimum=0, maximum=1, rationale="a proportion in [0, 1]"),
    RangeConstraint("tax_pct", minimum=0, maximum=1, rationale="a proportion in [0, 1]"),
    RangeConstraint("customer_rating", minimum=1, maximum=5, rationale="declared 1-5 scale"),
    RangeConstraint("employee_count", minimum=1, rationale="headcount is a positive integer"),
)


@register
class RangeViolationDetector:
    """Report values outside a declared hard bound."""

    name = "range_violation"

    def detect(
        self,
        frame: pd.DataFrame,
        *,
        ranges: tuple[RangeConstraint, ...] = DEFAULT_RANGES,
        **context: Any,
    ) -> list[Issue]:
        issues: list[Issue] = []
        for rule in ranges:
            if rule.column not in frame.columns:
                continue
            series = numeric_series(frame, rule.column)
            mask = pd.Series(False, index=series.index)
            if rule.minimum is not None:
                mask |= series < rule.minimum
            if rule.maximum is not None:
                mask |= series > rule.maximum
            mask &= series.notna()
            if not mask.any():
                continue

            rows = [int(i) for i in np.flatnonzero(mask.to_numpy())]
            offending = series[mask]
            issues.append(
                Issue(
                    id=f"RANGE-{rule.column}",
                    category=IssueCategory.RANGE_VIOLATION,
                    severity=Severity.CRITICAL_REVIEW,
                    detection_confidence=1.0,
                    rule_source=RuleSource.DATA_DICTIONARY,
                    columns=(rule.column,),
                    evidence=Evidence(
                        summary=(
                            f"{int(mask.sum())} values in {rule.column!r} fall outside "
                            f"[{rule.minimum}, {rule.maximum}] -- {rule.rationale}"
                        ),
                        affected_rows=tuple(rows),
                        sample_values=tuple(sorted(offending.unique())[:8]),
                        details={
                            "minimum": rule.minimum,
                            "maximum": rule.maximum,
                            "below": int((series < rule.minimum).sum())
                            if rule.minimum is not None
                            else 0,
                            "above": int((series > rule.maximum).sum())
                            if rule.maximum is not None
                            else 0,
                        },
                    ),
                    treatments=(
                        TreatmentCandidate(
                            name="quarantine_violating_rows",
                            description=(
                                "Move offending rows aside with the reason recorded, "
                                "rather than deleting or clipping them."
                            ),
                            repair_confidence=0.85,
                            reversibility=Reversibility.REVERSIBLE,
                            information_loss_risk=InformationLossRisk.LOW,
                        ),
                        TreatmentCandidate(
                            name="set_missing_with_flag",
                            description=(
                                "Replace the impossible value with missing and add an "
                                "indicator column."
                            ),
                            repair_confidence=0.80,
                            reversibility=Reversibility.REVERSIBLE_WITH_SNAPSHOT,
                            information_loss_risk=InformationLossRisk.MEDIUM,
                            statistical_impact=StatisticalImpact.MODERATE,
                        ),
                    ),
                    recommended="quarantine_violating_rows",
                )
            )
        return issues


@register
class SentinelDetector:
    """Identify placeholder codes masquerading as measurements.

    Evidence combined, never a single signal: the value is a repeated round
    number, it repeats exactly, and it sits far outside the rest of the
    distribution. Any one alone would produce false positives on genuinely
    large values.
    """

    name = "sentinel_candidate"

    #: Conventional placeholder codes.
    KNOWN = (999, 9999, 99999, 999999, 9999999, -1, -9, -99, -999, -9999)

    def detect(
        self, frame: pd.DataFrame, *, numeric_columns: tuple[str, ...] = (), **context: Any
    ) -> list[Issue]:
        columns = numeric_columns or tuple(
            c for c in frame.columns if numeric_series(frame, c).notna().sum() > 0
        )

        issues: list[Issue] = []
        for column in columns:
            series = numeric_series(frame, column).dropna()
            if len(series) < 30:
                continue
            counts = Counter(series)
            clean = series[~series.isin(self.KNOWN)]
            if clean.empty:
                continue
            ceiling = clean.quantile(0.999)
            spread = clean.quantile(0.75) - clean.quantile(0.25)

            found: dict[float, int] = {}
            for candidate in self.KNOWN:
                n = counts.get(float(candidate), 0)
                if n < 2:
                    continue
                # Far outside the genuine distribution, not merely at its edge.
                far_above = spread > 0 and candidate > ceiling + 10 * spread
                # A negative code in a column that is otherwise non-negative.
                impossible_sign = candidate < 0 and clean.min() >= 0
                if far_above or impossible_sign:
                    found[float(candidate)] = n
            if not found:
                continue

            rows = [int(i) for i, v in enumerate(numeric_series(frame, column)) if v in found]
            issues.append(
                Issue(
                    id=f"SENTINEL-{column}",
                    category=IssueCategory.SENTINEL_CANDIDATE,
                    severity=Severity.HIGH_WARNING,
                    detection_confidence=0.97,
                    rule_source=RuleSource.STATISTICAL_RULE,
                    columns=(column,),
                    evidence=Evidence(
                        summary=(
                            f"{column!r} repeats the round value(s) "
                            f"{sorted(found)} far outside its distribution -- "
                            "characteristic of a placeholder code, not a measurement"
                        ),
                        affected_rows=tuple(rows),
                        sample_values=tuple(sorted(found)),
                        details={
                            "occurrences": found,
                            "p99_9_excluding_candidates": float(ceiling),
                            "iqr_excluding_candidates": float(spread),
                        },
                    ),
                    treatments=(
                        TreatmentCandidate(
                            name="treat_as_missing",
                            description="Interpret the code as a missing marker.",
                            # We are confident it is *not* a real measurement.
                            # We are not confident what it was meant to encode --
                            # missing, refused, unknown or a typo all fit.
                            repair_confidence=0.55,
                            reversibility=Reversibility.REVERSIBLE_WITH_SNAPSHOT,
                            information_loss_risk=InformationLossRisk.MEDIUM,
                            domain_sensitivity=DomainSensitivity.CONTEXTUAL,
                        ),
                        TreatmentCandidate(
                            name="keep_and_flag",
                            description="Leave the value and mark the rows for review.",
                            repair_confidence=0.50,
                            reversibility=Reversibility.REVERSIBLE,
                        ),
                    ),
                    recommended="treat_as_missing",
                )
            )
        return issues
