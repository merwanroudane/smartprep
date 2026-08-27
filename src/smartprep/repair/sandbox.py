"""The treatment sandbox -- try a repair without committing to it.

Choosing between three candidate repairs by reading their names and
confidences is choosing blind. What a reviewer actually needs is what each one
would *do*: how many cells move, which rows, what happens to the mean, and
whether the distribution they were about to reason from survives the fix.

So a candidate can be previewed:

``Issue -> Candidates -> Preview -> Comparison -> chosen candidate -> Core operation``

The rule this module exists to enforce is **Preview is not Apply**. A preview:

* is computed against a copy and returns the original frame untouched;
* is not an :class:`~smartprep.core.audit.AuditRecord` and never enters the
  audit log -- considering a repair is not a thing that happened to the data;
* has no ``apply()``. Committing goes back through guided mode, which is the
  only path that records a decision, its author and its reason.

That last point is deliberate friction. A sandbox with a commit button is a
second way to change data, and the second way is always the one that skips the
audit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ..core.issue import Issue, TreatmentCandidate
from ..core.operations import RepairPlan
from ..viz.spec import ChartSpec
from .actions import build_operation

__all__ = ["SummaryDelta", "TreatmentPreview", "preview", "preview_candidates"]


@dataclass(frozen=True)
class SummaryDelta:
    """One statistic, before and after -- the honest cost of a repair.

    Imputation always improves completeness; that is what it is for, and a
    sandbox that reported only completeness would recommend imputing
    everything. The variance and the distinct count are shown beside it
    because those are what it spends.
    """

    column: str
    measure: str
    before: Any
    after: Any

    @property
    def changed(self) -> bool:
        return self.before != self.after

    def describe(self) -> str:
        if not self.changed:
            return f"{self.column}.{self.measure} unchanged at {_render(self.before)}"
        return f"{self.column}.{self.measure}: {_render(self.before)} -> {_render(self.after)}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "measure": self.measure,
            "before": self.before,
            "after": self.after,
            "changed": self.changed,
            "describe": self.describe(),
        }


def _render(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.4g}"
    return f"{value:,}" if isinstance(value, int) else str(value)


@dataclass
class TreatmentPreview:
    """What a candidate would do, computed without doing it.

    There is no ``apply()`` and no ``frame`` attribute holding a committed
    result. ``_previewed_frame`` exists for building the comparison charts and
    is private for that reason: a caller who wants the repaired data asks
    guided mode for it, and gets an audit record with it.
    """

    issue_id: str
    treatment: str
    description: str = ""
    repair_confidence: float = 0.0
    reversible: bool = True

    cells_changed: int = 0
    rows_affected: int = 0
    deltas: list[SummaryDelta] = field(default_factory=list)
    #: A handful of concrete before/after pairs. A reviewer trusts three real
    #: examples more than a count, and rightly so.
    examples: list[dict[str, Any]] = field(default_factory=list)
    charts: list[ChartSpec] = field(default_factory=list)

    #: Set when nothing could be previewed, and why. Abstention is a result.
    refusal: str | None = None

    #: The fingerprint of the frame this was computed against.
    #:
    #: A preview is only true of one dataset. Run the same treatment after
    #: three other repairs and it touches a different number of cells,
    #: because some of them have already been fixed. A sandbox that does not
    #: say which frame it was looking at invites a reader to compare two
    #: numbers that were never about the same data.
    against: str = ""

    _previewed_frame: pd.DataFrame | None = field(default=None, repr=False, compare=False)

    #: Always false. Present so the distinction is legible in the object
    #: itself rather than only in the documentation.
    applied: bool = False

    @property
    def is_possible(self) -> bool:
        return self.refusal is None

    @property
    def changes_anything(self) -> bool:
        return self.cells_changed > 0

    def summary(self) -> str:
        if self.refusal is not None:
            return f"{self.treatment}: cannot be previewed -- {self.refusal}"
        if not self.changes_anything:
            return f"{self.treatment}: would change nothing"
        moved = [d for d in self.deltas if d.changed]
        head = f"{self.treatment}: {self.cells_changed:,} cells across {self.rows_affected:,} rows"
        return head + ("; " + "; ".join(d.describe() for d in moved[:4]) if moved else "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "treatment": self.treatment,
            "description": self.description,
            "repair_confidence": self.repair_confidence,
            "reversible": self.reversible,
            "cells_changed": self.cells_changed,
            "rows_affected": self.rows_affected,
            "deltas": [d.to_dict() for d in self.deltas],
            "examples": list(self.examples),
            "refusal": self.refusal,
            "against": self.against,
            "applied": False,
            "summary": self.summary(),
        }


# --------------------------------------------------------------------------
# Measuring
# --------------------------------------------------------------------------


def _measures(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    """The statistics worth watching a repair move.

    Completeness, spread and shape together -- because a repair that improves
    one at the expense of another should have to show both.
    """
    from ..detectors.base import is_missing

    if column not in frame.columns:
        return {}

    values = frame[column]
    missing = int(values.map(is_missing).sum())
    present = len(values) - missing
    out: dict[str, Any] = {
        "missing": missing,
        "present": present,
        "distinct": int(values.nunique(dropna=True)),
    }

    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().sum() >= 2:
        out["mean"] = round(float(numeric.mean()), 6)
        out["std"] = round(float(numeric.std(ddof=1)), 6)
        out["min"] = round(float(numeric.min()), 6)
        out["max"] = round(float(numeric.max()), 6)
    return out


def _examples(
    before: pd.DataFrame, after: pd.DataFrame, columns: tuple[str, ...], limit: int = 5
) -> tuple[list[dict[str, Any]], int]:
    """Concrete before/after pairs, and how many rows changed in total."""
    from ..detectors.base import is_missing

    shown: list[dict[str, Any]] = []
    rows_changed = 0
    common = [c for c in columns if c in before.columns and c in after.columns]
    if not common or len(before) != len(after):
        return shown, rows_changed

    for position in range(len(before)):
        row_changed = False
        for column in common:
            old = before.iloc[position][column]
            new = after.iloc[position][column]
            if is_missing(old) and is_missing(new):
                continue
            if str(old) != str(new):
                row_changed = True
                if len(shown) < limit:
                    shown.append(
                        {
                            "row": position,
                            "column": column,
                            "before": "" if is_missing(old) else str(old)[:80],
                            "after": "" if is_missing(new) else str(new)[:80],
                        }
                    )
        rows_changed += int(row_changed)
    return shown, rows_changed


# --------------------------------------------------------------------------
# Previewing
# --------------------------------------------------------------------------


def preview(
    frame: pd.DataFrame,
    issue: Issue,
    treatment: TreatmentCandidate | str,
    *,
    with_charts: bool = True,
) -> TreatmentPreview:
    """Compute what a candidate would do to ``frame``, without doing it.

    ``frame`` is not modified. The executor already runs every plan against a
    copy, so previewing costs one copy and no additional machinery -- which is
    the point: preview and apply run the *same* operation, so what a reviewer
    is shown cannot drift from what they get.
    """
    candidate = (
        treatment
        if isinstance(treatment, TreatmentCandidate)
        else next((t for t in issue.treatments if t.name == treatment), None)
    )
    if candidate is None:
        return TreatmentPreview(
            issue_id=issue.id,
            treatment=str(treatment),
            refusal=f"{treatment!r} is not a candidate for this finding",
        )

    from ..core.snapshot import DatasetFingerprint

    result = TreatmentPreview(
        issue_id=issue.id,
        treatment=candidate.name,
        description=candidate.description,
        repair_confidence=candidate.repair_confidence,
        reversible=candidate.reversibility.name != "IRREVERSIBLE",
        against=DatasetFingerprint.of(frame).content_hash,
    )

    operation = build_operation(issue, candidate)
    if operation is None:
        # Abstention is a result. No implementation exists, and saying so is
        # better than showing an empty comparison that reads as "no effect".
        result.refusal = "no implementation exists for this treatment yet"
        return result

    from .executor import RepairExecutor

    plan = RepairPlan()
    plan.add(operation)
    outcome = RepairExecutor().run(frame, plan)

    if outcome.refused:
        result.refusal = outcome.refused[0][1]
        return result

    after = outcome.frame
    result._previewed_frame = after
    result.cells_changed = outcome.cells_changed

    columns = tuple(issue.columns) or tuple(str(c) for c in frame.columns)
    result.examples, result.rows_affected = _examples(frame, after, columns)

    for column in columns:
        was, now = _measures(frame, column), _measures(after, column)
        for measure in sorted(set(was) | set(now)):
            result.deltas.append(SummaryDelta(column, measure, was.get(measure), now.get(measure)))

    if with_charts:
        result.charts = _comparison_charts(frame, after, columns)
    return result


def _comparison_charts(
    before: pd.DataFrame, after: pd.DataFrame, columns: tuple[str, ...]
) -> list[ChartSpec]:
    """Before and after, as specs -- so the sandbox draws nothing itself.

    The charts come from the same builders the report uses, over the same
    profiles, which is what keeps a sandbox comparison and a report figure
    from disagreeing about the same repair.
    """
    from ..eda.profile import profile
    from ..viz.builders import distribution_chart

    charts: list[ChartSpec] = []
    for column in columns[:2]:
        if column not in before.columns or column not in after.columns:
            continue
        try:
            # One column each, not two whole frames -- see the note in
            # viz.compose: profiling everything to draw one chart is the most
            # expensive way to get the same picture.
            was = distribution_chart(profile(before[[column]]).get(column))
            now = distribution_chart(profile(after[[column]]).get(column))
        except (KeyError, ValueError):  # pragma: no cover - non-profilable column
            continue
        for spec, label in ((was, "before"), (now, "after")):
            if spec is not None:
                spec.title = f"{spec.title} ({label})"
                spec.subtitle = "preview only -- nothing has been applied"
                charts.append(spec)
    return charts


def preview_candidates(
    frame: pd.DataFrame, issue: Issue, *, with_charts: bool = False
) -> list[TreatmentPreview]:
    """Preview every candidate, so they can be compared side by side.

    Ordered by repair confidence, but the ordering is not a recommendation --
    the whole reason to show a comparison is that the most confident repair is
    not always the one a reviewer wants, and the deltas are what tell them so.
    """
    ordered = sorted(issue.treatments, key=lambda t: t.repair_confidence, reverse=True)
    return [preview(frame, issue, candidate, with_charts=with_charts) for candidate in ordered]
