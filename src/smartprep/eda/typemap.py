"""What each column type gets: which statistics apply, and which charts.

Every profiler makes this mapping. Most make it implicitly, scattered through
an ``if kind is NUMERIC`` here and an ``else: category_chart`` there — and the
``else`` is where the damage happens. It catches ordinal columns and draws
them out of order, catches free text and shows its top fifteen values as
though they were categories, and catches a column of dictionaries and reports
a category count for it that a reader will believe.

So the mapping is written down once, here, and both the analysis layer and the
chart layer read it. Three things follow:

* a type with no honest analysis gets **none**, with the reason stated, rather
  than falling through to whatever the last branch happened to be;
* every chart declared for a type must actually build for that type, which a
  test enforces — the same rule as encoding channels and marks;
* a reader can be shown the table, because it is a table.

``not_applicable`` matters as much as ``statistics``. A mean exists for
ordinal codes and means nothing; saying so where the decision is made is more
useful than a footnote nobody reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .profile import ColumnKind

__all__ = ["TypeSupport", "SUPPORT", "support_for", "support_table"]


@dataclass(frozen=True)
class TypeSupport:
    """What one column type supports, and what it deliberately does not."""

    kind: ColumnKind
    #: The summary object attached to the profile, or "" when none is.
    summary: str
    statistics: tuple[str, ...]
    charts: tuple[str, ...]
    why: str
    #: Statistics that are computable but not meaningful, and the reason.
    not_applicable: tuple[tuple[str, str], ...] = ()

    @property
    def is_analysed(self) -> bool:
        return bool(self.statistics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "summary": self.summary,
            "statistics": list(self.statistics),
            "charts": list(self.charts),
            "why": self.why,
            "not_applicable": [{"statistic": s, "reason": r} for s, r in self.not_applicable],
        }


_NUMERIC_STATS = (
    "count",
    "mean",
    "std",
    "min",
    "q1",
    "median",
    "q3",
    "max",
    "skew",
    "kurtosis",
    "zeros",
    "negatives",
    "infinities",
    "outliers_iqr",
    "histogram",
    "ecdf",
)

_CATEGORICAL_STATS = ("distinct", "top", "rare", "imbalance", "entropy")


#: The whole mapping. Every :class:`ColumnKind` appears exactly once.
SUPPORT: dict[ColumnKind, TypeSupport] = {
    ColumnKind.NUMERIC: TypeSupport(
        kind=ColumnKind.NUMERIC,
        summary="NumericSummary",
        statistics=_NUMERIC_STATS,
        charts=("distribution_chart", "ecdf_chart", "box_chart"),
        why=(
            "A measurement supports the full set: centre, spread, shape and "
            "tails. Three charts rather than one because they disagree "
            "usefully -- a histogram can be made to tell a different story by "
            "rebinning, an ECDF cannot, and a box plot answers about the "
            "fences without asking anyone to read a shape."
        ),
        not_applicable=(
            (
                "mode",
                "rarely meaningful on continuous values, where almost every value occurs once",
            ),
        ),
    ),
    ColumnKind.BOOLEAN: TypeSupport(
        kind=ColumnKind.BOOLEAN,
        summary="NumericSummary + CategoricalSummary",
        statistics=("count", "mean (the rate of true)", "distinct", "top", "imbalance"),
        charts=("category_chart",),
        why=(
            "Two levels, so the mean is the rate of true and the frequency "
            "bars are the picture. No histogram: binning a column with two "
            "values produces one bar and an empty axis."
        ),
        not_applicable=(
            ("histogram", "two values give degenerate bins"),
            ("std, skew, kurtosis", "defined, but they describe a shape with two points"),
            ("outliers", "a two-valued column has no tail to be outside of"),
        ),
    ),
    ColumnKind.ORDINAL: TypeSupport(
        kind=ColumnKind.ORDINAL,
        summary="CategoricalSummary",
        statistics=(*_CATEGORICAL_STATS, "declared order", "median level"),
        charts=("category_chart",),
        why=(
            "Ordered levels, drawn in the declared order rather than by "
            "frequency -- the ordering is the whole difference between this "
            "and a nominal column, and sorting by count destroys it. A median "
            "level is meaningful here and nowhere else in this table."
        ),
        not_applicable=(
            (
                "mean",
                "the codes are ranks, not quantities: the gap between low and "
                "mid is not the gap between mid and high",
            ),
        ),
    ),
    ColumnKind.CATEGORICAL: TypeSupport(
        kind=ColumnKind.CATEGORICAL,
        summary="CategoricalSummary",
        statistics=_CATEGORICAL_STATS,
        charts=("category_chart",),
        why=(
            "Frequency, imbalance and rarity. Sorted by count, because a rare "
            "level is what a reader needs to see and it is invisible in "
            "alphabetical order."
        ),
        not_applicable=(
            ("mean, median", "there is no order to take a middle of"),
            ("outliers", "a rare level is not an outlier; it is a rare level"),
        ),
    ),
    ColumnKind.TEXT: TypeSupport(
        kind=ColumnKind.TEXT,
        summary="TextSummary + CategoricalSummary",
        statistics=(
            "min_length",
            "max_length",
            "mean_length",
            "empty_strings",
            "whitespace_only",
            "non_ascii",
            "length_histogram",
            *_CATEGORICAL_STATS,
        ),
        charts=("text_length_chart", "category_chart"),
        why=(
            "Free text is described by its shape -- length, emptiness, "
            "encoding -- before its content. The frequency bars are still "
            "offered because a text column with a repeated value is usually a "
            "category nobody declared."
        ),
        not_applicable=(
            (
                "imbalance as a warning",
                "high imbalance in free text is ordinary, not a defect",
            ),
        ),
    ),
    ColumnKind.DATETIME: TypeSupport(
        kind=ColumnKind.DATETIME,
        summary="DatetimeSummary",
        statistics=("minimum", "maximum", "span_days", "frequency", "gaps", "by_period"),
        charts=("timeline_chart",),
        why=(
            "Range, inferred cadence and gaps. For the deeper checks -- "
            "duplicate timestamps, ordering, timezone consistency, stale runs "
            "-- see sp.timeseries()."
        ),
        not_applicable=(
            (
                "mean",
                "the average of two dates is a date, and almost never the one anybody wanted",
            ),
        ),
    ),
    ColumnKind.CONSTANT: TypeSupport(
        kind=ColumnKind.CONSTANT,
        summary="CategoricalSummary",
        statistics=("distinct", "the single value"),
        charts=(),
        why=(
            "One value. There is nothing to compare it with, so no chart is "
            "offered -- a single bar is a number wearing a costume."
        ),
        not_applicable=(("every dispersion statistic", "a constant has no spread"),),
    ),
    ColumnKind.EMPTY: TypeSupport(
        kind=ColumnKind.EMPTY,
        summary="",
        statistics=(),
        charts=(),
        why="Nothing present to describe. The emptiness is the finding.",
    ),
    ColumnKind.UNSUPPORTED: TypeSupport(
        kind=ColumnKind.UNSUPPORTED,
        summary="",
        statistics=(),
        charts=(),
        why=(
            "Complex numbers, nested objects, anything this library cannot "
            "summarise honestly. Named rather than filed under 'categorical', "
            "because a reader shown a category count for a column of "
            "dictionaries will believe it. The reason is on the profile as "
            "unsupported_reason."
        ),
    ),
}


def support_for(kind: ColumnKind) -> TypeSupport:
    """What this kind supports. Raises if a kind was added without an entry."""
    try:
        return SUPPORT[kind]
    except KeyError:  # pragma: no cover - the test suite prevents this
        raise KeyError(
            f"{kind} has no entry in the type map, so nothing knows which "
            "statistics or charts apply to it. Add one."
        ) from None


def support_table() -> str:
    """The mapping as Markdown, so documentation cannot drift from the code."""
    lines = [
        "| Type | Statistics | Charts | Not applicable |",
        "|---|---|---|---|",
    ]
    for support in SUPPORT.values():
        statistics = ", ".join(support.statistics) if support.statistics else "*none*"
        charts = (
            ", ".join(c.replace("_chart", "") for c in support.charts)
            if support.charts
            else "*none*"
        )
        excluded = (
            "; ".join(f"{s} — {r}" for s, r in support.not_applicable)
            if support.not_applicable
            else "—"
        )
        lines.append(f"| `{support.kind.value}` | {statistics} | {charts} | {excluded} |")
    return "\n".join(lines)
