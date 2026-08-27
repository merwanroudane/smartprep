"""The EDA model: profiling as data, not as a rendered page.

Every number a report or a chart or the Studio needs is computed here and
returned as a plain, serialisable object. Nothing in this module knows what a
plot looks like.

That ordering matters. A profiling layer that only exists inside an HTML
template cannot be tested, diffed, compared across versions, or driven from a
notebook -- and the interface ends up dictating the statistics rather than the
other way round.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

from ..detectors.base import is_missing, physical_type, to_number

__all__ = [
    "ColumnKind",
    "Histogram",
    "NumericSummary",
    "CategoricalSummary",
    "DatetimeSummary",
    "TextSummary",
    "ColumnProfile",
    "DatasetProfile",
    "profile",
]


class ColumnKind(Enum):
    """How a column should be summarised.

    Coarser than semantic type on purpose: this decides which statistics apply,
    not what the column means.
    """

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    #: Categories with a declared order. Distinct from CATEGORICAL because the
    #: order changes what is legitimate: a median exists for ordinal levels and
    #: does not for nominal ones, and an ordinal encoding is faithful here and
    #: an invention anywhere else.
    ORDINAL = "ordinal"
    DATETIME = "datetime"
    TEXT = "text"
    BOOLEAN = "boolean"
    CONSTANT = "constant"
    EMPTY = "empty"
    #: A column this library has no statistics for -- complex numbers, nested
    #: objects, anything it cannot summarise honestly. Named rather than
    #: silently filed under "categorical", because a reader who sees a
    #: category count for a column of dictionaries will believe it.
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class Histogram:
    """Binned counts, ready to plot but independent of any plotting library."""

    edges: tuple[float, ...]
    counts: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"edges": list(self.edges), "counts": list(self.counts)}

    @classmethod
    def of(cls, values: np.ndarray, bins: int = 20) -> Histogram:
        if len(values) == 0:
            return cls((), ())
        # A constant column has no range to bin; one bin is the honest answer.
        if float(values.min()) == float(values.max()):
            centre = float(values.min())
            return cls((centre, centre), (len(values),))
        counts, edges = np.histogram(values, bins=min(bins, max(len(values) // 2, 1)))
        return cls(tuple(float(e) for e in edges), tuple(int(c) for c in counts))


@dataclass(frozen=True)
class NumericSummary:
    count: int
    mean: float
    std: float
    minimum: float
    q1: float
    median: float
    q3: float
    maximum: float
    skew: float
    kurtosis: float
    zeros: int
    negatives: int
    infinities: int
    outliers_iqr: int
    histogram: Histogram
    ecdf_x: tuple[float, ...] = ()
    ecdf_y: tuple[float, ...] = ()

    @property
    def iqr(self) -> float:
        return self.q3 - self.q1

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "mean": _clean(self.mean),
            "std": _clean(self.std),
            "min": _clean(self.minimum),
            "q1": _clean(self.q1),
            "median": _clean(self.median),
            "q3": _clean(self.q3),
            "max": _clean(self.maximum),
            "iqr": _clean(self.iqr),
            "skew": _clean(self.skew),
            "kurtosis": _clean(self.kurtosis),
            "zeros": self.zeros,
            "negatives": self.negatives,
            "infinities": self.infinities,
            "outliers_iqr": self.outliers_iqr,
            "histogram": self.histogram.to_dict(),
        }


@dataclass(frozen=True)
class CategoricalSummary:
    distinct: int
    top: tuple[tuple[str, int], ...]
    rare: tuple[str, ...]
    imbalance: float
    entropy: float
    #: The declared order, when the column has one; empty for nominal
    #: categories. Kept because the caller already knew it -- discarding an
    #: ordering the DataFrame states throws away information the user supplied,
    #: without saying so.
    ordered_levels: tuple[str, ...] = ()

    @property
    def is_ordered(self) -> bool:
        return bool(self.ordered_levels)

    def to_dict(self) -> dict[str, Any]:
        return {
            "distinct": self.distinct,
            "top": [{"value": v, "count": c} for v, c in self.top],
            "rare": list(self.rare),
            "imbalance": _clean(self.imbalance),
            "entropy": _clean(self.entropy),
            "ordered": self.is_ordered,
            "ordered_levels": list(self.ordered_levels),
        }


@dataclass(frozen=True)
class DatetimeSummary:
    minimum: str
    maximum: str
    span_days: float
    inferred_frequency: str | None
    duplicate_timestamps: int
    gaps: int
    by_period: tuple[tuple[str, int], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "min": self.minimum,
            "max": self.maximum,
            "span_days": _clean(self.span_days),
            "inferred_frequency": self.inferred_frequency,
            "duplicate_timestamps": self.duplicate_timestamps,
            "gaps": self.gaps,
            "by_period": [{"period": p, "count": c} for p, c in self.by_period],
        }


@dataclass(frozen=True)
class TextSummary:
    min_length: int
    max_length: int
    mean_length: float
    empty_strings: int
    whitespace_only: int
    non_ascii: int
    length_histogram: Histogram

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_length": self.min_length,
            "max_length": self.max_length,
            "mean_length": _clean(self.mean_length),
            "empty_strings": self.empty_strings,
            "whitespace_only": self.whitespace_only,
            "non_ascii": self.non_ascii,
            "length_histogram": self.length_histogram.to_dict(),
        }


@dataclass
class ColumnProfile:
    """Everything known about one column, before anyone decides to draw it."""

    name: str
    kind: ColumnKind
    dtype: str
    count: int
    missing: int
    distinct: int
    memory_bytes: int
    physical_types: dict[str, int] = field(default_factory=dict)
    #: Why this column was not summarised, when it was not. Empty otherwise.
    unsupported_reason: str = ""
    numeric: NumericSummary | None = None
    categorical: CategoricalSummary | None = None
    datetime: DatetimeSummary | None = None
    text: TextSummary | None = None

    @property
    def missing_rate(self) -> float:
        return self.missing / self.count if self.count else 0.0

    @property
    def distinct_rate(self) -> float:
        present = self.count - self.missing
        return self.distinct / present if present else 0.0

    @property
    def is_constant(self) -> bool:
        return self.distinct <= 1

    @property
    def is_identifier_like(self) -> bool:
        """Nearly every value distinct -- a key rather than a measurement."""
        return self.distinct_rate > 0.95 and self.count - self.missing > 10

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind.value,
            "dtype": self.dtype,
            "count": self.count,
            "missing": self.missing,
            "missing_rate": round(self.missing_rate, 4),
            "distinct": self.distinct,
            "distinct_rate": round(self.distinct_rate, 4),
            "memory_bytes": self.memory_bytes,
            "physical_types": dict(self.physical_types),
            "flags": {
                "constant": self.is_constant,
                "identifier_like": self.is_identifier_like,
            },
        }
        for key, summary in (
            ("numeric", self.numeric),
            ("categorical", self.categorical),
            ("datetime", self.datetime),
            ("text", self.text),
        ):
            if summary is not None:
                payload[key] = summary.to_dict()
        return payload


@dataclass
class DatasetProfile:
    """A complete profile, serialisable and comparable."""

    rows: int
    columns: int
    memory_bytes: int
    duplicate_rows: int
    columns_profiled: dict[str, ColumnProfile] = field(default_factory=dict)
    missing_cells: int = 0

    @property
    def missing_rate(self) -> float:
        total = self.rows * self.columns
        return self.missing_cells / total if total else 0.0

    def by_kind(self, kind: ColumnKind) -> list[ColumnProfile]:
        return [c for c in self.columns_profiled.values() if c.kind is kind]

    def get(self, column: str) -> ColumnProfile:
        try:
            return self.columns_profiled[column]
        except KeyError:
            raise KeyError(
                f"no profile for {column!r}. Profiled: {sorted(self.columns_profiled)}"
            ) from None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "rows": self.rows,
            "columns": self.columns,
            "memory_bytes": self.memory_bytes,
            "duplicate_rows": self.duplicate_rows,
            "missing_cells": self.missing_cells,
            "missing_rate": round(self.missing_rate, 4),
            "columns_profiled": {k: v.to_dict() for k, v in self.columns_profiled.items()},
        }

    def summary(self) -> str:
        lines = [
            f"{self.rows:,} rows x {self.columns} columns, {self.memory_bytes / 1024:.1f} KB",
            f"{self.missing_cells:,} missing cells ({self.missing_rate:.2%}), "
            f"{self.duplicate_rows} duplicate rows",
            "",
            f"{'column':22s} {'kind':12s} {'missing':>8s} {'distinct':>9s}",
        ]
        for column in self.columns_profiled.values():
            lines.append(
                f"{column.name:22s} {column.kind.value:12s} "
                f"{column.missing_rate:7.1%} {column.distinct:9d}"
            )
        return "\n".join(lines)


def _clean(value: float) -> float | None:
    """JSON has no NaN or Infinity; null is the honest representation."""
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return None
    return round(float(value), 6)


def _declared_order(series: pd.Series) -> tuple[str, ...]:
    """The order a pandas ordered categorical declares, if any."""
    dtype = getattr(series, "dtype", None)
    if isinstance(dtype, pd.CategoricalDtype) and dtype.ordered:
        return tuple(str(level) for level in dtype.categories)
    return ()


#: Cell types nothing here can summarise. Recorded on the profile so the
#: column is visibly skipped instead of quietly mis-summarised.
_UNSUMMARISABLE = (complex, np.complexfloating, list, dict, set, tuple, bytes, bytearray)


def _unsupported_reason(series: pd.Series, values: list[Any]) -> str:
    """Why a column cannot be summarised, or ``""`` when it can."""
    if isinstance(series.dtype, pd.CategoricalDtype):
        return ""
    sample = values[:50]
    if sample and all(isinstance(v, _UNSUMMARISABLE) for v in sample):
        kind = type(sample[0]).__name__
        return f"every value is a {kind}; no summary statistic applies to it"
    return ""


def _duplicate_rows(frame: pd.DataFrame) -> int:
    """Duplicate rows, or 0 when the frame holds values that cannot be hashed.

    A column of lists or dicts makes ``DataFrame.duplicated`` raise, and a
    profiler that dies on a JSON column is a profiler nobody can point at real
    data. Comparing such columns as text would be a different answer wearing
    the same name, so the honest result is to skip the check.
    """
    if not len(frame):
        return 0
    try:
        return int(frame.duplicated().sum())
    except TypeError:
        comparable = [
            c
            for c in frame.columns
            if not any(isinstance(v, (list, dict, set)) for v in frame[c].head(50))
        ]
        if not comparable:
            return 0
        try:
            return int(frame[comparable].duplicated().sum())
        except TypeError:  # pragma: no cover - deeply exotic contents
            return 0


def _classify(series: pd.Series, values: list[Any], numeric: pd.Series) -> ColumnKind:
    if not values:
        return ColumnKind.EMPTY
    if _unsupported_reason(series, values):
        return ColumnKind.UNSUPPORTED
    if isinstance(series.dtype, pd.PeriodDtype):
        # A period is a span of time, so the datetime summary is the one that
        # means something -- range, span, and gaps.
        return ColumnKind.DATETIME
    distinct = len({str(v) for v in values})
    if distinct <= 1:
        return ColumnKind.CONSTANT
    if _declared_order(series):
        # The caller said these levels are ordered. Believing them costs
        # nothing and doubting them discards the only evidence available:
        # nothing in the values themselves can establish that low < mid < high.
        return ColumnKind.ORDINAL
    if all(isinstance(v, (bool, np.bool_)) for v in values):
        return ColumnKind.BOOLEAN

    forms = Counter(physical_type(v) for v in values)
    temporal = forms["datetime"] + forms["date"]
    # A mostly-datetime column is still a datetime column. Requiring purity
    # would push every real, partly-unparsed date column into the text branch
    # and lose its range, frequency and gap analysis -- exactly when they are
    # most worth having.
    if temporal >= 0.5 * len(values):
        return ColumnKind.DATETIME
    if numeric.notna().sum() >= 0.9 * len(values):
        return ColumnKind.NUMERIC
    # Few distinct values relative to length reads as categorical; many distinct
    # long strings read as free text.
    if distinct <= max(20, 0.05 * len(values)):
        return ColumnKind.CATEGORICAL
    return ColumnKind.TEXT


def _numeric_summary(values: np.ndarray) -> NumericSummary:
    finite = values[np.isfinite(values)]
    series = pd.Series(finite)
    q1 = float(series.quantile(0.25)) if len(finite) else float("nan")
    q3 = float(series.quantile(0.75)) if len(finite) else float("nan")
    iqr = q3 - q1
    outliers = (
        int(((finite < q1 - 1.5 * iqr) | (finite > q3 + 1.5 * iqr)).sum())
        if len(finite) and iqr > 0
        else 0
    )
    ordered = np.sort(finite)
    # Cap the stored ECDF so a million-row column does not produce a
    # million-point payload nobody can render.
    step = max(1, len(ordered) // 200)
    sampled = ordered[::step]

    return NumericSummary(
        count=len(finite),
        mean=float(series.mean()) if len(finite) else float("nan"),
        std=float(series.std(ddof=0)) if len(finite) else float("nan"),
        minimum=float(finite.min()) if len(finite) else float("nan"),
        q1=q1,
        median=float(series.median()) if len(finite) else float("nan"),
        q3=q3,
        maximum=float(finite.max()) if len(finite) else float("nan"),
        skew=float(series.skew()) if len(finite) > 2 else 0.0,
        kurtosis=float(series.kurtosis()) if len(finite) > 3 else 0.0,
        zeros=int((finite == 0).sum()),
        negatives=int((finite < 0).sum()),
        infinities=int(len(values) - len(finite)),
        outliers_iqr=outliers,
        histogram=Histogram.of(finite),
        ecdf_x=tuple(float(v) for v in sampled),
        ecdf_y=tuple(float((i * step + 1) / len(ordered)) for i in range(len(sampled))),
    )


def _categorical_summary(
    values: list[Any], top_n: int = 20, ordered_levels: tuple[str, ...] = ()
) -> CategoricalSummary:
    counts = Counter(str(v) for v in values)
    total = sum(counts.values())
    ordered = counts.most_common()
    probabilities = np.array([c / total for _, c in ordered])
    entropy = float(-(probabilities * np.log2(probabilities)).sum())
    return CategoricalSummary(
        distinct=len(counts),
        top=tuple((v, c) for v, c in ordered[:top_n]),
        # A level appearing in under 1% of rows will be sparse in any model
        # trained on it, and unseen in most cross-validation folds.
        rare=tuple(v for v, c in ordered if c / total < 0.01),
        imbalance=float(ordered[0][1] / total) if ordered else 0.0,
        entropy=entropy,
        ordered_levels=ordered_levels,
    )


def _datetime_summary(values: list[Any]) -> DatetimeSummary:
    stamps = pd.Series(pd.to_datetime(pd.Series(values), errors="coerce")).dropna()
    if stamps.empty:
        return DatetimeSummary("", "", 0.0, None, 0, 0)

    ordered = stamps.sort_values()
    deltas = ordered.diff().dropna()
    frequency: str | None = None
    gaps = 0
    if len(deltas) > 2:
        typical = deltas.median()
        if typical.total_seconds() > 0:
            frequency = _describe_frequency(typical)
            # A gap is an interval several times the typical spacing -- a
            # missing period rather than ordinary irregularity.
            gaps = int((deltas > typical * 3).sum())

    # A tz-aware column has to lose its zone to become a period, and pandas
    # does that silently. Converting to UTC first makes the choice explicit:
    # every timestamp is bucketed against the same clock, rather than against
    # whatever offset each one happened to carry.
    grouping = ordered.dt.tz_convert("UTC").dt.tz_localize(None) if ordered.dt.tz else ordered
    by_period = grouping.dt.to_period("M").astype(str).value_counts().sort_index().head(60)
    return DatetimeSummary(
        minimum=str(ordered.iloc[0]),
        maximum=str(ordered.iloc[-1]),
        span_days=float((ordered.iloc[-1] - ordered.iloc[0]).days),
        inferred_frequency=frequency,
        duplicate_timestamps=int(ordered.duplicated().sum()),
        gaps=gaps,
        by_period=tuple((str(k), int(v)) for k, v in by_period.items()),
    )


def _describe_frequency(delta: pd.Timedelta) -> str:
    seconds = delta.total_seconds()
    for threshold, label in (
        (1, "sub-second"),
        (60, "secondly"),
        (3600, "minutely"),
        (86400, "hourly"),
        (86400 * 6.5, "daily"),
        (86400 * 27, "weekly"),
        (86400 * 300, "monthly"),
    ):
        if seconds < threshold:
            return label
    return "yearly"


def _text_summary(values: list[Any]) -> TextSummary:
    strings = [str(v) for v in values]
    lengths = np.array([len(s) for s in strings], dtype=float)
    return TextSummary(
        min_length=int(lengths.min()) if len(lengths) else 0,
        max_length=int(lengths.max()) if len(lengths) else 0,
        mean_length=float(lengths.mean()) if len(lengths) else 0.0,
        empty_strings=sum(1 for s in strings if s == ""),
        whitespace_only=sum(1 for s in strings if s and not s.strip()),
        non_ascii=sum(1 for s in strings if any(ord(c) > 127 for c in s)),
        length_histogram=Histogram.of(lengths),
    )


def profile(frame: pd.DataFrame, *, top_categories: int = 20) -> DatasetProfile:
    """Compute a full dataset profile. The frame is never modified."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError(f"profile() expects a DataFrame, got {type(frame).__name__}")

    result = DatasetProfile(
        rows=len(frame),
        columns=frame.shape[1],
        memory_bytes=int(frame.memory_usage(deep=True).sum()),
        duplicate_rows=_duplicate_rows(frame),
    )

    for name in frame.columns:
        series = frame[name]
        values = [v for v in series if not is_missing(v)]
        numeric = series.map(to_number)
        kind = _classify(series, values, numeric)

        column = ColumnProfile(
            name=str(name),
            kind=kind,
            dtype=str(series.dtype),
            count=len(series),
            missing=len(series) - len(values),
            distinct=len({str(v) for v in values}),
            memory_bytes=int(series.memory_usage(deep=True)),
            physical_types=dict(Counter(physical_type(v) for v in series)),
            unsupported_reason=_unsupported_reason(series, values),
        )
        result.missing_cells += column.missing

        if kind in (ColumnKind.NUMERIC, ColumnKind.BOOLEAN):
            column.numeric = _numeric_summary(numeric.dropna().to_numpy(dtype=float))
            if kind is ColumnKind.BOOLEAN:
                # Two values give a degenerate histogram, so the frequency
                # counts are what can actually be drawn. Attached here rather
                # than left absent, because the type map promises a chart and
                # a promise nothing delivers is the bug this project keeps
                # rediscovering.
                column.categorical = _categorical_summary(values, top_categories)
        elif kind is ColumnKind.DATETIME:
            column.datetime = _datetime_summary(values)
        elif kind in (ColumnKind.CATEGORICAL, ColumnKind.CONSTANT, ColumnKind.ORDINAL):
            column.categorical = _categorical_summary(
                values, top_categories, _declared_order(series)
            )
        elif kind is ColumnKind.TEXT:
            column.text = _text_summary(values)
            column.categorical = _categorical_summary(values, top_categories)

        result.columns_profiled[str(name)] = column

    return result
