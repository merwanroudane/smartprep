"""ChartSpec -- a chart described as data, not as plotting code.

A chart written directly against Matplotlib cannot become an interactive HTML
chart, and a chart written against Plotly cannot go into a PDF. Writing it
three times guarantees the three drift apart, and the reader ends up looking at
subtly different pictures of the same numbers.

So a chart is a **specification**: mark, encodings, data, and intent. Renderers
turn it into a PNG, an interactive page, or a slide. Adding an output format
means adding one renderer, not revisiting every chart.

The spec also carries the honesty the plan requires: whether it is drawn from
full data or a sample, and why the chart was chosen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

__all__ = ["Mark", "Fidelity", "Interaction", "Encoding", "ChartSpec", "ChartSet"]


class Mark(Enum):
    """The visual form. Deliberately small -- these cover data preparation."""

    BAR = "bar"
    HORIZONTAL_BAR = "horizontal_bar"
    LINE = "line"
    AREA = "area"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    BOX = "box"
    HEATMAP = "heatmap"
    STEP = "step"
    MATRIX = "matrix"
    TEXT = "text"


class Fidelity(Enum):
    """What the chart was actually drawn from.

    Stated on every chart. A reader who thinks they are looking at a million
    points, and is looking at ten thousand, will draw conclusions the picture
    does not support.
    """

    FULL = "full"
    RANDOM_SAMPLE = "random_sample"
    STRATIFIED_SAMPLE = "stratified_sample"
    AGGREGATED = "aggregated"
    BINNED = "binned"


class Interaction(Enum):
    """What a reader can *do* with the chart once it is drawn.

    Deliberately not a boolean, and deliberately a different axis from
    animation. A chart can be animated but not interactive (stage frames
    printed as small multiples in a PDF), interactive but not animated (a
    scatter you can lasso), both, or neither. Collapsing the two into one
    flag is how a library ends up calling hover text "interactive".

    The spec declares the *most* a reader may do; a renderer delivers what
    its medium allows and never more. Paper cannot hover, so a Matplotlib
    figure is a picture whatever the spec permits; an SVG in an archival
    report tops out at hover; only Plotly can reach EXPLORE. Lowering the
    ceiling with :meth:`ChartSpec.as_static` is how a chart bound for print
    says so once, rather than each renderer inventing its own rule.
    """

    #: A picture. Print, slides, archival SVG.
    NONE = "none"
    #: Values on hover. A convenience for reading, not an analysis tool.
    HOVER = "hover"
    #: Hover plus zoom, pan and selection -- the reader can ask their own
    #: questions of the chart.
    EXPLORE = "explore"


@dataclass(frozen=True)
class Encoding:
    """One channel: which field, how it is treated, how it is labelled."""

    field: str
    kind: str = "quantitative"  # quantitative | nominal | ordinal | temporal
    title: str | None = None
    aggregate: str | None = None
    scale: str | None = None  # linear | log | symlog

    def to_dict(self) -> dict[str, Any]:
        return {
            k: v
            for k, v in {
                "field": self.field,
                "kind": self.kind,
                "title": self.title,
                "aggregate": self.aggregate,
                "scale": self.scale,
            }.items()
            if v is not None
        }


@dataclass
class ChartSpec:
    """A chart, fully described and independent of any renderer.

    ``data`` holds the values in long form -- a list of records. Keeping the
    data inside the spec is what lets a chart be serialised, cached, diffed and
    replayed without the original DataFrame.
    """

    mark: Mark
    data: list[dict[str, Any]] = field(default_factory=list)
    x: Encoding | None = None
    y: Encoding | None = None
    color: Encoding | None = None
    size: Encoding | None = None
    facet: Encoding | None = None

    title: str = ""
    subtitle: str = ""
    x_label: str = ""
    y_label: str = ""

    #: Why this chart, in one sentence. Rendered beneath it, because a chart
    #: nobody can justify is decoration.
    rationale: str = ""
    fidelity: Fidelity = Fidelity.FULL
    fidelity_note: str = ""

    #: Reference lines: ``(orientation, value, label)`` with orientation
    #: "x" or "y". Used for thresholds, medians, fences.
    rules: list[tuple[str, float, str]] = field(default_factory=list)
    annotations: list[dict[str, Any]] = field(default_factory=list)

    #: The field whose values order the frames of an animated rendering. Set
    #: only when the ordering carries meaning -- a stage, or time. Never for
    #: motion's own sake. Independent of :attr:`interaction`.
    animation_field: str | None = None

    #: A y-axis range every renderer must honour, when set. Exists so small
    #: multiples can share one scale: a grid of charts with private axes is a
    #: grid nobody may compare, and comparing them is the only reason to draw
    #: a grid.
    y_domain: tuple[float, float] | None = None

    #: The *ceiling* on reader interaction, honoured by every renderer. A
    #: renderer delivers the lesser of this and what its medium allows, so
    #: the default is the most a chart could ever offer and print lowers it
    #: rather than every screen chart having to opt in. Not the animation
    #: switch -- see :class:`Interaction`.
    interaction: Interaction = Interaction.EXPLORE

    height: int = 320
    width: int = 640

    def __post_init__(self) -> None:
        if self.mark is not Mark.TEXT and not self.data:
            # An empty chart is a lie of omission: it looks like "no signal"
            # when it means "no data reached the renderer".
            self.annotations.append({"kind": "empty", "text": "No data to display."})

    @property
    def is_sampled(self) -> bool:
        return self.fidelity is not Fidelity.FULL

    @property
    def is_interactive(self) -> bool:
        """Whether a reader may act on the chart. Says nothing about motion."""
        return self.interaction is not Interaction.NONE

    @property
    def is_animated(self) -> bool:
        """Whether the chart has ordered frames. Says nothing about interaction."""
        return self.animation_field is not None

    def size_of(self, row: dict[str, Any], smallest: float, largest: float) -> float:
        """The radius for one datum, scaled across the channel's range.

        Area, not radius, is what the eye reads as magnitude, so the value is
        mapped to area and the radius taken from its square root. Scaling the
        radius directly makes a doubled value look four times larger, which is
        the most common way a size channel lies.
        """
        if self.size is None:
            return largest
        values = [
            float(r[self.size.field])
            for r in self.data
            if isinstance(r.get(self.size.field), (int, float))
        ]
        if not values:
            return largest
        low, high = min(values), max(values)
        raw = row.get(self.size.field)
        if not isinstance(raw, (int, float)) or high == low:
            return (smallest + largest) / 2
        fraction = (float(raw) - low) / (high - low)
        area = smallest**2 + fraction * (largest**2 - smallest**2)
        return round(area**0.5, 2)

    def colour_groups(self) -> list[str]:
        """The distinct values of the colour channel, in a stable order.

        One list, computed once, so every renderer assigns the same colour to
        the same category. Two backends each deriving their own order is how
        a legend in a report and the same legend in a slide end up meaning
        different things.
        """
        if self.color is None:
            return []
        seen = {str(row.get(self.color.field, "")) for row in self.data}
        return sorted(seen - {""})

    def colour_of(self, row: dict[str, Any], palette: tuple[str, ...]) -> str | None:
        """The palette entry for one datum, or ``None`` when uncoloured."""
        groups = self.colour_groups()
        if not groups:
            return None
        value = str(row.get(self.color.field, "")) if self.color else ""
        if value not in groups:
            return None
        return palette[groups.index(value) % len(palette)]

    #: More panels than this and each is too small to read. Small multiples
    #: work because the eye compares them at a glance; thirty of them is a
    #: contact sheet, not a comparison.
    MAX_PANELS: ClassVar[int] = 12

    @property
    def is_faceted(self) -> bool:
        return self.facet is not None

    def facet_values(self) -> list[str]:
        """The distinct values of the facet field, in a stable order."""
        if self.facet is None:
            return []
        seen = {str(row.get(self.facet.field, "")) for row in self.data}
        return sorted(seen - {""})

    def panels(self) -> list[ChartSpec]:
        """One ordinary spec per facet value.

        Faceting is done here rather than in each renderer on purpose: a panel
        is just a chart, so every backend draws small multiples with the code
        it already had, and the three cannot drift apart. It also means a
        panel's marks keep their row keys, so brushing links across facets
        without anything extra.
        """
        from dataclasses import replace

        if self.facet is None:
            return [self]

        values = self.facet_values()
        if len(values) > self.MAX_PANELS:
            raise ValueError(
                f"{self.facet.field} has {len(values)} distinct values; "
                f"more than {self.MAX_PANELS} panels cannot be compared at a "
                "glance, which is the only thing small multiples are for. "
                "Filter to fewer groups first."
            )

        field_name = self.facet.field
        # One scale across every panel, computed here rather than in a
        # renderer, so all three backends draw comparable panels. A grid of
        # charts with private axes is a grid nobody may compare, and comparing
        # them is the only reason to draw a grid.
        shared = self.y_domain or self._domain_over(self.data)

        out: list[ChartSpec] = []
        for value in values:
            rows = [r for r in self.data if str(r.get(field_name, "")) == value]
            out.append(
                replace(
                    self,
                    data=rows,
                    facet=None,
                    y_domain=shared,
                    title=f"{field_name} = {value}",
                    subtitle="",
                    annotations=[],
                )
            )
        return out

    def _domain_over(self, rows: list[dict[str, Any]]) -> tuple[float, float] | None:
        field_name = self.y.field if self.y else "y"
        values = [
            float(row[field_name]) for row in rows if isinstance(row.get(field_name), (int, float))
        ]
        if not values:
            return None
        return (min(min(values), 0.0), max(values))

    def as_static(self) -> ChartSpec:
        """The same chart with interaction removed -- for print and slides."""
        from dataclasses import replace

        return replace(self, interaction=Interaction.NONE)

    def with_data(self, data: list[dict[str, Any]]) -> ChartSpec:
        from dataclasses import replace

        return replace(self, data=data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "mark": self.mark.value,
            "encodings": {
                name: encoding.to_dict()
                for name, encoding in (
                    ("x", self.x),
                    ("y", self.y),
                    ("color", self.color),
                    ("size", self.size),
                    ("facet", self.facet),
                )
                if encoding is not None
            },
            "title": self.title,
            "subtitle": self.subtitle,
            "labels": {"x": self.x_label, "y": self.y_label},
            "rationale": self.rationale,
            "fidelity": {
                "level": self.fidelity.value,
                "note": self.fidelity_note,
                "is_sampled": self.is_sampled,
            },
            "rules": [{"orientation": o, "value": v, "label": lbl} for o, v, lbl in self.rules],
            "annotations": list(self.annotations),
            "animation_field": self.animation_field,
            "animated": self.is_animated,
            "interaction": self.interaction.value,
            "y_domain": list(self.y_domain) if self.y_domain else None,
            "size": {"width": self.width, "height": self.height},
            "data": self.data,
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)

    def describe(self) -> str:
        parts = [f"{self.mark.value}: {self.title or '(untitled)'}"]
        if self.rationale:
            parts.append(f"  why: {self.rationale}")
        if self.is_sampled:
            parts.append(f"  fidelity: {self.fidelity.value} -- {self.fidelity_note}")
        parts.append(f"  rows: {len(self.data)}")
        return "\n".join(parts)


@dataclass
class ChartSet:
    """An ordered, titled group of charts -- one section of a report."""

    title: str
    charts: list[ChartSpec] = field(default_factory=list)
    description: str = ""

    def add(self, chart: ChartSpec | None) -> ChartSet:
        if chart is not None:
            self.charts.append(chart)
        return self

    def __len__(self) -> int:
        return len(self.charts)

    def __iter__(self) -> Any:
        return iter(self.charts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "charts": [c.to_dict() for c in self.charts],
        }
