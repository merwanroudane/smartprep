"""Markdown reports.

The golden rule for reporting, from the plan: the report does not say *here is
your clean data*. It says what the data was, what was found, what was decided,
what changed, what that did to the statistics, what is still open, and how to
reproduce all of it.

Markdown first because it is diffable, reviewable in a pull request, readable in
a terminal, and cannot silently drop a section the way a layout engine can.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.enums import RepairClass

if TYPE_CHECKING:  # pragma: no cover
    from ..prepare import PreparationResult
    from ..scan import ScanResult

__all__ = ["scan_report", "preparation_report", "comparison_report"]


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_None._\n"
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out) + "\n"


def scan_report(result: ScanResult, *, title: str = "Data Quality Scan") -> str:
    """Pre-cleaning report: what is in the data, before anything is changed."""
    health = result.health()
    lines = [
        f"# {title}",
        "",
        "> **RAW DATA — BEFORE CLEANING.** Nothing in this report has been modified.",
        "",
        "## Dataset",
        "",
        _table(
            ["Property", "Value"],
            [
                ["Rows", f"{result.row_count:,}"],
                ["Columns", str(result.column_count)],
            ],
        ),
        "## Scan coverage",
        "",
        f"**{result.coverage:.0%}** of applicable enabled checks completed "
        f"({len(result.completed_checks)} of {result.applicable_checks}).",
        "",
        "Coverage measures how much of the checking finished. It says nothing "
        "about whether the data is correct.",
        "",
    ]

    if result.skipped_checks or result.not_applicable_checks:
        lines += ["### Checks that did not run", ""]
        lines.append(
            _table(
                ["Check", "Status", "Reason"],
                [
                    [o.detector, o.status, o.reason]
                    for o in result.skipped_checks + result.not_applicable_checks
                ],
            )
        )

    if result.failed_checks:
        lines += [
            "### Failed checks",
            "",
            "**Coverage is incomplete.** These checks errored and their findings "
            "are missing from this report.",
            "",
            _table(
                ["Check", "Error"],
                [[o.detector, o.reason] for o in result.failed_checks],
            ),
        ]

    lines += ["## Data health", "", f"**{health.overall:.0f}/100**", ""]
    lines.append(
        _table(
            ["Dimension", "Score", "Driven by"],
            [
                [name, f"{dim.score:.0f}", ", ".join(dim.contributing) or "—"]
                for name, dim in sorted(health.dimensions.items())
            ],
        )
    )

    lines += ["## Findings by decision class", ""]
    for repair_class, issues in result.by_repair_class().items():
        lines += [
            f"### {repair_class.name} ({len(issues)})",
            "",
            _autonomy_note(repair_class),
            "",
            _table(
                ["Issue", "Severity", "Rows", "Summary"],
                [
                    [
                        f"`{i.id}`",
                        i.severity.name,
                        str(i.affected_row_count),
                        i.evidence.summary,
                    ]
                    for i in issues
                ],
            ),
        ]

    return "\n".join(lines)


def _autonomy_note(repair_class: RepairClass) -> str:
    return {
        RepairClass.SAFE_AUTO_FIX: "Repaired automatically. Reversible from the snapshot.",
        RepairClass.AUTO_FIX_WITH_LOG: "Repaired automatically and logged in full.",
        RepairClass.REVIEW_RECOMMENDED: "Left unchanged. A reviewer should look.",
        RepairClass.USER_CONFIRMATION_REQUIRED: (
            "Left unchanged. Needs an explicit decision before it can be applied."
        ),
        RepairClass.DOMAIN_RULE_REQUIRED: (
            "Left unchanged. Resolving it needs business knowledge the data does not contain."
        ),
        RepairClass.AMBIGUOUS: (
            "Left unchanged. The correct value is not inferable from the data."
        ),
        RepairClass.DO_NOT_TOUCH: (
            "**Must not be repaired automatically.** Acting here could destroy valid information."
        ),
    }.get(repair_class, "")


def preparation_report(result: PreparationResult, *, title: str = "Data Preparation Report") -> str:
    """Post-cleaning report, including the mandatory disclosure of inaction."""
    before, after = result.health_before, result.health_after

    lines = [
        f"# {title}",
        "",
        "## Automatic cleaning status",
        "",
        _table(
            ["Question", "Answer"],
            [
                ["Scan complete", "YES"],
                ["Scan coverage", f"{result.before_scan.coverage:.0%}"],
                ["Automatic repairs complete", "YES"],
                ["All issues resolved", "NO" if result.after_scan.issues else "YES"],
                ["Manual review required", "YES" if result.needs_guided_review else "NO"],
                ["Status", f"`{result.status.value}`"],
            ],
        ),
        "## What changed",
        "",
        _table(
            ["Measure", "Before", "After"],
            [
                [
                    "Data health",
                    f"{before.overall:.0f}",
                    f"{after.overall:.0f}",
                ],
                [
                    "Issues",
                    str(len(result.before_scan.issues)),
                    str(len(result.after_scan.issues)),
                ],
                ["Rows", str(len(result.raw_df)), str(len(result.clean_df))],
                [
                    "Columns",
                    str(result.raw_df.shape[1]),
                    str(result.clean_df.shape[1]),
                ],
                ["Cells changed", "—", str(result.cells_changed)],
                ["Operations applied", "—", str(len(result.audit.applied))],
            ],
        ),
        "### Health by dimension",
        "",
    ]

    delta = after.delta(before)
    lines.append(
        _table(
            ["Dimension", "Before", "After", "Change"],
            [
                [
                    name,
                    f"{before.dimensions[name].score:.0f}",
                    f"{dim.score:.0f}",
                    f"{delta.get(name, 0):+.1f}",
                ]
                for name, dim in sorted(after.dimensions.items())
            ],
        )
    )

    lines += ["## Operations applied", ""]
    lines.append(
        _table(
            ["ID", "Operation", "Columns", "Cells", "Reason"],
            [
                [
                    r.operation_id,
                    f"`{r.operation}`",
                    ", ".join(r.columns) or "—",
                    str(r.cells_changed),
                    r.reason,
                ]
                for r in result.audit.applied
            ],
        )
    )

    # The section that must never be buried (AD-001).
    lines += [
        "## What auto mode did NOT do",
        "",
        "This section is mandatory. `clean_df` is not a verified dataset.",
        "",
    ]
    open_issues = result.review_queue
    if not open_issues:
        lines.append("_Nothing was left open._\n")
    else:
        lines.append(
            _table(
                ["Issue", "Class", "Rows", "Why it was left alone"],
                [
                    [
                        f"`{i.id}`",
                        i.repair_class.name,
                        str(i.affected_row_count),
                        "; ".join(i.abstention_reasons) or i.evidence.summary,
                    ]
                    for i in open_issues
                ],
            )
        )

    if result.waivers:
        lines += [
            "## Waivers",
            "",
            "Findings a human accepted deliberately, on the record.",
            "",
            _table(
                ["Issue", "Reason"],
                [[f"`{k}`", v] for k, v in result.waivers.items()],
            ),
        ]

    if result.environment:
        env = result.environment.to_dict()
        lines += [
            "## Reproducibility",
            "",
            _table(["Property", "Value"], [[k, str(v)] for k, v in env.items()]),
        ]

    return "\n".join(lines)


def comparison_report(result: PreparationResult) -> str:
    """Before/after, issue by issue -- what was resolved and what survived."""
    before_ids = {i.id: i for i in result.before_scan.issues}
    after_ids = {i.id: i for i in result.after_scan.issues}

    rows: list[list[str]] = []
    for issue_id in sorted(before_ids | after_ids):
        was = before_ids.get(issue_id)
        now = after_ids.get(issue_id)
        if was and not now:
            state = "**resolved**"
        elif now and not was:
            state = "_new_"
        elif was and now and was.affected_row_count != now.affected_row_count:
            state = "reduced"
        else:
            state = "unchanged"
        rows.append(
            [
                f"`{issue_id}`",
                str(was.affected_row_count) if was else "—",
                str(now.affected_row_count) if now else "—",
                state,
            ]
        )

    return "\n".join(
        [
            "# Before / After Comparison",
            "",
            _table(["Issue", "Rows before", "Rows after", "Outcome"], rows),
            "",
            "A finding that appears only in the *after* column was not created by "
            "cleaning -- it became visible once the values it depends on were "
            "parsed into a form the detector could read.",
        ]
    )
