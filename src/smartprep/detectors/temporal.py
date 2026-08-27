"""Date integrity: invalid, ambiguous and format-conflicting values."""

from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

import pandas as pd

from ..core.enums import (
    InformationLossRisk,
    IssueCategory,
    Reversibility,
    RuleSource,
    Severity,
)
from ..core.issue import Evidence, Issue, TreatmentCandidate
from ..core.parsing import DateStatus, dominant_layout, parse_date
from .base import register

__all__ = ["DateIntegrityDetector"]


@register
class DateIntegrityDetector:
    """Classify string dates into four outcomes rather than one.

    The critical rule: an impossible date is reported, never corrected. There is
    no defensible mapping from ``31/02/2025`` to a real day, so the detector
    offers no treatment that invents one.
    """

    name = "date_integrity"

    def applicability(self, frame: pd.DataFrame, context: dict[str, Any]) -> tuple[Any, str]:
        from ..scan import Applicability

        named = context.get("date_columns") or ()
        if named:
            missing = [c for c in named if c not in frame.columns]
            if missing:
                return Applicability.NOT_APPLICABLE, f"columns not present: {missing}"
            return Applicability.APPLICABLE, ""
        # Fall back to inference: a column mixing text with real timestamps.
        for column in frame.columns:
            values = frame[column]
            if any(isinstance(v, str) for v in values) and any(
                isinstance(v, pd.Timestamp) for v in values
            ):
                return Applicability.APPLICABLE, ""
        return (
            Applicability.NOT_APPLICABLE,
            "no column mixes text with datetime values; pass date_columns=... to force",
        )

    def detect(
        self, frame: pd.DataFrame, *, date_columns: tuple[str, ...] = (), **context: Any
    ) -> list[Issue]:
        columns = date_columns or tuple(
            c
            for c in frame.columns
            if any(isinstance(v, str) for v in frame[c])
            and any(isinstance(v, pd.Timestamp) for v in frame[c])
        )

        issues: list[Issue] = []
        for column in columns:
            raw_strings = [
                (idx, v) for idx, v in enumerate(frame[column]) if isinstance(v, str) and v.strip()
            ]
            if not raw_strings:
                continue

            layout = dominant_layout([v for _, v in raw_strings])
            buckets: dict[DateStatus, list[tuple[int, str, str]]] = {
                status: [] for status in DateStatus
            }
            for idx, value in raw_strings:
                parsed = parse_date(value, layout)
                buckets[parsed.status].append((idx, value, parsed.note))

            issues.extend(self._invalid(column, buckets[DateStatus.INVALID], layout))
            issues.extend(self._ambiguous(column, buckets[DateStatus.AMBIGUOUS], layout))
            issues.extend(self._conflict(column, buckets[DateStatus.FORMAT_CONFLICT], layout))
            issues.extend(self._unparsed(frame, column, buckets, layout))
        return issues

    @staticmethod
    def _unparsed(
        frame: pd.DataFrame,
        column: str,
        buckets: dict[DateStatus, list[tuple[int, str, str]]],
        layout: str | None,
    ) -> list[Issue]:
        """A date column still held as text.

        The mixed-representation detector cannot see this: a column that is
        *entirely* strings has only one representation, so nothing looks mixed.
        But a column the caller named as a date, holding parseable text, is
        still stored in the wrong type -- and leaving it that way means every
        downstream temporal operation silently compares strings.
        """
        convertible = buckets[DateStatus.OK] + buckets[DateStatus.FORMAT_CONFLICT]
        if not convertible:
            return []
        # Already reported as mixed if real datetimes are present too.
        # pd.Timestamp subclasses datetime.datetime, so the one check covers
        # both -- checking Timestamp alone misses values read from Excel.
        if any(isinstance(v, dt.datetime) for v in frame[column]):
            return []

        return [
            Issue(
                id=f"DATE-UNPARSED-{column}",
                category=IssueCategory.MIXED_PHYSICAL_TYPE,
                severity=Severity.WARNING,
                detection_confidence=1.0,
                rule_source=RuleSource.PHYSICAL_TYPE_INFERENCE,
                columns=(column,),
                evidence=Evidence(
                    summary=(
                        f"{column!r} holds dates as text; {len(convertible)} values "
                        "parse unambiguously and can be converted"
                    ),
                    affected_rows=tuple(i for i, _, _ in convertible),
                    sample_values=tuple(v for _, v, _ in convertible)[:5],
                    details={"dominant_layout": layout, "convertible": len(convertible)},
                ),
                treatments=(
                    TreatmentCandidate(
                        name="parse_datetime_unambiguous",
                        description=(
                            "Convert unambiguous string dates to datetime; leave "
                            "invalid and ambiguous values for review."
                        ),
                        repair_confidence=0.99,
                        reversibility=Reversibility.REVERSIBLE_WITH_SNAPSHOT,
                        information_loss_risk=InformationLossRisk.LOW,
                    ),
                ),
                recommended="parse_datetime_unambiguous",
            )
        ]

    @staticmethod
    def _invalid(column: str, rows: list[tuple[int, str, str]], layout: str | None) -> list[Issue]:
        if not rows:
            return []
        counts = Counter(v for _, v, _ in rows)
        return [
            Issue(
                id=f"DATE-INVALID-{column}",
                category=IssueCategory.INVALID_DATE,
                severity=Severity.CRITICAL_REVIEW,
                detection_confidence=1.0,
                rule_source=RuleSource.PHYSICAL_TYPE_INFERENCE,
                columns=(column,),
                evidence=Evidence(
                    summary=(
                        f"{len(rows)} values in {column!r} are not valid calendar dates "
                        "under any supported layout"
                    ),
                    affected_rows=tuple(i for i, _, _ in rows),
                    sample_values=tuple(counts),
                    details={"value_counts": dict(counts), "dominant_layout": layout},
                ),
                # No treatment that produces a date. Offering one would mean
                # inventing data. Triage turns this into AMBIGUOUS.
                treatments=(),
                notes=(
                    "The correct value is not inferable. Options are to quarantine "
                    "the row or set the field to missing with a recorded reason -- "
                    "both are user decisions."
                ),
            )
        ]

    @staticmethod
    def _ambiguous(
        column: str, rows: list[tuple[int, str, str]], layout: str | None
    ) -> list[Issue]:
        if not rows:
            return []
        return [
            Issue(
                id=f"DATE-AMBIGUOUS-{column}",
                category=IssueCategory.AMBIGUOUS_DATE,
                severity=Severity.HIGH_WARNING,
                detection_confidence=1.0,
                rule_source=RuleSource.PHYSICAL_TYPE_INFERENCE,
                columns=(column,),
                evidence=Evidence(
                    summary=(
                        f"{len(rows)} values in {column!r} have more than one valid "
                        "reading; day-first and month-first both produce real dates"
                    ),
                    affected_rows=tuple(i for i, _, _ in rows),
                    sample_values=tuple(v for _, v, _ in rows)[:5],
                    details={"dominant_layout": layout},
                ),
                treatments=(
                    TreatmentCandidate(
                        name="apply_dominant_layout",
                        description=(
                            f"Read these using the column's dominant {layout} layout. "
                            "Supported by the column, not by the value itself."
                        ),
                        # Deliberately below the auto band: the column's habit is
                        # evidence, not proof, and a wrong reading silently moves
                        # a date by months.
                        repair_confidence=0.72,
                        reversibility=Reversibility.REVERSIBLE_WITH_SNAPSHOT,
                        information_loss_risk=InformationLossRisk.MEDIUM,
                    ),
                    TreatmentCandidate(
                        name="quarantine_for_review",
                        description="Hold these rows aside pending a per-value decision.",
                        repair_confidence=0.60,
                        reversibility=Reversibility.REVERSIBLE,
                    ),
                ),
                recommended="apply_dominant_layout",
            )
        ]

    @staticmethod
    def _conflict(column: str, rows: list[tuple[int, str, str]], layout: str | None) -> list[Issue]:
        if not rows:
            return []
        return [
            Issue(
                id=f"DATE-FORMAT-CONFLICT-{column}",
                category=IssueCategory.AMBIGUOUS_DATE,
                severity=Severity.NOTICE,
                detection_confidence=0.95,
                rule_source=RuleSource.INFERRED_RELATIONSHIP,
                columns=(column,),
                evidence=Evidence(
                    summary=(
                        f"{len(rows)} values in {column!r} parse to exactly one date, but "
                        f"in a layout that contradicts the column's dominant {layout}"
                    ),
                    affected_rows=tuple(i for i, _, _ in rows),
                    sample_values=tuple(v for _, v, _ in rows)[:5],
                    details={
                        "dominant_layout": layout,
                        "root_cause_hint": (
                            "a single unambiguous outlier layout often indicates a "
                            "different upstream export"
                        ),
                    },
                ),
                treatments=(
                    TreatmentCandidate(
                        name="accept_unambiguous_parse",
                        description=(
                            "Accept the only valid reading. The layout differs from the "
                            "column norm but the value itself is not ambiguous."
                        ),
                        repair_confidence=0.96,
                        reversibility=Reversibility.REVERSIBLE_WITH_SNAPSHOT,
                    ),
                ),
                recommended="accept_unambiguous_parse",
            )
        ]
