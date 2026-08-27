"""Before/after comparison -- what cleaning actually did to the statistics.

The question a researcher asks after a repair is not "is it clean now?" but
"did you change what the data says?". A pipeline that fills 8% of a column with
its median has not lied about any single value and has still shrunk the
variance, moved the correlations and narrowed the confidence intervals of
everything computed downstream.

So every comparison reports the distortion alongside the improvement, and flags
the changes large enough to alter a conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .profile import ColumnProfile, DatasetProfile

__all__ = ["ColumnComparison", "ProfileComparison", "compare_profiles"]

#: Relative change above which a shift is worth a reader's attention. Not a
#: significance test -- a heuristic for "look at this", deliberately generous
#: because a false alarm costs a glance and a miss costs a wrong conclusion.
MATERIAL_SHIFT = 0.10


@dataclass(frozen=True)
class ColumnComparison:
    """How one column changed."""

    name: str
    before: ColumnProfile | None
    after: ColumnProfile | None
    changes: dict[str, tuple[float | None, float | None]] = field(default_factory=dict)
    flags: tuple[str, ...] = ()

    @property
    def status(self) -> str:
        if self.before is None:
            return "added"
        if self.after is None:
            return "removed"
        return "changed" if self.changes else "unchanged"

    def relative_change(self, metric: str) -> float | None:
        pair = self.changes.get(metric)
        if not pair or pair[0] in (None, 0) or pair[1] is None:
            return None
        return (pair[1] - pair[0]) / abs(pair[0])

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.name,
            "status": self.status,
            "changes": {
                metric: {"before": before, "after": after}
                for metric, (before, after) in self.changes.items()
            },
            "flags": list(self.flags),
        }


@dataclass
class ProfileComparison:
    """Dataset-level before/after, with the statistical guardrails applied."""

    before: DatasetProfile
    after: DatasetProfile
    columns: list[ColumnComparison] = field(default_factory=list)

    @property
    def rows_delta(self) -> int:
        return self.after.rows - self.before.rows

    @property
    def missing_delta(self) -> int:
        return self.after.missing_cells - self.before.missing_cells

    @property
    def red_flags(self) -> list[tuple[str, str]]:
        """Changes big enough to alter a conclusion drawn from this data."""
        found: list[tuple[str, str]] = []

        if self.before.rows and abs(self.rows_delta) / self.before.rows > 0.05:
            found.append(
                (
                    "row_count",
                    f"{abs(self.rows_delta)} rows ({abs(self.rows_delta) / self.before.rows:.1%}) "
                    f"{'removed' if self.rows_delta < 0 else 'added'}",
                )
            )
        for column in self.columns:
            for flag in column.flags:
                found.append((column.name, flag))
        return found

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "rows": {"before": self.before.rows, "after": self.after.rows},
            "columns": {"before": self.before.columns, "after": self.after.columns},
            "missing_cells": {
                "before": self.before.missing_cells,
                "after": self.after.missing_cells,
            },
            "column_changes": [c.to_dict() for c in self.columns if c.status != "unchanged"],
            "red_flags": [{"where": w, "what": t} for w, t in self.red_flags],
            "note": (
                "A repair that improves completeness can still distort the "
                "distribution. Both are reported."
            ),
        }

    def summary(self) -> str:
        lines = [
            f"Rows           {self.before.rows} -> {self.after.rows}",
            f"Columns        {self.before.columns} -> {self.after.columns}",
            f"Missing cells  {self.before.missing_cells} -> {self.after.missing_cells}",
            "",
        ]
        changed = [c for c in self.columns if c.status != "unchanged"]
        if not changed:
            lines.append("No column-level statistic moved.")
        for column in changed:
            lines.append(f"  {column.name} ({column.status})")
            for metric, (before, after) in column.changes.items():
                lines.append(f"      {metric:12s} {before} -> {after}")

        if self.red_flags:
            lines += ["", "Red flags:"]
            for where, what in self.red_flags:
                lines.append(f"  {where}: {what}")
        return "\n".join(lines)


def _numeric_changes(
    before: ColumnProfile, after: ColumnProfile
) -> tuple[dict[str, tuple[float | None, float | None]], list[str]]:
    changes: dict[str, tuple[float | None, float | None]] = {}
    flags: list[str] = []

    if before.numeric is None or after.numeric is None:
        return changes, flags

    for metric in ("mean", "std", "median", "minimum", "maximum", "skew"):
        old = getattr(before.numeric, metric)
        new = getattr(after.numeric, metric)
        if old is None or new is None:
            continue
        if old != new:
            changes[metric] = (round(float(old), 6), round(float(new), 6))

    old_std, new_std = before.numeric.std, after.numeric.std
    if old_std and old_std > 0:
        shrinkage = (old_std - new_std) / old_std
        if shrinkage > MATERIAL_SHIFT:
            # The signature of mean or median imputation: values added at the
            # centre, spread reduced, downstream intervals too narrow.
            flags.append(
                f"variance shrank {shrinkage:.1%} -- imputation at the centre "
                "narrows every interval computed from this column"
            )

    old_mean, new_mean = before.numeric.mean, after.numeric.mean
    if old_mean and abs(old_mean) > 0:
        shift = abs(new_mean - old_mean) / abs(old_mean)
        if shift > MATERIAL_SHIFT:
            flags.append(f"mean moved {shift:.1%}")

    return changes, flags


def compare_profiles(before: DatasetProfile, after: DatasetProfile) -> ProfileComparison:
    """Compare two profiles column by column."""
    comparison = ProfileComparison(before=before, after=after)
    names = list(dict.fromkeys([*before.columns_profiled, *after.columns_profiled]))

    for name in names:
        old = before.columns_profiled.get(name)
        new = after.columns_profiled.get(name)

        if old is None or new is None:
            comparison.columns.append(ColumnComparison(name=name, before=old, after=new))
            continue

        changes: dict[str, tuple[float | None, float | None]] = {}
        flags: list[str] = []

        if old.missing != new.missing:
            changes["missing"] = (float(old.missing), float(new.missing))
        if old.distinct != new.distinct:
            changes["distinct"] = (float(old.distinct), float(new.distinct))
            # Halved or more. Exactly-halved is the commonest real case --
            # merging case variants collapses each pair into one.
            if new.distinct <= old.distinct * 0.5:
                flags.append(
                    f"distinct values fell from {old.distinct} to {new.distinct} -- "
                    "categories may have been merged"
                )
        if old.kind is not new.kind:
            flags.append(f"kind changed {old.kind.value} -> {new.kind.value}")

        numeric_changes, numeric_flags = _numeric_changes(old, new)
        changes.update(numeric_changes)
        flags.extend(numeric_flags)

        comparison.columns.append(
            ColumnComparison(name=name, before=old, after=new, changes=changes, flags=tuple(flags))
        )

    return comparison
