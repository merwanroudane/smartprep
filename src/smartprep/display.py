"""Tables built to journal convention, in every format the reader needs.

The core already knows everything worth reporting. What it lacked was a way
to say it: a notebook cell showed a nested dataclass with raw enum members,
and the one sentence that mattered was buried three lines into a ``repr``.

This module is that layer, and it computes nothing. A :class:`Table` is
handed values that already exist and decides only how they look --
alignment, precision, rules, order. Anything that counts, aggregates or
re-derives belongs upstream, because the moment a view calculates its own
number it acquires the ability to disagree with the object it came from.

**The conventions are not decoration.** Tables here follow the ones every
serious journal enforces, for reasons that survive the house style:

* **Horizontal rules only** -- above the header, below it, and at the foot.
  Vertical rules add ink without adding information; the eye already groups
  columns by alignment.
* **Figures right-aligned, text left.** Right alignment puts the units
  digit under the units digit, which is what makes two numbers comparable at
  a glance. Tabular figures keep the columns from shifting.
* **One precision per column**, chosen from the quantity rather than from
  whatever the float happened to be. ``0.9500000000000001`` is not more
  precise than ``0.95``, it is only longer.
* **Notes below the foot rule**, where caveats belong -- not in a footnote
  nobody scrolls to and not omitted.

Four output formats share one definition: plain text for a terminal,
Markdown for a report, HTML for a notebook, and LaTeX with ``booktabs`` for
a manuscript.
"""

from __future__ import annotations

import html as _html
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = ["Align", "Column", "Table", "format_number", "humanise"]


class Align(Enum):
    """Which edge a column's values line up against.

    Not cosmetic: right-aligned figures put the units digit under the units
    digit, which is what lets a reader compare two numbers without counting
    characters. Text reads from the left, so it aligns there.
    """

    LEFT = "left"
    RIGHT = "right"
    CENTRE = "center"

    @property
    def latex(self) -> str:
        return {"left": "l", "right": "r", "center": "c"}[self.value]


#: Typographic characters and what they degrade to in a terminal.
#:
#: A default Windows console is cp1252 and raises ``UnicodeEncodeError`` on an
#: em dash. A table that crashes the terminal it was written for is worse than
#: one that prints a hyphen, so plain text is transliterated and the richer
#: formats -- HTML, Markdown, LaTeX -- keep the real characters.
_ASCII = {"—": "-", "─": "-", "…": "...", "·": "-"}


def _ascii(text: str) -> str:
    for fancy, plain in _ASCII.items():
        text = text.replace(fancy, plain)
    return text


def format_number(value: Any, precision: int | None = None, unit: str = "") -> str:
    """One number, formatted the way a reader would have written it.

    Thousands separated, precision chosen from the magnitude rather than from
    the float's accidental tail, and a genuine em dash for absence -- an empty
    cell and a zero are different claims.
    """
    if value is None:
        return "—"
    if isinstance(value, Enum):
        return humanise(value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, str):
        return value
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "—"
    if not isinstance(value, (int, float)):
        return str(value)

    if unit == "%":
        return f"{value:.{precision if precision is not None else 0}%}"
    if isinstance(value, int):
        return f"{value:,}"

    if precision is None:
        magnitude = abs(value)
        # Small quantities need decimals to say anything; large ones do not,
        # and printing them implies a measurement precision that is not there.
        precision = 0 if magnitude >= 1000 else 2 if magnitude >= 1 else 4
    text = f"{value:,.{precision}f}"
    return f"{text} {unit}".strip() if unit and unit != "%" else text


def humanise(value: Any) -> str:
    """An enum member as a reader would say it.

    ``<Severity.HIGH_WARNING: 3>`` is a fact about the implementation.
    ``High warning`` is the same fact about the data.
    """
    if isinstance(value, Enum):
        return str(value.name).replace("_", " ").capitalize()
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None:
        return "—"
    return str(value)


@dataclass(frozen=True)
class Column:
    """One column: what it holds, how wide the numbers are, what unit."""

    key: str
    heading: str
    align: Align = Align.LEFT
    precision: int | None = None
    unit: str = ""
    #: Cut long free text to keep the table scannable. The full value stays
    #: in the object; a table is a summary and truncation is honest as long
    #: as it is visible.
    width: int | None = None

    def render(self, value: Any) -> str:
        # Enums first. Severity is an IntEnum, so a plain isinstance(int)
        # check formats it as the number 5 -- which is the implementation's
        # answer, not the reader's. "Blocking" is what they need.
        if isinstance(value, Enum):
            return humanise(value)
        numeric = self.align is Align.RIGHT or isinstance(value, (int, float))
        if numeric and not isinstance(value, str):
            return format_number(value, self.precision, self.unit)
        text = humanise(value)
        if self.width and len(text) > self.width:
            return text[: self.width - 1] + "…"
        return text


@dataclass
class Table:
    """Rows of already-computed values, and how to present them.

    Holds no logic beyond formatting. Every number in a table came from the
    object being described; none is derived here.
    """

    columns: list[Column]
    rows: list[dict[str, Any]] = field(default_factory=list)
    title: str = ""
    #: Caveats, printed below the foot rule. The place a reader looks for
    #: what the numbers do not say.
    notes: list[str] = field(default_factory=list)
    #: Shown in place of the table when it has no rows. "Nothing to show" and
    #: "nothing was found" are different, and only one is reassuring.
    empty: str = "No rows."

    def __len__(self) -> int:
        return len(self.rows)

    def _cells(self) -> list[list[str]]:
        return [
            [column.render(row.get(column.key)) for column in self.columns] for row in self.rows
        ]

    # -- plain text ---------------------------------------------------------

    def to_text(self, max_rows: int = 40) -> str:
        """For a terminal. Rules above and below the header, and at the foot."""
        if not self.rows:
            return f"{self.title}\n{self.empty}" if self.title else self.empty

        body = self._cells()[:max_rows]
        headings = [c.heading for c in self.columns]
        widths = [
            max(len(headings[i]), *(len(row[i]) for row in body)) if body else len(headings[i])
            for i in range(len(self.columns))
        ]

        def line(cells: list[str]) -> str:
            return "  ".join(
                cell.rjust(widths[i])
                if self.columns[i].align is Align.RIGHT
                else cell.ljust(widths[i])
                for i, cell in enumerate(cells)
            ).rstrip()

        rule = "-" * min(sum(widths) + 2 * (len(widths) - 1), 100)
        out = []
        if self.title:
            out += [self.title, ""]
        out += [rule, line(headings), rule, *(line(row) for row in body), rule]
        if len(self.rows) > max_rows:
            out.append(f"... {len(self.rows) - max_rows:,} more rows")
        out += [f"Note. {note}" for note in self.notes]
        return _ascii("\n".join(out))

    # -- markdown -----------------------------------------------------------

    def to_markdown(self, max_rows: int = 100) -> str:
        if not self.rows:
            return self.empty
        marker = {Align.LEFT: ":---", Align.RIGHT: "---:", Align.CENTRE: ":---:"}
        out = []
        if self.title:
            out += [f"**{self.title}**", ""]
        out.append("| " + " | ".join(c.heading for c in self.columns) + " |")
        out.append("|" + "|".join(marker[c.align] for c in self.columns) + "|")
        for row in self._cells()[:max_rows]:
            out.append("| " + " | ".join(row) + " |")
        if len(self.rows) > max_rows:
            out.append(f"\n*{len(self.rows) - max_rows:,} further rows omitted.*")
        for note in self.notes:
            out.append(f"\n*Note. {note}*")
        return "\n".join(out)

    # -- html ---------------------------------------------------------------

    def to_html(self, max_rows: int = 100) -> str:
        """For a notebook. Rules only, tabular figures, notes below."""
        if not self.rows:
            return f"<p class='sp-empty'>{_html.escape(self.empty)}</p>"

        head = "".join(
            f"<th scope='col' style='text-align:{c.align.value}'>{_html.escape(c.heading)}</th>"
            for c in self.columns
        )
        body = "".join(
            "<tr>"
            + "".join(
                f"<td style='text-align:{self.columns[i].align.value}'>{_html.escape(cell)}</td>"
                for i, cell in enumerate(row)
            )
            + "</tr>"
            for row in self._cells()[:max_rows]
        )
        more = (
            f"<p class='sp-more'>{len(self.rows) - max_rows:,} further rows omitted.</p>"
            if len(self.rows) > max_rows
            else ""
        )
        notes = "".join(f"<p class='sp-note'>Note. {_html.escape(n)}</p>" for n in self.notes)
        caption = f"<caption>{_html.escape(self.title)}</caption>" if self.title else ""
        return (
            f"{TABLE_CSS}<table class='sp-table'>{caption}"
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
            f"{more}{notes}"
        )

    # -- latex --------------------------------------------------------------

    def to_latex(self, label: str = "", max_rows: int = 200) -> str:
        """A ``booktabs`` table, ready to paste into a manuscript.

        Requires ``\\usepackage{booktabs}``. No vertical rules and no
        ``\\hline`` between rows, which is what booktabs exists to prevent.
        """

        def escape(text: str) -> str:
            for old, new in (
                ("\\", r"\textbackslash{}"),
                ("&", r"\&"),
                ("%", r"\%"),
                ("$", r"\$"),
                ("#", r"\#"),
                ("_", r"\_"),
                ("{", r"\{"),
                ("}", r"\}"),
                ("~", r"\textasciitilde{}"),
                ("^", r"\textasciicircum{}"),
                ("—", "---"),
                ("…", r"\ldots{}"),
            ):
                text = text.replace(old, new)
            return text

        spec = "".join(c.align.latex for c in self.columns)
        out = ["\\begin{table}[htbp]", "\\centering"]
        if self.title:
            out.append(f"\\caption{{{escape(self.title)}}}")
        if label:
            out.append(f"\\label{{{label}}}")
        out += [f"\\begin{{tabular}}{{{spec}}}", "\\toprule"]
        out.append(" & ".join(escape(c.heading) for c in self.columns) + " \\\\")
        out.append("\\midrule")
        for row in self._cells()[:max_rows]:
            out.append(" & ".join(escape(cell) for cell in row) + " \\\\")
        out.append("\\bottomrule")
        out.append("\\end{tabular}")
        for note in self.notes:
            out.append(
                f"\\begin{{tablenotes}}\\small\\item Note. {escape(note)}\\end{{tablenotes}}"
            )
        out.append("\\end{table}")
        return "\n".join(out)

    def to_records(self) -> list[dict[str, Any]]:
        """The values behind the table, unformatted, for a DataFrame."""
        return [{c.heading: row.get(c.key) for c in self.columns} for row in self.rows]

    def _repr_html_(self) -> str:  # pragma: no cover - notebook hook
        return self.to_html()

    def __repr__(self) -> str:  # pragma: no cover - display only
        return self.to_text()


#: Journal conventions in CSS: rules above and below the header and at the
#: foot, no vertical rules, tabular figures so digits line up, and notes set
#: smaller beneath. Inline because a notebook cell carries no stylesheet, and
#: scoped to `.sp-table` so it cannot reach the rest of the page.
TABLE_CSS = """<style>
.sp-table { border-collapse: collapse; margin: 0.6em 0; font-variant-numeric: tabular-nums;
  font-size: 0.92em; font-family: ui-sans-serif, system-ui, "Segoe UI", sans-serif; }
.sp-table caption { caption-side: top; text-align: left; font-weight: 600;
  padding-bottom: 0.5em; font-size: 1em; }
.sp-table thead th { border-top: 1.4px solid currentColor; border-bottom: 0.6px solid currentColor;
  padding: 0.42em 0.85em; font-weight: 600; }
.sp-table tbody td { padding: 0.34em 0.85em; border: 0; }
.sp-table tbody tr:last-child td { border-bottom: 1.4px solid currentColor; }
.sp-note, .sp-more { font-size: 0.84em; opacity: 0.72; margin: 0.45em 0 0; max-width: 62em; }
.sp-empty { font-style: italic; opacity: 0.72; }
.sp-badge { display: inline-block; padding: 0 0.5em; border-radius: 2px;
  font-size: 0.86em; font-weight: 600; }
</style>"""
