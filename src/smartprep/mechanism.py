"""Why values are missing -- and the limit of what data can say about it.

Every treatment of missing data rests on an assumption about the mechanism,
and the assumption is usually made silently by whoever picked the imputer.
The three named mechanisms are:

``MCAR``
    Missing completely at random. Absence is unrelated to anything, observed
    or not. Listwise deletion is unbiased; so is almost everything else.
``MAR``
    Missing at random *given the observed data*. Absence depends on columns
    you can see. Deletion is biased; imputation conditioned on those columns
    is not.
``MNAR``
    Missing not at random. Absence depends on the value that is missing --
    high earners declining to state income. Nothing conditioned on observed
    data fixes it.

**This module can rule out MCAR. It can never establish MNAR.** That is not a
limitation of the implementation; it is a fact about the problem. MAR and MNAR
differ only in whether absence depends on the *unobserved* value, and no test
on observed data can see an unobserved value. A library that reported "MNAR"
would be reporting a domain judgement as a measurement.

So the verdict is one of two things -- MCAR not rejected, or not MCAR -- plus
the evidence, and a standing note that ruling out MCAR narrows the answer to
{MAR, MNAR} and no further.

The tests are ordinary and non-parametric: for each column with missing
values, does every *other* column differ between the rows where it is present
and the rows where it is absent? Mann-Whitney for a numeric predictor,
chi-square for a categorical one. Many pairs are tested at once, so p-values
carry a Holm-Bonferroni correction -- without it, twenty columns produce a
spurious dependence by arithmetic alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

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

__all__ = ["Mechanism", "Dependence", "ColumnMechanism", "MechanismReport", "mechanism"]

#: Below this, a dependence is called real. Applied *after* correction.
_ALPHA = 0.05

#: Fewer rows than this on either side of the split and no test is trustworthy.
_MIN_GROUP = 8


class Mechanism(Enum):
    """What the observed data supports. Deliberately three, not four."""

    MCAR_NOT_REJECTED = "mcar_not_rejected"
    NOT_MCAR = "not_mcar"
    UNDETERMINED = "undetermined"

    @property
    def describe(self) -> str:
        return {
            "mcar_not_rejected": (
                "no observed column predicts this absence; consistent with MCAR, "
                "which is not the same as proof of it"
            ),
            "not_mcar": (
                "absence depends on observed columns, so it is MAR or MNAR -- "
                "the data cannot say which"
            ),
            "undetermined": "too few rows on one side of the split to test",
        }[self.value]


@dataclass(frozen=True)
class Dependence:
    """One column whose values differ by whether another is missing."""

    missing_in: str
    predictor: str
    test: str
    statistic: float
    p_value: float
    adjusted_p: float
    effect: str

    @property
    def is_significant(self) -> bool:
        return self.adjusted_p < _ALPHA

    def describe(self) -> str:
        return (
            f"{self.predictor} differs by whether {self.missing_in} is missing "
            f"({self.test}, p={self.adjusted_p:.2}"
            f"{' after correction' if self.adjusted_p != self.p_value else ''}): {self.effect}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "missing_in": self.missing_in,
            "predictor": self.predictor,
            "test": self.test,
            "statistic": round(self.statistic, 6),
            "p_value": round(self.p_value, 8),
            "adjusted_p": round(self.adjusted_p, 8),
            "significant": self.is_significant,
            "effect": self.effect,
            "describe": self.describe(),
        }


@dataclass
class ColumnMechanism:
    """What can be said about one column's missingness."""

    column: str
    missing: int
    rate: float
    verdict: Mechanism
    dependences: list[Dependence] = field(default_factory=list)
    #: Columns whose absence always accompanies this one's. In longitudinal
    #: data this is drop-out; elsewhere it usually means one source failed.
    monotone_with: tuple[str, ...] = ()
    tested_against: int = 0

    @property
    def predictors(self) -> list[Dependence]:
        return [d for d in self.dependences if d.is_significant]

    def summary(self) -> str:
        head = f"{self.column}: {self.missing:,} missing ({self.rate:.1%}) -- {self.verdict.value}"
        lines = [head, f"  {self.verdict.describe}"]
        for dependence in self.predictors[:4]:
            lines.append(f"  {dependence.describe()}")
        if self.monotone_with:
            lines.append(f"  always missing together with {', '.join(self.monotone_with)}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "missing": self.missing,
            "rate": round(self.rate, 6),
            "verdict": self.verdict.value,
            "explanation": self.verdict.describe,
            "tested_against": self.tested_against,
            "monotone_with": list(self.monotone_with),
            "dependences": [d.to_dict() for d in self.predictors],
        }


@dataclass
class MechanismReport:
    """Missingness mechanism evidence for a whole frame."""

    columns: list[ColumnMechanism] = field(default_factory=list)
    rows: int = 0
    issues: list[Issue] = field(default_factory=list)

    #: Stated on every report. The distinction it draws is the one that
    #: decides whether an imputation is defensible, and it is not decidable
    #: from data.
    caveat: str = (
        "Ruling out MCAR narrows the mechanism to MAR or MNAR and no further. "
        "The two differ only in whether absence depends on the value that is "
        "missing, which no test on observed data can see. Choosing between "
        "them is a judgement about how the data was collected."
    )

    @property
    def not_mcar(self) -> list[ColumnMechanism]:
        return [c for c in self.columns if c.verdict is Mechanism.NOT_MCAR]

    def get(self, column: str) -> ColumnMechanism:
        for candidate in self.columns:
            if candidate.column == column:
                return candidate
        raise KeyError(f"{column!r} has no missing values, or is not in this frame")

    def summary(self) -> str:
        if not self.columns:
            return "no column has missing values"
        lines = [f"{len(self.columns)} columns with missing values, {self.rows:,} rows"]
        lines.extend(c.summary() for c in self.columns)
        lines += ["", self.caveat]
        return "\n".join(lines)

    def charts(self) -> list[Any]:
        from .viz.spec import ChartSpec, Encoding, Mark

        if not self.columns:
            return []
        ordered = sorted(self.columns, key=lambda c: c.rate, reverse=True)
        return [
            ChartSpec(
                mark=Mark.HORIZONTAL_BAR,
                data=[
                    {
                        "label": c.column,
                        "value": round(c.rate, 6),
                        "verdict": c.verdict.value,
                    }
                    for c in ordered[:30]
                ],
                x=Encoding("value", "quantitative"),
                y=Encoding("label", "nominal"),
                color=Encoding("verdict", "nominal"),
                title="Missingness rate, coloured by mechanism evidence",
                x_label="share of rows missing",
                rationale=(
                    "A column whose absence is predictable from other columns "
                    "cannot be deleted listwise without bias, whatever its rate."
                ),
            )
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "caveat": self.caveat,
            "columns": [c.to_dict() for c in self.columns],
            "issues": [i.id for i in self.issues],
        }


# --------------------------------------------------------------------------
# Testing
# --------------------------------------------------------------------------


def _holm(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni step-down correction.

    Twenty columns give a hundred and ninety pairs, and at a nominal 5% about
    ten of them are significant by arithmetic alone. Reporting those as
    dependences would turn every wide dataset into a MAR diagnosis.
    """
    indexed = sorted(enumerate(p_values), key=lambda kv: kv[1])
    total = len(p_values)
    adjusted = [0.0] * total
    running = 0.0
    for rank, (position, value) in enumerate(indexed):
        candidate = min(1.0, value * (total - rank))
        running = max(running, candidate)
        adjusted[position] = running
    return adjusted


def _compare(
    missing_in: str, predictor: str, values: pd.Series, absent: pd.Series
) -> tuple[str, float, float, str] | None:
    """Does ``predictor`` differ between rows where ``missing_in`` is absent?"""
    from scipy import stats

    present_side = values[~absent]
    absent_side = values[absent]

    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().sum() >= 0.9 * values.notna().sum() and numeric.nunique() > 2:
        left = pd.to_numeric(present_side, errors="coerce").dropna()
        right = pd.to_numeric(absent_side, errors="coerce").dropna()
        if len(left) < _MIN_GROUP or len(right) < _MIN_GROUP:
            return None
        # Non-parametric on purpose: the columns most likely to predict
        # missingness are skewed ones, and a t-test on those reports
        # significance driven by a tail rather than a shift.
        statistic, p_value = stats.mannwhitneyu(left, right, alternative="two-sided")
        effect = f"median {left.median():,.4g} when present, {right.median():,.4g} when absent"
        return "Mann-Whitney U", float(statistic), float(p_value), effect

    table = pd.crosstab(values.astype(str), absent)
    if table.shape[0] < 2 or table.shape[1] < 2 or table.to_numpy().min() < 1:
        return None
    if min(table.sum(axis=0)) < _MIN_GROUP:
        return None
    statistic, p_value, _, _ = stats.chi2_contingency(table)

    rates = table[True] / table.sum(axis=1) if True in table.columns else None
    effect = "the level mix differs"
    if rates is not None and len(rates):
        worst = rates.idxmax()
        effect = f"{worst!r} is absent {rates.max():.0%} of the time"
    return "chi-square", float(statistic), float(p_value), effect


def mechanism(
    frame: pd.DataFrame,
    *,
    columns: tuple[str, ...] | None = None,
    max_predictors: int = 25,
) -> MechanismReport:
    """Test each column's missingness against every other column.

    ``frame`` is never modified. Returns evidence, not a decision: the verdict
    is at most "not MCAR", and choosing between MAR and MNAR is a judgement
    about collection that no test can make.
    """
    from .detectors.base import is_missing

    report = MechanismReport(rows=len(frame))
    absent_masks = {str(name): frame[name].map(is_missing) for name in frame.columns}

    targets = columns or tuple(
        name for name, mask in absent_masks.items() if 0 < int(mask.sum()) < len(frame)
    )
    predictors = [str(c) for c in frame.columns][:max_predictors]

    for target in targets:
        absent = absent_masks[str(target)]
        count = int(absent.sum())
        column = ColumnMechanism(
            column=str(target),
            missing=count,
            rate=count / len(frame) if len(frame) else 0.0,
            verdict=Mechanism.UNDETERMINED,
        )

        if count < _MIN_GROUP or (len(frame) - count) < _MIN_GROUP:
            report.columns.append(column)
            continue

        raw: list[tuple[str, str, float, float, str]] = []
        for predictor in predictors:
            if predictor == target:
                continue
            outcome = _compare(str(target), predictor, frame[predictor], absent)
            if outcome is None:
                continue
            test, statistic, p_value, effect = outcome
            raw.append((predictor, test, statistic, p_value, effect))

        column.tested_against = len(raw)
        if not raw:
            report.columns.append(column)
            continue

        adjusted = _holm([p for _, _, _, p, _ in raw])
        column.dependences = [
            Dependence(
                missing_in=str(target),
                predictor=predictor,
                test=test,
                statistic=statistic,
                p_value=p_value,
                adjusted_p=adjusted_p,
                effect=effect,
            )
            for (predictor, test, statistic, p_value, effect), adjusted_p in zip(
                raw, adjusted, strict=True
            )
        ]
        column.verdict = Mechanism.NOT_MCAR if column.predictors else Mechanism.MCAR_NOT_REJECTED

        column.monotone_with = tuple(
            other
            for other, mask in absent_masks.items()
            if other != str(target) and int(mask.sum()) and bool((absent & mask).sum() == count)
        )
        report.columns.append(column)

    report.issues = _issues_for(report)
    return report


def _issues_for(report: MechanismReport) -> list[Issue]:
    issues: list[Issue] = []
    for column in report.not_mcar:
        drivers = ", ".join(d.predictor for d in column.predictors[:3])
        issues.append(
            Issue(
                id=f"MECHANISM-NOT-MCAR-{column.column}",
                category=IssueCategory.SUSPICIOUS_MISSINGNESS,
                severity=Severity.HIGH_WARNING,
                detection_confidence=0.9,
                rule_source=RuleSource.STATISTICAL_RULE,
                columns=(column.column,),
                evidence=Evidence(
                    summary=(
                        f"{column.column} is missing in a pattern predicted by "
                        f"{drivers}, so its absence is not random. Dropping these "
                        f"{column.missing:,} rows biases every estimate that uses "
                        "them; imputing without conditioning on those columns "
                        "does the same"
                    ),
                    affected_rows=(),
                    details=column.to_dict(),
                ),
                detector="mechanism",
                treatments=(
                    TreatmentCandidate(
                        name="review_missingness_mechanism",
                        description=(
                            "Decide whether absence depends on the missing value "
                            "itself -- which the data cannot tell you"
                        ),
                        repair_confidence=0.0,
                        information_loss_risk=InformationLossRisk.HIGH,
                        statistical_impact=StatisticalImpact.MATERIAL,
                        domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                    ),
                ),
                notes=report.caveat,
            )
        )
    return issues
