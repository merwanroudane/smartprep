"""Turning EDA objects into chart specifications.

The selection rule is **diagnostic-driven**, not dtype-driven. A histogram is
chosen because the column is skewed and that matters for imputation, not
because the column happens to be a float. Every chart therefore carries a
``rationale``, and a chart nobody can justify does not get built.
"""

from __future__ import annotations

from typing import Any

from ..eda.associations import AssociationMatrix, MissingnessPattern
from ..eda.comparison import ProfileComparison
from ..eda.profile import ColumnProfile, DatasetProfile
from .spec import ChartSet, ChartSpec, Encoding, Fidelity, Mark

__all__ = [
    "distribution_chart",
    "box_chart",
    "ecdf_chart",
    "scatter_chart",
    "target_chart",
    "kpi_chart",
    "stage_chart",
    "category_chart",
    "missingness_chart",
    "association_heatmap",
    "timeline_chart",
    "health_chart",
    "before_after_chart",
    "issue_chart",
    "column_charts",
    "overview_charts",
]

#: Above this many points a scatter becomes an ink blob rather than a chart,
#: and the browser starts to struggle.
SCATTER_LIMIT = 3000


def distribution_chart(column: ColumnProfile) -> ChartSpec | None:
    """Histogram for a numeric column, annotated with what matters for cleaning."""
    if column.numeric is None or not column.numeric.histogram.counts:
        return None

    histogram = column.numeric.histogram
    edges, counts = histogram.edges, histogram.counts
    data = [
        {
            "bin_start": edges[i],
            "bin_end": edges[i + 1] if i + 1 < len(edges) else edges[i],
            "centre": (edges[i] + edges[min(i + 1, len(edges) - 1)]) / 2,
            "count": counts[i],
        }
        for i in range(len(counts))
    ]

    summary = column.numeric
    reasons = []
    if abs(summary.skew) > 1:
        reasons.append(f"skew {summary.skew:+.2f}, so the mean is not the centre")
    if summary.outliers_iqr:
        reasons.append(f"{summary.outliers_iqr} values outside the IQR fences")
    if summary.zeros > summary.count * 0.3:
        reasons.append(f"{summary.zeros} zeros -- possibly zero-inflated")

    rules = [("x", summary.median, "median")]
    if summary.outliers_iqr:
        rules += [
            ("x", summary.q1 - 1.5 * summary.iqr, "lower fence"),
            ("x", summary.q3 + 1.5 * summary.iqr, "upper fence"),
        ]

    return ChartSpec(
        mark=Mark.HISTOGRAM,
        data=data,
        x=Encoding("centre", "quantitative", column.name),
        y=Encoding("count", "quantitative", "rows"),
        title=f"Distribution of {column.name}",
        x_label=column.name,
        y_label="rows",
        rationale="; ".join(reasons) or "shape of the column, for choosing a treatment",
        fidelity=Fidelity.BINNED,
        fidelity_note=f"{len(counts)} bins over {summary.count} values",
        rules=rules,
    )


def category_chart(column: ColumnProfile, *, top: int = 15) -> ChartSpec | None:
    """Ordered frequency bars, which is how a rare level becomes visible."""
    if column.categorical is None or not column.categorical.top:
        return None

    summary = column.categorical
    counts = dict(summary.top)
    if summary.is_ordered:
        # Declared order, not frequency. Sorting an ordinal column by count
        # destroys the one thing that distinguishes it from a nominal one, and
        # the resulting chart looks entirely reasonable while saying something
        # the data does not.
        levels = [level for level in summary.ordered_levels if level in counts][:top]
    else:
        # Frequency, because a rare level is what a reader needs to see and it
        # is invisible in alphabetical order.
        levels = [value for value, _ in summary.top[:top]]
    data = [
        {"category": value, "count": counts.get(value, 0), "rare": value in summary.rare}
        for value in levels
    ]

    reasons = []
    if summary.imbalance > 0.8:
        reasons.append(f"one level holds {summary.imbalance:.0%} of rows")
    if summary.rare:
        reasons.append(f"{len(summary.rare)} levels under 1% of rows")
    if summary.distinct > 30:
        reasons.append(f"{summary.distinct} levels -- one-hot would be costly")

    return ChartSpec(
        mark=Mark.HORIZONTAL_BAR,
        data=data,
        x=Encoding("count", "quantitative", "rows"),
        y=Encoding("category", "nominal", column.name),
        color=Encoding("rare", "nominal", "rare level"),
        title=f"{column.name} by frequency",
        x_label="rows",
        y_label=column.name,
        rationale="; ".join(reasons) or "level balance, for encoding decisions",
        fidelity=Fidelity.FULL if summary.distinct <= top else Fidelity.AGGREGATED,
        fidelity_note=(
            "" if summary.distinct <= top else f"top {top} of {summary.distinct} levels"
        ),
    )


def text_length_chart(column: ColumnProfile) -> ChartSpec | None:
    """How long the values are.

    Free text is described by its shape before its content. A bimodal length
    distribution usually means two kinds of record share one column, which no
    frequency count of the values themselves would show.
    """
    if column.text is None:
        return None
    histogram = column.text.length_histogram
    if not histogram.counts:
        return None

    data = [
        {"bin_start": lo, "bin_end": hi, "centre": (lo + hi) / 2, "count": count}
        for lo, hi, count in zip(
            histogram.edges[:-1], histogram.edges[1:], histogram.counts, strict=False
        )
    ]
    notes = []
    if column.text.empty_strings:
        notes.append(f"{column.text.empty_strings:,} empty strings")
    if column.text.whitespace_only:
        notes.append(f"{column.text.whitespace_only:,} whitespace only")
    if column.text.non_ascii:
        notes.append(f"{column.text.non_ascii:,} with non-ASCII characters")

    return ChartSpec(
        mark=Mark.HISTOGRAM,
        data=data,
        x=Encoding("centre", "quantitative"),
        y=Encoding("count", "quantitative"),
        title=f"Value length in {column.name}",
        x_label="characters",
        y_label="rows",
        rationale=(
            "Two lengths where one was expected usually means two kinds of "
            "record share a column." + ("  " + "; ".join(notes) if notes else "")
        ),
    )


def missingness_chart(pattern: MissingnessPattern) -> ChartSpec | None:
    """Missingness by column, ordered -- the first question about any dataset."""
    affected = {k: v for k, v in pattern.by_column.items() if v}
    if not affected:
        return None

    data = [
        {"column": name, "missing": count}
        for name, count in sorted(affected.items(), key=lambda kv: -kv[1])
    ]
    reason = "which columns are incomplete, and by how much"
    if pattern.co_missing:
        left, right, score = pattern.co_missing[0]
        reason += (
            f"; {left} and {right} go missing together ({score:.0%} overlap), "
            "which usually means one shared upstream cause"
        )

    return ChartSpec(
        mark=Mark.HORIZONTAL_BAR,
        data=data,
        x=Encoding("missing", "quantitative", "missing rows"),
        y=Encoding("column", "nominal", "column"),
        title="Missing values by column",
        x_label="missing rows",
        y_label="",
        rationale=reason,
    )


def association_heatmap(matrix: AssociationMatrix, *, minimum: float = 0.0) -> ChartSpec | None:
    """Mixed-type association matrix.

    Includes categorical columns, which a Pearson-only matrix silently drops --
    leaving the reader to conclude they carry no signal.
    """
    if not matrix.pairs:
        return None

    data: list[dict[str, Any]] = []
    for pair in matrix.pairs:
        if abs(pair.value) < minimum:
            continue
        for left, right in ((pair.left, pair.right), (pair.right, pair.left)):
            data.append(
                {
                    "left": left,
                    "right": right,
                    "value": round(pair.value, 4),
                    "measure": pair.measure,
                }
            )
    for column in matrix.columns:
        data.append({"left": column, "right": column, "value": 1.0, "measure": "self"})

    measures = sorted({p.measure for p in matrix.pairs})
    return ChartSpec(
        mark=Mark.MATRIX,
        data=data,
        x=Encoding("left", "nominal"),
        y=Encoding("right", "nominal"),
        color=Encoding("value", "quantitative", "association"),
        title="Association matrix",
        rationale=(
            f"measures used: {', '.join(measures)}. These are not interchangeable -- "
            "Spearman is signed, Cramer's V and the correlation ratio are unsigned "
            "strengths on [0, 1]"
        ),
        height=max(320, 22 * len(matrix.columns)),
    )


def timeline_chart(column: ColumnProfile) -> ChartSpec | None:
    """Records over time -- where gaps and irregular coverage become obvious."""
    if column.datetime is None or not column.datetime.by_period:
        return None

    summary = column.datetime
    data = [{"period": period, "count": count} for period, count in summary.by_period]
    reasons = [f"span {summary.span_days:.0f} days"]
    if summary.inferred_frequency:
        reasons.append(f"inferred {summary.inferred_frequency}")
    if summary.gaps:
        reasons.append(f"{summary.gaps} gaps well above the typical interval")
    if summary.duplicate_timestamps:
        reasons.append(f"{summary.duplicate_timestamps} duplicate timestamps")

    return ChartSpec(
        mark=Mark.BAR,
        data=data,
        x=Encoding("period", "temporal", column.name),
        y=Encoding("count", "quantitative", "rows"),
        title=f"{column.name} over time",
        x_label="period",
        y_label="rows",
        rationale="; ".join(reasons),
        fidelity=Fidelity.AGGREGATED,
        fidelity_note="counts per month",
    )


def health_chart(before: Any, after: Any = None) -> ChartSpec:
    """Health by dimension, so an improvement can be located rather than trusted."""
    data: list[dict[str, Any]] = []
    for name, dimension in sorted(before.dimensions.items()):
        data.append({"dimension": name, "score": round(dimension.score, 1), "stage": "before"})
    if after is not None:
        for name, dimension in sorted(after.dimensions.items()):
            data.append({"dimension": name, "score": round(dimension.score, 1), "stage": "after"})

    return ChartSpec(
        mark=Mark.HORIZONTAL_BAR,
        data=data,
        x=Encoding("score", "quantitative", "score"),
        y=Encoding("dimension", "nominal", "dimension"),
        color=Encoding("stage", "nominal", "stage") if after is not None else None,
        title="Data health by dimension",
        x_label="score (0-100)",
        y_label="",
        rationale=(
            "one overall number hides which kind of wrongness moved; the "
            "dimensions are scored independently"
        ),
        rules=[("x", 100.0, "")],
    )


def before_after_chart(comparison: ProfileComparison) -> ChartSpec | None:
    """Which columns changed, and by how much -- the distortion, not the win."""
    rows: list[dict[str, Any]] = []
    for column in comparison.columns:
        if column.status != "changed":
            continue
        for metric in ("mean", "std", "missing"):
            change = column.relative_change(metric)
            if change is not None and abs(change) > 0.001:
                rows.append(
                    {
                        "column": column.name,
                        "metric": metric,
                        "relative_change": round(change, 4),
                        "flagged": bool(column.flags),
                    }
                )
    if not rows:
        return None

    return ChartSpec(
        mark=Mark.HORIZONTAL_BAR,
        data=sorted(rows, key=lambda r: -abs(r["relative_change"]))[:25],
        x=Encoding("relative_change", "quantitative", "relative change"),
        y=Encoding("column", "nominal", "column"),
        color=Encoding("metric", "nominal", "metric"),
        title="What cleaning changed",
        x_label="relative change",
        y_label="",
        rationale=(
            "a repair that improves completeness can still move the mean and "
            "shrink the variance; both belong in the same picture"
        ),
        rules=[("x", 0.0, "no change")],
    )


def issue_chart(issues: list[Any]) -> ChartSpec | None:
    """Findings by decision class -- what is automatic and what needs a person."""
    if not issues:
        return None

    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.repair_class.name] = counts.get(issue.repair_class.name, 0) + 1

    order = [
        "SAFE_AUTO_FIX",
        "AUTO_FIX_WITH_LOG",
        "REVIEW_RECOMMENDED",
        "USER_CONFIRMATION_REQUIRED",
        "DOMAIN_RULE_REQUIRED",
        "AMBIGUOUS",
        "DO_NOT_TOUCH",
    ]
    data = [
        {
            "repair_class": name,
            "count": counts[name],
            "autonomous": name.startswith(("SAFE", "AUTO")),
        }
        for name in order
        if name in counts
    ]

    # Counted from the source dict rather than the rendered rows, whose values
    # are a heterogeneous mapping.
    autonomous = sum(n for name, n in counts.items() if name.startswith(("SAFE", "AUTO")))
    return ChartSpec(
        mark=Mark.HORIZONTAL_BAR,
        data=data,
        x=Encoding("count", "quantitative", "findings"),
        y=Encoding("repair_class", "nominal", "decision class"),
        color=Encoding("autonomous", "nominal", "automatic"),
        title="Findings by decision class",
        x_label="findings",
        y_label="",
        rationale=(
            f"{autonomous} of {len(issues)} can be repaired without asking; the "
            "rest need a decision, and the class says whose"
        ),
    )


def column_charts(column: ColumnProfile) -> ChartSet:
    """Every chart that applies to one column.

    Driven by :mod:`smartprep.eda.typemap` rather than by a chain of
    ``elif``. The chain always ends in an ``else``, and the ``else`` is where
    an ordinal column gets drawn out of order and a column of dictionaries
    gets a category count -- both of which look entirely reasonable and say
    something the data does not.

    A type with no honest chart gets none. An empty panel is better than a
    confident wrong one.
    """
    from ..eda.typemap import support_for

    support = support_for(column.kind)
    charts = ChartSet(title=column.name, description=support.why)
    for name in support.charts:
        builder = _BUILDERS.get(name)
        if builder is not None:
            charts.add(builder(column))
    return charts


#: The single-column builders the type map may name. A chart declared in the
#: map with no builder here would silently never appear, so a test asserts the
#: two agree.
_BUILDERS: dict[str, Any] = {
    "distribution_chart": distribution_chart,
    "ecdf_chart": lambda c: ecdf_chart(c),
    "box_chart": lambda c: box_chart(c),
    "category_chart": category_chart,
    "timeline_chart": timeline_chart,
    "text_length_chart": text_length_chart,
}


def overview_charts(
    dataset_profile: DatasetProfile,
    matrix: AssociationMatrix | None = None,
    pattern: MissingnessPattern | None = None,
    *,
    max_columns: int = 12,
) -> ChartSet:
    """The charts worth seeing first, in the order worth seeing them."""
    charts = ChartSet(
        title="Overview",
        description=f"{dataset_profile.rows:,} rows x {dataset_profile.columns} columns",
    )
    if pattern is not None:
        charts.add(missingness_chart(pattern))
    if matrix is not None:
        charts.add(association_heatmap(matrix))

    # Most-informative columns first: the ones actually carrying variation.
    ranked = sorted(
        (
            column
            for column in dataset_profile.columns_profiled.values()
            if not column.is_constant and not column.is_identifier_like
        ),
        key=lambda column: -column.distinct,
    )
    for column in ranked[:max_columns]:
        for chart in column_charts(column):
            charts.add(chart)
    return charts


def box_chart(*columns: ColumnProfile) -> ChartSpec | None:
    """Five-number summaries side by side.

    A histogram shows one column's shape; a box plot compares several on one
    scale. Useful precisely when deciding whether columns need the same
    treatment.
    """
    rows = []
    for column in columns:
        summary = column.numeric
        if summary is None or summary.count == 0:
            continue
        fence_low = summary.q1 - 1.5 * summary.iqr
        fence_high = summary.q3 + 1.5 * summary.iqr
        # The whiskers stop at the fences, not at the extremes -- otherwise the
        # box collapses to a sliver next to one distant value.
        rows.append(
            {
                "label": column.name,
                "min": max(summary.minimum, fence_low),
                "q1": summary.q1,
                "median": summary.median,
                "q3": summary.q3,
                "max": min(summary.maximum, fence_high),
                "outliers": [v for v in summary.ecdf_x if v < fence_low or v > fence_high][:40],
            }
        )
    if not rows:
        return None

    flagged = sum(1 for r in rows if r["outliers"])
    return ChartSpec(
        mark=Mark.BOX,
        data=rows,
        x=Encoding("value", "quantitative", "value"),
        y=Encoding("label", "nominal", "column"),
        title="Spread and outliers",
        x_label="value",
        rationale=(
            f"{flagged} of {len(rows)} columns have values beyond the IQR fences; "
            "whiskers stop at the fences so one extreme cannot flatten the box"
        ),
        fidelity=Fidelity.AGGREGATED,
        fidelity_note="five-number summary per column",
        height=max(220, 46 * len(rows) + 90),
    )


def ecdf_chart(column: ColumnProfile) -> ChartSpec | None:
    """The empirical distribution function.

    Reads quantiles directly and, unlike a histogram, has no bin width to
    choose -- so it cannot be made to tell a different story by rebinning.
    """
    summary = column.numeric
    if summary is None or not summary.ecdf_x:
        return None

    data = [
        {"value": x, "proportion": y} for x, y in zip(summary.ecdf_x, summary.ecdf_y, strict=False)
    ]
    return ChartSpec(
        mark=Mark.STEP,
        data=data,
        x=Encoding("value", "quantitative", column.name),
        y=Encoding("proportion", "quantitative", "cumulative share"),
        title=f"Cumulative distribution of {column.name}",
        x_label=column.name,
        y_label="cumulative share",
        rationale=(
            "quantiles read directly, with no bin width to choose -- a histogram "
            "can be made to look different by rebinning, this cannot"
        ),
        fidelity=Fidelity.AGGREGATED if len(data) < summary.count else Fidelity.FULL,
        fidelity_note=f"{len(data)} points from {summary.count} values",
        rules=[("y", 0.5, "median")],
    )


def scatter_chart(
    frame: Any,
    x: str,
    y: str,
    *,
    limit: int = SCATTER_LIMIT,
    reason: str = "",
) -> ChartSpec | None:
    """Two numeric columns against each other, sampled if large.

    Beyond a few thousand points a scatter becomes an ink blob that hides its
    own density, so it samples and says so rather than drawing a lie.
    """
    from ..detectors.base import to_number

    if x not in frame.columns or y not in frame.columns:
        return None

    pair = frame[[x, y]].copy()
    pair[x] = pair[x].map(to_number)
    pair[y] = pair[y].map(to_number)
    pair = pair.dropna()
    if len(pair) < 3:
        return None

    total = len(pair)
    fidelity, note = Fidelity.FULL, ""
    if total > limit:
        # Deterministic sample: the same data always yields the same picture.
        pair = pair.sample(limit, random_state=0)
        fidelity = Fidelity.RANDOM_SAMPLE
        note = f"{limit:,} of {total:,} points"

    return ChartSpec(
        mark=Mark.SCATTER,
        data=[{"x": float(a), "y": float(b)} for a, b in zip(pair[x], pair[y], strict=True)],
        x=Encoding("x", "quantitative", x),
        y=Encoding("y", "quantitative", y),
        title=f"{y} against {x}",
        x_label=x,
        y_label=y,
        rationale=reason or f"relationship between {x} and {y}",
        fidelity=fidelity,
        fidelity_note=note,
    )


def target_chart(frame: Any, column: str, target: str, *, max_levels: int = 12) -> ChartSpec | None:
    """How the target behaves across a feature's levels.

    The question that decides whether a feature is worth keeping, and the one
    a plain frequency chart cannot answer.
    """
    from ..detectors.base import to_number

    if column not in frame.columns or target not in frame.columns:
        return None

    values = frame[target].map(to_number)
    pair = frame[[column]].assign(_t=values).dropna()
    if pair.empty or pair[column].nunique() > max_levels:
        return None

    grouped = pair.groupby(pair[column].astype(str))["_t"]
    data: list[dict[str, Any]] = [
        {"level": str(level), "mean_target": round(float(group.mean()), 5), "n": len(group)}
        for level, group in grouped
    ]
    if len(data) < 2:
        return None

    means = [float(r["mean_target"]) for r in data]
    spread = max(means) - min(means)
    overall = float(values.mean())
    return ChartSpec(
        mark=Mark.HORIZONTAL_BAR,
        data=sorted(data, key=lambda r: -float(r["mean_target"])),
        x=Encoding("mean_target", "quantitative", f"mean {target}"),
        y=Encoding("level", "nominal", column),
        title=f"{target} by {column}",
        x_label=f"mean {target}",
        rationale=(
            f"levels separate the target by {spread:.4g}; a feature whose levels "
            "do not separate it carries nothing for a model"
        ),
        fidelity=Fidelity.AGGREGATED,
        fidelity_note="group means",
        rules=[("x", overall, "overall mean")],
    )


def kpi_chart(items: list[tuple[str, Any]], *, title: str = "Summary") -> ChartSpec:
    """Headline figures as a chart, so a tile and a plot share one vocabulary."""
    return ChartSpec(
        mark=Mark.TEXT,
        data=[{"value": str(value), "label": label} for label, value in items],
        title=title,
        rationale="headline figures",
        height=44 * len(items) + 70,
        width=280,
    )


def stage_chart(stages: list[tuple[str, float]], *, title: str, reason: str) -> ChartSpec:
    """A measure across cleaning stages, with the stage as the animation axis.

    This is the one place animation earns its keep: the frames are ordered
    steps of a real process, so motion carries the meaning rather than
    decorating it.
    """
    return ChartSpec(
        mark=Mark.AREA,
        data=[{"stage": name, "value": round(value, 4)} for name, value in stages],
        x=Encoding("stage", "ordinal", "stage"),
        y=Encoding("value", "quantitative", "value"),
        title=title,
        x_label="stage",
        y_label="value",
        rationale=reason,
        animation_field="stage",
        fidelity=Fidelity.AGGREGATED,
        fidelity_note="one value per cleaning stage",
    )
