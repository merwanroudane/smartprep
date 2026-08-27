"""``auto_prepare()`` -- safe automatic preparation (AD-001, AD-002, AD-004).

The rule this module implements:

> Automatic mode may finish with unresolved issues. It may never hide them.

So the flow is not "find problems, fix problems". It is:

    scan -> triage -> plan -> execute in dependency order
         -> rescan what the repairs invalidated
         -> measure impact -> record everything, including the refusals
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .core.audit import AuditLog, DecisionSource
from .core.enums import CompletionState, RepairClass, Severity
from .core.health import DataHealthScore
from .core.issue import Issue
from .core.operations import RepairPlan
from .core.snapshot import DatasetSnapshot, EnvironmentManifest
from .exceptions import SmartPrepUnsafeRepairError
from .repair.actions import build_operation
from .repair.executor import ExecutionOutcome, RepairExecutor
from .scan import ScanResult, scan

__all__ = ["PreparationResult", "auto_prepare", "clean"]


def _completion_state(
    remaining: list[Issue], applied: int, refused_actionable: int
) -> CompletionState:
    """Decide the terminal state from what is still open (AD-004).

    Ordered from most to least severe, so the first match wins.
    """
    if any(i.repair_class is RepairClass.DO_NOT_TOUCH for i in remaining):
        return CompletionState.BLOCKED
    if any(i.repair_class is RepairClass.DOMAIN_RULE_REQUIRED for i in remaining):
        return CompletionState.DOMAIN_REVIEW_REQUIRED
    if any(i.repair_class is RepairClass.USER_CONFIRMATION_REQUIRED for i in remaining):
        return CompletionState.GUIDED_REVIEW_REQUIRED
    if any(i.repair_class is RepairClass.AMBIGUOUS for i in remaining):
        return CompletionState.GUIDED_REVIEW_RECOMMENDED
    if any(i.repair_class is RepairClass.REVIEW_RECOMMENDED for i in remaining):
        return CompletionState.GUIDED_REVIEW_RECOMMENDED
    if refused_actionable:
        return CompletionState.PARTIALLY_RESOLVED
    if any(i.severity >= Severity.WARNING for i in remaining):
        return CompletionState.CLEAN_WITH_WARNINGS
    if remaining:
        return CompletionState.CLEAN_WITH_NOTES
    return CompletionState.CLEAN if applied else CompletionState.CLEAN


@dataclass
class PreparationResult:
    """Everything an automatic run produced, including what it refused to do."""

    raw_df: pd.DataFrame
    clean_df: pd.DataFrame
    before_scan: ScanResult
    after_scan: ScanResult
    audit: AuditLog
    plan: RepairPlan
    snapshots: list[DatasetSnapshot] = field(default_factory=list)
    environment: EnvironmentManifest | None = None
    waivers: dict[str, str] = field(default_factory=dict)
    #: The semantic context the scan ran with, carried so a guided handoff can
    #: continue without the caller re-supplying it.
    context: dict[str, Any] = field(default_factory=dict)
    _finalized: bool = False

    # -- issue views --------------------------------------------------------

    @property
    def issues(self) -> list[Issue]:
        return self.after_scan.issues

    @property
    def fixed_issues(self) -> list[Issue]:
        """Findings present before and absent after."""
        after_ids = {i.id for i in self.after_scan.issues}
        return [i for i in self.before_scan.issues if i.id not in after_ids]

    @property
    def unresolved_issues(self) -> list[Issue]:
        return self.after_scan.issues

    @property
    def review_queue(self) -> list[Issue]:
        """Open findings, most urgent first -- the input to Guided mode."""
        return sorted(
            self.after_scan.needs_review + self.after_scan.blocking,
            key=lambda i: (-i.severity, -i.affected_row_count),
        )

    @property
    def blocking_issues(self) -> list[Issue]:
        return self.after_scan.blocking

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.after_scan.issues if i.severity >= Severity.WARNING]

    @property
    def needs_guided_review(self) -> bool:
        return bool(self.review_queue)

    # -- state and health ---------------------------------------------------

    @property
    def status(self) -> CompletionState:
        """Terminal state, counting waived findings as decided.

        A waiver is a recorded human decision to proceed. Leaving the status at
        BLOCKED after one would mean the library never accepts an answer it
        asked for.
        """
        refused = len([r for r in self.audit.refused if r.operation != "abstained"])
        outstanding = [i for i in self.after_scan.issues if i.id not in self.waivers]
        return _completion_state(outstanding, len(self.audit.applied), refused)

    @property
    def health_before(self) -> DataHealthScore:
        return self.before_scan.health()

    @property
    def health_after(self) -> DataHealthScore:
        return self.after_scan.health()

    @property
    def cells_changed(self) -> int:
        return self.audit.cells_changed

    # -- finalisation -------------------------------------------------------

    def waive(self, issue_id: str, reason: str) -> PreparationResult:
        """Accept an open finding deliberately, on the record.

        A waiver is not a fix. It is an audited statement that a human looked
        at the finding and chose to proceed, and it is required before
        ``verified_df`` will hand anything back.
        """
        if not reason.strip():
            raise ValueError("a waiver must state a reason; that is the point of it")
        self.after_scan.get(issue_id)  # raises KeyError if unknown
        self.waivers[issue_id] = reason
        return self

    def finalize(self, *, require_no_blocking_issues: bool = True) -> PreparationResult:
        """Mark the dataset verified, if it has earned it."""
        outstanding = [
            i
            for i in self.review_queue
            if i.id not in self.waivers
            and (require_no_blocking_issues or i.repair_class is not RepairClass.DO_NOT_TOUCH)
        ]
        if outstanding:
            raise SmartPrepUnsafeRepairError(
                f"cannot finalize: {len(outstanding)} finding(s) still require a decision.\n"
                + "\n".join(
                    f"  {i.id} [{i.repair_class.name}] {i.evidence.summary}"
                    for i in outstanding[:8]
                )
                + "\n\nResolve them in guided mode, or waive each one explicitly with "
                "result.waive(issue_id, reason='...')."
            )
        self._finalized = True
        return self

    @property
    def verified_df(self) -> pd.DataFrame:
        """The data, only once nothing is left unresolved or unwaived (AD-004)."""
        if not self._finalized:
            raise SmartPrepUnsafeRepairError(
                "verified_df is not available until finalize() succeeds. Use clean_df "
                "if you accept that unresolved findings remain -- it is the same data, "
                "under an honest name."
            )
        return self.clean_df.copy(deep=True)

    # -- reproducibility ----------------------------------------------------

    def rollback(self, version: int = 0) -> pd.DataFrame:
        """Return the dataset as it was at a given snapshot version."""
        for snapshot in self.snapshots:
            if snapshot.version == version:
                return snapshot.restore()
        available = sorted(s.version for s in self.snapshots)
        raise KeyError(f"no snapshot for version {version}; available: {available}")

    def history(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.snapshots]

    def what_auto_mode_did_not_do(self) -> str:
        """The mandatory disclosure section (AD-001)."""
        open_issues = self.review_queue
        if not open_issues:
            return "Auto mode resolved every finding it was permitted to act on."

        lines = ["Auto Mode intentionally left the following unchanged:", ""]
        for issue in open_issues:
            reasons = issue.abstention_reasons
            lines.append(
                f"  {issue.id} [{issue.repair_class.name}] "
                f"{issue.affected_row_count} rows -- {issue.evidence.summary}"
            )
            for reason in reasons:
                lines.append(f"      why: {reason}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": self.status.value,
            "environment": self.environment.to_dict() if self.environment else None,
            "health": {
                "before": self.health_before.to_dict(),
                "after": self.health_after.to_dict(),
                "delta": self.health_after.delta(self.health_before),
            },
            "operations": {
                "planned": len(self.plan),
                "applied": len(self.audit.applied),
                "refused": len(self.audit.refused),
                "cells_changed": self.cells_changed,
            },
            "issues": {
                "before": len(self.before_scan.issues),
                "after": len(self.after_scan.issues),
                "fixed": [i.id for i in self.fixed_issues],
                "unresolved": [i.id for i in self.unresolved_issues],
                "blocking": [i.id for i in self.blocking_issues],
            },
            "waivers": dict(self.waivers),
            "audit": self.audit.to_list(),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    # -- reports ------------------------------------------------------------

    def report(self, kind: str = "preparation", fmt: str = "markdown") -> str:
        """Render a report.

        ``kind`` is ``"scan"`` (pre-cleaning), ``"preparation"`` (post-cleaning,
        including what was left alone) or ``"comparison"`` (issue by issue).
        ``fmt`` is ``"markdown"`` or ``"html"``.
        """
        from .reporting import (
            comparison_report,
            preparation_html,
            preparation_report,
            scan_html,
            scan_report,
        )

        if fmt not in ("markdown", "html"):
            raise ValueError(f"unknown format {fmt!r}; expected 'markdown' or 'html'")

        if kind == "scan":
            return (
                scan_report(self.before_scan)
                if fmt == "markdown"
                else scan_html(self.before_scan, self.raw_df)
            )
        if kind == "preparation":
            return preparation_report(self) if fmt == "markdown" else preparation_html(self)
        if kind == "comparison":
            if fmt == "html":
                return preparation_html(self)
            return comparison_report(self)
        raise ValueError(
            f"unknown report kind {kind!r}; expected 'scan', 'preparation' or 'comparison'"
        )

    def export_report(self, path: str, kind: str = "preparation", fmt: str | None = None) -> str:
        """Write a report to disk. The format is inferred from the suffix."""
        import pathlib

        target = pathlib.Path(path)
        chosen = fmt or ("html" if target.suffix.lower() in (".html", ".htm") else "markdown")
        target.write_text(self.report(kind, chosen), encoding="utf-8")
        return str(target)

    def profile(self, *, stage: str = "after") -> Any:
        """Profile the data before or after preparation."""
        from .eda import profile as build

        return build(self.clean_df if stage == "after" else self.raw_df)

    def compare_profiles(self) -> Any:
        """Statistical before/after, including the distortion the repairs caused."""
        from .eda import compare_profiles
        from .eda import profile as build

        return compare_profiles(build(self.raw_df), build(self.clean_df))

    def publish(self, path: str, **kwargs: Any) -> str:
        """Publish to PDF, PowerPoint, a notebook, HTML or Markdown.

        Every format renders the same chart specs and the same EDA numbers, so
        the figure in the slide deck cannot disagree with the one on screen.
        """
        from .reporting import publish as _publish

        return _publish(self, path, **kwargs)

    def studio(self, **kwargs: Any) -> Any:
        """Open the Studio over this result."""
        from .studio import studio

        return studio(self, **kwargs)

    def show(self, **kwargs: Any) -> Any:
        """Alias for :meth:`studio`, for notebook use."""
        return self.studio(**kwargs)

    # -- presentation -------------------------------------------------------
    #
    # `display`, not `show`: `show()` already opens the Studio on this class
    # and that is published behaviour. Repurposing a shipped method to mean
    # something else is the kind of break a major version exists for, and a
    # table is not worth one.

    def display(self, what: str = "audit", limit: int = 40) -> None:
        """Print a readable table: audit, applied, declined, health or findings."""
        print(self.table(what, limit=limit).to_text(max_rows=limit))

    def table(self, what: str = "audit", limit: int = 40) -> Any:
        from .views import audit_table, declined_table, health_table, issue_table

        builders = {
            "audit": lambda: audit_table(self.audit),
            "applied": lambda: audit_table(self.audit, applied_only=True),
            "declined": lambda: declined_table(self),
            "health": lambda: health_table(self.health_before, self.health_after),
            "findings": lambda: issue_table(self.unresolved_issues, limit=limit),
        }
        if what not in builders:
            raise ValueError(f"{what!r} is not a view; choose from {', '.join(sorted(builders))}")
        return builders[what]()

    def to_frame(self, what: str = "audit") -> Any:
        import pandas as pd

        return pd.DataFrame(self.table(what, limit=0).to_records())

    def explain(self) -> str:
        """Why the run ended where it did, in prose.

        The disclosure that makes the rest trustworthy: a tool reporting only
        its successes leaves its silence to be interpreted, and readers
        interpret silence as "nothing to see".
        """
        from .views import preparation_summary

        lines = [preparation_summary(self), ""]
        open_issues = self.unresolved_issues
        if not open_issues:
            lines.append("Nothing was left open.")
        else:
            lines.append(
                f"{len(open_issues)} findings were left open. Automatic mode "
                "repairs only what it can justify; the rest is reported."
            )
            grouped: dict[str, int] = {}
            for issue in open_issues:
                reason = issue.triage()[0]
                grouped[reason.name] = grouped.get(reason.name, 0) + 1
            for name, count in sorted(grouped.items(), key=lambda kv: -kv[1]):
                lines.append(f"  {count:>3}  {name.replace('_', ' ').capitalize()}")
            lines += [
                "",
                "Use guided_prepare() to decide these, or finalize() to accept "
                "the dataset with the remaining findings waived on the record.",
            ]
        return "\n".join(lines)

    def _repr_html_(self) -> str:  # pragma: no cover - notebook hook
        from .views import preparation_html

        return preparation_html(self)

    def summary(self) -> str:
        before, after = self.health_before, self.health_after
        lines = [
            f"Status: {self.status.value}",
            "",
            f"Scan coverage           {self.before_scan.coverage:.0%}",
            f"Data health             {before.overall:.0f} -> {after.overall:.0f}",
            f"Operations applied      {len(self.audit.applied)}",
            f"Cells changed           {self.cells_changed}",
            f"Issues                  {len(self.before_scan.issues)} -> "
            f"{len(self.after_scan.issues)}",
            f"Resolved                {len(self.fixed_issues)}",
            f"Still open              {len(self.after_scan.issues)}",
            f"Needs review            {len(self.review_queue)}",
            f"Blocking                {len(self.blocking_issues)}",
        ]
        if self.status is not CompletionState.CLEAN:
            lines += ["", self.what_auto_mode_did_not_do()]
        lines += [
            "",
            "clean_df contains unresolved findings. It is not a verified dataset.",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:  # pragma: no cover - display only
        return (
            f"<PreparationResult status={self.status.value} "
            f"applied={len(self.audit.applied)} open={len(self.after_scan.issues)}>"
        )


def _build_plan(result: ScanResult) -> tuple[RepairPlan, AuditLog, list[Issue]]:
    """Turn autonomous findings into a plan, recording every abstention."""
    plan = RepairPlan()
    audit = AuditLog()
    skipped: list[Issue] = []

    for issue in result.issues:
        repair_class, reasons = issue.triage()
        treatment = issue.recommended_treatment

        if not repair_class.is_autonomous or treatment is None:
            RepairExecutor.record_abstention(
                audit, issue.id, issue.columns, repair_class, reasons, issue.rows
            )
            skipped.append(issue)
            continue

        operation = build_operation(issue, treatment)
        if operation is None:
            # Eligible in policy, but nobody has written the repair yet. Saying
            # so is better than pretending the issue was handled.
            RepairExecutor.record_abstention(
                audit,
                issue.id,
                issue.columns,
                repair_class,
                [f"treatment {treatment.name!r} has no implementation yet"],
                issue.rows,
            )
            skipped.append(issue)
            continue

        plan.add(operation)

    return plan, audit, skipped


def auto_prepare(
    frame: pd.DataFrame,
    *,
    strict: bool = False,
    progress: Any = None,
    **context: Any,
) -> PreparationResult:
    """Scan, apply only what is provably safe, then re-verify.

    The input frame is never modified (AD-003). The result may legitimately end
    in ``CLEAN_WITH_WARNINGS`` or ``BLOCKED``; that is not a failure, it is the
    library declining to guess.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError(f"auto_prepare() expects a DataFrame, got {type(frame).__name__}")

    from . import __version__

    raw = frame.copy(deep=True)
    before = scan(raw, strict=strict, progress=progress, **context)

    plan, audit, _ = _build_plan(before)
    executor = RepairExecutor(decision_source=DecisionSource.AUTOMATIC)
    outcome: ExecutionOutcome = executor.run(raw, plan, audit=audit)

    # Repairs change what the other detectors would see. Parsing a column from
    # text to numbers makes every range, formula and sentinel finding stale, so
    # the affected checks are recomputed rather than carried forward.
    after = scan(outcome.frame, strict=strict, **context)

    return PreparationResult(
        raw_df=raw,
        clean_df=outcome.frame,
        before_scan=before,
        after_scan=after,
        audit=outcome.audit,
        plan=plan,
        snapshots=outcome.snapshots,
        environment=EnvironmentManifest.capture(__version__),
        context=dict(context),
    )


def clean(
    frame: pd.DataFrame,
    *,
    detailed: bool = False,
    **context: Any,
) -> pd.DataFrame | PreparationResult:
    """Convenience wrapper for :func:`auto_prepare` (AD-002).

    This is a shortcut, **not** a more aggressive mode. It applies exactly the
    same safe-only policy. When findings remain, it says so on stderr rather
    than returning a quietly incomplete dataset.
    """
    result = auto_prepare(frame, **context)
    if detailed:
        return result

    if result.needs_guided_review:
        import sys

        print(
            f"smartprep: {len(result.review_queue)} finding(s) still need a decision "
            f"(status {result.status.value}). Use sp.auto_prepare(df) to inspect them, "
            "or sp.guided_prepare(df) to resolve them.",
            file=sys.stderr,
        )
    return result.clean_df
