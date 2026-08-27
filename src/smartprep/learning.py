"""Learning validation rules from data that is believed to be good.

Writing a validation plan by hand is the step everyone skips. Learning one is
easy and dangerous in equal measure: a rule inferred from a sample is a
statement about *that sample*, and the moment it is applied to next month's
data it becomes a claim about the world. A learner that does not say the
difference produces a plan that fails on the first legitimate new value and
teaches its owner to disable validation.

So every learned rule carries three things a hand-written one does not:

``evidence``
    How many rows supported it. A range learned from forty rows and one
    learned from four million are not the same rule.
``confidence``
    How likely it is to be a property of the world rather than of the sample.
``caveat``
    What would falsify it, in words.

And the learner **abstains** rather than guessing. A category set from thirty
rows is not a category set; a range from a skewed column is a range that will
reject the next tail value. Where the evidence is thin, no rule is emitted and
the reason is recorded, because an unlearned rule is visible and a wrong one
is not.

Nothing here validates anything. It produces a
:class:`~smartprep.validation.plan.ValidationPlan` you read, edit and then
run -- the review step is the point, and a learner that ran its own output
would have removed it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pandas as pd

from .validation.plan import ValidationPlan

__all__ = ["LearnedRule", "LearnedPlan", "learn_rules"]

#: Below this many rows, a learned constraint describes the sample only.
_MIN_ROWS = 50

#: A categorical column with more distinct levels than this is not a fixed
#: vocabulary, whatever the sample suggests.
_MAX_LEVELS = 25

#: Levels must be seen at least this often before the set is called closed.
_MIN_LEVEL_SUPPORT = 3


@dataclass(frozen=True)
class LearnedRule:
    """One rule, with what supports it and what would break it."""

    kind: str
    column: str
    parameters: dict[str, Any]
    evidence_rows: int
    confidence: float
    caveat: str

    def describe(self) -> str:
        detail = ", ".join(f"{k}={v!r}" for k, v in self.parameters.items())
        return f"{self.kind}({self.column}{', ' + detail if detail else ''})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "column": self.column,
            "parameters": dict(self.parameters),
            "evidence_rows": self.evidence_rows,
            "confidence": round(self.confidence, 4),
            "caveat": self.caveat,
            "describe": self.describe(),
        }


@dataclass
class LearnedPlan:
    """Rules learned from a sample, and everything not learned from it."""

    rules: list[LearnedRule] = field(default_factory=list)
    #: Columns a rule was considered for and refused, with the reason.
    abstained: list[tuple[str, str]] = field(default_factory=list)
    rows: int = 0

    #: Printed with every plan. The distinction it draws is the one that turns
    #: a useful learner into a harmful one when it is forgotten.
    caveat: str = (
        "These rules describe the sample they were learned from. Applied to "
        "new data they become claims about the world, and the world was not "
        "consulted. Read them before running them."
    )

    def plan(self) -> ValidationPlan:
        """The rules as a runnable plan. Read it before you run it."""
        built = ValidationPlan()
        for rule in self.rules:
            if rule.kind == "not_null":
                built.not_null(rule.column)
            elif rule.kind == "unique":
                built.unique(rule.column)
            elif rule.kind == "between":
                built.between(rule.column, rule.parameters["minimum"], rule.parameters["maximum"])
            elif rule.kind == "isin":
                built.isin(rule.column, list(rule.parameters["allowed"]))
            elif rule.kind == "matches":
                built.matches(rule.column, rule.parameters["pattern"])
        return built

    def summary(self) -> str:
        lines = [f"{len(self.rules)} rules learned from {self.rows:,} rows"]
        for rule in self.rules:
            lines.append(f"  {rule.describe()}  [{rule.confidence:.0%}] {rule.caveat}")
        for column, reason in self.abstained:
            lines.append(f"  no rule for {column}: {reason}")
        lines += ["", self.caveat]
        return "\n".join(lines)

    def to_python(self) -> str:
        """The plan as code, so it can be reviewed and version-controlled.

        A learned plan nobody reads is a learned plan nobody can correct, and
        the corrections are where the domain knowledge enters.
        """
        lines = ["import smartprep as sp", "", "plan = (", "    sp.ValidationPlan()"]
        for rule in self.rules:
            if rule.kind == "between":
                call = (
                    f'.between("{rule.column}", {rule.parameters["minimum"]!r}, '
                    f"{rule.parameters['maximum']!r})"
                )
            elif rule.kind == "isin":
                call = f'.isin("{rule.column}", {list(rule.parameters["allowed"])!r})'
            elif rule.kind == "matches":
                call = f'.matches("{rule.column}", r"{rule.parameters["pattern"]}")'
            else:
                call = f'.{rule.kind}("{rule.column}")'
            lines.append(f"    {call}  # {rule.confidence:.0%} -- {rule.caveat}")
        lines += [")", "", "result = plan.run(df)"]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "caveat": self.caveat,
            "rules": [r.to_dict() for r in self.rules],
            "abstained": [{"column": c, "reason": r} for c, r in self.abstained],
        }


def _numeric_rule(column: str, values: pd.Series, rows: int, margin: float) -> LearnedRule | None:
    numbers = pd.to_numeric(values, errors="coerce").dropna()
    if len(numbers) < _MIN_ROWS:
        return None

    low, high = float(numbers.min()), float(numbers.max())
    span = high - low
    if span <= 0:
        return None

    # Widened deliberately. A bound learned at exactly the observed minimum
    # rejects the first legitimately smaller value, which is a false alarm on
    # day one and the reason validation gets switched off.
    padded_low = low - span * margin
    padded_high = high + span * margin

    # Widening must not invent a sign the data has never shown. A quantity
    # that has never been negative in four hundred rows gets a floor of zero,
    # not of minus a hundred -- a bound that admits impossible values is not a
    # rule, it is decoration.
    floor_note = ""
    if low >= 0 > padded_low:
        padded_low = 0.0
        floor_note = "; floored at zero, which the column has never gone below"

    # Round to something a reader would have written by hand. A bound of
    # 17.43219 reads as a measurement; 17 reads as a decision.
    if float(numbers.round().eq(numbers).mean()) > 0.99:
        padded_low, padded_high = float(int(padded_low)), float(int(padded_high) + 1)

    # cast(): Series.skew() is typed as returning any scalar the frame
    # could hold, though on a numeric Series it is always a float.
    skew = float(cast(float, numbers.skew())) if len(numbers) > 2 else 0.0
    confidence = 0.9 if abs(skew) < 2 else 0.6
    caveat = (
        f"observed {low:,.4g} to {high:,.4g} in {len(numbers):,} rows, widened "
        f"by {margin:.0%}{floor_note}"
    )
    if abs(skew) >= 2:
        caveat += "; the column is skewed, so the upper tail is under-sampled"

    return LearnedRule(
        kind="between",
        column=column,
        parameters={"minimum": padded_low, "maximum": padded_high},
        evidence_rows=len(numbers),
        confidence=confidence,
        caveat=caveat,
    )


def _category_rule(column: str, values: pd.Series, rows: int) -> LearnedRule | None:
    counts = values.dropna().astype(str).value_counts()
    if len(counts) > _MAX_LEVELS or counts.empty:
        return None
    if int(counts.min()) < _MIN_LEVEL_SUPPORT:
        # A level seen once may be the first of many, or a typo. Closing the
        # set on that evidence rejects whichever it turns out to be.
        return None

    return LearnedRule(
        kind="isin",
        column=column,
        parameters={"allowed": tuple(counts.index)},
        evidence_rows=int(counts.sum()),
        confidence=0.85 if len(counts) <= 10 else 0.7,
        caveat=(
            f"{len(counts)} levels, each seen at least {int(counts.min())} times; "
            "a genuinely new category will fail this rule, which may be what you "
            "want or may be a false alarm"
        ),
    )


def learn_rules(
    frame: pd.DataFrame,
    *,
    margin: float = 0.1,
    columns: tuple[str, ...] | None = None,
) -> LearnedPlan:
    """Learn a validation plan from data believed to be good.

    ``frame`` is never modified, and nothing is validated. The result is a
    plan to read, edit and then run.

    Parameters
    ----------
    margin:
        How far to widen a learned numeric bound beyond what was observed. A
        bound at exactly the observed minimum rejects the first legitimately
        smaller value.
    """
    from .detectors.base import is_missing
    from .eda.profile import ColumnKind, profile

    learned = LearnedPlan(rows=len(frame))
    if len(frame) < _MIN_ROWS:
        learned.abstained.append(
            (
                "*",
                f"{len(frame)} rows is below the {_MIN_ROWS} needed for a rule to "
                "describe anything but this sample",
            )
        )
        return learned

    described = profile(frame)
    wanted = columns or tuple(str(c) for c in frame.columns)

    for name in wanted:
        if name not in frame.columns:
            continue
        column = described.get(name)
        values = frame[name]
        absent = int(values.map(is_missing).sum())

        if column.kind is ColumnKind.UNSUPPORTED:
            learned.abstained.append((name, column.unsupported_reason))
            continue

        # Completeness. Only claimed when the sample is unanimous -- one
        # missing value in the sample means missing is possible.
        if absent == 0:
            learned.rules.append(
                LearnedRule(
                    kind="not_null",
                    column=name,
                    parameters={},
                    evidence_rows=len(frame),
                    confidence=0.9,
                    caveat=f"no value was missing in {len(frame):,} rows",
                )
            )

        # Uniqueness. A column unique across the sample may simply not have
        # collided yet, so this is offered at lower confidence.
        present = values[~values.map(is_missing)]
        # A float column being all-distinct is what floats do, not evidence of
        # a key. Offering `unique` there produces a rule that passes until the
        # first legitimate coincidence and then fails for no reason.
        could_be_key = not pd.api.types.is_float_dtype(values) or (
            column.kind is not ColumnKind.NUMERIC
        )
        if could_be_key and len(present) >= _MIN_ROWS and present.nunique() == len(present):
            learned.rules.append(
                LearnedRule(
                    kind="unique",
                    column=name,
                    parameters={},
                    evidence_rows=len(present),
                    confidence=0.75,
                    caveat=(
                        f"no duplicate in {len(present):,} rows, which is evidence "
                        "of a key and not proof of one"
                    ),
                )
            )

        rule: LearnedRule | None = None
        if column.kind is ColumnKind.NUMERIC:
            rule = _numeric_rule(name, values, len(frame), margin)
            if rule is None:
                learned.abstained.append((name, "too few numeric values, or no spread to bound"))
        elif column.kind in (ColumnKind.CATEGORICAL, ColumnKind.ORDINAL):
            rule = _category_rule(name, values, len(frame))
            if rule is None:
                learned.abstained.append(
                    (
                        name,
                        f"more than {_MAX_LEVELS} levels, or a level seen fewer "
                        f"than {_MIN_LEVEL_SUPPORT} times -- not a closed vocabulary",
                    )
                )
        elif column.kind is ColumnKind.TEXT:
            learned.abstained.append((name, "free text has no shape worth asserting from a sample"))

        if rule is not None:
            learned.rules.append(rule)

    return learned
