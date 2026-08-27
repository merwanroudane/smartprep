"""Time-series diagnostics -- what is wrong with the *shape* of a series.

SmartPrep diagnoses preparation problems; it does not forecast. The
distinction matters because the two want opposite things from a gap: a
forecasting package fills it so a model can run, and a preparation library
tells you it is there so you can decide whether the model should run at all.

Nothing here repairs anything. Findings are ordinary
:class:`~smartprep.core.issue.Issue` objects, so they pass through the same
triage, the same confidence ladder and the same guided review as everything
else -- a missing quarter is not a special kind of problem needing a special
kind of decision.

The checks:

* **frequency** -- inferred from the gaps that actually occur, and reported
  with how much of the series agrees with it;
* **missing periods** -- expected timestamps that are absent;
* **duplicate timestamps** -- two observations claiming the same instant;
* **irregular spacing** -- gaps that do not match the inferred frequency;
* **ordering** -- rows out of chronological order;
* **timezone consistency** -- mixed aware and naive timestamps;
* **stale runs** -- a value repeating far longer than the series suggests it
  should, which is usually a feed that stopped updating rather than a
  quantity that stopped moving.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .core.enums import (
    DomainSensitivity,
    InformationLossRisk,
    IssueCategory,
    Reversibility,
    RuleSource,
    Severity,
    StatisticalImpact,
)
from .core.issue import Evidence, Issue, TreatmentCandidate

__all__ = ["TimeSeriesReport", "Cadence", "timeseries"]


#: Frequencies worth naming, longest first so a month is not called 28 days.
_CADENCES: tuple[tuple[str, pd.Timedelta], ...] = (
    ("yearly", pd.Timedelta(days=365)),
    ("quarterly", pd.Timedelta(days=91)),
    ("monthly", pd.Timedelta(days=30)),
    ("weekly", pd.Timedelta(days=7)),
    ("daily", pd.Timedelta(days=1)),
    ("hourly", pd.Timedelta(hours=1)),
    ("minutely", pd.Timedelta(minutes=1)),
    ("secondly", pd.Timedelta(seconds=1)),
)


@dataclass(frozen=True)
class Cadence:
    """The inferred frequency, and how much of the series actually keeps it.

    ``agreement`` is the honest part. A daily series with a handful of gaps
    and a daily series that is really weekly with noise both infer "daily";
    only the agreement figure separates them, so it is reported wherever the
    cadence is.
    """

    name: str
    step: pd.Timedelta | None
    agreement: float = 0.0
    note: str = ""

    @property
    def is_regular(self) -> bool:
        return self.agreement >= 0.9

    def describe(self) -> str:
        if self.step is None:
            return "no regular cadence could be inferred"
        return f"{self.name} ({self.agreement:.0%} of gaps agree)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "step_seconds": self.step.total_seconds() if self.step is not None else None,
            "agreement": round(self.agreement, 4),
            "regular": self.is_regular,
            "note": self.note,
        }


@dataclass
class TimeSeriesReport:
    """Everything the shape of a series says about itself."""

    column: str
    rows: int
    cadence: Cadence
    first: Any = None
    last: Any = None
    duplicates: int = 0
    missing_periods: tuple[Any, ...] = ()
    out_of_order: int = 0
    unparsed: int = 0
    mixed_timezones: bool = False
    stale_runs: tuple[dict[str, Any], ...] = ()
    issues: list[Issue] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        """Observed periods as a share of expected ones."""
        expected = len(self.missing_periods) + self.rows - self.duplicates
        return (self.rows - self.duplicates) / expected if expected else 1.0

    def summary(self) -> str:
        lines = [
            f"{self.column}: {self.rows:,} rows, {self.cadence.describe()}",
            f"  span {self.first} to {self.last}",
        ]
        if self.unparsed:
            lines.append(f"  {self.unparsed:,} values could not be read as a time")
        if self.duplicates:
            lines.append(f"  {self.duplicates:,} duplicate timestamps")
        if self.missing_periods:
            lines.append(
                f"  {len(self.missing_periods):,} missing periods ({self.coverage:.0%} coverage)"
            )
        if self.out_of_order:
            lines.append(f"  {self.out_of_order:,} rows out of chronological order")
        if self.mixed_timezones:
            lines.append("  mixed aware and naive timestamps")
        for run in self.stale_runs:
            lines.append(f"  {run['column']} repeated {run['length']:,} times from {run['start']}")
        return "\n".join(lines)

    def charts(self) -> list[Any]:
        """Specs describing the series, built from this report's own numbers."""
        from .viz.spec import ChartSpec, Encoding, Mark

        out: list[ChartSpec] = []
        if self.missing_periods:
            out.append(
                ChartSpec(
                    mark=Mark.BAR,
                    data=[{"label": str(p)[:10], "value": 1.0} for p in self.missing_periods[:60]],
                    x=Encoding("label", "nominal"),
                    y=Encoding("value"),
                    title=f"Missing periods in {self.column}",
                    rationale=(
                        "A gap in a series is a decision, not a detail: filling it "
                        "and dropping it give different answers."
                    ),
                )
            )
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "rows": self.rows,
            "cadence": self.cadence.to_dict(),
            "first": str(self.first),
            "last": str(self.last),
            "duplicates": self.duplicates,
            "missing_periods": [str(p) for p in self.missing_periods[:200]],
            "missing_period_count": len(self.missing_periods),
            "coverage": round(self.coverage, 4),
            "out_of_order": self.out_of_order,
            "unparsed": self.unparsed,
            "mixed_timezones": self.mixed_timezones,
            "stale_runs": [dict(r) for r in self.stale_runs],
            "issues": [i.id for i in self.issues],
        }


def _infer_cadence(times: pd.Series) -> Cadence:
    ordered = times.dropna().sort_values()
    if len(ordered) < 3:
        return Cadence("unknown", None, 0.0, "fewer than three timestamps")

    gaps = ordered.diff().dropna()
    gaps = gaps[gaps > pd.Timedelta(0)]
    if gaps.empty:
        return Cadence("unknown", None, 0.0, "every timestamp is identical")

    typical = gaps.median()
    for name, step in _CADENCES:
        if typical >= step * 0.75:
            # Agreement within a quarter of the step: a daily series with a
            # few hours of jitter is still daily, and calling it irregular
            # would bury the finding that matters under one that does not.
            close = (gaps - step).abs() <= step * 0.25
            return Cadence(name, step, float(close.mean()))
    return Cadence("sub-second", typical, 1.0)


#: A sentinel that is not any value a column could hold. ``object()`` inline
#: would be a fresh object every time, so ``is not object()`` is always true
#: and the guard it looks like never fires.
_UNSET: Any = object()


def _same(left: Any, right: Any) -> bool:
    """Equality that treats two missing values as the same run.

    ``NaN != NaN``, so without this a column of missing values looks like a
    run of length one repeated forever, and never reports as stale.
    """
    if left is _UNSET or right is _UNSET:
        return False
    left_missing, right_missing = pd.isna(left), pd.isna(right)
    if left_missing or right_missing:
        return bool(left_missing and right_missing)
    return bool(left == right)


def _stale_runs(
    frame: pd.DataFrame, times: pd.Series, columns: tuple[str, ...], minimum: int
) -> tuple[dict[str, Any], ...]:
    """Values that stop changing for longer than a series should allow.

    Usually a feed that stopped updating rather than a quantity that stopped
    moving -- and the two are indistinguishable from the value alone, which
    is exactly why it is reported rather than repaired.
    """
    order = times.argsort()
    found: list[dict[str, Any]] = []
    for column in columns:
        values = frame[column].iloc[order].reset_index(drop=True)
        run_start: int = 0
        run_value: Any = _UNSET
        # The trailing sentinel closes the final run: without it, a series that
        # ends inside a stale stretch never reports it, which is precisely the
        # case a reader most wants to know about.
        for position, value in enumerate([*values.tolist(), _UNSET]):
            if position and _same(value, run_value):
                continue
            length = position - run_start
            if length >= minimum and run_value is not _UNSET and pd.notna(run_value):
                found.append(
                    {
                        "column": column,
                        "value": str(run_value)[:40],
                        "length": length,
                        "start": str(times.iloc[order[run_start]]),
                    }
                )
            run_start, run_value = position, value
    return tuple(found)


def timeseries(
    frame: pd.DataFrame,
    time: str,
    *,
    watch: tuple[str, ...] | None = None,
    stale_after: int = 0,
) -> TimeSeriesReport:
    """Diagnose the shape of a series.

    Parameters
    ----------
    frame:
        The data. Never modified.
    time:
        The column holding the timestamps.
    watch:
        Columns to check for stale runs. Defaults to every numeric column.
    stale_after:
        How many identical consecutive values count as stale. ``0`` picks a
        threshold from the length of the series rather than imposing one:
        five repeats in a hundred points means something different from five
        in a million.
    """
    if time not in frame.columns:
        raise KeyError(f"no column {time!r} in this frame")

    raw = frame[time]
    times = pd.to_datetime(raw, errors="coerce", format="mixed")
    unparsed = int(times.isna().sum() - raw.isna().sum())

    report = TimeSeriesReport(
        column=time,
        rows=len(frame),
        cadence=_infer_cadence(times),
        first=times.min(),
        last=times.max(),
        unparsed=max(unparsed, 0),
    )

    present = times.dropna()
    report.duplicates = int(present.duplicated().sum())
    report.out_of_order = int((present.diff() < pd.Timedelta(0)).sum())
    report.mixed_timezones = _mixed_timezones(raw)

    if report.cadence.step is not None and len(present) > 2:
        expected = pd.date_range(present.min(), present.max(), freq=report.cadence.step)
        observed = set(present)
        report.missing_periods = tuple(t for t in expected if t not in observed)

    watched = watch or tuple(
        c for c in frame.columns if c != time and pd.api.types.is_numeric_dtype(frame[c])
    )
    threshold = stale_after or max(5, len(frame) // 10)
    if watched and len(present) == len(frame):
        report.stale_runs = _stale_runs(frame, times, watched, threshold)

    report.issues = _issues_for(report, times)
    return report


def _mixed_timezones(raw: pd.Series) -> bool:
    """Whether aware and naive timestamps are mixed in one column.

    Comparing an aware timestamp with a naive one is an error in pandas and a
    silent hour's difference in most other places, so it is worth its own
    check rather than being folded into "unparsed".
    """
    kinds = set()
    for value in raw.dropna().head(500):
        if isinstance(value, pd.Timestamp) or hasattr(value, "tzinfo"):
            kinds.add(value.tzinfo is not None)
    return len(kinds) > 1


def _issues_for(report: TimeSeriesReport, times: pd.Series) -> list[Issue]:
    """Findings, in the same shape every other detector produces.

    Deliberately not a parallel finding type: a gap in a series and a missing
    category go through one triage, one ladder and one review queue.
    """
    issues: list[Issue] = []
    column = report.column

    if report.duplicates:
        positions = tuple(int(p) for p in times.duplicated().to_numpy().nonzero()[0])
        issues.append(
            Issue(
                id=f"TS-DUPLICATE-{column}",
                category=IssueCategory.EXACT_DUPLICATE,
                severity=Severity.HIGH_WARNING,
                detection_confidence=1.0,
                rule_source=RuleSource.STATISTICAL_RULE,
                columns=(column,),
                evidence=Evidence(
                    summary=(
                        f"{report.duplicates:,} rows share a timestamp with another "
                        "row; a series with two observations at one instant has no "
                        "single value there"
                    ),
                    affected_rows=positions,
                    details={"duplicates": report.duplicates},
                ),
                detector="timeseries",
                treatments=(
                    TreatmentCandidate(
                        name="review_duplicate_timestamps",
                        description=(
                            "Decide whether these are genuine repeated measurements, "
                            "a failed de-duplication, or a resolution problem"
                        ),
                        repair_confidence=0.0,
                        domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                    ),
                ),
                notes="which observation is correct is a question about the source",
            )
        )

    if report.missing_periods:
        issues.append(
            Issue(
                id=f"TS-GAP-{column}",
                category=IssueCategory.MISSINGNESS,
                severity=Severity.WARNING,
                detection_confidence=0.95 if report.cadence.is_regular else 0.6,
                rule_source=RuleSource.STATISTICAL_RULE,
                columns=(column,),
                evidence=Evidence(
                    summary=(
                        f"{len(report.missing_periods):,} expected "
                        f"{report.cadence.name} periods are absent "
                        f"({report.coverage:.0%} coverage)"
                    ),
                    sample_values=tuple(str(p) for p in report.missing_periods[:5]),
                    details={
                        "cadence": report.cadence.name,
                        "agreement": round(report.cadence.agreement, 3),
                        "coverage": round(report.coverage, 4),
                    },
                ),
                detector="timeseries",
                treatments=(
                    TreatmentCandidate(
                        name="review_temporal_gaps",
                        description=(
                            "Decide whether the periods are missing or simply did "
                            "not exist -- a closed market has no Sunday"
                        ),
                        repair_confidence=0.0,
                        information_loss_risk=InformationLossRisk.HIGH,
                        statistical_impact=StatisticalImpact.MATERIAL,
                        domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                    ),
                ),
                notes=(
                    "filling a gap and dropping it give different answers, and "
                    "nothing in the data says which is right"
                ),
            )
        )

    if report.out_of_order:
        issues.append(
            Issue(
                id=f"TS-ORDER-{column}",
                category=IssueCategory.UNUSUAL_PATTERN,
                severity=Severity.WARNING,
                detection_confidence=1.0,
                rule_source=RuleSource.STATISTICAL_RULE,
                columns=(column,),
                evidence=Evidence(
                    summary=(
                        f"{report.out_of_order:,} rows are out of chronological "
                        "order; anything computed with a window or a lag will be "
                        "computed over the wrong neighbours"
                    ),
                    details={"out_of_order": report.out_of_order},
                ),
                detector="timeseries",
                treatments=(
                    TreatmentCandidate(
                        name="sort_chronologically",
                        description="Order the rows by their timestamp",
                        repair_confidence=0.97,
                        reversibility=Reversibility.REVERSIBLE,
                    ),
                ),
                recommended="sort_chronologically",
            )
        )

    if report.mixed_timezones:
        issues.append(
            Issue(
                id=f"TS-TIMEZONE-{column}",
                category=IssueCategory.MIXED_PHYSICAL_TYPE,
                severity=Severity.BLOCKING,
                detection_confidence=1.0,
                rule_source=RuleSource.STATISTICAL_RULE,
                columns=(column,),
                evidence=Evidence(
                    summary=(
                        "aware and naive timestamps are mixed in one column; "
                        "comparing them is an error in pandas and a silent hour's "
                        "difference nearly everywhere else"
                    )
                ),
                detector="timeseries",
                notes="the correct zone for the naive values is not in the data",
            )
        )

    for run in report.stale_runs:
        issues.append(
            Issue(
                id=f"TS-STALE-{run['column']}-{run['length']}",
                category=IssueCategory.UNUSUAL_PATTERN,
                severity=Severity.WARNING,
                detection_confidence=0.7,
                rule_source=RuleSource.STATISTICAL_RULE,
                columns=(run["column"],),
                evidence=Evidence(
                    summary=(
                        f"{run['column']} held {run['value']!r} for "
                        f"{run['length']:,} consecutive periods from {run['start']}"
                    ),
                    details=dict(run),
                ),
                detector="timeseries",
                notes=(
                    "a feed that stopped updating and a quantity that stopped "
                    "moving look identical from the value alone"
                ),
            )
        )

    return issues
