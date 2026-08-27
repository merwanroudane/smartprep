"""Views over results that already exist.

Every table here is assembled from values the core computed. Nothing is
counted, aggregated, re-derived or rounded into a different answer -- the
moment a view calculates its own number it can disagree with the object it
describes, and then a reader has two figures and no way to choose. A test
asserts the agreement rather than trusting this paragraph.

Three levels, per the output specification:

* an **executive summary** a reader understands without training;
* a **structured table** they can sort, filter or export;
* the **technical detail**, on request only.

The detection/repair distinction is carried into every one of them. It is the
rule the library is built on, and until now it was visible only to someone who
knew to look for two similarly named fields in a dataclass dump.
"""

from __future__ import annotations

from typing import Any

from .display import Align, Column, Table, format_number, humanise

__all__ = [
    "scan_summary",
    "issue_table",
    "severity_table",
    "category_table",
    "column_table",
    "audit_table",
    "preparation_summary",
]

#: Printed under tables that show both confidences. The distinction decides
#: whether a repair may run at all, so it travels with the numbers rather
#: than living in documentation.
_CONFIDENCE_NOTE = (
    "Detection confidence is the certainty that a defect exists. Repair "
    "confidence is the certainty that a proposed fix is correct. Only the "
    "second decides whether SmartPrep may act: 31/02/2025 is certainly "
    "invalid and there is no way to know what date was meant."
)


def _recommended(issue: Any) -> float | None:
    """The repair confidence of the recommended treatment, if there is one."""
    treatment = issue.recommended_treatment
    return treatment.repair_confidence if treatment is not None else None


# --------------------------------------------------------------------------
# Scan
# --------------------------------------------------------------------------


def scan_summary(result: Any) -> str:
    """The executive line: shape, coverage, and what was found."""
    health = result.health()
    return (
        f"{result.row_count:,} rows x {result.column_count} columns  |  "
        f"health {health.overall:.0f}/100  |  "
        f"{len(result.issues)} findings  |  "
        f"coverage {result.coverage:.0%} of applicable checks"
    )


def issue_table(issues: list[Any], *, limit: int = 0) -> Table:
    """One row per finding, ordered as the review queue orders them."""
    rows = []
    for issue in issues if not limit else issues[:limit]:
        rows.append(
            {
                "id": issue.id,
                "severity": issue.severity,
                "columns": ", ".join(issue.columns) or "—",
                "rows": issue.affected_row_count,
                "detection": issue.detection_confidence,
                "repair": _recommended(issue),
                "action": issue.triage()[0],
                "summary": issue.evidence.summary,
            }
        )
    return Table(
        columns=[
            Column("id", "Finding", width=34),
            Column("severity", "Severity"),
            Column("columns", "Columns", width=24),
            Column("rows", "Rows", Align.RIGHT),
            Column("detection", "Detection", Align.RIGHT, precision=0, unit="%"),
            Column("repair", "Repair", Align.RIGHT, precision=0, unit="%"),
            Column("action", "Disposition"),
        ],
        rows=rows,
        title="Findings",
        notes=[_CONFIDENCE_NOTE],
        empty="No findings. Every applicable check passed.",
    )


def severity_table(issues: list[Any]) -> Table:
    """How urgent the findings are, most urgent first."""
    counts: dict[Any, int] = {}
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
    total = sum(counts.values())
    rows = [
        {"severity": severity, "n": n, "share": n / total if total else 0.0}
        for severity, n in sorted(counts.items(), key=lambda kv: kv[0], reverse=True)
    ]
    return Table(
        columns=[
            Column("severity", "Severity"),
            Column("n", "Findings", Align.RIGHT),
            Column("share", "Share", Align.RIGHT, precision=0, unit="%"),
        ],
        rows=rows,
        title="Findings by severity",
        empty="No findings.",
    )


def category_table(issues: list[Any]) -> Table:
    """What kinds of problem the dataset has."""
    counts: dict[Any, list[Any]] = {}
    for issue in issues:
        counts.setdefault(issue.category, []).append(issue)
    rows = [
        {
            "category": category,
            "n": len(found),
            "columns": len({c for i in found for c in i.columns}),
            "rows": sum(i.affected_row_count for i in found),
        }
        for category, found in sorted(counts.items(), key=lambda kv: -len(kv[1]))
    ]
    return Table(
        columns=[
            Column("category", "Category"),
            Column("n", "Findings", Align.RIGHT),
            Column("columns", "Columns", Align.RIGHT),
            Column("rows", "Rows affected", Align.RIGHT),
        ],
        rows=rows,
        title="Findings by category",
        empty="No findings.",
    )


def column_table(result: Any) -> Table:
    """Which columns carry the problems, worst first."""
    by_column: dict[str, list[Any]] = {}
    for issue in result.issues:
        for column in issue.columns:
            by_column.setdefault(column, []).append(issue)

    rows = [
        {
            "column": column,
            "n": len(found),
            "worst": max(i.severity for i in found),
            "rows": sum(i.affected_row_count for i in found),
            "auto": sum(1 for i in found if i.triage()[0].is_autonomous),
        }
        for column, found in sorted(
            by_column.items(), key=lambda kv: (-max(i.severity for i in kv[1]), -len(kv[1]))
        )
    ]
    return Table(
        columns=[
            Column("column", "Column", width=28),
            Column("n", "Findings", Align.RIGHT),
            Column("worst", "Worst severity"),
            Column("rows", "Rows affected", Align.RIGHT),
            Column("auto", "Auto-fixable", Align.RIGHT),
        ],
        rows=rows,
        title="Findings by column",
        notes=[
            "A column absent from this table had no finding, which is not the "
            "same as having been checked -- see scan coverage."
        ],
        empty="No column raised a finding.",
    )


# --------------------------------------------------------------------------
# Preparation and audit
# --------------------------------------------------------------------------


def preparation_summary(result: Any) -> str:
    """What automatic mode did, and what it deliberately did not."""
    applied = len(result.audit.applied)
    return (
        f"{humanise(result.status)}  |  "
        f"{result.audit.cells_changed:,} cells changed by {applied} operations  |  "
        f"{len(result.unresolved_issues)} findings left open  |  "
        f"health {result.health_before.overall:.0f} -> {result.health_after.overall:.0f}"
    )


def audit_table(audit: Any, *, applied_only: bool = False) -> Table:
    """The record of what happened, including what did not.

    Abstentions are shown by default. An audit that listed only its actions
    would make silence look like nothing had been considered.
    """
    rows = []
    for record in audit:
        if applied_only and not record.applied:
            continue
        rows.append(
            {
                "id": record.operation_id,
                "operation": record.operation,
                "columns": ", ".join(record.columns) or "—",
                "cells": record.cells_changed,
                "outcome": (
                    "Applied"
                    if record.applied and record.cells_changed
                    else "No change"
                    if record.applied
                    else "Declined"
                ),
                "confidence": record.repair_confidence or None,
                "reason": record.reason,
            }
        )
    return Table(
        columns=[
            Column("id", "Operation"),
            Column("operation", "Action", width=30),
            Column("columns", "Columns", width=22),
            Column("cells", "Cells", Align.RIGHT),
            Column("outcome", "Outcome"),
            Column("confidence", "Repair", Align.RIGHT, precision=0, unit="%"),
        ],
        rows=rows,
        title="Audit",
        notes=[
            "Declined entries are decisions too: automatic mode considered the "
            "finding and refused it. The reason is on each record."
        ],
        empty="Nothing was applied and nothing was declined.",
    )


def declined_table(result: Any) -> Table:
    """Why automatic mode left findings open -- the disclosure that makes the
    rest trustworthy."""
    rows = []
    for issue in result.unresolved_issues:
        repair_class, reasons = issue.triage()
        rows.append(
            {
                "id": issue.id,
                "severity": issue.severity,
                "action": repair_class,
                "why": reasons[0] if reasons else "no treatment could be constructed",
                "detection": issue.detection_confidence,
                "repair": _recommended(issue),
            }
        )
    return Table(
        columns=[
            Column("id", "Finding", width=34),
            Column("severity", "Severity"),
            Column("detection", "Detection", Align.RIGHT, precision=0, unit="%"),
            Column("repair", "Repair", Align.RIGHT, precision=0, unit="%"),
            Column("why", "Why it was left open", width=58),
        ],
        rows=rows,
        title="What automatic mode did not do",
        notes=[_CONFIDENCE_NOTE],
        empty="Nothing was left open.",
    )


def health_table(before: Any, after: Any = None) -> Table:
    """Data health by dimension, before and after."""
    rows = []
    for name, dimension in before.dimensions.items():
        row: dict[str, Any] = {"dimension": name, "before": dimension.score}
        if after is not None:
            later = after.dimensions.get(name)
            row["after"] = later.score if later is not None else None
            row["change"] = row["after"] - dimension.score if later is not None else None
        rows.append(row)

    columns = [Column("dimension", "Dimension"), Column("before", "Before", Align.RIGHT, 1)]
    if after is not None:
        columns += [
            Column("after", "After", Align.RIGHT, 1),
            Column("change", "Change", Align.RIGHT, 1),
        ]
    return Table(
        columns=columns,
        rows=rows,
        title="Data health",
        notes=[
            "Health describes what the checks found. It is not scan coverage, "
            "which counts the checks that ran."
        ],
        empty="No dimension was scored.",
    )


def _panel(title: str, body: str) -> str:
    """One HTML block: a heading and its content."""
    return f"<h4 style='margin:1.1em 0 0.3em;font-weight:600'>{title}</h4>{body}"


def scan_html(result: Any) -> str:
    """The notebook view of a scan: summary, then tables, then the detail."""
    parts = [
        f"<p style='margin:0 0 0.2em'><strong>"
        f"{format_number(len(result.issues))} findings</strong> in "
        f"{result.row_count:,} rows x {result.column_count} columns</p>",
        f"<p class='sp-note' style='margin:0 0 0.8em'>{scan_summary(result)}</p>",
    ]
    if result.issues:
        parts.append(_panel("By severity", severity_table(result.issues).to_html()))
        parts.append(_panel("By column", column_table(result).to_html()))
        parts.append(_panel("Findings", issue_table(result.issues, limit=25).to_html()))
    else:
        parts.append("<p>No findings. Every applicable check passed.</p>")
    return "".join(parts)


def preparation_html(result: Any) -> str:
    """The notebook view of a preparation run."""
    parts = [
        f"<p style='margin:0 0 0.2em'><strong>{humanise(result.status)}</strong></p>",
        f"<p class='sp-note' style='margin:0 0 0.8em'>{preparation_summary(result)}</p>",
        _panel("Data health", health_table(result.health_before, result.health_after).to_html()),
        _panel("Audit", audit_table(result.audit).to_html()),
    ]
    if result.unresolved_issues:
        parts.append(_panel("What automatic mode did not do", declined_table(result).to_html()))
    return "".join(parts)
