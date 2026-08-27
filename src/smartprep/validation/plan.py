"""Validation as a readable plan, not a stack trace.

A failed assertion tells you something broke. A validation *report* tells you
which rule, how many rows, whether that crosses the threshold you set, and lets
you pull the failing rows out to look at them.

The design follows the chainable-plan idea proven by Pointblank and Great
Expectations, with two additions: rules can be **inferred** from the data and
proposed for confirmation, and every failure links back to the rows.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

from ..core.rows import RowSet
from ..detectors.base import is_missing, to_number
from ..exceptions import SmartPrepValidationError

__all__ = ["Outcome", "Rule", "RuleResult", "ValidationResult", "ValidationPlan"]


class Outcome(Enum):
    """Graded rather than binary: 2% failures and 40% are not the same event."""

    PASS = "pass"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def failed(self) -> bool:
        return self is not Outcome.PASS


@dataclass(frozen=True)
class Rule:
    """One check, with the thresholds that decide how bad a failure is."""

    name: str
    description: str
    columns: tuple[str, ...]
    #: Takes the frame, returns a boolean Series: True where the rule holds.
    #: Typed loosely because the rule builders bind columns via default
    #: arguments, which changes the arity without changing the contract.
    predicate: Callable[..., pd.Series]
    warn_at: float = 0.0
    error_at: float = 0.05
    critical_at: float = 0.25

    def grade(self, failure_rate: float) -> Outcome:
        if failure_rate <= self.warn_at:
            return Outcome.PASS
        if failure_rate >= self.critical_at:
            return Outcome.CRITICAL
        if failure_rate >= self.error_at:
            return Outcome.ERROR
        return Outcome.WARNING


@dataclass(frozen=True)
class RuleResult:
    """What one rule found."""

    rule: Rule
    evaluated: int
    failed: int
    outcome: Outcome
    rows: RowSet

    @property
    def failure_rate(self) -> float:
        return self.failed / self.evaluated if self.evaluated else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule.name,
            "description": self.rule.description,
            "columns": list(self.rule.columns),
            "evaluated": self.evaluated,
            "failed": self.failed,
            "failure_rate": round(self.failure_rate, 4),
            "outcome": self.outcome.value,
            "thresholds": {
                "warn_at": self.rule.warn_at,
                "error_at": self.rule.error_at,
                "critical_at": self.rule.critical_at,
            },
        }

    def describe(self) -> str:
        return (
            f"{self.outcome.value.upper():9s} {self.rule.name:34s} "
            f"{self.failed}/{self.evaluated} failed ({self.failure_rate:.2%})"
        )


@dataclass
class ValidationResult:
    """The interrogation report."""

    frame: pd.DataFrame
    results: list[RuleResult] = field(default_factory=list)

    @property
    def outcome(self) -> Outcome:
        """The worst outcome across all rules."""
        order = [Outcome.PASS, Outcome.WARNING, Outcome.ERROR, Outcome.CRITICAL]
        return max((r.outcome for r in self.results), key=order.index, default=Outcome.PASS)

    @property
    def passed(self) -> bool:
        return self.outcome is Outcome.PASS

    @property
    def failing_rules(self) -> list[RuleResult]:
        return [r for r in self.results if r.outcome.failed]

    def failing_row_positions(self) -> set[int]:
        positions: set[int] = set()
        for result in self.results:
            positions |= set(result.rows.positions)
        return positions

    def split(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Separate the rows that passed everything from those that did not.

        Sundering the data is more useful than a verdict: the valid part can
        proceed while the invalid part is investigated.
        """
        failing = sorted(self.failing_row_positions())
        mask = np.ones(len(self.frame), dtype=bool)
        mask[failing] = False
        return self.frame.iloc[mask], self.frame.iloc[~mask]

    def get(self, rule_name: str) -> RuleResult:
        for result in self.results:
            if result.rule.name == rule_name:
                return result
        raise KeyError(f"no rule named {rule_name!r}. Ran: {[r.rule.name for r in self.results]}")

    def raise_if_failed(self, at: Outcome = Outcome.ERROR) -> ValidationResult:
        """Raise when the worst outcome reaches ``at``. For CI gates."""
        order = [Outcome.PASS, Outcome.WARNING, Outcome.ERROR, Outcome.CRITICAL]
        if order.index(self.outcome) >= order.index(at):
            failures = "\n".join(f"  {r.describe()}" for r in self.failing_rules)
            raise SmartPrepValidationError(
                f"validation reached {self.outcome.value} (gate is {at.value}):\n{failures}"
            )
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "outcome": self.outcome.value,
            "rows": len(self.frame),
            "rules": [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def summary(self) -> str:
        lines = [
            f"Validation: {self.outcome.value.upper()}",
            f"{len(self.frame)} rows, {len(self.results)} rules",
            "",
        ]
        lines += [f"  {r.describe()}" for r in self.results]
        if self.failing_rules:
            valid, invalid = self.split()
            lines += ["", f"  {len(valid)} rows pass every rule, {len(invalid)} do not."]
        return "\n".join(lines)

    def __repr__(self) -> str:  # pragma: no cover - display only
        return f"<ValidationResult {self.outcome.value} rules={len(self.results)}>"


class ValidationPlan:
    """Chainable rules, interrogated in one pass.

    Rules are collected first and run together, so one failure does not hide
    the next. Every rule reports how many rows it evaluated, not just whether
    it passed -- a rule that silently evaluated nothing is not a pass.
    """

    def __init__(self, frame: pd.DataFrame | None = None) -> None:
        self.frame = frame
        self.rules: list[Rule] = []

    def _add(self, rule: Rule) -> ValidationPlan:
        if any(r.name == rule.name for r in self.rules):
            raise ValueError(f"a rule named {rule.name!r} is already in this plan")
        self.rules.append(rule)
        return self

    # -- structural ---------------------------------------------------------

    def column_exists(self, column: str, **thresholds: float) -> ValidationPlan:
        return self._add(
            Rule(
                name=f"column_exists:{column}",
                description=f"{column!r} must be present",
                columns=(column,),
                predicate=lambda f, c=column: (
                    pd.Series([c in f.columns] * max(len(f), 1), index=f.index[: max(len(f), 1)])
                    if len(f)
                    else pd.Series([c in f.columns])
                ),
                **thresholds,
            )
        )

    def no_unexpected_columns(self, expected: list[str], **thresholds: float) -> ValidationPlan:
        """Fail when the frame carries columns the contract does not declare.

        A dataset-level rule rather than a row-level one, so it reports a single
        pass or fail rather than a per-row rate.
        """
        allowed = list(expected)
        return self._add(
            Rule(
                name="no_unexpected_columns",
                description=f"only the declared columns may be present: {sorted(allowed)}",
                columns=(),
                predicate=lambda f, a=allowed: _dataset_rule(
                    f, not [c for c in f.columns if c not in a]
                ),
                **thresholds,
            )
        )

    def not_null(self, column: str, **thresholds: float) -> ValidationPlan:
        return self._add(
            Rule(
                name=f"not_null:{column}",
                description=f"{column!r} must not be missing",
                columns=(column,),
                predicate=lambda f, c=column: ~f[c].map(is_missing),
                **thresholds,
            )
        )

    def unique(self, column: str, **thresholds: float) -> ValidationPlan:
        return self._add(
            Rule(
                name=f"unique:{column}",
                description=f"{column!r} must not repeat",
                columns=(column,),
                predicate=lambda f, c=column: ~f[c].duplicated(keep=False),
                **thresholds,
            )
        )

    def unique_together(self, *columns: str, **thresholds: float) -> ValidationPlan:
        cols = list(columns)
        return self._add(
            Rule(
                name=f"unique_together:{'+'.join(cols)}",
                description=f"the combination {cols} must not repeat",
                columns=tuple(cols),
                predicate=lambda f, c=cols: ~f.duplicated(subset=c, keep=False),
                **thresholds,
            )
        )

    # -- values -------------------------------------------------------------

    def between(
        self, column: str, minimum: float, maximum: float, **thresholds: float
    ) -> ValidationPlan:
        return self._add(
            Rule(
                name=f"between:{column}",
                description=f"{column!r} must lie in [{minimum}, {maximum}]",
                columns=(column,),
                predicate=lambda f, c=column: _in_range(f[c], minimum, maximum),
                **thresholds,
            )
        )

    def isin(self, column: str, allowed: list[Any], **thresholds: float) -> ValidationPlan:
        permitted = {str(v) for v in allowed}
        return self._add(
            Rule(
                name=f"isin:{column}",
                description=f"{column!r} must be one of {sorted(permitted)}",
                columns=(column,),
                predicate=lambda f, c=column: f[c].map(
                    lambda v: is_missing(v) or str(v) in permitted
                ),
                **thresholds,
            )
        )

    def matches(self, column: str, pattern: str, **thresholds: float) -> ValidationPlan:
        compiled = re.compile(pattern)
        return self._add(
            Rule(
                name=f"matches:{column}",
                description=f"{column!r} must match {pattern}",
                columns=(column,),
                predicate=lambda f, c=column: f[c].map(
                    lambda v: is_missing(v) or bool(compiled.match(str(v)))
                ),
                **thresholds,
            )
        )

    # -- cross-column -------------------------------------------------------

    def custom(
        self,
        expression: str,
        *,
        name: str | None = None,
        columns: tuple[str, ...] = (),
        **thresholds: float,
    ) -> ValidationPlan:
        """A row-level rule written as a pandas expression.

        Evaluated with ``DataFrame.eval``, which does not execute arbitrary
        Python -- a rule from a config file cannot become code execution.
        """
        return self._add(
            Rule(
                name=name or f"custom:{expression}",
                description=expression,
                columns=columns,
                predicate=lambda f, e=expression: _eval_expression(f, e),
                **thresholds,
            )
        )

    def implies(
        self,
        when: str,
        then: str,
        *,
        name: str | None = None,
        **thresholds: float,
    ) -> ValidationPlan:
        """``when`` true requires ``then`` true. Rows where ``when`` is false pass."""
        return self._add(
            Rule(
                name=name or f"implies:{when}=>{then}",
                description=f"where {when}, {then} must hold",
                columns=(),
                predicate=lambda f, w=when, t=then: (
                    (~_eval_expression(f, w)) | _eval_expression(f, t)
                ),
                **thresholds,
            )
        )

    # -- running ------------------------------------------------------------

    def run(self, frame: pd.DataFrame | None = None) -> ValidationResult:
        """Interrogate. Every rule runs, so one failure cannot hide another."""
        target = frame if frame is not None else self.frame
        if target is None:
            raise ValueError("run() needs a DataFrame, either here or at construction")

        result = ValidationResult(frame=target)
        for rule in self.rules:
            missing = [c for c in rule.columns if c and c not in target.columns]
            if missing and not rule.name.startswith("column_exists"):
                result.results.append(
                    RuleResult(
                        rule,
                        0,
                        len(target),
                        Outcome.CRITICAL,
                        RowSet.of(range(len(target))),
                    )
                )
                continue
            try:
                holds = rule.predicate(target).fillna(False).astype(bool)
            except Exception as exc:
                raise SmartPrepValidationError(
                    f"rule {rule.name!r} could not be evaluated: {type(exc).__name__}: {exc}"
                ) from exc

            failed_positions = [int(i) for i in np.flatnonzero(~holds.to_numpy())]
            evaluated = len(holds)
            outcome = rule.grade(len(failed_positions) / evaluated if evaluated else 0.0)
            result.results.append(
                RuleResult(
                    rule=rule,
                    evaluated=evaluated,
                    failed=len(failed_positions),
                    outcome=outcome,
                    rows=RowSet.of(failed_positions).with_index(target.index),
                )
            )
        return result

    def __len__(self) -> int:
        return len(self.rules)

    def describe(self) -> str:
        lines = [f"Validation plan: {len(self.rules)} rules", ""]
        for rule in self.rules:
            lines.append(f"  {rule.name:36s} {rule.description}")
        return "\n".join(lines)


def _dataset_rule(frame: pd.DataFrame, holds: bool) -> pd.Series:
    """Express a whole-dataset check as a per-row Series.

    Every row shares the verdict, so the rule reads as 0% or 100% failed rather
    than pretending to be a row-level rate.
    """
    return pd.Series([holds] * len(frame), index=frame.index, dtype=bool)


def _in_range(series: pd.Series, minimum: float, maximum: float) -> pd.Series:
    values = series.map(to_number)
    # Missing values are the not_null rule's business, not this one's. A rule
    # that fails on absence conflates two different problems.
    return values.isna() | ((values >= minimum) & (values <= maximum))


def _eval_expression(frame: pd.DataFrame, expression: str) -> pd.Series:
    outcome = frame.eval(expression)
    if not isinstance(outcome, pd.Series):
        outcome = pd.Series([bool(outcome)] * len(frame), index=frame.index)
    return outcome.fillna(False).astype(bool)
