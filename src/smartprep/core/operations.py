"""Operations: the only thing allowed to change data.

Nothing mutates a frame except by executing an :class:`Operation`. That is what
makes every change auditable, reversible and reproducible -- there is exactly
one path through which data can move.

Each operation declares its **scope**, which is how the engine knows what a
change invalidates. Parsing ``unit_price`` from text to numbers does not just
fix a type: it changes what the range, formula and sentinel detectors would
find, because those were computed against the old representation. Re-running
them is not optional.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

from .enums import RepairClass, Reversibility, RuleSource

__all__ = ["OperationScope", "Operation", "RepairPlan", "OperationResult"]


class OperationScope(Enum):
    """What kind of change an operation makes, and therefore what it affects."""

    #: Changes how values are stored without changing what they mean
    #: (text "1,200" -> 1200.0). Invalidates every numeric and temporal finding.
    REPRESENTATION = "representation"

    #: Changes text content (case, whitespace, homoglyphs). Invalidates
    #: category, entity and text findings.
    TEXT = "text"

    #: Changes values. Invalidates statistical findings for those columns.
    VALUE = "value"

    #: Adds or removes rows or columns. Invalidates everything.
    STRUCTURAL = "structural"

    #: Records a decision without touching data.
    NO_OP = "no_op"


#: Which detectors a scope invalidates. A scope not listed here invalidates
#: nothing; ``STRUCTURAL`` invalidates all registered detectors.
SCOPE_INVALIDATES: dict[OperationScope, frozenset[str]] = {
    OperationScope.REPRESENTATION: frozenset(
        {
            "mixed_physical_type",
            "range_violation",
            "sentinel_candidate",
            "formula_invariant",
            "date_integrity",
            "state_consistency",
            "accounting_plausibility",
            "missingness",
        }
    ),
    OperationScope.TEXT: frozenset(
        {
            "category_variant",
            "unicode_confusable",
            "geographic_consistency",
            "currency_context",
            "duplicate_identifier",
            "state_consistency",
        }
    ),
    OperationScope.VALUE: frozenset(
        {
            "range_violation",
            "sentinel_candidate",
            "formula_invariant",
            "accounting_plausibility",
            "missingness",
            "state_consistency",
        }
    ),
    OperationScope.NO_OP: frozenset(),
}

#: Execution order by scope. Representation must settle before anything reads
#: values as numbers, and structural changes come last so earlier operations see
#: every row.
SCOPE_ORDER: dict[OperationScope, int] = {
    OperationScope.REPRESENTATION: 0,
    OperationScope.TEXT: 1,
    OperationScope.VALUE: 2,
    OperationScope.STRUCTURAL: 3,
    OperationScope.NO_OP: 4,
}


@dataclass(frozen=True)
class OperationResult:
    """Outcome of executing one operation."""

    frame: pd.DataFrame
    cells_changed: int
    note: str = ""


@dataclass(frozen=True)
class Operation:
    """A single, self-describing, executable change.

    ``execute`` receives a copy and returns a new frame. It must never modify
    its argument in place.
    """

    name: str
    scope: OperationScope
    columns: tuple[str, ...]
    execute: Callable[[pd.DataFrame], OperationResult]
    issue_ids: tuple[str, ...] = ()
    reason: str = ""
    rule_source: RuleSource = RuleSource.STATISTICAL_RULE
    repair_class: RepairClass = RepairClass.SAFE_AUTO_FIX
    repair_confidence: float = 1.0
    reversibility: Reversibility = Reversibility.REVERSIBLE_WITH_SNAPSHOT
    parameters: dict[str, Any] = field(default_factory=dict)

    #: Reserved for the multi-backend planner (AD-012 note): operations that
    #: cannot execute lazily must announce it rather than silently collecting.
    requires_materialization: bool = False

    @property
    def invalidates(self) -> frozenset[str]:
        if self.scope is OperationScope.STRUCTURAL:
            return frozenset({"*"})
        return SCOPE_INVALIDATES.get(self.scope, frozenset())

    @property
    def sort_key(self) -> tuple[int, str]:
        return (SCOPE_ORDER[self.scope], self.name)


@dataclass
class RepairPlan:
    """An ordered set of operations, sequenced by dependency rather than by
    the order the detectors happened to run.

    The ordering rule comes from the issue dependency graph: normalise
    representation, then text, then values, then structure. Applying a range
    check before the column has been parsed produces a confident answer to the
    wrong question.
    """

    operations: list[Operation] = field(default_factory=list)

    def add(self, operation: Operation) -> RepairPlan:
        self.operations.append(operation)
        return self

    def __len__(self) -> int:
        return len(self.operations)

    def __iter__(self) -> Any:
        return iter(self.ordered())

    def ordered(self) -> list[Operation]:
        """Operations in dependency order, stable within a scope."""
        return sorted(self.operations, key=lambda op: op.sort_key)

    @property
    def columns(self) -> tuple[str, ...]:
        seen: list[str] = []
        for op in self.operations:
            for column in op.columns:
                if column not in seen:
                    seen.append(column)
        return tuple(seen)

    def invalidated_detectors(self) -> frozenset[str]:
        """Detectors whose findings must be recomputed after this plan runs."""
        result: set[str] = set()
        for op in self.operations:
            result |= op.invalidates
        return frozenset(result)

    def describe(self) -> str:
        if not self.operations:
            return "No operations planned."
        lines = [f"{len(self.operations)} operations, in dependency order:"]
        for i, op in enumerate(self.ordered(), 1):
            lines.append(
                f"  {i}. [{op.scope.value:14s}] {op.name:32s} {', '.join(op.columns) or '-'}"
            )
        return "\n".join(lines)
