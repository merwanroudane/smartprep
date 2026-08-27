"""The repair executor: snapshot, apply, verify, commit or roll back.

Two guarantees this module exists to provide:

1. **Nothing is applied without a restore point.** Every operation snapshots
   first, so "reversible" is enforced rather than asserted.
2. **A failed operation cannot leave the data half-changed.** If execution
   raises, the snapshot is restored and the failure is recorded as a refusal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..core.audit import AuditLog, AuditRecord, DecisionSource
from ..core.enums import RepairClass, Reversibility
from ..core.operations import Operation, RepairPlan
from ..core.rows import RowSet
from ..core.snapshot import DatasetFingerprint, DatasetSnapshot

__all__ = ["ExecutionOutcome", "RepairExecutor"]


@dataclass
class ExecutionOutcome:
    """Result of running a plan."""

    frame: pd.DataFrame
    audit: AuditLog
    snapshots: list[DatasetSnapshot] = field(default_factory=list)
    applied: list[Operation] = field(default_factory=list)
    refused: list[tuple[Operation, str]] = field(default_factory=list)

    @property
    def cells_changed(self) -> int:
        return self.audit.cells_changed

    @property
    def touched_columns(self) -> tuple[str, ...]:
        seen: list[str] = []
        for op in self.applied:
            for column in op.columns:
                if column not in seen:
                    seen.append(column)
        return tuple(seen)


class RepairExecutor:
    """Applies a :class:`RepairPlan` under transaction semantics."""

    def __init__(self, *, decision_source: DecisionSource = DecisionSource.AUTOMATIC) -> None:
        self.decision_source = decision_source

    def run(
        self,
        frame: pd.DataFrame,
        plan: RepairPlan,
        *,
        audit: AuditLog | None = None,
    ) -> ExecutionOutcome:
        """Execute a plan in dependency order against a copy.

        The caller's frame is never touched, so running a plan *is* a preview.
        Committing is the caller keeping ``outcome.frame``; discarding it is the
        rollback.
        """
        audit = audit if audit is not None else AuditLog()
        current = frame.copy(deep=True)
        outcome = ExecutionOutcome(frame=current, audit=audit)

        version = 0
        outcome.snapshots.append(DatasetSnapshot.of(current, version, "raw"))

        for operation in plan.ordered():
            before_fp = DatasetFingerprint.of(current)
            restore_point = current.copy(deep=True)

            try:
                result = operation.execute(current)
            except Exception as exc:
                # A broken operation must never leave the frame partly edited.
                current = restore_point
                reason = (
                    f"operation raised {type(exc).__name__}: {exc}; "
                    "the dataset was restored to its previous state"
                )
                outcome.refused.append((operation, reason))
                audit.append(self._record(operation, RowSet(), 0, reason, applied=False))
                continue

            if result.frame is current:
                # An action that returns its input has mutated in place or
                # forgotten to copy; either way the snapshot promise is void.
                current = restore_point
                reason = "operation returned the input frame instead of a new one"
                outcome.refused.append((operation, reason))
                audit.append(self._record(operation, RowSet(), 0, reason, applied=False))
                continue

            current = result.frame
            version += 1
            outcome.snapshots.append(DatasetSnapshot.of(current, version, operation.name))
            outcome.applied.append(operation)

            note = result.note or operation.reason
            audit.append(
                self._record(
                    operation,
                    RowSet(),
                    result.cells_changed,
                    note,
                    applied=True,
                    before=before_fp,
                    after=DatasetFingerprint.of(current),
                    version=version,
                )
            )

        outcome.frame = current
        return outcome

    def _record(
        self,
        operation: Operation,
        rows: RowSet,
        cells: int,
        reason: str,
        *,
        applied: bool,
        before: DatasetFingerprint | None = None,
        after: DatasetFingerprint | None = None,
        version: int = 0,
    ) -> AuditRecord:
        return AuditRecord(
            operation_id=AuditRecord.next_id(),
            operation=operation.name,
            issue_ids=operation.issue_ids,
            columns=operation.columns,
            rows=rows,
            parameters=operation.parameters,
            reason=reason,
            rule_source=operation.rule_source,
            repair_class=operation.repair_class,
            decision_source=self.decision_source,
            repair_confidence=operation.repair_confidence,
            reversible=operation.reversibility is not Reversibility.IRREVERSIBLE,
            before_fingerprint=before,
            after_fingerprint=after,
            cells_changed=cells,
            dataset_version=version,
            applied=applied,
        )

    @staticmethod
    def record_abstention(
        audit: AuditLog,
        issue_id: str,
        columns: tuple[str, ...],
        repair_class: RepairClass,
        reasons: list[str],
        rows: RowSet,
    ) -> AuditRecord:
        """Record that automatic mode deliberately did not act.

        This is the entry that lets the report answer "why is this still
        flagged?" without the user having to guess.
        """
        from ..core.enums import RuleSource

        return audit.append(
            AuditRecord(
                operation_id=AuditRecord.next_id("SKIP"),
                operation="abstained",
                issue_ids=(issue_id,),
                columns=columns,
                rows=rows,
                parameters={},
                reason="; ".join(reasons) if reasons else "not eligible for automatic repair",
                rule_source=RuleSource.STATISTICAL_RULE,
                repair_class=repair_class,
                decision_source=DecisionSource.AUTOMATIC,
                repair_confidence=0.0,
                reversible=True,
                applied=False,
            )
        )
