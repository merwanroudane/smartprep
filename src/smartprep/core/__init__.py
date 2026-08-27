"""Core models: issues, confidence policy, operations, audit, parsing."""

from .audit import AuditLog, AuditRecord, DecisionSource
from .eligibility import DEFAULT_LADDER, ConfidenceLadder, RiskProfile, band_for, classify
from .enums import (
    CompletionState,
    DomainSensitivity,
    InformationLossRisk,
    IssueCategory,
    MatchKind,
    RepairClass,
    Reversibility,
    RuleSource,
    Severity,
    StatisticalImpact,
)
from .health import DataHealthScore, Dimension, score_issues
from .identity import IdentitySource, StableRowIndex
from .issue import Evidence, Issue, TreatmentCandidate
from .operations import Operation, OperationResult, OperationScope, RepairPlan
from .rows import RowSet
from .snapshot import DatasetFingerprint, DatasetSnapshot, EnvironmentManifest
from .state import Comparison, FilterClause, Selection, StudioState

__all__ = [
    "AuditLog",
    "AuditRecord",
    "DecisionSource",
    "IdentitySource",
    "StableRowIndex",
    "StudioState",
    "Selection",
    "FilterClause",
    "Comparison",
    "DEFAULT_LADDER",
    "ConfidenceLadder",
    "RiskProfile",
    "band_for",
    "classify",
    "CompletionState",
    "DomainSensitivity",
    "InformationLossRisk",
    "IssueCategory",
    "MatchKind",
    "RepairClass",
    "Reversibility",
    "RuleSource",
    "Severity",
    "StatisticalImpact",
    "DataHealthScore",
    "Dimension",
    "score_issues",
    "Evidence",
    "Issue",
    "TreatmentCandidate",
    "Operation",
    "OperationResult",
    "OperationScope",
    "RepairPlan",
    "RowSet",
    "DatasetFingerprint",
    "DatasetSnapshot",
    "EnvironmentManifest",
]
