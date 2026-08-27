"""Recommending preprocessing, rather than making the user guess.

The library already knows the cardinality, the skew, the missing rate and the
analysis goal. Making the user choose between fifteen encoders without that
context is a documentation problem dressed as flexibility.

Every recommendation carries its reason and the alternatives it beat, so
disagreeing with it is easy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

from ..detectors.base import is_missing, to_number
from .core import Preprocessor

__all__ = ["Goal", "Recommendation", "PreprocessingAdvice", "recommend"]


class Goal(Enum):
    """What the data is being prepared for.

    The same column is prepared differently for a descriptive report and for a
    gradient-boosted model, and pretending otherwise is how econometric data
    gets silently standardised.
    """

    EDA = "eda"
    MACHINE_LEARNING = "machine_learning"
    LINEAR_MODEL = "linear_model"
    TREE_MODEL = "tree_model"
    ECONOMETRICS = "econometrics"
    TIME_SERIES = "time_series"


@dataclass(frozen=True)
class Recommendation:
    """One proposed step, with its justification."""

    column: str
    kind: str
    method: str
    confidence: float
    reason: str
    alternatives: tuple[tuple[str, str], ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "kind": self.kind,
            "method": self.method,
            "confidence": self.confidence,
            "reason": self.reason,
            "alternatives": [{"method": m, "why_not": w} for m, w in self.alternatives],
        }


@dataclass
class PreprocessingAdvice:
    """Recommendations for a dataset, convertible into a pipeline."""

    goal: Goal
    recommendations: list[Recommendation] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_preprocessor(self, *, target: str | None = None) -> Preprocessor:
        """Build the pipeline. Review it before fitting -- it is a proposal."""
        prep = Preprocessor(target=target)
        for rec in sorted(self.recommendations, key=lambda r: _ORDER[r.kind]):
            if rec.kind == "add_missing_indicator":
                prep.add_missing_indicator(rec.column)
            else:
                getattr(prep, rec.kind)(rec.column, method=rec.method, **rec.parameters)
        return prep

    def summary(self) -> str:
        lines = [f"Preprocessing advice for goal '{self.goal.value}'", ""]
        for rec in sorted(self.recommendations, key=lambda r: (_ORDER[r.kind], r.column)):
            lines.append(
                f"  {rec.column:22s} {rec.kind:8s} {rec.method:16s} ({rec.confidence:.0%})"
            )
            lines.append(f"      {rec.reason}")
            for method, why_not in rec.alternatives:
                lines.append(f"      not {method}: {why_not}")
        if self.notes:
            lines += ["", "Notes:"]
            lines += [f"  - {n}" for n in self.notes]
        return "\n".join(lines)


#: Steps run in this order. Indicators are recorded *before* imputation fills
#: the gaps, or there would be nothing left to indicate.
_ORDER = {"add_missing_indicator": 0, "impute": 1, "encode": 2, "scale": 3}


def _scalar(value: Any) -> float:
    """Narrow a pandas reduction to a float.

    ``Series.skew()`` and friends are typed as a wide union covering every
    dtype a Series could hold. These call sites have already established the
    column is numeric, so the narrowing happens once, here, rather than being
    ignored at each use.
    """
    return float(value)


def recommend(
    frame: pd.DataFrame,
    *,
    goal: Goal | str = Goal.MACHINE_LEARNING,
    target: str | None = None,
    max_cardinality: int = 50,
) -> PreprocessingAdvice:
    """Propose a preprocessing pipeline for this data and this goal."""
    goal = Goal(goal) if isinstance(goal, str) else goal
    advice = PreprocessingAdvice(goal=goal)

    if goal in (Goal.EDA, Goal.ECONOMETRICS):
        advice.notes.append(
            "Scaling and encoding are omitted by default for this goal. They change "
            "how coefficients read, and a descriptive report does not need them."
        )

    for column in frame.columns:
        if column == target:
            continue
        series = frame[column]
        missing_rate = sum(1 for v in series if is_missing(v)) / max(len(series), 1)
        numeric = series.map(to_number)
        is_numeric = numeric.notna().sum() > 0.9 * max(series.notna().sum(), 1)

        if 0 < missing_rate < 0.5:
            advice.recommendations.append(
                _impute_advice(column, series, numeric, is_numeric, missing_rate, goal)
            )
            if missing_rate > 0.05:
                advice.recommendations.append(
                    Recommendation(
                        column=column,
                        kind="add_missing_indicator",
                        method="indicator",
                        confidence=0.9,
                        reason=(
                            f"{missing_rate:.1%} missing is enough that whether a value "
                            "was present may itself be informative"
                        ),
                    )
                )
        elif missing_rate >= 0.5:
            advice.notes.append(
                f"{column!r} is {missing_rate:.0%} missing. Imputing more than half a "
                "column invents most of it; consider dropping it instead."
            )

        if is_numeric and goal not in (Goal.EDA, Goal.ECONOMETRICS, Goal.TREE_MODEL):
            scale = _scale_advice(column, numeric.dropna(), goal)
            if scale is not None:
                advice.recommendations.append(scale)
        elif not is_numeric and series.nunique(dropna=True) <= max_cardinality:
            if goal not in (Goal.EDA, Goal.ECONOMETRICS):
                advice.recommendations.append(
                    _encode_advice(column, series, target, goal, max_cardinality)
                )

    return advice


def _impute_advice(
    column: str,
    series: pd.Series,
    numeric: pd.Series,
    is_numeric: bool,
    missing_rate: float,
    goal: Goal,
) -> Recommendation:
    if not is_numeric:
        return Recommendation(
            column=column,
            kind="impute",
            method="mode",
            confidence=0.75,
            reason="categorical column; the most frequent level is the safest fill",
            alternatives=(("constant", "creates a synthetic level that models may latch onto"),),
        )

    if goal is Goal.TIME_SERIES:
        return Recommendation(
            column=column,
            kind="impute",
            method="forward_fill",
            confidence=0.8,
            reason="time series; carrying the last observation forward uses no future data",
            alternatives=(
                ("interpolate", "interpolation reads the next observation, which is the future"),
                ("median", "a global median ignores the series' level and trend"),
            ),
        )

    values = numeric.dropna()
    skew = _scalar(values.skew()) if len(values) > 2 else 0.0
    if abs(skew) > 1.0:
        return Recommendation(
            column=column,
            kind="impute",
            method="median",
            confidence=0.85,
            reason=f"skew is {skew:.2f}; the mean is pulled by the tail, the median is not",
            alternatives=(("mean", "distorted by the skew in this column"),),
        )
    return Recommendation(
        column=column,
        kind="impute",
        method="median",
        confidence=0.8,
        reason="roughly symmetric, but the median is robust and costs nothing here",
        alternatives=(("mean", "equivalent here; the median is the safer default"),),
    )


def _scale_advice(column: str, values: pd.Series, goal: Goal) -> Recommendation | None:
    if len(values) < 3 or values.nunique() < 2:
        return None

    skew = _scalar(values.skew())
    q1, q3 = _scalar(values.quantile(0.25)), _scalar(values.quantile(0.75))
    iqr = q3 - q1
    outlier_rate = (
        float(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).mean()) if iqr > 0 else 0.0
    )

    if abs(skew) > 2.0 and values.min() >= 0:
        return Recommendation(
            column=column,
            kind="scale",
            method="log1p",
            confidence=0.8,
            reason=f"heavily right-skewed ({skew:.1f}) and non-negative",
            alternatives=(
                ("standard", "standardising a skewed column leaves it skewed"),
                ("yeo_johnson", "also works and handles negatives, but is harder to explain"),
            ),
        )
    if outlier_rate > 0.05:
        return Recommendation(
            column=column,
            kind="scale",
            method="robust",
            confidence=0.85,
            reason=f"{outlier_rate:.1%} of values sit outside the fences; median/IQR resists them",
            alternatives=(("standard", "mean and standard deviation move with the outliers"),),
        )
    return Recommendation(
        column=column,
        kind="scale",
        method="standard",
        confidence=0.9,
        reason="roughly symmetric with few extremes",
        alternatives=(("minmax", "bounded output, but one extreme compresses everything else"),),
    )


def _encode_advice(
    column: str, series: pd.Series, target: str | None, goal: Goal, max_cardinality: int
) -> Recommendation:
    cardinality = int(series.nunique(dropna=True))
    n = max(len(series), 1)

    dtype = getattr(series, "dtype", None)
    if isinstance(dtype, pd.CategoricalDtype) and dtype.ordered:
        # The usual objection to ordinal encoding is that it invents an order.
        # Here the caller declared one, so encoding it is the faithful choice
        # and one-hot would be the lossy one: it discards the ranking the user
        # went to the trouble of stating.
        levels = [str(level) for level in dtype.categories]
        return Recommendation(
            column=column,
            kind="encode",
            method="ordinal",
            confidence=0.95,
            reason=(
                f"the column declares an order ({' < '.join(levels[:4])}"
                f"{' < ...' if len(levels) > 4 else ''}); "
                "ordinal encoding preserves it, one-hot would discard it"
            ),
            parameters={"order": levels},
            alternatives=(("one_hot", "readable, but throws away the declared ranking"),),
        )

    if cardinality <= 2:
        return Recommendation(
            column=column,
            kind="encode",
            method="ordinal",
            confidence=0.95,
            reason="binary; one column is enough and one-hot would duplicate it",
        )
    if cardinality <= 15:
        return Recommendation(
            column=column,
            kind="encode",
            method="one_hot",
            confidence=0.9,
            reason=f"{cardinality} levels; one-hot stays readable and assumes no ordering",
            alternatives=(
                ("ordinal", "invents an ordering these levels do not have"),
                ("target", "leaks unless cross-fitted, and is unnecessary at this cardinality"),
            ),
        )
    if target is not None and goal in (Goal.MACHINE_LEARNING, Goal.TREE_MODEL):
        return Recommendation(
            column=column,
            kind="encode",
            method="target",
            confidence=0.7,
            reason=(
                f"{cardinality} levels across {n} rows; one-hot would add {cardinality} "
                "sparse columns"
            ),
            alternatives=(
                ("one_hot", f"would add {cardinality} columns, most of them near-empty"),
                ("frequency", "cheaper and leak-free, but discards the outcome signal"),
            ),
        )
    return Recommendation(
        column=column,
        kind="encode",
        method="frequency",
        confidence=0.75,
        reason=f"{cardinality} levels and no target available; frequency is compact and leak-free",
        alternatives=(
            ("one_hot", f"would add {cardinality} columns"),
            ("target", "needs a target column"),
        ),
    )
