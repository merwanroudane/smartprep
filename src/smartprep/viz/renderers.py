"""Renderer backends: one specification, several outputs.

The whole point of describing a chart as data is that the destination chooses
the renderer, not the author. Three exist:

``svg``
    Built in, no dependency. Always available, so a report can always draw.
``matplotlib``
    Publication-quality static figures, and the route to PNG and PDF.
``plotly``
    Genuine interactivity -- zoom, pan, box and lasso select, rich tooltips.

The optional two are imported lazily and never at module import. A missing
backend produces a message naming the install command, not an ImportError from
somewhere deep in a report.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .spec import ChartSpec, Interaction, Mark
from .svg import LIGHT, Theme, render_svg

if TYPE_CHECKING:  # pragma: no cover
    import matplotlib.figure

__all__ = [
    "available_backends",
    "render",
    "to_matplotlib",
    "to_plotly",
    "save_chart",
    "BackendUnavailable",
]


class BackendUnavailable(RuntimeError):
    """A renderer was asked for that is not installed."""


def _require(module: str, extra: str) -> Any:
    try:
        return __import__(module)
    except ImportError as exc:
        raise BackendUnavailable(
            f"the {module!r} backend is not installed. Install it with "
            f'`pip install "smartprep[{extra}]"`, or use the built-in SVG '
            "renderer, which needs nothing."
        ) from exc


def available_backends() -> dict[str, bool]:
    """Which renderers this environment can actually use."""
    backends = {"svg": True}
    for name, module in (("matplotlib", "matplotlib"), ("plotly", "plotly")):
        try:
            __import__(module)
            backends[name] = True
        except ImportError:
            backends[name] = False
    return backends


def render(spec: ChartSpec, backend: str = "svg", theme: Theme = LIGHT) -> Any:
    """Render a spec with the named backend."""
    if backend == "svg":
        return render_svg(spec, theme)
    if backend == "matplotlib":
        return to_matplotlib(spec, theme)
    if backend == "plotly":
        return to_plotly(spec, theme)
    raise ValueError(f"unknown backend {backend!r}; expected 'svg', 'matplotlib' or 'plotly'")


# --------------------------------------------------------------------------
# Matplotlib
# --------------------------------------------------------------------------


def _matplotlib_facets(spec: ChartSpec, theme: Theme) -> Any:
    """Small multiples, one subplot per panel.

    Each panel is an ordinary spec drawn by the ordinary code path, so a
    faceted figure and an unfaceted one cannot disagree about the numbers.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    panels = spec.panels()
    columns = min(3, len(panels))
    rows_of = (len(panels) + columns - 1) // columns
    figure, grid = plt.subplots(
        rows_of,
        columns,
        figsize=(spec.width / 100, spec.height / 100 * rows_of * 0.8),
        dpi=110,
        squeeze=False,
    )
    figure.patch.set_facecolor(theme.background)

    for index, panel in enumerate(panels):
        axis = grid[index // columns][index % columns]
        drawn = to_matplotlib(panel, theme)
        source = drawn.axes[0]
        for patch in list(source.patches):
            patch.remove()
            axis.add_patch(patch)
        for line in list(source.lines):
            axis.plot(line.get_xdata(), line.get_ydata(), color=line.get_color())
        for collection in list(source.collections):
            points = np.asarray(collection.get_offsets())
            if points.size:
                axis.scatter(points[:, 0], points[:, 1], s=14, alpha=0.55, color=theme.accent)
        axis.set_xlim(source.get_xlim())
        axis.set_ylim(panel.y_domain or source.get_ylim())
        axis.set_title(panel.title, fontsize=9, loc="left")
        axis.set_facecolor(theme.background)
        axis.tick_params(labelsize=7)
        drawn.clf()
        plt.close(drawn)

    for empty in range(len(panels), rows_of * columns):
        grid[empty // columns][empty % columns].set_axis_off()

    figure.suptitle(spec.title, fontsize=12, x=0.02, ha="left")
    figure.tight_layout(rect=(0, 0, 1, 0.96))
    return figure


def _colours(spec: ChartSpec, rows: list[dict[str, Any]], theme: Theme) -> Any:
    """Per-mark colours from the spec's colour channel.

    Returns a single colour when the channel is unset, so an uncoloured chart
    stays exactly as it was. The group ordering lives on the spec, so a
    category is the same colour in every backend -- a legend that means one
    thing on screen and another in a slide is worse than no legend.
    """
    if spec.color is None:
        return theme.accent
    return [spec.colour_of(row, theme.series) or theme.accent for row in rows]


def to_matplotlib(spec: ChartSpec, theme: Theme = LIGHT) -> matplotlib.figure.Figure:
    """Build a Matplotlib figure -- the route to PNG, PDF and print.

    Static by design. A figure destined for a paper or a slide should not
    depend on a reader hovering over it.
    """
    _require("matplotlib", "viz")
    import matplotlib

    matplotlib.use("Agg", force=False)  # no display needed, and none assumed
    import matplotlib.pyplot as plt

    if spec.is_faceted:
        return _matplotlib_facets(spec, theme)

    figure, axes = plt.subplots(figsize=(spec.width / 100, spec.height / 100), dpi=110)
    figure.patch.set_facecolor(theme.background)
    axes.set_facecolor(theme.background)

    rows = spec.data
    x_field = spec.x.field if spec.x else "x"
    y_field = spec.y.field if spec.y else "y"

    if not rows:
        axes.text(
            0.5,
            0.5,
            "No data to display.",
            ha="center",
            va="center",
            color=theme.muted,
            fontsize=10,
        )
        axes.set_axis_off()
    elif spec.mark is Mark.HORIZONTAL_BAR:
        labels = [str(r.get(y_field, "")) for r in rows][::-1]
        values = [float(r.get(x_field, 0) or 0) for r in rows][::-1]
        axes.barh(labels, values, color=_colours(spec, rows[::-1], theme))
        axes.set_xlabel(spec.x_label)
    elif spec.mark in (Mark.BAR, Mark.HISTOGRAM):
        key = "centre" if spec.mark is Mark.HISTOGRAM else x_field
        value_key = "count" if spec.mark is Mark.HISTOGRAM else y_field
        labels = [r.get(key, "") for r in rows]
        values = [float(r.get(value_key, 0) or 0) for r in rows]
        axes.bar(range(len(values)), values, color=_colours(spec, rows, theme))
        step = max(1, len(labels) // 10)
        axes.set_xticks(range(0, len(labels), step))
        axes.set_xticklabels(
            [
                f"{labels[i]:.4g}" if isinstance(labels[i], float) else str(labels[i])
                for i in range(0, len(labels), step)
            ],
            rotation=35,
            ha="right",
            fontsize=8,
        )
        axes.set_ylabel(spec.y_label)
    elif spec.mark is Mark.SCATTER:
        axes.scatter(
            [float(r.get(x_field, 0) or 0) for r in rows],
            [float(r.get(y_field, 0) or 0) for r in rows],
            # Matplotlib sizes markers by area already, so the radius the spec
            # computes is squared back into one rather than scaled again.
            s=[spec.size_of(r, 2.0, 9.0) ** 2 for r in rows] if spec.size else 14,
            alpha=0.55,
            color=_colours(spec, rows, theme),
        )
        axes.set_xlabel(spec.x_label)
        axes.set_ylabel(spec.y_label)
    elif spec.mark in (Mark.LINE, Mark.STEP, Mark.AREA):
        values = [float(r.get(y_field, 0) or 0) for r in rows]
        drawstyle = "steps-post" if spec.mark is Mark.STEP else "default"
        axes.plot(range(len(values)), values, color=theme.accent, drawstyle=drawstyle)
        if spec.mark is Mark.AREA:
            axes.fill_between(
                range(len(values)),
                values,
                alpha=0.22,
                color=theme.accent,
                step="post" if drawstyle != "default" else None,
            )
        axes.set_ylabel(spec.y_label)
    elif spec.mark is Mark.BOX:
        stats = [
            {
                "label": str(r.get("label", "")),
                "med": float(r.get("median", 0) or 0),
                "q1": float(r.get("q1", 0) or 0),
                "q3": float(r.get("q3", 0) or 0),
                "whislo": float(r.get("min", 0) or 0),
                "whishi": float(r.get("max", 0) or 0),
                "fliers": [float(v) for v in r.get("outliers", [])],
            }
            for r in rows
        ]
        # `orientation` replaced `vert` in matplotlib 3.10; keep both paths so
        # the renderer works across the supported range without a warning.
        import matplotlib as _mpl
        from packaging.version import Version as _V

        orient = (
            {"orientation": "horizontal"} if _V(_mpl.__version__) >= _V("3.10") else {"vert": False}
        )
        axes.bxp(
            stats,
            showfliers=True,
            patch_artist=True,
            **orient,
            boxprops={"facecolor": theme.accent_soft, "edgecolor": theme.accent},
            medianprops={"color": theme.foreground},
        )
    elif spec.mark in (Mark.MATRIX, Mark.HEATMAP):
        labels = sorted({str(r["left"]) for r in rows} | {str(r["right"]) for r in rows})
        index = {label: i for i, label in enumerate(labels)}
        grid = [[0.0] * len(labels) for _ in labels]
        for row in rows:
            grid[index[str(row["right"])]][index[str(row["left"])]] = float(row["value"])
        image = axes.imshow(grid, cmap="RdBu_r", vmin=-1, vmax=1)
        axes.set_xticks(range(len(labels)))
        axes.set_xticklabels(labels, rotation=90, fontsize=7)
        axes.set_yticks(range(len(labels)))
        axes.set_yticklabels(labels, fontsize=7)
        figure.colorbar(image, ax=axes, shrink=0.8)
    elif spec.mark is Mark.TEXT:
        axes.set_axis_off()
        for i, row in enumerate(rows[:8]):
            axes.text(
                0.02,
                0.92 - i * 0.12,
                str(row.get("value", "")),
                fontsize=18,
                fontweight="bold",
                color=theme.foreground,
            )
            axes.text(
                0.02, 0.86 - i * 0.12, str(row.get("label", "")), fontsize=8, color=theme.muted
            )
    else:  # pragma: no cover - every Mark is covered above
        axes.text(
            0.5,
            0.5,
            f"No matplotlib renderer for {spec.mark.value}",
            ha="center",
            color=theme.muted,
        )
        axes.set_axis_off()

    for orientation, value, label in spec.rules:
        line = axes.axvline if orientation == "x" else axes.axhline
        line(value, color=theme.warning, linestyle="--", linewidth=1)
        if label:
            axes.annotate(
                label,
                xy=(value, 0),
                xycoords=("data", "axes fraction"),
                fontsize=7,
                color=theme.warning,
                rotation=90,
                va="bottom",
                ha="right",
            )

    if spec.y_domain is not None:
        # A shared domain is the spec's instruction, not a suggestion: panels
        # drawn to different scales cannot be compared, and comparison is the
        # only reason small multiples exist.
        axes.set_ylim(*spec.y_domain)
    axes.set_title(spec.title, fontsize=11, fontweight="600", loc="left")
    caption = spec.rationale
    if spec.is_sampled:
        caption = f"{caption}  [{spec.fidelity.value}: {spec.fidelity_note}]"
    if caption:
        figure.text(0.01, 0.01, caption[:150], fontsize=7, color=theme.muted)
    figure.tight_layout(rect=(0, 0.04, 1, 1))
    return figure


# --------------------------------------------------------------------------
# Plotly
# --------------------------------------------------------------------------


def to_plotly(spec: ChartSpec, theme: Theme = LIGHT) -> Any:
    """Build a Plotly figure -- zoom, pan, box and lasso select, rich hover.

    This is what ``Interaction.EXPLORE`` properly means. The SVG renderer's
    hover titles are ``Interaction.HOVER`` -- a convenience for reading, not an
    analysis tool -- and calling them interactive would overstate what they do.

    Interaction is not animation: a figure built from a spec with an
    ``animation_field`` is still only as interactive as its
    :class:`~smartprep.viz.spec.Interaction` level says.
    """
    _require("plotly", "viz")
    import plotly.graph_objects as go

    if spec.is_faceted:
        return _plotly_facets(spec, theme)

    rows = spec.data
    x_field = spec.x.field if spec.x else "x"
    y_field = spec.y.field if spec.y else "y"
    figure = go.Figure()

    if not rows:
        figure.add_annotation(text="No data to display.", showarrow=False)
    elif spec.mark is Mark.HORIZONTAL_BAR:
        figure.add_trace(
            go.Bar(
                x=[float(r.get(x_field, 0) or 0) for r in rows],
                y=[str(r.get(y_field, "")) for r in rows],
                orientation="h",
                marker_color=[spec.colour_of(r, theme.series) or theme.accent for r in rows],
            )
        )
    elif spec.mark in (Mark.BAR, Mark.HISTOGRAM):
        key = "centre" if spec.mark is Mark.HISTOGRAM else x_field
        value_key = "count" if spec.mark is Mark.HISTOGRAM else y_field
        figure.add_trace(
            go.Bar(
                x=[r.get(key, "") for r in rows],
                y=[float(r.get(value_key, 0) or 0) for r in rows],
                # The colour channel comes from the spec, and the group order
                # comes from the spec too, so a category is the same colour
                # here as it is in the SVG and in the PDF.
                marker_color=[spec.colour_of(r, theme.series) or theme.accent for r in rows],
            )
        )
    elif spec.mark is Mark.SCATTER:
        figure.add_trace(
            go.Scattergl(
                x=[float(r.get(x_field, 0) or 0) for r in rows],
                y=[float(r.get(y_field, 0) or 0) for r in rows],
                mode="markers",
                marker={
                    "color": [spec.colour_of(r, theme.series) or theme.accent for r in rows],
                    "opacity": 0.6,
                    "size": ([spec.size_of(r, 4.0, 16.0) for r in rows] if spec.size else 6),
                },
            )
        )
    elif spec.mark in (Mark.LINE, Mark.STEP, Mark.AREA):
        figure.add_trace(
            go.Scatter(
                x=[r.get(x_field, i) for i, r in enumerate(rows)],
                y=[float(r.get(y_field, 0) or 0) for r in rows],
                mode="lines",
                line={"color": theme.accent, "shape": "hv" if spec.mark is Mark.STEP else "linear"},
                fill="tozeroy" if spec.mark is Mark.AREA else None,
            )
        )
    elif spec.mark is Mark.BOX:
        for row in rows:
            figure.add_trace(
                go.Box(
                    name=str(row.get("label", "")),
                    q1=[float(row.get("q1", 0) or 0)],
                    median=[float(row.get("median", 0) or 0)],
                    q3=[float(row.get("q3", 0) or 0)],
                    lowerfence=[float(row.get("min", 0) or 0)],
                    upperfence=[float(row.get("max", 0) or 0)],
                    orientation="h",
                    marker_color=theme.accent,
                )
            )
    elif spec.mark in (Mark.MATRIX, Mark.HEATMAP):
        labels = sorted({str(r["left"]) for r in rows} | {str(r["right"]) for r in rows})
        index = {label: i for i, label in enumerate(labels)}
        grid = [[0.0] * len(labels) for _ in labels]
        for row in rows:
            grid[index[str(row["right"])]][index[str(row["left"])]] = float(row["value"])
        figure.add_trace(
            go.Heatmap(z=grid, x=labels, y=labels, zmin=-1, zmax=1, colorscale="RdBu_r")
        )
    elif spec.mark is Mark.TEXT:
        for i, row in enumerate(rows[:8]):
            figure.add_annotation(
                x=0,
                y=1 - i * 0.14,
                xref="paper",
                yref="paper",
                showarrow=False,
                text=f"<b style='font-size:20px'>{row.get('value', '')}</b><br>"
                f"<span style='color:{theme.muted}'>{row.get('label', '')}</span>",
                align="left",
            )
        figure.update_xaxes(visible=False)
        figure.update_yaxes(visible=False)

    for orientation, value, label in spec.rules:
        figure.add_shape(
            type="line",
            **(
                {"x0": value, "x1": value, "y0": 0, "y1": 1, "yref": "paper"}
                if orientation == "x"
                else {"y0": value, "y1": value, "x0": 0, "x1": 1, "xref": "paper"}
            ),
            line={"color": theme.warning, "dash": "dash", "width": 1},
        )
        if label:
            figure.add_annotation(
                text=label,
                showarrow=False,
                font={"size": 9, "color": theme.warning},
                **(
                    {"x": value, "y": 1, "yref": "paper"}
                    if orientation == "x"
                    else {"y": value, "x": 1, "xref": "paper"}
                ),
            )

    subtitle = spec.rationale
    if spec.is_sampled:
        subtitle = f"{subtitle}  [{spec.fidelity.value}: {spec.fidelity_note}]"

    figure.update_layout(
        title={"text": spec.title, "x": 0, "font": {"size": 14}},
        xaxis_title=spec.x_label or None,
        yaxis_title=spec.y_label or None,
        width=spec.width,
        height=spec.height + 40,
        paper_bgcolor=theme.background,
        plot_bgcolor=theme.background,
        font={"family": theme.font, "color": theme.foreground, "size": 11},
        margin={"l": 70, "r": 20, "t": 50, "b": 60},
        showlegend=False,
        # The spec's Interaction ceiling, honoured rather than assumed. A spec
        # bound for print declares NONE and gets a picture even here; only
        # EXPLORE gets the box and lasso select that make a chart an analysis
        # tool rather than an illustration.
        yaxis_range=list(spec.y_domain) if spec.y_domain else None,
        dragmode={
            Interaction.NONE: False,
            Interaction.HOVER: False,
            Interaction.EXPLORE: "zoom",
        }[spec.interaction],
        hovermode="closest" if spec.is_interactive else False,
        annotations=list(figure.layout.annotations)
        + (
            [
                {
                    "text": subtitle[:150],
                    "showarrow": False,
                    "x": 0,
                    "y": -0.22,
                    "xref": "paper",
                    "yref": "paper",
                    "align": "left",
                    "font": {"size": 9, "color": theme.muted},
                }
            ]
            if subtitle
            else []
        ),
    )
    return figure


def _plotly_facets(spec: ChartSpec, theme: Theme) -> Any:
    """Small multiples as Plotly subplots, drawn from ordinary panels."""
    from plotly.subplots import make_subplots

    panels = spec.panels()
    columns = min(3, len(panels))
    rows_of = (len(panels) + columns - 1) // columns
    figure = make_subplots(
        rows=rows_of,
        cols=columns,
        subplot_titles=[p.title for p in panels],
        shared_yaxes=True,
    )
    for index, panel in enumerate(panels):
        for trace in to_plotly(panel, theme).data:
            figure.add_trace(trace, row=index // columns + 1, col=index % columns + 1)

    if panels and panels[0].y_domain is not None:
        figure.update_yaxes(range=list(panels[0].y_domain))
    figure.update_layout(
        title={"text": spec.title, "x": 0, "font": {"size": 14}},
        showlegend=False,
        paper_bgcolor=theme.background,
        plot_bgcolor=theme.background,
        font={"family": theme.font, "color": theme.foreground, "size": 10},
        height=spec.height * rows_of * 0.8 + 60,
        width=spec.width,
    )
    return figure


# --------------------------------------------------------------------------
# Saving
# --------------------------------------------------------------------------


def save_chart(
    spec: ChartSpec,
    path: str,
    *,
    backend: str | None = None,
    theme: Theme = LIGHT,
    dpi: int = 200,
) -> str:
    """Write a chart to disk. The format follows the file suffix.

    ``.svg`` needs nothing. ``.png`` and ``.pdf`` need matplotlib; ``.html``
    prefers plotly and falls back to embedded SVG, so the call still succeeds
    without it.
    """
    import pathlib

    target = pathlib.Path(path)
    suffix = target.suffix.lower()

    if suffix == ".svg" and backend in (None, "svg"):
        target.write_text(render_svg(spec, theme), encoding="utf-8")
        return str(target.resolve())

    if suffix in (".png", ".pdf", ".svg"):
        figure = to_matplotlib(spec, theme)
        figure.savefig(target, dpi=dpi, bbox_inches="tight", facecolor=figure.get_facecolor())
        import matplotlib.pyplot as plt

        plt.close(figure)
        return str(target.resolve())

    if suffix in (".html", ".htm"):
        if backend == "plotly" or available_backends()["plotly"]:
            to_plotly(spec, theme).write_html(str(target), include_plotlyjs="inline")
        else:
            # Still self-contained, just not interactive -- better than failing.
            target.write_text(
                f"<!doctype html><meta charset='utf-8'><title>{spec.title}</title>"
                f"{render_svg(spec, theme)}",
                encoding="utf-8",
            )
        return str(target.resolve())

    if suffix == ".json":
        target.write_text(spec.to_json(indent=2), encoding="utf-8")
        return str(target.resolve())

    raise ValueError(
        f"cannot infer a format from {target.suffix!r}; expected .svg, .png, .pdf, .html or .json"
    )
