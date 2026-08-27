"""SVG renderer -- static charts with no plotting dependency.

Matplotlib is the obvious choice and a heavy one: it is optional here, and a
report that cannot draw its own charts without it is not self-contained. SVG is
text, so it embeds directly in HTML, scales without blurring, prints cleanly,
and needs nothing installed.

The renderer is deliberately small. It draws the handful of marks data
preparation actually needs, and draws them legibly, rather than reimplementing
a plotting library.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from .spec import ChartSpec, Mark

__all__ = ["Theme", "render_svg", "LIGHT"]


@dataclass(frozen=True)
class Theme:
    """Colours and spacing. Light by default, per the interface guidance."""

    background: str = "#ffffff"
    foreground: str = "#1f2933"
    # muted and warning carry real text -- rationales, captions, fidelity
    # notes -- so both clear 4.5:1 against the background. The earlier values
    # measured 3.66 and 3.64, which is a caveat a reader may not be able to
    # read, and the caveats are the part that matters most.
    muted: str = "#5c6873"
    grid: str = "#e4e7eb"
    accent: str = "#2f6f9f"
    accent_soft: str = "#9fc0d8"
    warning: str = "#8a5a10"
    danger: str = "#b83232"
    positive: str = "#2f855a"
    font: str = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    #: Ordered categorical palette, chosen to stay distinguishable in greyscale
    #: and for the most common forms of colour blindness.
    series: tuple[str, ...] = (
        "#2f6f9f",
        "#b7791f",
        "#2f855a",
        "#8c5bb0",
        "#b83232",
        "#4c7a8a",
        "#946c3a",
    )


LIGHT = Theme()

_PADDING = {"top": 44, "right": 24, "bottom": 52, "left": 130}


#: Past this many points, marks are drawn without individual hover text. The
#: chart's data table is the accessible and the readable route at that density.
_MAX_LABELLED_POINTS = 250

#: Hover text emitted by the mark renderers, stripped for non-interactive output.
_TITLE_RE = re.compile(r"<title>.*?</title>", re.DOTALL)


def _brushable(row: dict[str, object]) -> str:
    """Attributes that make a mark selectable, when the datum names its rows.

    A mark that does not know which rows it was computed from cannot be
    brushed, and gets nothing -- silently doing something with the mark's
    *position* instead is how a selection ends up landing on the wrong
    records.
    """
    keys = row.get("keys")
    if not isinstance(keys, (list, tuple)) or not keys:
        return ""
    listed = _escape(",".join(str(k) for k in keys if k))
    if not listed:
        return ""
    return f' data-keys="{listed}" tabindex="0" role="button" style="cursor:pointer"'


def _escape(text: object) -> str:
    return html.escape(str(text), quote=True)


def _nice_number(value: float) -> str:
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if magnitude >= 1_000:
        return f"{value / 1_000:.1f}k"
    if magnitude >= 10:
        return f"{value:.0f}"
    if magnitude >= 0.01:
        return f"{value:.2f}"
    return f"{value:.2e}"


def render_svg(spec: ChartSpec, theme: Theme = LIGHT) -> str:
    """Render a spec to a standalone SVG string."""
    if spec.is_faceted:
        return _small_multiples(spec, theme)
    if not spec.data:
        return _empty(spec, theme)

    renderer = {
        Mark.HORIZONTAL_BAR: _horizontal_bar,
        Mark.BAR: _vertical_bar,
        Mark.HISTOGRAM: _histogram,
        Mark.MATRIX: _matrix,
        Mark.HEATMAP: _matrix,
        Mark.LINE: _line,
        Mark.STEP: _step,
        Mark.SCATTER: _scatter,
        Mark.AREA: _area,
        Mark.BOX: _box,
        Mark.TEXT: _text,
    }.get(spec.mark)

    if renderer is None:
        return _empty(spec, theme, message=f"No renderer for mark {spec.mark.value!r}.")
    body = renderer(spec, theme)
    if not spec.is_interactive:
        # The marks emit <title> for hover. On paper and in slides nothing
        # hovers, so a spec that declares Interaction.NONE gets none: the
        # field is honoured rather than merely declared.
        body = _TITLE_RE.sub("", body)
    return _wrap(spec, body, theme)


def _small_multiples(spec: ChartSpec, theme: Theme = LIGHT) -> str:
    """Facets, laid out as a grid of ordinary charts.

    Each panel is rendered by the same code as any other chart, so a faceted
    view and an unfaceted one cannot disagree about the same numbers -- and
    the marks keep their row keys, so a selection made in one panel highlights
    its rows in all of them.

    The panels share an axis scale, because small multiples whose axes differ
    invite exactly the comparison they cannot support.
    """
    from dataclasses import replace

    panels = spec.panels()
    if not panels:
        return _empty(spec, theme)

    columns = min(3, len(panels))
    rows = (len(panels) + columns - 1) // columns
    cell_width = max(220, spec.width // columns)
    cell_height = max(170, spec.height // max(rows, 1))

    # One scale for every panel: a grid of charts with private axes is a grid
    # of charts nobody may compare, and comparing them is the only reason to
    # draw a grid.
    shared = panels[0].y_domain

    body = []
    for index, panel in enumerate(panels):
        sized = replace(panel, width=cell_width, height=cell_height)
        x = (index % columns) * cell_width
        y = (index // columns) * cell_height + 30
        inner = render_svg(sized, theme) if sized.data else _empty(sized, theme)
        body.append(f'<g transform="translate({x},{y})">{inner}</g>')

    total_width = cell_width * columns
    total_height = cell_height * rows + 40
    scale_note = (
        f"; shared scale {_nice_number(shared[0])} to {_nice_number(shared[1])}" if shared else ""
    )
    caption = _escape(
        f"{len(panels)} panels by {spec.facet.field if spec.facet else ''}{scale_note}"
        + (f"  |  {spec.rationale}" if spec.rationale else "")
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" '
        f'height="{total_height}" viewBox="0 0 {total_width} {total_height}" '
        f'role="img" aria-label="{_escape(spec.title)}" '
        f'font-family="{theme.font}">'
        f"<title>{_escape(spec.title or 'Chart')}</title>"
        f"<desc>{caption}</desc>"
        f'<rect width="{total_width}" height="{total_height}" fill="{theme.background}"/>'
        f'<text x="16" y="21" font-size="13" font-weight="600" '
        f'fill="{theme.foreground}">{_escape(spec.title)}</text>'
        f"{''.join(body)}"
        f'<text x="16" y="{total_height - 10}" font-size="10" '
        f'fill="{theme.muted}">{caption[:190]}</text>'
        "</svg>"
    )


def _wrap(spec: ChartSpec, body: str, theme: Theme) -> str:
    footnote = ""
    notes = []
    if spec.rationale:
        notes.append(spec.rationale)
    if spec.is_sampled:
        # Never let a reader assume they are seeing every point.
        notes.append(f"[{spec.fidelity.value}] {spec.fidelity_note}".strip())
    if notes:
        text = _escape("  |  ".join(notes))
        footnote = (
            f'<text x="{_PADDING["left"]}" y="{spec.height - 8}" '
            f'font-size="10" fill="{theme.muted}">{text[:170]}</text>'
        )

    # Accessibility: <title> and <desc> as the first children are what a
    # screen reader announces. The description carries the rationale and the
    # fidelity caveat, so a reader who cannot see the picture is told the
    # same caveats as one who can -- a sampled chart must not read as full.
    described = "  |  ".join([spec.subtitle, *notes]).strip(" |")
    accessible = f"<title>{_escape(spec.title or 'Chart')}</title>" + (
        f"<desc>{_escape(described)}</desc>" if described else ""
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{spec.width}" '
        f'height="{spec.height}" viewBox="0 0 {spec.width} {spec.height}" '
        f'role="img" aria-label="{_escape(spec.title)}" '
        f'font-family="{theme.font}">'
        f"{accessible}"
        f'<rect width="{spec.width}" height="{spec.height}" fill="{theme.background}"/>'
        f'<text x="{_PADDING["left"]}" y="24" font-size="13" font-weight="600" '
        f'fill="{theme.foreground}">{_escape(spec.title)}</text>'
        f"{body}{footnote}</svg>"
    )


def _empty(spec: ChartSpec, theme: Theme, message: str = "No data to display.") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{spec.width}" height="120" '
        f'font-family="{theme.font}">'
        f'<rect width="{spec.width}" height="120" fill="{theme.background}"/>'
        f'<text x="16" y="30" font-size="13" font-weight="600" fill="{theme.foreground}">'
        f"{_escape(spec.title)}</text>"
        f'<text x="16" y="60" font-size="11" fill="{theme.muted}">{_escape(message)}</text>'
        f"</svg>"
    )


def _plot_area(spec: ChartSpec) -> tuple[int, int, int, int]:
    left, top = _PADDING["left"], _PADDING["top"]
    width = spec.width - left - _PADDING["right"]
    height = spec.height - top - _PADDING["bottom"]
    return left, top, max(width, 10), max(height, 10)


def _colour_for(value: object, spec: ChartSpec, theme: Theme, index: int) -> str:
    if spec.color is None:
        return theme.accent
    if isinstance(value, bool):
        return theme.warning if value else theme.accent
    return theme.series[index % len(theme.series)]


def _horizontal_bar(spec: ChartSpec, theme: Theme) -> str:
    left, top, width, height = _plot_area(spec)
    x_field = spec.x.field if spec.x else "value"
    y_field = spec.y.field if spec.y else "label"

    rows = spec.data
    values = [float(r.get(x_field, 0) or 0) for r in rows]
    low, high = min(min(values), 0.0), max(max(values), 0.0)
    span = (high - low) or 1.0
    zero = left + (0 - low) / span * width

    bar_height = min(24, max(6, height / max(len(rows), 1) - 4))
    step = height / max(len(rows), 1)

    parts = [
        f'<line x1="{zero:.1f}" y1="{top}" x2="{zero:.1f}" y2="{top + height}" '
        f'stroke="{theme.grid}"/>'
    ]

    for i, row in enumerate(rows):
        value = float(row.get(x_field, 0) or 0)
        y = top + i * step + (step - bar_height) / 2
        bar_width = abs(value) / span * width
        x = zero if value >= 0 else zero - bar_width
        colour = spec.colour_of(row, theme.series) or theme.accent

        label = _escape(row.get(y_field, ""))[:26]
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(bar_width, 1):.1f}" '
            f'height="{bar_height:.1f}" fill="{colour}" rx="2"{_brushable(row)}>'
            f"<title>{label}: {_nice_number(value)}</title></rect>"
        )
        parts.append(
            f'<text x="{left - 8}" y="{y + bar_height / 2 + 3.5:.1f}" font-size="10" '
            f'text-anchor="end" fill="{theme.foreground}">{label}</text>'
        )
        parts.append(
            f'<text x="{x + bar_width + 5:.1f}" y="{y + bar_height / 2 + 3.5:.1f}" '
            f'font-size="9.5" fill="{theme.muted}">{_nice_number(value)}</text>'
        )

    return "".join(parts)


def _vertical_bar(spec: ChartSpec, theme: Theme) -> str:
    left, top, width, height = _plot_area(spec)
    x_field = spec.x.field if spec.x else "label"
    y_field = spec.y.field if spec.y else "value"

    rows = spec.data
    values = [float(r.get(y_field, 0) or 0) for r in rows]
    # A shared domain wins, so faceted panels are drawn to one scale.
    high = spec.y_domain[1] if spec.y_domain else max(max(values), 1.0)
    high = high or 1.0
    step = width / max(len(rows), 1)
    bar_width = max(2.0, step * 0.7)

    parts = [
        f'<line x1="{left}" y1="{top + height}" x2="{left + width}" '
        f'y2="{top + height}" stroke="{theme.grid}"/>'
    ]
    # Label every nth tick only, or they collide into a grey smear.
    tick_every = max(1, len(rows) // 12)

    for i, row in enumerate(rows):
        value = float(row.get(y_field, 0) or 0)
        bar_height = value / high * height
        x = left + i * step + (step - bar_width) / 2
        y = top + height - bar_height
        label = _escape(row.get(x_field, ""))
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
            f'height="{max(bar_height, 1):.1f}" '
            f'fill="{spec.colour_of(row, theme.series) or theme.accent}" '
            f'rx="1.5"{_brushable(row)}>'
            f"<title>{label}: {_nice_number(value)}</title></rect>"
        )
        if i % tick_every == 0:
            parts.append(
                f'<text x="{x + bar_width / 2:.1f}" y="{top + height + 14}" '
                f'font-size="9" text-anchor="middle" fill="{theme.muted}" '
                f'transform="rotate(-35 {x + bar_width / 2:.1f} {top + height + 14})">'
                f"{label[:12]}</text>"
            )

    parts.append(
        f'<text x="{left - 8}" y="{top + 10}" font-size="9.5" text-anchor="end" '
        f'fill="{theme.muted}">{_nice_number(high)}</text>'
    )
    return "".join(parts)


def _histogram(spec: ChartSpec, theme: Theme) -> str:
    left, top, width, height = _plot_area(spec)
    rows = spec.data
    counts = [float(r.get("count", 0) or 0) for r in rows]
    high = max(max(counts), 1.0)
    centres = [float(r.get("centre", 0) or 0) for r in rows]
    low_x, high_x = min(centres), max(centres)
    span_x = (high_x - low_x) or 1.0
    bar_width = max(1.5, width / max(len(rows), 1) - 1)

    parts = [
        f'<line x1="{left}" y1="{top + height}" x2="{left + width}" '
        f'y2="{top + height}" stroke="{theme.grid}"/>'
    ]
    for i, row in enumerate(rows):
        count = float(row.get("count", 0) or 0)
        bar_height = count / high * height
        x = left + i * (width / max(len(rows), 1))
        y = top + height - bar_height
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
            f'height="{max(bar_height, 0.5):.1f}" fill="{theme.accent}" rx="1">'
            f"<title>{_nice_number(row.get('bin_start', 0))} to "
            f"{_nice_number(row.get('bin_end', 0))}: {int(count)} rows</title></rect>"
        )

    for orientation, value, label in spec.rules:
        if orientation != "x" or not (low_x <= value <= high_x):
            continue
        x = left + (value - low_x) / span_x * width
        colour = theme.danger if "fence" in label else theme.warning
        parts.append(
            f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + height}" '
            f'stroke="{colour}" stroke-width="1.2" stroke-dasharray="4 3"/>'
        )
        parts.append(
            f'<text x="{x + 3:.1f}" y="{top + 10}" font-size="9" fill="{colour}">'
            f"{_escape(label)}</text>"
        )

    for fraction in (0.0, 0.5, 1.0):
        x = left + fraction * width
        parts.append(
            f'<text x="{x:.1f}" y="{top + height + 15}" font-size="9" '
            f'text-anchor="middle" fill="{theme.muted}">'
            f"{_nice_number(low_x + fraction * span_x)}</text>"
        )
    parts.append(
        f'<text x="{left - 8}" y="{top + 10}" font-size="9.5" text-anchor="end" '
        f'fill="{theme.muted}">{_nice_number(high)}</text>'
    )
    return "".join(parts)


def _matrix(spec: ChartSpec, theme: Theme) -> str:
    rows = spec.data
    labels = sorted({str(r["left"]) for r in rows} | {str(r["right"]) for r in rows})
    if not labels:
        return ""

    left, top, width, height = _plot_area(spec)
    cell = min(width / len(labels), height / len(labels))
    lookup = {(str(r["left"]), str(r["right"])): r for r in rows}

    parts = []
    for row_index, row_label in enumerate(labels):
        for col_index, col_label in enumerate(labels):
            entry = lookup.get((row_label, col_label))
            value = float(entry["value"]) if entry else 0.0
            x = left + col_index * cell
            y = top + row_index * cell
            intensity = min(abs(value), 1.0)
            colour = theme.accent if value >= 0 else theme.danger
            measure = entry.get("measure", "") if entry else ""
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" '
                f'fill="{colour}" fill-opacity="{intensity:.3f}" '
                f'stroke="{theme.background}" stroke-width="0.5">'
                f"<title>{_escape(row_label)} / {_escape(col_label)}: "
                f"{value:+.3f} ({_escape(measure)})</title></rect>"
            )
        parts.append(
            f'<text x="{left - 6}" y="{top + row_index * cell + cell / 2 + 3:.1f}" '
            f'font-size="8.5" text-anchor="end" fill="{theme.foreground}">'
            f"{_escape(row_label)[:18]}</text>"
        )
    return "".join(parts)


def _line(spec: ChartSpec, theme: Theme) -> str:
    left, top, width, height = _plot_area(spec)
    # Points are spaced evenly along x, so only the y field is read.
    y_field = spec.y.field if spec.y else "y"

    rows = spec.data
    ys = [float(r.get(y_field, 0) or 0) for r in rows]
    low, high = min(ys), max(ys)
    span = (high - low) or 1.0

    points = []
    for i, value in enumerate(ys):
        x = left + (i / max(len(ys) - 1, 1)) * width
        y = top + height - (value - low) / span * height
        points.append(f"{x:.1f},{y:.1f}")

    return (
        f'<polyline points="{" ".join(points)}" fill="none" '
        f'stroke="{theme.accent}" stroke-width="1.8"/>'
        + _y_axis_labels(left, top, height, low, high, theme)
    )


def _step(spec: ChartSpec, theme: Theme) -> str:
    """A step line. Correct for anything that holds a value until it changes --
    a count per period, a state over time -- where a sloped line would imply
    interpolation that never happened."""
    left, top, width, height = _plot_area(spec)
    y_field = spec.y.field if spec.y else "y"
    ys = [float(r.get(y_field, 0) or 0) for r in spec.data]
    if not ys:
        return ""
    low, high = min(ys), max(ys)
    span = (high - low) or 1.0
    step_x = width / max(len(ys), 1)

    points: list[str] = []
    for i, value in enumerate(ys):
        y = top + height - (value - low) / span * height
        points.append(f"{left + i * step_x:.1f},{y:.1f}")
        points.append(f"{left + (i + 1) * step_x:.1f},{y:.1f}")

    return (
        f'<polyline points="{" ".join(points)}" fill="none" '
        f'stroke="{theme.accent}" stroke-width="1.8"/>'
        + _y_axis_labels(left, top, height, low, high, theme)
    )


def _area(spec: ChartSpec, theme: Theme) -> str:
    """A filled line. Reserved for cumulative or part-of-whole quantities --
    filling under a non-additive measure implies an area that means nothing."""
    left, top, width, height = _plot_area(spec)
    y_field = spec.y.field if spec.y else "y"
    ys = [float(r.get(y_field, 0) or 0) for r in spec.data]
    if not ys:
        return ""

    # Baseline at zero when the data is non-negative, so the filled area is
    # proportional to the quantity rather than to an arbitrary offset.
    low = min(min(ys), 0.0)
    high = max(ys)
    span = (high - low) or 1.0
    step_x = width / max(len(ys) - 1, 1)

    points = [
        f"{left + i * step_x:.1f},{top + height - (v - low) / span * height:.1f}"
        for i, v in enumerate(ys)
    ]
    baseline_y = top + height - (0 - low) / span * height
    polygon = (
        [f"{left:.1f},{baseline_y:.1f}"]
        + points
        + [f"{left + (len(ys) - 1) * step_x:.1f},{baseline_y:.1f}"]
    )

    return (
        f'<polygon points="{" ".join(polygon)}" fill="{theme.accent}" '
        f'fill-opacity="0.22"/>'
        f'<polyline points="{" ".join(points)}" fill="none" '
        f'stroke="{theme.accent}" stroke-width="1.6"/>'
        + _y_axis_labels(left, top, height, low, high, theme)
    )


def _box(spec: ChartSpec, theme: Theme) -> str:
    """Box plots from precomputed five-number summaries.

    Each record supplies ``min``, ``q1``, ``median``, ``q3``, ``max`` and
    optionally ``outliers``. The renderer never computes statistics -- that is
    the EDA engine's job, and duplicating it here would let the two disagree.
    """
    left, top, width, height = _plot_area(spec)
    rows = spec.data
    label_field = spec.y.field if spec.y else "label"

    values: list[float] = []
    for row in rows:
        values += [float(row.get(k, 0) or 0) for k in ("min", "q1", "median", "q3", "max")]
        values += [float(v) for v in row.get("outliers", [])]
    if not values:
        return ""
    low, high = min(values), max(values)
    span = (high - low) or 1.0

    def to_x(value: float) -> float:
        return left + (value - low) / span * width

    band = height / max(len(rows), 1)
    box_height = min(26.0, band * 0.55)
    parts: list[str] = []

    for i, row in enumerate(rows):
        centre = top + i * band + band / 2
        minimum = float(row.get("min", 0) or 0)
        q1 = float(row.get("q1", 0) or 0)
        median = float(row.get("median", 0) or 0)
        q3 = float(row.get("q3", 0) or 0)
        maximum = float(row.get("max", 0) or 0)
        label = _escape(row.get(label_field, ""))[:24]

        # Whiskers to the fences, then the box, then the median line.
        parts.append(
            f'<line x1="{to_x(minimum):.1f}" y1="{centre:.1f}" '
            f'x2="{to_x(maximum):.1f}" y2="{centre:.1f}" '
            f'stroke="{theme.muted}" stroke-width="1"/>'
        )
        for end in (minimum, maximum):
            parts.append(
                f'<line x1="{to_x(end):.1f}" y1="{centre - box_height / 3:.1f}" '
                f'x2="{to_x(end):.1f}" y2="{centre + box_height / 3:.1f}" '
                f'stroke="{theme.muted}" stroke-width="1"/>'
            )
        parts.append(
            f'<rect x="{to_x(q1):.1f}" y="{centre - box_height / 2:.1f}" '
            f'width="{max(to_x(q3) - to_x(q1), 1):.1f}" height="{box_height:.1f}" '
            f'fill="{theme.accent}" fill-opacity="0.30" stroke="{theme.accent}" rx="2">'
            f"<title>{label}: min {_nice_number(minimum)}, q1 {_nice_number(q1)}, "
            f"median {_nice_number(median)}, q3 {_nice_number(q3)}, "
            f"max {_nice_number(maximum)}</title></rect>"
        )
        parts.append(
            f'<line x1="{to_x(median):.1f}" y1="{centre - box_height / 2:.1f}" '
            f'x2="{to_x(median):.1f}" y2="{centre + box_height / 2:.1f}" '
            f'stroke="{theme.foreground}" stroke-width="1.8"/>'
        )
        for outlier in row.get("outliers", [])[:60]:
            parts.append(
                f'<circle cx="{to_x(float(outlier)):.1f}" cy="{centre:.1f}" r="2" '
                f'fill="{theme.danger}" fill-opacity="0.65">'
                f"<title>outlier {_nice_number(float(outlier))}</title></circle>"
            )
        parts.append(
            f'<text x="{left - 8}" y="{centre + 3.5:.1f}" font-size="10" '
            f'text-anchor="end" fill="{theme.foreground}">{label}</text>'
        )

    for fraction in (0.0, 0.5, 1.0):
        x = left + fraction * width
        parts.append(
            f'<text x="{x:.1f}" y="{top + height + 15}" font-size="9" '
            f'text-anchor="middle" fill="{theme.muted}">'
            f"{_nice_number(low + fraction * span)}</text>"
        )
    return "".join(parts)


def _text(spec: ChartSpec, theme: Theme) -> str:
    """A text panel -- a headline figure, or a stated finding.

    Belongs in the chart vocabulary because a dashboard tile and a chart occupy
    the same slot in a layout and should be describable the same way.
    """
    left, top, _, _ = _plot_area(spec)
    parts = []
    for i, row in enumerate(spec.data[:8]):
        value = _escape(row.get("value", ""))
        label = _escape(row.get("label", ""))
        y = top + i * 44
        parts.append(
            f'<text x="{left}" y="{y + 20}" font-size="22" font-weight="600" '
            f'fill="{theme.foreground}">{value}</text>'
        )
        parts.append(
            f'<text x="{left}" y="{y + 36}" font-size="10" fill="{theme.muted}">{label}</text>'
        )
    return "".join(parts)


def _y_axis_labels(left: int, top: int, height: int, low: float, high: float, theme: Theme) -> str:
    return (
        f'<text x="{left - 8}" y="{top + 10}" font-size="9.5" text-anchor="end" '
        f'fill="{theme.muted}">{_nice_number(high)}</text>'
        f'<text x="{left - 8}" y="{top + height}" font-size="9.5" text-anchor="end" '
        f'fill="{theme.muted}">{_nice_number(low)}</text>'
    )


def _scatter(spec: ChartSpec, theme: Theme) -> str:
    left, top, width, height = _plot_area(spec)
    x_field = spec.x.field if spec.x else "x"
    y_field = spec.y.field if spec.y else "y"

    xs = [float(r.get(x_field, 0) or 0) for r in spec.data]
    ys = [float(r.get(y_field, 0) or 0) for r in spec.data]
    x_low, x_high = min(xs), max(xs)
    y_low, y_high = min(ys), max(ys)
    x_span, y_span = (x_high - x_low) or 1.0, (y_high - y_low) or 1.0

    # Per-point hover text is a real affordance at fifty points and a hundred
    # kilobytes of markup at twelve hundred, where nobody is hovering an
    # individual dot anyway. Past the threshold the points are drawn plain and
    # the chart's data table carries the values instead.
    dense = len(spec.data) > _MAX_LABELLED_POINTS

    parts = []
    for row, x_value, y_value in zip(spec.data, xs, ys, strict=True):
        cx = left + (x_value - x_low) / x_span * width
        cy = top + height - (y_value - y_low) / y_span * height
        radius = spec.size_of(row, 1.6, 6.0) if spec.size else 2.4
        circle = (
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius}" '
            f'fill="{spec.colour_of(row, theme.series) or theme.accent}" '
            f'fill-opacity="0.55"{_brushable(row)}'
        )
        parts.append(
            f"{circle}/>"
            if dense
            else f"{circle}>"
            f"<title>{_nice_number(x_value)}, {_nice_number(y_value)}</title></circle>"
        )
    return "".join(parts)
