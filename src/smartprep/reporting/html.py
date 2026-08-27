"""Self-contained HTML reporting, and the Studio built on the same parts.

One file, no CDN, no build step, no server. That constraint is not modesty --
a report that needs a network to render is a report that stops working the
moment it is archived, emailed or opened on a locked-down machine.

The Studio is the same rendering pipeline with navigation and decision capture
added. It holds **no cleaning logic of its own**: every number in it was
computed by the core, and every decision it captures is exported as the same
JSON that ``guided_prepare(decisions=...)`` replays. A click that cannot be
replayed is not allowed to exist.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..viz.spec import ChartSet, ChartSpec
from ..viz.svg import LIGHT, Theme, render_svg
from .interactive import CHART_SCRIPT, GRID_CSS, GRID_SCRIPT, data_grid_html
from .linked import BUILDER_SCRIPT, LINKED_CSS, SANDBOX_SCRIPT, STATE_SCRIPT

if TYPE_CHECKING:  # pragma: no cover
    from ..prepare import PreparationResult
    from ..scan import ScanResult

__all__ = ["HtmlDocument", "Section", "scan_html", "preparation_html", "studio_html"]


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


CSS = """
:root {
  /* Every token that carries text clears 4.5:1 against --bg. --muted and
     --warn previously measured 3.66 and 3.64: a caveat a reader cannot
     read is a caveat that was not given. */
  --bg: #ffffff; --fg: #1f2933; --muted: #5c6873; --line: #e4e7eb;
  --accent: #2f6f9f; --warn: #8a5a10; --danger: #b83232; --ok: #2f855a;
  --panel: #f7f9fa;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 14px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
.wrap { display: flex; min-height: 100vh; }
nav { width: 200px; flex: 0 0 200px; border-right: 1px solid var(--line);
  padding: 20px 0; position: sticky; top: 0; height: 100vh; overflow-y: auto;
  background: var(--panel); }
nav h1 { font-size: 14px; margin: 0 18px 16px; letter-spacing: .02em; }
nav a { display: block; padding: 7px 18px; color: var(--fg); text-decoration: none;
  font-size: 13px; border-left: 3px solid transparent; }
nav a:hover { background: #eef2f4; }
/* Accessibility. A keyboard user must be able to see where they are, and a
   reader who has asked their system for less motion must be listened to --
   the stage walkthrough is meaningful motion, which is not the same as
   motion everybody can tolerate. */
a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible,
[tabindex]:focus-visible, th:focus-visible, tr:focus-visible {
  outline: 3px solid var(--accent); outline-offset: 2px; border-radius: 3px; }
.skip-link { position: absolute; left: -9999px; top: 0; background: var(--accent);
  color: #fff; padding: 9px 14px; z-index: 99; border-radius: 0 0 5px 0; }
.skip-link:focus { left: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .001ms !important;
    animation-iteration-count: 1 !important; transition-duration: .001ms !important;
    scroll-behavior: auto !important; }
}
nav a.active { border-left-color: var(--accent); font-weight: 600; color: var(--accent); }
main { flex: 1; padding: 28px 34px 80px; max-width: 1180px; }
section { display: none; }
section.active { display: block; }
h2 { font-size: 20px; margin: 0 0 6px; }
h3 { font-size: 15px; margin: 26px 0 10px; }
.lede { color: var(--muted); margin: 0 0 22px; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(165px, 1fr));
  gap: 12px; margin: 18px 0 26px; }
.card { border: 1px solid var(--line); border-radius: 7px; padding: 13px 15px; }
.card .k { font-size: 11px; color: var(--muted); text-transform: uppercase;
  letter-spacing: .05em; }
.card .v { font-size: 23px; font-weight: 600; margin-top: 3px; }
.card .n { font-size: 11px; color: var(--muted); margin-top: 2px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0 22px; font-size: 13px; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line);
  vertical-align: top; }
th { font-weight: 600; font-size: 11px; text-transform: uppercase;
  letter-spacing: .04em; color: var(--muted); }
tbody tr:hover { background: var(--panel); }
code, .mono { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 12px; }
.tag { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 11px;
  font-weight: 600; border: 1px solid; }
.tag.ok { color: var(--ok); border-color: #b7dfc6; background: #f0f9f4; }
.tag.warn { color: var(--warn); border-color: #ecd9a8; background: #fdf8ee; }
.tag.danger { color: var(--danger); border-color: #eec0c0; background: #fdf2f2; }
.tag.muted { color: var(--muted); border-color: var(--line); background: var(--panel); }
.charts { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 16px; }
.chart { border: 1px solid var(--line); border-radius: 7px; padding: 8px;
  overflow-x: auto; }
.chart svg { display: block; max-width: 100%; height: auto; }
.notice { border-left: 3px solid var(--warn); background: #fdf8ee; padding: 12px 16px;
  margin: 18px 0; border-radius: 0 5px 5px 0; }
.notice.strong { border-left-color: var(--danger); background: #fdf2f2; }
.notice h4 { margin: 0 0 5px; font-size: 13px; }
.notice p { margin: 0; font-size: 13px; }
.issue { border: 1px solid var(--line); border-radius: 7px; padding: 13px 15px;
  margin-bottom: 11px; }
.issue .hd { display: flex; gap: 9px; align-items: center; flex-wrap: wrap; }
.issue .id { font-weight: 600; font-family: ui-monospace, Menlo, monospace;
  font-size: 12px; }
.issue .why { color: var(--muted); font-size: 12px; margin-top: 7px; }
.issue .why b { color: var(--fg); font-weight: 600; }
.decide { margin-top: 11px; display: flex; gap: 7px; flex-wrap: wrap;
  align-items: center; }
.decide button { font: inherit; font-size: 12px; padding: 4px 11px; cursor: pointer;
  border: 1px solid var(--line); background: #fff; border-radius: 5px; }
.decide button:hover { border-color: var(--accent); color: var(--accent); }
.decide button.sel { background: var(--accent); color: #fff; border-color: var(--accent); }
.decide input { font: inherit; font-size: 12px; padding: 4px 8px; flex: 1;
  min-width: 190px; border: 1px solid var(--line); border-radius: 5px; }
.bar { height: 7px; background: var(--line); border-radius: 4px; overflow: hidden; }
.bar > i { display: block; height: 100%; background: var(--accent); }
footer { margin-top: 44px; padding-top: 14px; border-top: 1px solid var(--line);
  color: var(--muted); font-size: 12px; }
.export { position: fixed; right: 22px; bottom: 22px; background: var(--accent);
  color: #fff; border: none; border-radius: 7px; padding: 11px 17px; cursor: pointer;
  font: inherit; font-size: 13px; box-shadow: 0 2px 9px rgba(0,0,0,.16); }
.export:disabled { background: var(--muted); cursor: default; }
@media print {
  nav, .export { display: none; }
  section { display: block !important; page-break-after: always; }
}
"""

SCRIPT = """
(function () {
  var links = document.querySelectorAll('nav a');
  var panes = document.querySelectorAll('section');
  function show(id) {
    panes.forEach(function (p) { p.classList.toggle('active', p.id === id); });
    links.forEach(function (a) { a.classList.toggle('active', a.dataset.target === id); });
  }
  links.forEach(function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); show(a.dataset.target); });
  });
  if (panes.length) { show(panes[0].id); }

  // Decisions are recorded here and exported as the same JSON that
  // guided_prepare(decisions=...) replays. Nothing is applied in the browser.
  var decisions = {};
  document.querySelectorAll('.decide button').forEach(function (b) {
    b.addEventListener('click', function () {
      var box = b.closest('.issue');
      var id = box.dataset.issue;
      box.querySelectorAll('.decide button').forEach(function (o) {
        o.classList.remove('sel');
      });
      b.classList.add('sel');
      var reasonBox = box.querySelector('input');
      decisions[id] = {
        issue_id: id,
        action: b.dataset.action,
        treatment: b.dataset.treatment || null,
        reason: reasonBox ? reasonBox.value : ''
      };
      var out = document.getElementById('export');
      if (out) {
        out.disabled = false;
        out.textContent = 'Export ' + Object.keys(decisions).length + ' decision(s)';
      }
    });
  });

  var button = document.getElementById('export');
  if (button) {
    button.addEventListener('click', function () {
      var list = Object.keys(decisions).map(function (k) {
        var d = decisions[k];
        var box = document.querySelector('[data-issue="' + k + '"] input');
        if (box) { d.reason = box.value; }
        return d;
      });
      var payload = JSON.stringify(
        { schema_version: 1, level: 'standard', decisions: list }, null, 2);
      navigator.clipboard && navigator.clipboard.writeText(payload);
      var pre = document.getElementById('decisions-json');
      if (pre) {
        pre.textContent = payload;
        pre.parentElement.style.display = 'block';
        pre.scrollIntoView({ behavior: 'smooth' });
      }
    });
  }
})();
"""


@dataclass
class Section:
    """One navigable pane."""

    id: str
    title: str
    body: str


class HtmlDocument:
    """Assembles sections into one self-contained page."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        theme: Theme = LIGHT,
        *,
        interactive: bool = False,
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.theme = theme
        self.sections: list[Section] = []
        self.floating: str = ""
        #: Interactivity is opt-in, and the archival report deliberately does
        #: not get it. A file meant to open correctly in ten years should not
        #: depend on scripts having run.
        self.interactive = interactive
        self.payloads: dict[str, Any] = {}

    def add(self, section: Section) -> HtmlDocument:
        self.sections.append(section)
        return self

    def render(self) -> str:
        nav = "".join(
            f'<a href="#{s.id}" data-target="{s.id}">{_esc(s.title)}</a>' for s in self.sections
        )
        panes = "".join(f'<section id="{s.id}">{s.body}</section>' for s in self.sections)

        css = CSS + ((GRID_CSS + LINKED_CSS) if self.interactive else "")
        data = ""
        if self.payloads:
            body = "".join(
                f"window.{name} = {json.dumps(value, ensure_ascii=False, default=str)};"
                for name, value in self.payloads.items()
            )
            data = f"<script>{body}</script>"
        # Order matters: the state store must exist before any panel
        # subscribes to it. Everything else is a subscriber.
        scripts = STATE_SCRIPT + GRID_SCRIPT + CHART_SCRIPT + BUILDER_SCRIPT + SANDBOX_SCRIPT
        extra = f"<script>{scripts}</script>" if self.interactive else ""

        return (
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>{_esc(self.title)}</title><style>{css}</style></head><body>"
            "<a class='skip-link' href='#content'>Skip to content</a>"
            f"<div class='wrap'><nav aria-label='Sections'>"
            f"<h1>{_esc(self.title)}</h1>{nav}</nav>"
            f"<main id='content' tabindex='-1'>{panes}"
            "<footer>Generated by SmartPrep. Scan coverage measures checks executed, "
            "not data correctness. <code>clean_df</code> is not a verified dataset."
            "</footer></main></div>"
            f"{self.floating}{data}<script>{SCRIPT}</script>{extra}</body></html>"
        )


# -- fragments -------------------------------------------------------------


def _cards(items: list[tuple[str, Any, str]]) -> str:
    cells = "".join(
        f"<div class='card'><div class='k'>{_esc(k)}</div>"
        f"<div class='v'>{_esc(v)}</div>"
        f"<div class='n'>{_esc(note)}</div></div>"
        for k, v, note in items
    )
    return f"<div class='cards'>{cells}</div>"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "<p class='lede'>Nothing to show.</p>"
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def chart_data_table(spec: ChartSpec, limit: int = 60) -> str:
    """The chart's numbers, as a table.

    A picture is not an accessible format. Alt text can say what a chart is
    *about*; only the numbers say what it shows, and a reader using a screen
    reader is entitled to the same evidence as one who can see the bars. It
    doubles as the answer to "what exactly is that value?", which sighted
    readers ask of every chart anyway.

    Built from ``spec.data`` -- the same rows the renderer drew -- so the
    table and the picture cannot disagree.
    """
    rows = [r for r in spec.data if r]
    if not rows:
        return ""
    columns = [k for k in rows[0] if k != "keys"]
    if not columns:
        return ""

    head = "".join(f"<th scope='col'>{_esc(c)}</th>" for c in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{_esc(_number(row.get(c)))}</td>" for c in columns) + "</tr>"
        for row in rows[:limit]
    )
    more = (
        f"<p class='lede'>Showing {limit} of {len(rows):,} points.</p>" if len(rows) > limit else ""
    )
    return (
        "<details class='data-table'><summary>Show the numbers behind this chart"
        "</summary>"
        f"<table><caption class='sr-only'>Data for: {_esc(spec.title)}</caption>"
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>{more}</details>"
    )


def _number(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.4g}"
    return f"{value:,}" if isinstance(value, int) else str(value)


def _figure(spec: ChartSpec, theme: Theme, *, table: bool = True) -> str:
    """One chart: the picture, its caption, and its numbers."""
    caption = spec.rationale
    if spec.is_sampled:
        caption = f"{caption} [{spec.fidelity.value}: {spec.fidelity_note}]".strip()
    return (
        "<div class='chart'><figure>"
        f"{render_svg(spec, theme)}"
        + (f"<figcaption>{_esc(caption)}</figcaption>" if caption else "")
        + "</figure>"
        + (chart_data_table(spec) if table else "")
        + "</div>"
    )


def _charts(chart_set: ChartSet, theme: Theme) -> str:
    if not len(chart_set):
        return ""
    blocks = "".join(_figure(c, theme) for c in chart_set)
    return f"<div class='charts'>{blocks}</div>"


def _chart(spec: ChartSpec | None, theme: Theme) -> str:
    return "" if spec is None else _figure(spec, theme)


def _class_tag(name: str) -> str:
    if name in ("SAFE_AUTO_FIX", "AUTO_FIX_WITH_LOG"):
        return "ok"
    if name == "DO_NOT_TOUCH":
        return "danger"
    return "warn"


def _issue_block(issue: Any, *, decidable: bool = False) -> str:
    repair_class, reasons = issue.triage()
    why = "".join(f"<div class='why'><b>why:</b> {_esc(r)}</div>" for r in reasons)

    buttons = ""
    if decidable:
        from ..repair.actions import has_action

        options = [t for t in issue.treatments if has_action(t.name)]
        parts = [
            f"<button data-action='choose_alternative' data-treatment='{_esc(t.name)}'>"
            f"{_esc(t.name)} ({t.repair_confidence:.0%})</button>"
            for t in options
        ]
        parts.append("<button data-action='skip'>skip</button>")
        parts.append("<button data-action='waive'>waive</button>")
        parts.append("<input placeholder='reason (required to waive)'>")
        buttons = f"<div class='decide'>{''.join(parts)}</div>"

    return (
        f"<div class='issue' data-issue='{_esc(issue.id)}'>"
        f"<div class='hd'><span class='id'>{_esc(issue.id)}</span>"
        f"<span class='tag {_class_tag(repair_class.name)}'>{_esc(repair_class.name)}</span>"
        f"<span class='tag muted'>{_esc(issue.severity.name)}</span>"
        f"<span class='tag muted'>{issue.affected_row_count} rows</span></div>"
        f"<div>{_esc(issue.evidence.summary)}</div>{why}{buttons}</div>"
    )


def _profile_section(frame: Any, theme: Theme) -> tuple[str, ChartSet, Any]:
    from ..eda import associations, missingness, profile

    dataset_profile = profile(frame)
    matrix = associations(frame, dataset_profile)
    pattern = missingness(frame)

    def _flag(column: Any) -> str:
        if column.is_identifier_like:
            return "identifier"
        return "constant" if column.is_constant else ""

    rows = [
        [
            f"<code>{_esc(c.name)}</code>",
            f"<span class='tag muted'>{_esc(c.kind.value)}</span>",
            f"{c.missing} ({c.missing_rate:.1%})",
            str(c.distinct),
            _flag(c),
        ]
        for c in dataset_profile.columns_profiled.values()
    ]
    body = (
        _cards(
            [
                ("Rows", f"{dataset_profile.rows:,}", ""),
                ("Columns", dataset_profile.columns, ""),
                (
                    "Missing cells",
                    f"{dataset_profile.missing_cells:,}",
                    f"{dataset_profile.missing_rate:.2%}",
                ),
                ("Duplicate rows", dataset_profile.duplicate_rows, ""),
                ("Memory", f"{dataset_profile.memory_bytes / 1024:.0f} KB", ""),
            ]
        )
        + "<h3>Columns</h3>"
        + _table(["column", "kind", "missing", "distinct", "flags"], rows)
    )
    from ..viz import overview_charts

    return body, overview_charts(dataset_profile, matrix, pattern), dataset_profile


def _smart_grid(
    frame: Any, scan_result: ScanResult, identity: Any = None
) -> tuple[str, dict[str, Any]]:
    """Grid shell plus the row payload, with quality flags per cell.

    The overlay is the whole reason this is not merely a table: a cell that is
    part of a finding is coloured, so a reader sees *where* the problem is
    rather than reading that one exists.
    """
    from ..detectors.base import is_missing

    columns = [str(c) for c in frame.columns]
    flagged: dict[int, set[str]] = {}
    for issue in scan_result.issues:
        for position in issue.rows.positions:
            flagged.setdefault(position, set()).update(issue.columns)

    # Capped: a browser asked to hold a million rows in one payload stops being
    # a tool. The cap is stated on the page rather than applied silently.
    limit = 500
    rows = []
    for position in range(min(len(frame), limit)):
        record = frame.iloc[position]
        cells, flags = [], []
        for column in columns:
            value = record[column]
            cells.append("" if is_missing(value) else str(value)[:90])
            if is_missing(value):
                flags.append("missing")
            elif column in flagged.get(position, ()):
                flags.append("flagged")
            else:
                flags.append("")
        rows.append(
            {
                "i": position,
                # The stable key, so a row selected here is the same row a
                # chart highlights -- and still the same row after a repair.
                "key": identity.key_at(position) if identity is not None else str(position),
                "cells": cells,
                "flags": flags,
            }
        )

    note = ""
    if len(frame) > limit:
        note = (
            f"<p class='lede'>Showing the first {limit:,} of {len(frame):,} rows. "
            "The full dataset stays in Python.</p>"
        )
    return note + data_grid_html(columns), {"columns": columns, "rows": rows}


#: How many compositions ship inside the page.
#:
#: Every precomputed chart is markup that travels with the file, so the full
#: cross product of a twenty-column frame produced a workspace nobody could
#: email. Anything past the cap is reachable through the Python line the
#: builder prints.
_MAX_PRECOMPOSED = 28


def _visual_builder(
    frame: Any, dataset_profile: Any, theme: Theme, identity: Any = None
) -> tuple[str, dict[str, Any]]:
    """Drag a field onto a shelf, or select it and press 1 or 2.

    The builder does not aggregate. Every combination it can show was composed
    in Python by :func:`smartprep.viz.compose` and rendered before the page was
    written, so a chart a reader assembles by hand is the same kind of object
    as one the report generated, computed by the same code. A combination
    nobody precomputed is answered with the Python line that produces it --
    honest about what a single file can do, rather than a second aggregation
    engine written in JavaScript.
    """
    from ..viz.compose import Composition, CompositionRefused, compose, fields_of, recommend

    fields = fields_of(dataset_profile)
    usable = [f for f in fields if f.plottable is None]
    if not usable:
        return "<h2>Build</h2><p class='lede'>No column here can be plotted.</p>", {}

    quantities = [f for f in usable if f.is_quantitative][:5]
    categories = [f for f in usable if f.is_categorical and f.distinct <= 40][:5]
    times = [f for f in usable if f.is_temporal][:2]

    # The catalogue is capped, and the cap is the honest consequence of a
    # single-file design: every precomputed chart is markup that ships with
    # the page, and the full cross product of twenty columns is a workspace
    # nobody can email. Single-field charts first (the cheapest and the most
    # asked for), then the explained recommendations, then a thin slice of
    # pairings. Anything beyond it is reachable through the Python line the
    # builder prints, which is the designed escape hatch rather than a gap.
    wanted: list[Composition] = []
    for measure in quantities:
        wanted.append(Composition(x=measure.name))
    for category in categories:
        wanted.append(Composition(x=category.name))
    wanted.extend(r.composition for r in recommend(fields, limit=10))
    for category in categories[:3]:
        for measure in quantities[:2]:
            wanted.append(Composition(x=category.name, y=measure.name, aggregate="mean"))
    for when in times[:1]:
        for measure in quantities[:2]:
            wanted.append(Composition(x=when.name, y=measure.name))

    specs: dict[str, dict[str, str]] = {}

    # The single-column views the composition grammar cannot express: an ECDF
    # and a box plot are alternative readings of one field rather than a
    # pairing of two, and a target chart asks a question about a column that
    # is not on either axis. They lived in a second panel that otherwise
    # duplicated this one; folding them in removes the duplicate rather than
    # dropping the capability.
    from ..viz import box_chart, ecdf_chart, target_chart

    for measure in quantities:
        column = dataset_profile.get(measure.name)
        for suffix, built in (
            ("ecdf", ecdf_chart(column)),
            ("box", box_chart(column)),
        ):
            if built is None:
                continue
            specs[f"{measure.name}||{suffix}"] = {
                "svg": render_svg(built, theme),
                "rationale": built.rationale,
                "table": chart_data_table(built),
            }

    for category in categories[:3]:
        for measure in quantities[:2]:
            built = target_chart(frame, category.name, measure.name)
            if built is None:
                continue
            specs[f"{category.name}|{measure.name}|target"] = {
                "svg": render_svg(built, theme),
                "rationale": built.rationale,
                "table": chart_data_table(built),
            }

    for composition in wanted:
        if len(specs) >= _MAX_PRECOMPOSED:
            break
        signature = f"{composition.x or ''}|{composition.y or ''}|{composition.aggregate}"
        if signature in specs:
            continue
        try:
            spec = compose(frame, fields, composition, identity=identity)
        except (CompositionRefused, ValueError, KeyError):
            # A refusal is a legitimate answer. It simply does not become a
            # choice the reader can pick.
            continue
        specs[signature] = {
            "svg": render_svg(spec, theme),
            "rationale": spec.rationale,
            "table": chart_data_table(spec),
        }

    catalogue = {
        "fields": [f.to_dict() for f in fields],
        "recommendations": [r.to_dict() for r in recommend(fields, limit=6)],
        "specs": specs,
    }

    aggregates = "".join(
        f"<option value='{a}'{' selected' if a == 'count' else ''}>{a}</option>"
        for a in ("count", "mean", "sum", "median", "min", "max", "ecdf", "box", "target")
    )
    body = (
        "<h2>Build</h2>"
        "<p class='lede'>Drag a field onto a shelf, or focus one and press "
        "<kbd>1</kbd> for the first shelf and <kbd>2</kbd> for the second. Both "
        "routes build the same composition — the keyboard is not a lesser "
        "path.</p>"
        f"<p class='lede'>{len(specs)} combinations are built into this page. "
        "The Studio does not aggregate in the browser, so any other pairing is "
        "answered with the line of Python that produces it.</p>"
        "<div class='builder-grid'>"
        "<div class='field-well' id='field-well' role='listbox' "
        "aria-label='Fields available to plot'></div>"
        "<div>"
        "<div class='shelf' id='shelf-x' aria-label='First field'></div>"
        "<div class='shelf' id='shelf-y' aria-label='Second field'></div>"
        "<label style='font-size:11px;color:var(--muted)'>Read it as "
        f"<select id='compose-aggregate'>{aggregates}</select></label>"
        "<p class='lede mono' id='compose-why' role='status' aria-live='polite'></p>"
        "<div id='compose-out'></div>"
        "<h3>Suggested, with reasons</h3>"
        "<div class='recs' id='compose-recs'></div>"
        "</div></div>"
    )
    return body, catalogue


def _sandbox(frame: Any, scan_result: ScanResult) -> tuple[str, dict[str, Any]]:
    """What each candidate repair would do, before anybody chooses one.

    Nothing here is applied and nothing here can be. The sandbox has no commit
    button on purpose: a second path that changes data is the path that skips
    the audit, so committing goes back through Guided, which records who
    decided and why.
    """
    from ..repair.sandbox import preview_candidates

    decidable = [i for i in scan_result.issues if i.treatments][:12]
    if frame is None or not decidable:
        return (
            "<h2>Sandbox</h2><p class='lede'>No finding here has a treatment to weigh up.</p>",
            {},
        )

    previews: dict[str, Any] = {}
    options: list[str] = []
    for issue in decidable:
        candidates = preview_candidates(frame, issue, with_charts=False)
        if not candidates:
            continue
        previews[issue.id] = [c.to_dict() for c in candidates]
        options.append(f"<option value='{_esc(issue.id)}'>{_esc(issue.id)}</option>")

    if not options:
        return "<h2>Sandbox</h2><p class='lede'>Nothing to preview.</p>", {}

    body = (
        "<h2>Treatment sandbox</h2>"
        "<p class='lede'>Every candidate repair, and what it would actually do — "
        "how many cells move, which values, and what it costs the statistics you "
        "were about to reason from. Imputation always improves completeness; the "
        "spread beside it is what it spends.</p>"
        "<label style='font-size:11px;color:var(--muted)'>Finding "
        f"<select id='sandbox-issue'>{''.join(options)}</select></label>"
        "<div id='sandbox-out' style='margin-top:14px'></div>"
    )
    return body, previews


def _pipeline_canvas(run: Any, workflow: Any) -> str:
    """The pipeline, and what each stage actually cost.

    Every number here was computed by :mod:`smartprep.workflow` in Python and
    is rendered as text -- the canvas exposes execution, it does not perform
    it. A node's audit operations are named rather than restated, so the
    audit stays the single record of what changed.
    """
    import html as _html

    cards = []
    for position, outcome in enumerate(run.outcomes, start=1):
        node = workflow.ordered()[position - 1]
        status = outcome.status
        metrics = [
            f"<span><b>{outcome.cells_changed:,}</b> cells</span>",
            f"<span><b>{outcome.rows_affected:,}</b> rows</span>",
        ]
        if outcome.issues_resolved:
            metrics.append(f"<span class='up'><b>-{outcome.issues_resolved}</b> findings</span>")
        if outcome.issues_created:
            metrics.append(f"<span class='down'><b>+{outcome.issues_created}</b> findings</span>")
        delta = outcome.health_delta
        if delta:
            css = "up" if delta > 0 else "down"
            metrics.append(f"<span class='{css}'>health <b>{delta:+.1f}</b></span>")
        if outcome.elapsed_seconds:
            metrics.append(f"<span>{outcome.elapsed_seconds * 1000:.0f} ms</span>")
        if outcome.validation_passed is not None:
            word = "passed" if outcome.validation_passed else "FAILED"
            metrics.append(f"<span>validation <b>{word}</b></span>")

        warnings = "".join(
            f"<p class='warn'>{_html.escape(str(w))}</p>" for w in outcome.warnings[:3]
        )
        operations = ""
        if outcome.audit_operations:
            listed = ", ".join(outcome.audit_operations[:6])
            more = (
                f" and {len(outcome.audit_operations) - 6} more"
                if len(outcome.audit_operations) > 6
                else ""
            )
            operations = f"<p class='ops'>audit: {_html.escape(listed)}{more}</p>"

        cards.append(
            f"<div class='node {status}'>"
            f"<h4><span class='stage-no'>{position:02d}</span>"
            f"{_html.escape(node.label)}"
            f"<span class='tag {'ok' if status == 'ran' else 'muted'}'>{status}</span></h4>"
            f"<div class='metrics'>{''.join(metrics)}</div>"
            f"{warnings}{operations}</div>"
        )

    flow = "<div class='flow-arrow' aria-hidden='true'>\u2193</div>".join(cards)
    exported = _html.escape(workflow.to_python())

    return (
        "<h2>Pipeline</h2>"
        "<p class='lede'>Each stage is a filter over the plan the core already "
        "built, handed to the same executor. Running every stage produces the "
        "frame and the audit that <code>auto_prepare</code> produces \u2014 a test "
        "asserts it. Disabling one leaves its findings open and says so.</p>"
        f"<div class='canvas' role='list' aria-label='Preparation pipeline'>{flow}</div>"
        "<div class='canvas-export'><h3>This pipeline as Python</h3>"
        "<p class='lede'>A pipeline you cannot export is a pipeline you cannot "
        "review, version or run without a browser.</p>"
        f"<pre class='mono'>{exported}</pre></div>"
    )


def _link_bar(identity: Any) -> str:
    """The one place the page says what is filtered and what is selected."""
    warning = ""
    if identity is not None and not identity.is_stable:
        warning = (
            "<span class='warn-unstable'>Row identity is positional here: a "
            "selection will not survive a transformation.</span>"
        )
    return (
        "<div class='linkbar'>"
        "<span class='count' id='link-count' role='status' aria-live='polite'></span>"
        "<button type='button' id='link-clear'>Clear all</button>"
        "<button type='button' id='link-copy'>Copy view state</button>"
        f"{warning}"
        "</div>"
        "<div class='chips' id='filter-chips'></div>"
    )


def _stage_view(result: PreparationResult, theme: Theme) -> tuple[str, list[dict[str, str]]]:
    """Health across cleaning stages, as frames the reader steps through.

    The one animation that earns its place: the frames are ordered steps of a
    real process, so movement carries meaning. Nothing here moves for effect.
    """
    from ..viz import health_chart, issue_chart

    before_chart = issue_chart(result.before_scan.issues)
    after_chart = issue_chart(result.after_scan.issues)

    frames = [
        {
            "label": "Raw",
            "note": (
                f"{len(result.before_scan.issues)} findings, health "
                f"{result.health_before.overall:.0f}"
            ),
            "svg": render_svg(before_chart, theme) if before_chart else "",
        },
        {
            "label": "After safe repairs",
            "note": (
                f"{len(result.after_scan.issues)} findings, health "
                f"{result.health_after.overall:.0f}; "
                f"{len(result.audit.applied)} operations, "
                f"{result.cells_changed} cells changed"
            ),
            "svg": render_svg(after_chart, theme) if after_chart else "",
        },
        {
            "label": "Health by dimension",
            "note": "before against after, per dimension",
            "svg": render_svg(health_chart(result.health_before, result.health_after), theme),
        },
    ]

    return (
        "<h2>Cleaning stages</h2>"
        "<p class='lede'>Step through the stages. These frames are ordered steps of "
        "one process, which is the only reason motion belongs here.</p>"
        "<div class='stage-controls'>"
        "<button id='stage-play' type='button' aria-pressed='false' "
        "aria-controls='stage-out'>Play</button>"
        "<label class='sr-only' for='stage-slider'>Stage</label>"
        "<input type='range' id='stage-slider' min='0' value='0' step='1'>"
        "<label class='sr-only' for='stage-speed'>Playback speed</label>"
        "<select id='stage-speed'>"
        "<option value='1400'>slow</option>"
        "<option value='700' selected>normal</option>"
        "<option value='320'>fast</option>"
        "</select>"
        "</div>"
        "<div class='stage-steps' id='stage-steps' role='group' "
        "aria-label='Jump to a step'></div>"
        "<p class='mono' id='stage-label' role='status' aria-live='polite'></p>"
        "<div class='chart' id='stage-out'></div>",
        frames,
    )


def scan_html(result: ScanResult, frame: Any = None, *, theme: Theme = LIGHT) -> str:
    """Pre-cleaning report: profile, charts and findings, nothing modified."""
    from ..viz import issue_chart

    document = HtmlDocument("SmartPrep — Scan", theme=theme)
    health = result.health()

    overview = (
        "<h2>Scan</h2>"
        "<p class='lede'>RAW DATA — BEFORE CLEANING. Nothing here has been modified.</p>"
        + _cards(
            [
                ("Rows", f"{result.row_count:,}", ""),
                ("Columns", result.column_count, ""),
                ("Coverage", f"{result.coverage:.0%}", "of applicable checks"),
                ("Data health", f"{health.overall:.0f}", "out of 100"),
                ("Findings", len(result.issues), ""),
                ("Blocking", len(result.blocking), "must not be touched"),
            ]
        )
        + "<div class='notice'><h4>Coverage is not correctness</h4>"
        "<p>100% coverage means every applicable check finished. It says nothing "
        "about whether the data is right.</p></div>"
        + _chart(issue_chart(result.issues), theme)
        + _table(
            ["dimension", "score", "driven by"],
            [
                [
                    _esc(name),
                    f"<div class='bar'><i style='width:{d.score:.0f}%'></i></div> {d.score:.0f}",
                    f"<span class='mono'>{_esc(', '.join(d.contributing) or '—')}</span>",
                ]
                for name, d in sorted(health.dimensions.items())
            ],
        )
    )
    document.add(Section("overview", "Overview", overview))

    if frame is not None:
        body, charts, _ = _profile_section(frame, theme)
        document.add(Section("profile", "Profile", "<h2>Profile</h2>" + body))
        document.add(
            Section("eda", "EDA", "<h2>Exploratory analysis</h2>" + _charts(charts, theme))
        )

    findings = "<h2>Findings</h2>"
    for repair_class, issues in result.by_repair_class().items():
        findings += f"<h3>{_esc(repair_class.name)} ({len(issues)})</h3>"
        findings += "".join(_issue_block(i) for i in issues)
    document.add(Section("issues", "Findings", findings))

    coverage = "<h2>Checks</h2>" + _table(
        ["check", "status", "findings", "reason", "ms"],
        [
            [
                f"<code>{_esc(o.detector)}</code>",
                f"<span class='tag {'ok' if o.status == 'completed' else 'muted'}'>"
                f"{_esc(o.status)}</span>",
                str(o.issue_count),
                _esc(o.reason),
                f"{o.duration_ms:.1f}",
            ]
            for o in result.outcomes
        ],
    )
    document.add(Section("checks", "Checks", coverage))
    return document.render()


def preparation_html(
    result: PreparationResult, *, theme: Theme = LIGHT, decidable: bool = False
) -> str:
    """Post-cleaning report, with the mandatory disclosure of inaction."""
    from ..eda import compare_profiles, profile
    from ..viz import before_after_chart, health_chart, issue_chart

    document = HtmlDocument("SmartPrep — Preparation", theme=theme)
    before, after = result.health_before, result.health_after
    comparison = compare_profiles(profile(result.raw_df), profile(result.clean_df))

    status_tag = "ok" if result.status.value.startswith("CLEAN") else "warn"
    overview = (
        "<h2>Preparation</h2>"
        f"<p class='lede'>Status <span class='tag {status_tag}'>"
        f"{_esc(result.status.value)}</span></p>"
        + _cards(
            [
                ("Health", f"{before.overall:.0f} → {after.overall:.0f}", "out of 100"),
                ("Operations", len(result.audit.applied), "applied"),
                ("Cells changed", result.cells_changed, ""),
                (
                    "Findings",
                    f"{len(result.before_scan.issues)} → {len(result.after_scan.issues)}",
                    "",
                ),
                ("Needs review", len(result.review_queue), ""),
                ("Blocking", len(result.blocking_issues), ""),
            ]
        )
        + "<div class='notice strong'><h4>clean_df is not a verified dataset</h4>"
        "<p>Safe repairs have been applied. Findings that could not be resolved "
        "safely remain, and are listed below.</p></div>"
        + "<div class='charts'>"
        + _chart(health_chart(before, after), theme)
        + _chart(issue_chart(result.after_scan.issues), theme)
        + _chart(before_after_chart(comparison), theme)
        + "</div>"
    )
    document.add(Section("overview", "Overview", overview))

    not_done = "<h2>What auto mode did NOT do</h2>"
    not_done += "<p class='lede'>Mandatory section. Every finding left open, and why.</p>"
    if not result.review_queue:
        not_done += "<p>Nothing was left open.</p>"
    else:
        not_done += "".join(_issue_block(i, decidable=decidable) for i in result.review_queue)
    document.add(Section("open", "Open findings", not_done))

    changed = "<h2>Before / after</h2>"
    if comparison.red_flags:
        flags = "<br>".join(f"<b>{_esc(w)}</b>: {_esc(t)}" for w, t in comparison.red_flags)
        changed += f"<div class='notice'><h4>Red flags</h4><p>{flags}</p></div>"
    changed += _table(
        ["column", "status", "changes", "flags"],
        [
            [
                f"<code>{_esc(c.name)}</code>",
                _esc(c.status),
                "<span class='mono'>"
                + "<br>".join(f"{k}: {v[0]} → {v[1]}" for k, v in c.changes.items())
                + "</span>",
                "<br>".join(_esc(f) for f in c.flags),
            ]
            for c in comparison.columns
            if c.status != "unchanged"
        ],
    )
    document.add(Section("compare", "Before / after", changed))

    audit = "<h2>Audit</h2>" + _table(
        ["id", "operation", "columns", "cells", "applied", "reason"],
        [
            [
                f"<code>{_esc(r.operation_id)}</code>",
                f"<code>{_esc(r.operation)}</code>",
                _esc(", ".join(r.columns) or "—"),
                str(r.cells_changed),
                f"<span class='tag {'ok' if r.applied else 'muted'}'>"
                f"{'applied' if r.applied else 'refused'}</span>",
                _esc(r.reason),
            ]
            for r in result.audit
        ],
    )
    document.add(Section("audit", "Audit", audit))
    return document.render()


def _canvas_section(frame: Any, prepared: Any) -> str:
    """The pipeline canvas, when there is a prepared run to show one for."""
    if prepared is None:
        return ""
    from ..workflow import WorkflowError, default_workflow

    workflow = default_workflow()
    try:
        run = workflow.run(frame, **prepared.context)
    except (WorkflowError, ValueError, KeyError):
        # A canvas that cannot be built is not worth a broken panel.
        return ""
    return _pipeline_canvas(run, workflow)


def studio_html(
    result: PreparationResult | ScanResult,
    frame: Any = None,
    *,
    theme: Theme = LIGHT,
) -> str:
    """The Studio: navigation, EDA, findings and decision capture in one page.

    Decisions made here are **not applied in the browser**. They are exported as
    the JSON that ``guided_prepare(decisions=...)`` replays, so the interface
    can never become a second implementation of cleaning.
    """
    from ..prepare import PreparationResult as Prepared

    # Bind the narrowed value once rather than re-testing the union at every
    # use -- otherwise every access needs its own guard and one gets missed.
    prepared: PreparationResult | None = result if isinstance(result, Prepared) else None
    scan_result: ScanResult = prepared.after_scan if prepared else result  # type: ignore[assignment]
    source = frame if frame is not None else (prepared.clean_df if prepared else None)

    document = HtmlDocument("SmartPrep Studio", theme=theme, interactive=True)
    health = scan_result.health()

    # One identity and one state for the whole page. Every panel reads these
    # and nothing else, which is what makes a selection in the grid and a
    # highlight in a chart the same fact seen twice rather than two facts
    # that have to be kept in step.
    from ..core.identity import StableRowIndex
    from ..core.state import StudioState

    identity = StableRowIndex.of(source) if source is not None else None
    if source is not None:
        document.payloads["__SMARTPREP_STATE__"] = StudioState.of(source).to_dict()

    overview = (
        "<h2>Overview</h2>"
        + _cards(
            [
                ("Rows", f"{scan_result.row_count:,}", ""),
                ("Columns", scan_result.column_count, ""),
                ("Data health", f"{health.overall:.0f}", "out of 100"),
                ("Coverage", f"{scan_result.coverage:.0%}", "of applicable checks"),
                ("Findings", len(scan_result.issues), ""),
                ("Auto-fixable", len(scan_result.auto_fixable), ""),
                ("Needs review", len(scan_result.needs_review), ""),
                ("Blocking", len(scan_result.blocking), ""),
            ]
        )
        + "<div class='notice'><h4>This view applies nothing</h4>"
        "<p>Every number here was computed by the SmartPrep core. Decisions you "
        "record below are exported as JSON and replayed through "
        "<code>guided_prepare(decisions=...)</code>, so a click is always "
        "reproducible.</p></div>"
    )
    from ..viz import health_chart, issue_chart

    overview += "<div class='charts'>"
    overview += _chart(issue_chart(scan_result.issues), theme)
    if prepared is not None:
        overview += _chart(health_chart(prepared.health_before, prepared.health_after), theme)
    else:
        overview += _chart(health_chart(health), theme)
    overview += "</div>"
    document.add(Section("overview", "Overview", overview))

    if source is not None:
        body, charts, dataset_profile = _profile_section(source, theme)
        document.add(Section("data", "Data", "<h2>Data</h2>" + body))

        grid, grid_payload = _smart_grid(source, scan_result, identity)
        document.payloads["__SMARTPREP_GRID__"] = grid_payload
        document.add(
            Section(
                "grid",
                "Grid",
                "<h2>Smart data grid</h2>" + _link_bar(identity) + grid,
            )
        )

        document.add(
            Section("eda", "EDA", "<h2>Exploratory analysis</h2>" + _charts(charts, theme))
        )

        build, catalogue = _visual_builder(source, dataset_profile, theme, identity)
        document.payloads["__SMARTPREP_COMPOSITIONS__"] = catalogue
        document.add(Section("build", "Build", _link_bar(identity) + build))

        sandbox, previews = _sandbox(source, scan_result)
        document.payloads["__SMARTPREP_PREVIEWS__"] = previews
        document.add(Section("sandbox", "Sandbox", sandbox))

        canvas = _canvas_section(source, prepared)
        if canvas:
            document.add(Section("pipeline", "Pipeline", canvas))

    inbox = "<h2>Issue inbox</h2>"
    for repair_class, issues in scan_result.by_repair_class().items():
        inbox += f"<h3>{_esc(repair_class.name)} ({len(issues)})</h3>"
        inbox += "".join(_issue_block(i) for i in issues)
    document.add(Section("issues", "Issues", inbox))

    queue = prepared.review_queue if prepared is not None else scan_result.needs_review
    guided = (
        "<h2>Guided decisions</h2>"
        "<p class='lede'>Exactly what automatic mode refused to decide. Choose an "
        "option, then export.</p>"
        + ("".join(_issue_block(i, decidable=True) for i in queue) or "<p>Nothing open.</p>")
        + "<div style='display:none' class='chart'><h3>Decisions JSON</h3>"
        "<pre id='decisions-json' class='mono'></pre></div>"
    )
    document.add(Section("guided", "Guided", guided))

    if prepared is not None:
        stages_html, stage_payload = _stage_view(prepared, theme)
        document.payloads["__SMARTPREP_STAGES__"] = stage_payload
        document.add(Section("stages", "Stages", stages_html))

        audit = "<h2>Audit timeline</h2>" + _table(
            ["id", "operation", "columns", "cells", "applied", "reason"],
            [
                [
                    f"<code>{_esc(r.operation_id)}</code>",
                    f"<code>{_esc(r.operation)}</code>",
                    _esc(", ".join(r.columns) or "—"),
                    str(r.cells_changed),
                    f"<span class='tag {'ok' if r.applied else 'muted'}'>"
                    f"{'applied' if r.applied else 'refused'}</span>",
                    _esc(r.reason),
                ]
                for r in prepared.audit
            ],
        )
        document.add(Section("audit", "Audit", audit))

    document.floating = "<button class='export' id='export' disabled>No decisions yet</button>"
    return document.render()
