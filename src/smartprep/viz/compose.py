"""The visual builder -- a reader's choices, turned into a ChartSpec.

``Field metadata -> Composition -> ChartSpec -> Renderer``

A drag-and-drop builder is usually where a charting library stops being
honest: the page grows its own idea of what the data means, and the chart the
reader assembles by hand no longer comes from the same numbers as the chart in
the report. Nothing here draws anything. It turns what a reader chose into a
specification, and the existing renderers realise it -- so a hand-built chart
and a generated one are the same kind of object and cannot disagree.

Two things this module refuses to do:

* **Draw a chart that cannot be read.** A nominal field with nine thousand
  levels does not become a bar chart; the composition is rejected with the
  reason, because a wall of unreadable bars is worse than an empty panel.
* **Recommend without explaining.** Every recommendation carries the sentence
  that justifies it. A recommendation a reader cannot argue with is one they
  cannot learn from either.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from ..core.identity import StableRowIndex
from ..core.state import FilterClause
from .spec import ChartSpec, Encoding, Fidelity, Mark

__all__ = [
    "Field",
    "Composition",
    "Recommendation",
    "fields_of",
    "compose",
    "recommend",
    "AGGREGATES",
]

#: How a measure is summarised within a group. ``count`` needs no field, which
#: is why it is the fallback when a reader has chosen only a category.
AGGREGATES = ("count", "mean", "median", "sum", "min", "max")

#: Above this, a categorical axis is a wall of labels rather than a chart.
_MAX_CATEGORIES = 40

#: Above this many marks, a chart stops being individually brushable.
#:
#: Two reasons, and they agree. Tabbing through twelve hundred focusable
#: points is not keyboard access, it is a keyboard trap. And a key on every
#: point is roughly fifty bytes of markup each, which is how a workspace meant
#: to be emailed turns into a multi-megabyte file. Selecting one point out of
#: a thousand was never the useful gesture; filtering to a region is, and that
#: is what the grid and the filter chips are for.
_MAX_BRUSHABLE_MARKS = 250


@dataclass(frozen=True)
class Field:
    """One column, described in the terms a chart cares about."""

    name: str
    kind: str  # quantitative | nominal | ordinal | temporal
    distinct: int = 0
    missing_rate: float = 0.0
    identifier_like: bool = False
    constant: bool = False

    @property
    def is_quantitative(self) -> bool:
        return self.kind == "quantitative"

    @property
    def is_categorical(self) -> bool:
        return self.kind in ("nominal", "ordinal")

    @property
    def is_temporal(self) -> bool:
        return self.kind == "temporal"

    @property
    def plottable(self) -> str | None:
        """Why this field should not be an axis, or ``None`` if it may be."""
        if self.constant:
            return "every value is the same, so there is nothing to compare"
        if self.identifier_like and self.is_categorical:
            # Only categoricals. A date column is nearly all-distinct because
            # that is what dates are, and a measurement can be too; neither is
            # evidence of a key.
            return "nearly every value is distinct -- this is a key, not a measurement"
        if self.missing_rate >= 1.0:
            return "the column is entirely missing"
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "distinct": self.distinct,
            "missing_rate": round(self.missing_rate, 4),
            "identifier_like": self.identifier_like,
            "constant": self.constant,
            "blocked": self.plottable,
        }


def fields_of(dataset_profile: Any) -> list[Field]:
    """Field metadata from an EDA profile.

    From the profile, never from the frame: the builder must describe the same
    columns the report describes, with the same counts, or a reader comparing
    the two is comparing two different analyses.
    """
    kinds = {
        "numeric": "quantitative",
        "datetime": "temporal",
        "boolean": "nominal",
        "categorical": "nominal",
        "ordinal": "ordinal",
        "text": "nominal",
        "constant": "nominal",
        "empty": "nominal",
    }
    out: list[Field] = []
    for column in dataset_profile.columns_profiled.values():
        kind = kinds.get(column.kind.value, "nominal")
        out.append(
            Field(
                name=column.name,
                kind=kind,
                distinct=column.distinct,
                missing_rate=column.missing_rate,
                identifier_like=column.is_identifier_like,
                constant=column.is_constant,
            )
        )
    return out


@dataclass
class Composition:
    """What the reader put where.

    Plain data, so a composition can be saved, shared, replayed and diffed --
    and so the keyboard route and the drag route produce exactly the same
    thing. An accessible alternative that builds a *different* object is not
    an alternative.
    """

    x: str | None = None
    y: str | None = None
    color: str | None = None
    facet: str | None = None
    aggregate: str = "count"
    mark: Mark | None = None
    filters: tuple[FilterClause, ...] = ()
    title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "color": self.color,
            "facet": self.facet,
            "aggregate": self.aggregate,
            "mark": self.mark.value if self.mark else None,
            "filters": [f.to_dict() for f in self.filters],
            "title": self.title,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Composition:
        raw_mark = payload.get("mark")
        return cls(
            x=payload.get("x") or None,
            y=payload.get("y") or None,
            color=payload.get("color") or None,
            facet=payload.get("facet") or None,
            aggregate=str(payload.get("aggregate", "count")),
            mark=Mark(raw_mark) if raw_mark else None,
            filters=tuple(FilterClause.from_dict(f) for f in payload.get("filters", [])),
            title=str(payload.get("title", "")),
        )


class CompositionRefused(ValueError):
    """The chosen combination would not produce a readable chart."""


# --------------------------------------------------------------------------
# Composing
# --------------------------------------------------------------------------


def _surviving(frame: pd.DataFrame, filters: tuple[FilterClause, ...]) -> list[int]:
    """Row *positions* of ``frame`` that pass every clause.

    Positions, not index labels. A frame with a duplicated index -- ordinary
    after a concat -- has several rows answering to the same label, so a
    label-keyed lookup silently resolves all of them to whichever came last.
    Every mark would then carry plausible-looking keys pointing at the wrong
    rows, and brushing would highlight records that were never in the bar.
    """
    positions = list(range(len(frame)))
    for clause in filters:
        mask = clause.mask(frame.iloc[positions]).to_numpy()
        positions = [p for p, keep in zip(positions, mask, strict=True) if keep]
    return positions


def _keys_at(identity: StableRowIndex | None, positions: list[int], within: Any) -> list[str]:
    """Keys for rows named by their offsets *within* a filtered subset.

    Falls back to empty strings when no identity was supplied -- a mark with no
    key is a mark that cannot be brushed, which is the correct outcome, and
    better than one that brushes the wrong rows.
    """
    if identity is None:
        return ["" for _ in within]
    return [identity.key_at(positions[i]) if 0 <= int(i) < len(positions) else "" for i in within]


def _lookup(fields: list[Field], name: str | None) -> Field | None:
    return next((f for f in fields if f.name == name), None) if name else None


def compose(
    frame: pd.DataFrame,
    fields: list[Field],
    composition: Composition,
    *,
    identity: StableRowIndex | None = None,
) -> ChartSpec:
    """Turn a composition into a spec.

    Raises :class:`CompositionRefused` with a sentence a reader can act on,
    rather than returning an empty chart that looks like an absence of signal.

    When an ``identity`` is supplied, every datum carries the stable row keys
    it was computed from, under ``"keys"``. That is what makes brushing real:
    clicking a bar selects the rows behind the bar, not the bar's position.
    Without it, a selection taken from a chart could only be a highlight.
    """
    x_field = _lookup(fields, composition.x)
    y_field = _lookup(fields, composition.y)
    colour = _lookup(fields, composition.color)

    if x_field is None and y_field is None:
        raise CompositionRefused("choose at least one field to place on an axis")

    for candidate in (x_field, y_field, colour):
        if candidate is not None and (why := candidate.plottable) is not None:
            raise CompositionRefused(f"{candidate.name}: {why}")

    panel = _lookup(fields, composition.facet)
    if composition.facet is not None:
        if panel is None:
            raise CompositionRefused(f"{composition.facet!r} is not a column here")
        if not panel.is_categorical:
            raise CompositionRefused(
                f"{panel.name} is {panel.kind}; small multiples need groups, and a "
                "measurement has none. Bin it first, or facet on a category."
            )
        if panel.distinct > ChartSpec.MAX_PANELS:
            raise CompositionRefused(
                f"{panel.name} has {panel.distinct:,} distinct values; more than "
                f"{ChartSpec.MAX_PANELS} panels cannot be compared at a glance, "
                "which is the only thing small multiples are for. Filter to fewer "
                "groups first."
            )

    if composition.aggregate not in AGGREGATES:
        raise CompositionRefused(
            f"{composition.aggregate!r} is not an aggregate; choose one of {', '.join(AGGREGATES)}"
        )

    # ``kept`` maps every row of ``working`` back to its position in ``frame``,
    # which is what lets a mark name its rows without going through the index.
    kept = _surviving(frame, composition.filters)
    working = frame.iloc[kept].reset_index(drop=True)
    if working.empty:
        raise CompositionRefused("the filters leave no rows to draw")

    fidelity, note = Fidelity.FULL, ""

    # -- two quantitative fields: a scatter, no aggregation ----------------
    if x_field and y_field and x_field.is_quantitative and y_field.is_quantitative:
        pairs = working[[x_field.name, y_field.name]].apply(pd.to_numeric, errors="coerce")
        pairs = pairs.dropna()
        if len(pairs) > 3000:
            pairs = pairs.sample(3000, random_state=0).sort_index()
            fidelity = Fidelity.RANDOM_SAMPLE
            note = f"3,000 of {len(working):,} rows"
        keys = (
            _keys_at(identity, kept, pairs.index)
            if len(pairs) <= _MAX_BRUSHABLE_MARKS
            else ["" for _ in range(len(pairs))]
        )
        data: list[dict[str, Any]] = [
            {x_field.name: float(a), y_field.name: float(b), "keys": [key] if key else []}
            for (a, b), key in zip(
                zip(pairs[x_field.name], pairs[y_field.name], strict=True), keys, strict=True
            )
        ]
        if colour is not None:
            for datum, value in zip(data, working[colour.name].iloc[pairs.index], strict=True):
                datum[colour.name] = None if pd.isna(value) else str(value)
        spec = ChartSpec(
            mark=composition.mark or Mark.SCATTER,
            data=data,
            x=Encoding(x_field.name, "quantitative"),
            y=Encoding(y_field.name, "quantitative"),
            color=Encoding(colour.name, "nominal") if colour is not None else None,
            title=composition.title or f"{y_field.name} against {x_field.name}",
            x_label=x_field.name,
            y_label=y_field.name,
            rationale="Two measurements: the pairing shows whether they move together.",
            fidelity=fidelity,
            fidelity_note=note,
        )
        return _annotate(
            _note_unbrushable(_apply_facet(spec, panel, working, pairs.index)),
            composition,
        )

    # -- a category, with or without a measure -----------------------------
    grouping = x_field if x_field and x_field.is_categorical else y_field
    measure = y_field if grouping is x_field else x_field

    if grouping is not None and grouping.is_categorical:
        if grouping.distinct > _MAX_CATEGORIES:
            raise CompositionRefused(
                f"{grouping.name} has {grouping.distinct:,} distinct values; "
                f"a chart with more than {_MAX_CATEGORIES} bars is a wall of "
                "labels. Filter it, or group the small categories first."
            )
        # Without a quantitative measure there is nothing to aggregate, so
        # the honest summary of a lone category is how many rows are in it.
        summarising = measure if measure is not None and measure.is_quantitative else None
        aggregate = composition.aggregate if summarising is not None else "count"

        if summarising is None or aggregate == "count":
            series = working.groupby(grouping.name, dropna=True).size()
            label = f"rows per {grouping.name}"
        else:
            numbers = pd.to_numeric(working[summarising.name], errors="coerce")
            series = numbers.groupby(working[grouping.name], dropna=True).agg(aggregate)
            label = f"{aggregate} of {summarising.name}"
            fidelity = Fidelity.AGGREGATED
            note = f"{aggregate} within each {grouping.name}"

        series = series.sort_values(ascending=False).head(_MAX_CATEGORIES)
        members: dict[str, list[str]] = {}
        if identity is not None:
            for offset, value in enumerate(working[grouping.name]):
                if pd.isna(value):
                    continue
                members.setdefault(str(value), []).append(identity.key_at(kept[offset]))
        data = [
            {"label": str(k), "value": float(v), "keys": members.get(str(k), [])}
            for k, v in series.items()
            if pd.notna(v)
        ]
        spec = ChartSpec(
            mark=composition.mark or Mark.HORIZONTAL_BAR,
            data=data,
            x=Encoding("value", "quantitative"),
            y=Encoding("label", "nominal"),
            title=composition.title or f"{label.capitalize()}",
            x_label=label,
            y_label=grouping.name,
            rationale=(
                f"A category against a measure: comparing {label} across "
                f"{grouping.name} is what the pairing implies."
            ),
            fidelity=fidelity,
            fidelity_note=note,
        )
        return _annotate(
            _note_unbrushable(_apply_facet(spec, panel, working, None)),
            composition,
        )

    # -- time on one axis ---------------------------------------------------
    if x_field and x_field.is_temporal and y_field and y_field.is_quantitative:
        times = pd.to_datetime(working[x_field.name], errors="coerce")
        numbers = pd.to_numeric(working[y_field.name], errors="coerce")
        ordered = pd.DataFrame({"t": times, "v": numbers}).dropna().sort_values("t")
        keys = (
            _keys_at(identity, kept, ordered.index)
            if len(ordered) <= _MAX_BRUSHABLE_MARKS
            else ["" for _ in range(len(ordered))]
        )
        data = [
            {"t": str(t.date()), "v": float(v), "keys": [key] if key else []}
            for (t, v), key in zip(zip(ordered["t"], ordered["v"], strict=True), keys, strict=True)
        ]
        spec = ChartSpec(
            mark=composition.mark or Mark.LINE,
            data=data,
            x=Encoding("t", "temporal"),
            y=Encoding("v", "quantitative"),
            title=composition.title or f"{y_field.name} over {x_field.name}",
            x_label=x_field.name,
            y_label=y_field.name,
            rationale="A measure against time: the ordering is what carries meaning.",
        )
        return _annotate(
            _note_unbrushable(_apply_facet(spec, panel, working, ordered.index)),
            composition,
        )

    # -- one quantitative field: its distribution ---------------------------
    only = x_field or y_field
    if only is not None and only.is_quantitative:
        from ..eda.profile import profile
        from .builders import distribution_chart

        # One column, not the whole frame. Profiling every column to draw a
        # chart of one is quadratic in the size of the catalogue: twenty-eight
        # precomputed compositions each paid for a full profile, which is how
        # building a Studio over fifty thousand rows took four minutes.
        built = distribution_chart(profile(working[[only.name]]).get(only.name))
        if built is None:
            raise CompositionRefused(f"{only.name} has too few values to describe")
        if composition.title:
            built.title = composition.title
        return _annotate(built, composition)

    raise CompositionRefused(
        "that combination has no chart that would be honest. Pair a category "
        "with a measure, two measures, or a measure with time."
    )


def _note_unbrushable(spec: ChartSpec) -> ChartSpec:
    """Say when a chart's marks were left unselectable, and why.

    Silence would read as "this chart is not linked to anything", which is a
    different and more discouraging claim than "there are too many points here
    for picking one to mean much".
    """
    if (
        spec.data
        and len(spec.data) > _MAX_BRUSHABLE_MARKS
        and not any(row.get("keys") for row in spec.data)
    ):
        spec.annotations.append(
            {
                "kind": "unbrushable",
                "text": (
                    f"{len(spec.data):,} points: individual selection is off. Filter instead."
                ),
            }
        )
    return spec


def _apply_facet(
    spec: ChartSpec,
    panel: Field | None,
    working: pd.DataFrame,
    offsets: Any = None,
) -> ChartSpec:
    """Attach the facet channel, and the group each datum belongs to.

    The group has to travel with the datum: a panel is a filter over
    ``spec.data``, so a row that does not carry its group cannot be placed in
    one. ``offsets`` names which rows of ``working`` produced the data, in
    order -- the same mapping the row keys use -- because a chart that dropped
    missing pairs no longer lines up row for row with the frame, and guessing
    that it does is how a point lands in the wrong panel.
    """
    if panel is None:
        return spec

    if offsets is None:
        # No mapping means the data was aggregated or reshaped, and the groups
        # cannot be attached honestly. Saying so beats attaching wrong ones.
        raise CompositionRefused(
            f"this chart aggregates, so it cannot also be split by {panel.name}. "
            "Facet the underlying rows, or drop the aggregate."
        )

    column = working[panel.name]
    for datum, offset in zip(spec.data, offsets, strict=True):
        value = column.iloc[int(offset)]
        datum[panel.name] = "" if pd.isna(value) else str(value)
    spec.facet = Encoding(panel.name, "nominal")
    return spec


def _annotate(spec: ChartSpec, composition: Composition) -> ChartSpec:
    """Record the filters on the chart itself.

    A filtered chart that does not say it is filtered is the visual form of a
    sampled chart that does not say it was sampled.
    """
    if composition.filters:
        described = " and ".join(c.describe() for c in composition.filters)
        prefix = f"{spec.subtitle}  " if spec.subtitle else ""
        spec.subtitle = prefix + f"filtered where {described}"
        spec.annotations.append({"kind": "filter", "text": described})
    return spec


# --------------------------------------------------------------------------
# Recommending
# --------------------------------------------------------------------------


@dataclass
class Recommendation:
    """A suggested composition, and the sentence that justifies it."""

    composition: Composition
    why: str
    score: float = 0.0
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "composition": self.composition.to_dict(),
            "why": self.why,
            "score": round(self.score, 4),
            "label": self.label,
        }


def recommend(fields: list[Field], limit: int = 8) -> list[Recommendation]:
    """Compositions worth trying, each with its reason.

    Ranked, but the ranking is a starting order rather than an answer -- which
    is why every entry carries its justification instead of a bare score.
    """
    usable = [f for f in fields if f.plottable is None]
    quantities = [f for f in usable if f.is_quantitative]
    categories = [f for f in usable if f.is_categorical and f.distinct <= _MAX_CATEGORIES]
    times = [f for f in usable if f.is_temporal]

    out: list[Recommendation] = []

    for measure in quantities[:4]:
        out.append(
            Recommendation(
                Composition(x=measure.name, title=f"Distribution of {measure.name}"),
                why=(
                    f"{measure.name} is a measurement, and the first question about "
                    "a measurement is how it is spread."
                ),
                score=0.9 - measure.missing_rate,
                label=f"How is {measure.name} distributed?",
            )
        )

    for category in categories[:3]:
        for measure in quantities[:2]:
            out.append(
                Recommendation(
                    Composition(x=category.name, y=measure.name, aggregate="mean"),
                    why=(
                        f"{category.name} has {category.distinct} readable groups, so "
                        f"comparing the mean of {measure.name} across them is legible."
                    ),
                    score=0.8 - category.distinct / (_MAX_CATEGORIES * 4),
                    label=f"Does {measure.name} differ by {category.name}?",
                )
            )

    for i, first in enumerate(quantities[:3]):
        for second in quantities[i + 1 : 3]:
            out.append(
                Recommendation(
                    Composition(x=first.name, y=second.name),
                    why="Two measurements: a scatter shows whether they move together.",
                    score=0.7,
                    label=f"Do {first.name} and {second.name} move together?",
                )
            )

    for when in times[:2]:
        for measure in quantities[:2]:
            out.append(
                Recommendation(
                    Composition(x=when.name, y=measure.name),
                    why=f"{when.name} is a date, so {measure.name} has an order worth following.",
                    score=0.75,
                    label=f"How does {measure.name} move over {when.name}?",
                )
            )

    out.sort(key=lambda r: r.score, reverse=True)
    return out[:limit]
