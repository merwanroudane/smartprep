"""Concrete repairs, one per treatment name.

Every action here is deliberately conservative. Where a treatment could be
implemented aggressively or narrowly, it is implemented narrowly: the values it
cannot fix with certainty are left alone and stay visible as open issues.

An action returns a **new** frame. Mutating the input would break the snapshot
guarantee that makes rollback possible.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from typing import Any

import pandas as pd

from ..core.issue import Issue, TreatmentCandidate
from ..core.operations import Operation, OperationResult, OperationScope
from ..core.parsing import DateStatus, dominant_layout, parse_date
from ..detectors.base import is_missing, physical_type, to_number
from ..detectors.textual import CONFUSABLES, INVISIBLE

__all__ = ["ACTIONS", "action", "build_operation", "has_action"]

#: treatment name -> builder that turns an issue into an executable operation
ACTIONS: dict[str, Callable[[Issue, TreatmentCandidate], Operation]] = {}


def action(treatment_name: str) -> Callable[[Any], Any]:
    """Register the implementation of a named treatment."""

    def decorate(builder: Any) -> Any:
        if treatment_name in ACTIONS:
            raise ValueError(f"action {treatment_name!r} is already registered")
        ACTIONS[treatment_name] = builder
        return builder

    return decorate


def has_action(treatment_name: str) -> bool:
    return treatment_name in ACTIONS


def build_operation(issue: Issue, treatment: TreatmentCandidate) -> Operation | None:
    """Turn a recommended treatment into an executable operation.

    Returns ``None`` when no implementation exists yet. A missing action is not
    an error -- it means auto mode leaves the issue open and says so, which is
    the correct behaviour for a treatment nobody has written.
    """
    builder = ACTIONS.get(treatment.name)
    return None if builder is None else builder(issue, treatment)


def _changed(before: pd.Series, after: pd.Series) -> int:
    """Count cells that actually differ, treating missing == missing."""
    total = 0
    for old, new in zip(before, after, strict=True):
        old_missing, new_missing = is_missing(old), is_missing(new)
        if old_missing and new_missing:
            continue
        if old_missing != new_missing or old != new:
            total += 1
    return total


def _op(
    name: str,
    scope: OperationScope,
    issue: Issue,
    treatment: TreatmentCandidate,
    execute: Callable[[pd.DataFrame], OperationResult],
    **extra: Any,
) -> Operation:
    return Operation(
        name=name,
        scope=scope,
        columns=issue.columns,
        execute=execute,
        issue_ids=(issue.id,),
        reason=treatment.description,
        rule_source=issue.rule_source,
        repair_class=issue.repair_class,
        repair_confidence=treatment.repair_confidence,
        reversibility=treatment.reversibility,
        parameters={**treatment.parameters, **extra},
    )


# --------------------------------------------------------------------------
# Representation
# --------------------------------------------------------------------------


@action("parse_numeric")
def _parse_numeric(issue: Issue, treatment: TreatmentCandidate) -> Operation:
    column = issue.columns[0]

    def execute(frame: pd.DataFrame) -> OperationResult:
        out = frame.copy(deep=True)
        before = out[column]
        parsed = before.map(to_number)
        # Only accept the conversion where it actually produced a number. A
        # value that fails to parse keeps its original form and stays visible.
        rebuilt = [
            new if (not is_missing(old) and not pd.isna(new)) else old
            for old, new in zip(before, parsed, strict=True)
        ]
        out[column] = pd.Series(rebuilt, index=out.index, dtype="float64")
        return OperationResult(out, _changed(before, out[column]))

    return _op("parse_numeric", OperationScope.REPRESENTATION, issue, treatment, execute)


@action("parse_datetime_unambiguous")
def _parse_datetime(issue: Issue, treatment: TreatmentCandidate) -> Operation:
    column = issue.columns[0]

    def execute(frame: pd.DataFrame) -> OperationResult:
        out = frame.copy(deep=True)
        before = out[column].copy()
        strings = [v for v in before if isinstance(v, str) and v.strip()]
        layout = dominant_layout(strings)

        converted = 0
        skipped = 0
        values = list(before)
        for i, value in enumerate(values):
            if not isinstance(value, str) or not value.strip():
                continue
            parsed = parse_date(value, layout)
            # Only the unambiguous ones. Ambiguous and invalid values stay as
            # they are so the date detector keeps reporting them.
            if parsed.status in (DateStatus.OK, DateStatus.FORMAT_CONFLICT) and parsed.value:
                values[i] = pd.Timestamp(parsed.value)
                converted += 1
            else:
                skipped += 1

        out[column] = pd.Series(values, index=out.index, dtype=object)
        return OperationResult(
            out,
            converted,
            note=f"{converted} converted, {skipped} left for review",
        )

    return _op(
        "parse_datetime_unambiguous",
        OperationScope.REPRESENTATION,
        issue,
        treatment,
        execute,
    )


@action("accept_unambiguous_parse")
def _accept_unambiguous(issue: Issue, treatment: TreatmentCandidate) -> Operation:
    """Convert values that parse to exactly one date in a non-dominant layout."""
    column = issue.columns[0]

    def execute(frame: pd.DataFrame) -> OperationResult:
        out = frame.copy(deep=True)
        before = out[column].copy()
        strings = [v for v in before if isinstance(v, str) and v.strip()]
        layout = dominant_layout(strings)

        values = list(before)
        converted = 0
        for i, value in enumerate(values):
            if not isinstance(value, str) or not value.strip():
                continue
            parsed = parse_date(value, layout)
            if parsed.status is DateStatus.FORMAT_CONFLICT and parsed.value:
                values[i] = pd.Timestamp(parsed.value)
                converted += 1

        out[column] = pd.Series(values, index=out.index, dtype=object)
        return OperationResult(out, converted)

    return _op("accept_unambiguous_parse", OperationScope.REPRESENTATION, issue, treatment, execute)


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------


@action("canonicalise_mechanical")
def _canonicalise(issue: Issue, treatment: TreatmentCandidate) -> Operation:
    """Apply only the merges that are pure whitespace, case or punctuation.

    The semantic candidates in the same issue -- spelling and language variants
    -- are deliberately not applied. They need confirmation.
    """
    column = issue.columns[0]
    mapping: dict[str, str] = dict(treatment.parameters.get("mapping", {}))

    def execute(frame: pd.DataFrame) -> OperationResult:
        out = frame.copy(deep=True)
        before = out[column].copy()
        out[column] = before.map(lambda v: mapping.get(v, v) if isinstance(v, str) else v)
        return OperationResult(out, _changed(before, out[column]))

    return _op(
        "canonicalise_mechanical",
        OperationScope.TEXT,
        issue,
        treatment,
        execute,
        merges=len(mapping),
    )


@action("fold_confusables")
def _fold_confusables(issue: Issue, treatment: TreatmentCandidate) -> Operation:
    column = issue.columns[0]

    def repair(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        folded = "".join(CONFUSABLES.get(ch, "" if ch in INVISIBLE else ch) for ch in value)
        # Normalise to NFC so visually identical strings compare equal, without
        # stripping the accents that carry meaning.
        return unicodedata.normalize("NFC", folded)

    def execute(frame: pd.DataFrame) -> OperationResult:
        out = frame.copy(deep=True)
        before = out[column].copy()
        out[column] = before.map(repair)
        return OperationResult(out, _changed(before, out[column]))

    return _op("fold_confusables", OperationScope.TEXT, issue, treatment, execute)


# --------------------------------------------------------------------------
# Recorded decisions that change nothing
# --------------------------------------------------------------------------


def _no_op(name: str) -> Callable[[Issue, TreatmentCandidate], Operation]:
    def builder(issue: Issue, treatment: TreatmentCandidate) -> Operation:
        def execute(frame: pd.DataFrame) -> OperationResult:
            return OperationResult(frame.copy(deep=True), 0, note="recorded; no change made")

        return _op(name, OperationScope.NO_OP, issue, treatment, execute)

    return builder


#: Leaving data alone is a decision, and it belongs in the audit trail as
#: explicitly as any edit. Imputing a payment date onto an unpaid invoice would
#: fabricate an event that never happened.
ACTIONS["leave_unchanged"] = _no_op("leave_unchanged")
ACTIONS["record_only"] = _no_op("record_only")


def physical_composition(frame: pd.DataFrame, column: str) -> dict[str, int]:
    """Helper for reports: how a column is stored, after repair."""
    counts: dict[str, int] = {}
    for value in frame[column]:
        form = physical_type(value)
        counts[form] = counts.get(form, 0) + 1
    return counts
