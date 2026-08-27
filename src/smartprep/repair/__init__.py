"""Repair layer: the only path through which data changes."""

from .actions import ACTIONS, action, build_operation, has_action
from .executor import ExecutionOutcome, RepairExecutor
from .sandbox import SummaryDelta, TreatmentPreview, preview, preview_candidates

__all__ = [
    "ACTIONS",
    "action",
    "build_operation",
    "has_action",
    "ExecutionOutcome",
    "RepairExecutor",
    "preview",
    "preview_candidates",
    "TreatmentPreview",
    "SummaryDelta",
]
