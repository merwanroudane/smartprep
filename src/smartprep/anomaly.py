"""Outliers that no single column can see.

The IQR fence already applied to every numeric column finds values that are
extreme *on their own*. It cannot find the two failures that matter most in
real data:

**Multivariate.** A person 1.6 m tall is ordinary. A person weighing 140 kg is
ordinary. One who is both is not, and neither column's fences contain a hint
of it. Mahalanobis distance measures how far a row sits from the centre *in
the shape of the data*, so a point can be unremarkable on every axis and still
be far away.

**Contextual.** A temperature of 30 °C is unexceptional; in February in
Reykjavik it is not. The value is only extreme relative to its group, so the
test has to be run within groups, and a row that is ordinary overall can be
the most extreme member of the segment it belongs to.

Neither is a defect. Both are *questions*, and the module says so: an outlier
is a row worth looking at, and how it got there decides whether it is a
mis-keyed digit, a rare genuine case, or the most interesting record in the
dataset. Every finding here carries a repair confidence of zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .core.enums import (
    DomainSensitivity,
    InformationLossRisk,
    IssueCategory,
    RuleSource,
    Severity,
    StatisticalImpact,
)
from .core.issue import Evidence, Issue, TreatmentCandidate

__all__ = ["Outlier", "AnomalyReport", "anomalies"]

#: Chi-square quantile for the Mahalanobis cutoff. 0.999 rather than 0.95:
#: at 95% roughly one row in twenty is "anomalous", which is a list nobody
#: reads.
_QUANTILE = 0.999

#: Fewer rows than this in a group and a within-group z-score is noise.
_MIN_GROUP = 12

#: Below this many rows per dimension the covariance estimate is unstable and
#: Mahalanobis distance stops meaning anything.
_ROWS_PER_DIMENSION = 5


@dataclass(frozen=True)
class Outlier:
    """One row worth a look, and why it stood out."""

    row: int
    score: float
    kind: str  # "multivariate" | "contextual"
    columns: tuple[str, ...]
    explanation: str
    group: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "row": self.row,
            "score": round(self.score, 4),
            "kind": self.kind,
            "columns": list(self.columns),
            "group": self.group,
            "explanation": self.explanation,
        }


@dataclass
class AnomalyReport:
    """Rows that are unusual jointly, or unusual for their group."""

    rows: int
    multivariate: list[Outlier] = field(default_factory=list)
    contextual: list[Outlier] = field(default_factory=list)
    columns_used: tuple[str, ...] = ()
    #: Why a test was not run, when it was not. Abstention is a result.
    skipped: tuple[str, ...] = ()
    issues: list[Issue] = field(default_factory=list)

    @property
    def all_outliers(self) -> list[Outlier]:
        return sorted([*self.multivariate, *self.contextual], key=lambda o: o.score, reverse=True)

    def summary(self) -> str:
        lines = [
            f"{len(self.multivariate):,} jointly unusual rows, "
            f"{len(self.contextual):,} unusual for their group, "
            f"across {self.rows:,} rows"
        ]
        if self.columns_used:
            lines.append(f"  measured on {', '.join(self.columns_used)}")
        for note in self.skipped:
            lines.append(f"  not tested: {note}")
        for outlier in self.all_outliers[:6]:
            lines.append(f"  row {outlier.row}: {outlier.explanation}")
        return "\n".join(lines)

    def charts(self) -> list[Any]:
        from .viz.spec import ChartSpec, Encoding, Mark

        found = self.all_outliers
        if not found:
            return []
        return [
            ChartSpec(
                mark=Mark.HORIZONTAL_BAR,
                data=[
                    {
                        "label": f"row {o.row}" + (f" · {o.group}" if o.group else ""),
                        "value": round(o.score, 4),
                        "kind": o.kind,
                    }
                    for o in found[:25]
                ],
                x=Encoding("value", "quantitative"),
                y=Encoding("label", "nominal"),
                color=Encoding("kind", "nominal"),
                title="Rows worth a look",
                x_label="distance from the ordinary",
                rationale=(
                    "A row can be unremarkable on every column and still be far "
                    "from the centre of all of them together."
                ),
            )
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "columns_used": list(self.columns_used),
            "skipped": list(self.skipped),
            "multivariate": [o.to_dict() for o in self.multivariate],
            "contextual": [o.to_dict() for o in self.contextual],
            "issues": [i.id for i in self.issues],
        }


def _mahalanobis(frame: pd.DataFrame, columns: tuple[str, ...]) -> tuple[list[Outlier], str]:
    """Distance from the centre, measured in the shape of the data."""
    from scipy import stats

    matrix = frame[list(columns)].apply(pd.to_numeric, errors="coerce")
    # Positions, never index labels: get_indexer raises on a duplicated index,
    # and a frame with one is ordinary after a concat. Resolving a row by label
    # would also return the wrong row when several answer to the same one.
    keep = [i for i, ok in enumerate(matrix.notna().all(axis=1)) if ok]
    usable = matrix.iloc[keep]
    dimensions = len(columns)

    if len(usable) < dimensions * _ROWS_PER_DIMENSION:
        return [], (
            f"multivariate distance needs about {dimensions * _ROWS_PER_DIMENSION} "
            f"complete rows for {dimensions} columns; {len(usable):,} are available, "
            "and a covariance estimated from fewer is not a shape"
        )

    values = usable.to_numpy(dtype=float)
    centre = values.mean(axis=0)
    covariance = np.cov(values, rowvar=False)
    try:
        inverse = np.linalg.pinv(covariance)
    except np.linalg.LinAlgError:  # pragma: no cover - pinv rarely fails
        return [], "the covariance matrix could not be inverted"

    deviations = values - centre
    squared = np.einsum("ij,jk,ik->i", deviations, inverse, deviations)
    cutoff = float(stats.chi2.ppf(_QUANTILE, df=dimensions))

    found: list[Outlier] = []
    for offset, distance in enumerate(squared):
        if distance <= cutoff:
            continue
        row = usable.iloc[offset]
        extreme = sorted(
            (
                (abs((row[c] - centre[i]) / (values[:, i].std() or 1)), c)
                for i, c in enumerate(columns)
            ),
            reverse=True,
        )[:2]
        described = ", ".join(f"{c}={row[c]:,.4g}" for _, c in extreme)
        found.append(
            Outlier(
                row=keep[offset],
                score=float(distance),
                kind="multivariate",
                columns=columns,
                explanation=(
                    f"far from the centre of {len(columns)} columns jointly "
                    f"(d²={distance:,.1f} vs {cutoff:,.1f}); most extreme on {described}"
                ),
            )
        )
    found.sort(key=lambda o: o.score, reverse=True)
    return found, ""


def _contextual(
    frame: pd.DataFrame, value: str, by: str, threshold: float
) -> tuple[list[Outlier], str]:
    """Values extreme relative to their own group rather than overall."""
    numbers = pd.to_numeric(frame[value], errors="coerce").to_numpy(dtype=float)
    groups = frame[by].astype(str).to_numpy()
    found: list[Outlier] = []
    small = 0

    positions: dict[str, list[int]] = {}
    for position, name in enumerate(groups):
        positions.setdefault(str(name), []).append(position)

    for name, members in positions.items():
        usable = [p for p in members if not pd.isna(numbers[p])]
        inside = pd.Series([numbers[p] for p in usable])
        if len(inside) < _MIN_GROUP:
            small += 1
            continue
        centre = inside.median()
        # Median absolute deviation, not the standard deviation: an outlier
        # inflates the very spread being used to detect it, and on a small
        # group it can hide itself entirely.
        spread = (inside - centre).abs().median() * 1.4826
        if spread <= 0:
            continue
        for offset, cell in enumerate(inside):
            score = abs(cell - centre) / spread
            if score < threshold:
                continue
            found.append(
                Outlier(
                    row=usable[offset],
                    score=float(score),
                    kind="contextual",
                    columns=(value, by),
                    group=str(name),
                    explanation=(
                        f"{value}={cell:,.4g} is {score:,.1f} deviations from the "
                        f"median of {by}={name!r} ({centre:,.4g}); "
                        "unremarkable against the column as a whole"
                    ),
                )
            )

    note = ""
    if small:
        note = (
            f"{small} group(s) of {by} had fewer than {_MIN_GROUP} rows; a "
            "within-group score from that few is noise"
        )
    found.sort(key=lambda o: o.score, reverse=True)
    return found, note


def anomalies(
    frame: pd.DataFrame,
    *,
    columns: tuple[str, ...] | None = None,
    by: str | None = None,
    value: str | None = None,
    threshold: float = 4.0,
    limit: int = 50,
) -> AnomalyReport:
    """Find rows that are unusual jointly, or unusual for their group.

    ``frame`` is never modified, and nothing is repaired. An outlier is a
    question about a row, not a defect in it.

    Parameters
    ----------
    columns:
        Numeric columns for the multivariate test. Defaults to every numeric
        column that is not an identifier.
    by, value:
        Group and measure for the contextual test. Both are needed; a
        contextual outlier is only defined relative to something.
    threshold:
        Deviations from the group median, in robust units. Four rather than
        three, because three flags about one row in three hundred by chance.
    """
    report = AnomalyReport(rows=len(frame))
    skipped: list[str] = []

    numeric = columns or tuple(
        str(c)
        for c in frame.columns
        if pd.api.types.is_numeric_dtype(frame[c]) and frame[c].nunique(dropna=True) > 2
    )
    if len(numeric) >= 2:
        report.columns_used = numeric
        found, note = _mahalanobis(frame, numeric)
        report.multivariate = found[:limit]
        if note:
            skipped.append(note)
    else:
        skipped.append(
            f"multivariate distance needs at least two numeric columns; {len(numeric)} available"
        )

    if by is not None and value is not None:
        for name in (by, value):
            if name not in frame.columns:
                raise KeyError(f"no column {name!r} in this frame")
        found, note = _contextual(frame, value, by, threshold)
        report.contextual = found[:limit]
        if note:
            skipped.append(note)
    elif by is not None or value is not None:
        raise ValueError(
            "a contextual outlier needs both 'by' and 'value' -- extreme "
            "relative to what, and extreme in what"
        )

    report.skipped = tuple(skipped)
    report.issues = _issues_for(report)
    return report


def _issues_for(report: AnomalyReport) -> list[Issue]:
    """One finding per kind, carrying the rows. Never one per row: fifty
    findings that all say "look at this row" is a queue nobody works."""
    issues: list[Issue] = []

    for kind, found in (
        ("multivariate", report.multivariate),
        ("contextual", report.contextual),
    ):
        if not found:
            continue
        columns = found[0].columns
        issues.append(
            Issue(
                id=f"ANOMALY-{kind.upper()}-{'-'.join(columns[:2])}",
                category=IssueCategory.UNUSUAL_PATTERN,
                severity=Severity.WARNING,
                detection_confidence=0.75,
                rule_source=RuleSource.STATISTICAL_RULE,
                columns=columns,
                evidence=Evidence(
                    summary=(
                        f"{len(found):,} rows are unusual "
                        + (
                            "across these columns jointly while being ordinary on each one alone"
                            if kind == "multivariate"
                            else "for the group they belong to, while being "
                            "ordinary against the column as a whole"
                        )
                    ),
                    affected_rows=tuple(o.row for o in found),
                    sample_values=tuple(o.explanation for o in found[:3]),
                    details={"kind": kind, "outliers": [o.to_dict() for o in found[:20]]},
                ),
                detector="anomaly",
                treatments=(
                    TreatmentCandidate(
                        name="review_anomalous_rows",
                        description=(
                            "Look at these rows and decide what they are -- a "
                            "mis-keyed digit, a rare genuine case, or the most "
                            "interesting records in the dataset"
                        ),
                        repair_confidence=0.0,
                        information_loss_risk=InformationLossRisk.HIGH,
                        statistical_impact=StatisticalImpact.MATERIAL,
                        domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                    ),
                ),
                notes=(
                    "an outlier is a question about a row, not a defect in it; "
                    "deleting one because it is far away is how a dataset loses "
                    "its most informative records"
                ),
            )
        )
    return issues
