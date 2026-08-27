"""Date interpretation with explicit ambiguity (plan, "Date Ambiguity Resolver").

``pd.to_datetime(errors="coerce")`` collapses three genuinely different
situations into one silent outcome:

* ``31/02/2025`` -- **invalid**. No correct date exists. Nothing may be invented.
* ``04/05/2024`` -- **ambiguous**. Two valid readings; the data cannot choose.
* ``08-26-2024`` -- **format conflict**. Exactly one valid reading, but it
  contradicts the column's dominant layout, which is itself evidence.

Conflating them is how cleaning tools silently corrupt date columns.
"""

from __future__ import annotations

import datetime as _dt
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

__all__ = ["DateStatus", "DateInterpretation", "DateParse", "parse_date", "dominant_layout"]


class DateStatus(Enum):
    OK = "ok"
    AMBIGUOUS = "ambiguous"
    FORMAT_CONFLICT = "format_conflict"
    INVALID = "invalid"


#: ``(strptime format, layout label)``. Layout labels group formats that imply
#: the same field order, so ``DD/MM`` and ``DD-MM`` are one layout.
_FORMATS: tuple[tuple[str, str], ...] = (
    ("%Y-%m-%d", "iso"),
    ("%Y/%m/%d", "iso"),
    ("%d/%m/%Y", "day_first"),
    ("%d-%m-%Y", "day_first"),
    ("%d.%m.%Y", "day_first"),
    ("%m/%d/%Y", "month_first"),
    ("%m-%d-%Y", "month_first"),
    ("%m.%d.%Y", "month_first"),
)


@dataclass(frozen=True)
class DateInterpretation:
    value: _dt.date
    layout: str
    fmt: str


@dataclass(frozen=True)
class DateParse:
    raw: str
    status: DateStatus
    value: _dt.date | None = None
    interpretations: tuple[DateInterpretation, ...] = ()
    note: str = ""
    details: dict[str, object] = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        """True when a single correct value is known without asking the user."""
        return self.status is DateStatus.OK


def _interpretations(text: str) -> list[DateInterpretation]:
    found: list[DateInterpretation] = []
    for fmt, layout in _FORMATS:
        try:
            parsed = _dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        found.append(DateInterpretation(parsed, layout, fmt))
    return found


def dominant_layout(values: list[str]) -> str | None:
    """Infer the column's prevailing field order from unambiguous values only.

    Ambiguous values are excluded deliberately: letting them vote would make the
    inference circular.
    """
    votes: Counter[str] = Counter()
    for raw in values:
        found = _interpretations(raw.strip())
        layouts = {i.layout for i in found}
        if len(layouts) == 1:
            votes[layouts.pop()] += 1
    if not votes:
        return None
    return votes.most_common(1)[0][0]


def parse_date(value: str, prefer_layout: str | None = None) -> DateParse:
    """Interpret one date string, reporting ambiguity rather than resolving it."""
    text = value.strip()
    found = _interpretations(text)

    if not found:
        note = "no valid calendar date matches any supported layout"
        details: dict[str, object] = {}
        # Distinguish "impossible calendar date" from "unsupported layout" --
        # the first is a data error, the second may be a parser gap.
        parts = [p for p in text.replace("/", "-").split("-") if p]
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            details["numeric_components"] = parts
            note = (
                "components are numeric but form no valid date under any "
                "supported layout; the correct value is not inferable"
            )
        return DateParse(text, DateStatus.INVALID, note=note, details=details)

    distinct = {i.value for i in found}

    if len(distinct) == 1:
        only = found[0]
        layouts = {i.layout for i in found}
        # ISO-8601 is self-describing, so it never "conflicts" with a column's
        # dominant layout. Treating it as a conflict is a false positive.
        if prefer_layout and prefer_layout not in layouts and "iso" not in layouts:
            return DateParse(
                text,
                DateStatus.FORMAT_CONFLICT,
                value=only.value,
                interpretations=tuple(found),
                note=(
                    f"parses unambiguously as {only.layout}, which contradicts the "
                    f"column's dominant {prefer_layout} layout"
                ),
            )
        return DateParse(text, DateStatus.OK, value=only.value, interpretations=tuple(found))

    # Several valid, different readings.
    if prefer_layout:
        preferred = [i for i in found if i.layout == prefer_layout]
        if preferred:
            return DateParse(
                text,
                DateStatus.AMBIGUOUS,
                value=preferred[0].value,
                interpretations=tuple(found),
                note=(
                    f"{len(distinct)} valid readings; the dominant {prefer_layout} "
                    "layout suggests one but the value itself cannot confirm it"
                ),
            )
    return DateParse(
        text,
        DateStatus.AMBIGUOUS,
        interpretations=tuple(found),
        note=f"{len(distinct)} equally valid readings and no basis to choose",
    )
