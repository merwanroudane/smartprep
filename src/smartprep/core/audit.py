"""The audit trail.

"Auditable" is only a real property if every change is recorded with enough
detail for someone who was not present to reconstruct what happened and decide
whether they agree with it.

An audit record therefore names the issue it answers, the rule that justified
it, who decided, what it touched, and the fingerprints on both sides of the
change.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .enums import RepairClass, RuleSource
from .rows import RowSet
from .snapshot import DatasetFingerprint

__all__ = ["DecisionSource", "AuditRecord", "AuditLog"]

_counter = itertools.count(1)


class DecisionSource(Enum):
    """Who authorised a change."""

    AUTOMATIC = "automatic"
    USER = "user"
    DOMAIN_RULE = "domain_rule"
    LEARNED_RULE = "learned_rule"


@dataclass(frozen=True)
class AuditRecord:
    """One recorded change, or one recorded refusal to change."""

    operation_id: str
    operation: str
    issue_ids: tuple[str, ...]
    columns: tuple[str, ...]
    rows: RowSet
    parameters: dict[str, Any]
    reason: str
    rule_source: RuleSource
    repair_class: RepairClass
    decision_source: DecisionSource
    repair_confidence: float
    reversible: bool
    before_fingerprint: DatasetFingerprint | None = None
    after_fingerprint: DatasetFingerprint | None = None
    cells_changed: int = 0
    parent_operation: str | None = None
    dataset_version: int = 0
    applied: bool = True
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @staticmethod
    def next_id(prefix: str = "OP") -> str:
        return f"{prefix}-{next(_counter):05d}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation": self.operation,
            "applied": self.applied,
            "issue_ids": list(self.issue_ids),
            "columns": list(self.columns),
            "rows_affected": len(self.rows),
            "cells_changed": self.cells_changed,
            "parameters": {str(k): str(v) for k, v in self.parameters.items()},
            "reason": self.reason,
            "rule_source": self.rule_source.value,
            "repair_class": self.repair_class.name,
            "decision_source": self.decision_source.value,
            "repair_confidence": self.repair_confidence,
            "reversible": self.reversible,
            "before_fingerprint": (
                self.before_fingerprint.to_dict() if self.before_fingerprint else None
            ),
            "after_fingerprint": (
                self.after_fingerprint.to_dict() if self.after_fingerprint else None
            ),
            "parent_operation": self.parent_operation,
            "dataset_version": self.dataset_version,
            "timestamp": self.timestamp,
        }


@dataclass
class AuditLog:
    """Ordered record of everything that happened, including what did not.

    Refusals are recorded alongside changes. A log that only lists successful
    edits cannot answer the question users actually ask, which is "why is this
    still wrong?".
    """

    records: list[AuditRecord] = field(default_factory=list)

    def append(self, record: AuditRecord) -> AuditRecord:
        self.records.append(record)
        return record

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self) -> Any:
        return iter(self.records)

    @property
    def applied(self) -> list[AuditRecord]:
        return [r for r in self.records if r.applied]

    @property
    def refused(self) -> list[AuditRecord]:
        return [r for r in self.records if not r.applied]

    @property
    def cells_changed(self) -> int:
        return sum(r.cells_changed for r in self.applied)

    def for_issue(self, issue_id: str) -> list[AuditRecord]:
        return [r for r in self.records if issue_id in r.issue_ids]

    def for_column(self, column: str) -> list[AuditRecord]:
        return [r for r in self.records if column in r.columns]

    def to_list(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self.records]

    def summary(self) -> str:
        lines = [f"{len(self.applied)} operations applied, {len(self.refused)} refused"]
        for record in self.records:
            mark = "applied " if record.applied else "REFUSED "
            lines.append(
                f"  {mark}{record.operation_id} {record.operation:32s} "
                f"{', '.join(record.columns) or '-':24s} "
                f"rows={len(record.rows):<5d} cells={record.cells_changed}"
            )
            if not record.applied:
                lines.append(f"      reason: {record.reason}")
        return "\n".join(lines)
