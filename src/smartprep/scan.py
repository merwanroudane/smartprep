"""``sp.scan()`` -- diagnosis only, zero modification (AD-002).

Scan coverage and data health are reported as two separate numbers. Completing
every applicable check says nothing about whether the data is correct, and
conflating the two is the specific dishonesty this design refuses.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

from .core.enums import IssueCategory, RepairClass, Severity
from .core.health import DataHealthScore, score_issues
from .core.issue import Issue
from .detectors import REGISTRY
from .detectors.base import Detector, DetectorRegistry
from .exceptions import SmartPrepError

__all__ = ["Applicability", "ScanResult", "CheckOutcome", "scan"]


class Applicability(Enum):
    """Whether a detector can meaningfully run on this data.

    Distinguishing "ran and found nothing" from "could not run" is what makes a
    coverage figure mean anything. Without it, a scan that silently skipped
    half its checks still reports 100%.
    """

    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    SKIPPED_MISSING_CONTEXT = "skipped_missing_context"
    SKIPPED_MISSING_DEPENDENCY = "skipped_missing_dependency"

    @property
    def runs(self) -> bool:
        return self is Applicability.APPLICABLE


@dataclass(frozen=True)
class CheckOutcome:
    """Execution record for one detector -- separate from what it found."""

    detector: str
    status: str  # "completed" | "skipped" | "not_applicable" | "failed"
    issue_count: int = 0
    reason: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector": self.detector,
            "status": self.status,
            "issues": self.issue_count,
            "reason": self.reason,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class ScanResult:
    """Diagnosis only. Holds no modified data by construction."""

    issues: list[Issue] = field(default_factory=list)
    outcomes: list[CheckOutcome] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0

    # -- execution progress -------------------------------------------------

    @property
    def completed_checks(self) -> list[CheckOutcome]:
        return [o for o in self.outcomes if o.status == "completed"]

    @property
    def skipped_checks(self) -> list[CheckOutcome]:
        return [o for o in self.outcomes if o.status == "skipped"]

    @property
    def not_applicable_checks(self) -> list[CheckOutcome]:
        return [o for o in self.outcomes if o.status == "not_applicable"]

    @property
    def failed_checks(self) -> list[CheckOutcome]:
        return [o for o in self.outcomes if o.status == "failed"]

    @property
    def applicable_checks(self) -> int:
        return len(self.completed_checks) + len(self.failed_checks)

    @property
    def coverage(self) -> float:
        """Share of *applicable* checks that completed.

        1.0 means every applicable check ran. It does **not** mean the data is
        correct, and no caller may present it as such. Checks that were skipped
        or did not apply are excluded from the denominator and reported
        separately, with their reasons.
        """
        return (
            1.0
            if self.applicable_checks == 0
            else (len(self.completed_checks) / self.applicable_checks)
        )

    # -- findings -----------------------------------------------------------

    def health(self) -> DataHealthScore:
        return score_issues(self.issues, self.row_count)

    def by_severity(self) -> dict[Severity, list[Issue]]:
        grouped: dict[Severity, list[Issue]] = {}
        for issue in self.issues:
            grouped.setdefault(issue.severity, []).append(issue)
        return dict(sorted(grouped.items(), key=lambda kv: kv[0], reverse=True))

    def by_category(self) -> dict[IssueCategory, list[Issue]]:
        grouped: dict[IssueCategory, list[Issue]] = {}
        for issue in self.issues:
            grouped.setdefault(issue.category, []).append(issue)
        return grouped

    def by_repair_class(self) -> dict[RepairClass, list[Issue]]:
        grouped: dict[RepairClass, list[Issue]] = {}
        for issue in self.issues:
            grouped.setdefault(issue.repair_class, []).append(issue)
        return dict(sorted(grouped.items(), key=lambda kv: kv[0], reverse=True))

    def get(self, issue_id: str) -> Issue:
        """Fetch one issue by id.

        Raises ``KeyError`` naming the available ids -- a bare ``StopIteration``
        from a generator would surface far from the mistake.
        """
        for issue in self.issues:
            if issue.id == issue_id:
                return issue
        raise KeyError(
            f"no issue with id {issue_id!r}. Available: {sorted(i.id for i in self.issues)}"
        )

    def find(
        self,
        category: IssueCategory | None = None,
        *,
        column: str | None = None,
        min_severity: Severity | None = None,
        repair_class: RepairClass | None = None,
    ) -> list[Issue]:
        """Filter findings by any combination of criteria."""
        found = self.issues
        if category is not None:
            found = [i for i in found if i.category is category]
        if column is not None:
            found = [i for i in found if column in i.columns]
        if min_severity is not None:
            found = [i for i in found if i.severity >= min_severity]
        if repair_class is not None:
            found = [i for i in found if i.repair_class is repair_class]
        return found

    @property
    def auto_fixable(self) -> list[Issue]:
        return [i for i in self.issues if i.repair_class.is_autonomous]

    @property
    def needs_review(self) -> list[Issue]:
        return [
            i
            for i in self.issues
            if not i.repair_class.is_autonomous and i.repair_class > RepairClass.DO_NOT_TOUCH
        ]

    @property
    def blocking(self) -> list[Issue]:
        return [i for i in self.issues if i.repair_class is RepairClass.DO_NOT_TOUCH]

    # -- serialisation ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "dataset": {"rows": self.row_count, "columns": self.column_count},
            "coverage": {
                "ratio": round(self.coverage, 4),
                "applicable": self.applicable_checks,
                "completed": len(self.completed_checks),
                "skipped": [o.to_dict() for o in self.skipped_checks],
                "not_applicable": [o.to_dict() for o in self.not_applicable_checks],
                "failed": [o.to_dict() for o in self.failed_checks],
                "note": "Checks executed. Not a statement about data correctness.",
            },
            "health": self.health().to_dict(),
            "issues": [i.to_dict() for i in self.issues],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def report(self, fmt: str = "markdown", frame: Any = None) -> str:
        """Render the pre-cleaning report.

        ``fmt`` is ``"markdown"`` or ``"html"``. Pass ``frame`` to include the
        profile and charts -- the scan holds findings, not the data.
        """
        from .reporting import scan_html, scan_report

        if fmt == "markdown":
            return scan_report(self)
        if fmt == "html":
            return scan_html(self, frame)
        raise ValueError(f"unknown report format {fmt!r}; expected 'markdown' or 'html'")

    def profile(self, frame: pd.DataFrame) -> Any:
        """Profile the data this scan describes."""
        from .eda import profile as build

        return build(frame)

    # -- presentation -------------------------------------------------------
    #
    # These render values this object already holds. They compute nothing:
    # a view that derived its own counts could disagree with `self`, and a
    # reader with two numbers has no way to choose between them.

    def display(self, what: str = "findings", limit: int = 25) -> None:
        """Print a readable table: findings, severity, columns or categories."""
        print(self.table(what, limit=limit).to_text())

    def table(self, what: str = "findings", limit: int = 25) -> Any:
        """One of the views, as a :class:`~smartprep.display.Table`."""
        from .views import category_table, column_table, issue_table, severity_table

        builders = {
            "findings": lambda: issue_table(self.issues, limit=limit),
            "severity": lambda: severity_table(self.issues),
            "columns": lambda: column_table(self),
            "categories": lambda: category_table(self.issues),
        }
        if what not in builders:
            raise ValueError(f"{what!r} is not a view; choose from {', '.join(sorted(builders))}")
        return builders[what]()

    def to_frame(self, what: str = "findings") -> Any:
        """The same view as a DataFrame, for sorting, filtering and export."""
        return self.table(what, limit=0).to_frame()

    def _repr_html_(self) -> str:  # pragma: no cover - notebook hook
        from .views import scan_html

        return scan_html(self)

    def __repr__(self) -> str:  # pragma: no cover - display only
        return (
            f"<ScanResult rows={self.row_count:,} cols={self.column_count} "
            f"issues={len(self.issues)} coverage={self.coverage:.0%}>"
        )

    def summary(self) -> str:
        counts = Counter(i.repair_class.name for i in self.issues)
        lines = [
            f"Rows {self.row_count}  Columns {self.column_count}",
            f"Scan coverage {self.coverage:.0%} of applicable enabled checks "
            f"({len(self.completed_checks)} completed, {len(self.skipped_checks)} skipped, "
            f"{len(self.not_applicable_checks)} not applicable)",
        ]
        if self.failed_checks:
            lines.append(
                f"WARNING: {len(self.failed_checks)} detector(s) failed; coverage is "
                "incomplete: " + ", ".join(o.detector for o in self.failed_checks)
            )
        lines += ["", f"{len(self.issues)} issues detected:"]
        for name, n in sorted(counts.items()):
            lines.append(f"  {name:30s} {n}")
        lines += ["", self.health().summary(), ""]
        lines.append("Scan coverage measures checks executed, not data correctness.")
        return "\n".join(lines)


def _applicability(
    detector: Detector, frame: pd.DataFrame, context: dict[str, Any]
) -> tuple[Applicability, str]:
    """Ask a detector whether it can run. Detectors without the method run."""
    probe = getattr(detector, "applicability", None)
    if probe is None:
        return Applicability.APPLICABLE, ""
    result = probe(frame, context)
    if isinstance(result, tuple):
        return result
    return result, ""


def scan(
    frame: pd.DataFrame,
    *,
    registry: DetectorRegistry = REGISTRY,
    strict: bool = False,
    progress: Callable[[str, int, int], None] | bool | None = None,
    only: Iterable[str] | None = None,
    **context: Any,
) -> ScanResult:
    """Run every applicable detector. The input frame is never modified.

    Parameters
    ----------
    strict:
        Raise if any detector fails, instead of recording the failure and
        continuing. Research and regulated workflows should set this: silently
        reduced coverage is worse than a loud stop.
    progress:
        ``True`` to print progress, or a callable receiving
        ``(detector_name, completed, total)``.
    only:
        Restrict the scan to named detectors.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError(f"scan() expects a DataFrame, got {type(frame).__name__}")

    import time

    before = frame.copy(deep=True)
    result = ScanResult(row_count=len(frame), column_count=frame.shape[1])

    detectors = [d for d in registry if only is None or d.name in set(only)]
    total = len(detectors)

    report: Callable[[str, int, int], None]
    if progress is True:

        def report(name: str, done: int, count: int) -> None:
            pct = int(100 * done / count) if count else 100
            print(f"[{pct:3d}%] {done}/{count} {name}", flush=True)
    elif callable(progress):
        report = progress
    else:

        def report(name: str, done: int, count: int) -> None:
            return None

    for position, detector in enumerate(detectors, 1):
        applies, why = _applicability(detector, frame, context)
        if not applies.runs:
            status = "not_applicable" if applies is Applicability.NOT_APPLICABLE else "skipped"
            result.outcomes.append(CheckOutcome(detector.name, status, reason=why or applies.value))
            report(detector.name, position, total)
            continue

        started = time.perf_counter()
        try:
            found = detector.detect(frame, **context)
        except Exception as exc:
            elapsed = (time.perf_counter() - started) * 1000
            reason = f"{type(exc).__name__}: {exc}"
            result.outcomes.append(
                CheckOutcome(detector.name, "failed", reason=reason, duration_ms=elapsed)
            )
            if strict:
                raise SmartPrepError(
                    f"detector {detector.name!r} failed during scan: {reason}. "
                    "Scanning with strict=False records the failure and continues, "
                    "at the cost of reduced coverage."
                ) from exc
            report(detector.name, position, total)
            continue

        elapsed = (time.perf_counter() - started) * 1000
        for issue in found:
            # Attach index labels once, centrally, so positions and labels can
            # never drift apart (see core.rows).
            issue.evidence = issue.evidence.with_index(frame.index)
            if not issue.detector:
                issue.detector = detector.name
        result.issues.extend(found)
        result.outcomes.append(
            CheckOutcome(
                detector.name,
                "completed",
                len(found),
                "" if found else "no findings",
                elapsed,
            )
        )
        report(detector.name, position, total)

    # AD-003 is a guarantee, so it is enforced rather than documented.
    if not frame.equals(before):
        raise RuntimeError("a detector modified the input frame; scan() must never mutate (AD-003)")
    return result
