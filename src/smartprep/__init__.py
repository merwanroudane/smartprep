"""SmartPrep -- intelligent, auditable data preparation.

The public API is deliberately explicit. There is no call that decides on your
behalf whether to repair automatically or ask you (AD-002)::

    sp.scan(df)            # diagnose only, never modifies
    sp.auto_prepare(df)    # repair only what is provably safe
    sp.guided_prepare(df)  # ask about everything that is not
    sp.studio(df)          # the same engine, with a screen

``sp.clean(df)`` is a convenience alias for ``auto_prepare``. It is not a more
aggressive mode, and it does not suppress warnings.
"""

from __future__ import annotations

from .anomaly import AnomalyReport, Outlier, anomalies
from .capabilities import CAPABILITIES, Capability, capability_table
from .core import (
    AuditLog,
    AuditRecord,
    Comparison,
    CompletionState,
    ConfidenceLadder,
    DataHealthScore,
    Evidence,
    FilterClause,
    Issue,
    IssueCategory,
    Operation,
    RepairClass,
    RepairPlan,
    RowSet,
    Selection,
    Severity,
    StudioState,
    TreatmentCandidate,
)
from .core.identity import StableRowIndex
from .display import Align, Column, Table, format_number
from .drift import DriftReport, DriftSeverity, cleaning_drift
from .drift import compare as compare_reference
from .eda import (
    AssociationMatrix,
    ColumnProfile,
    DatasetProfile,
    MissingnessPattern,
    associations,
    compare_profiles,
    missingness,
    profile,
    support_for,
    support_table,
)
from .exceptions import (
    SmartPrepAmbiguityError,
    SmartPrepBackendError,
    SmartPrepContractError,
    SmartPrepError,
    SmartPrepPrivacyError,
    SmartPrepSchemaError,
    SmartPrepTypeError,
    SmartPrepUnsafeRepairError,
    SmartPrepValidationError,
)
from .guided import (
    Action,
    Decision,
    GuidedSession,
    Question,
    QuestionLevel,
    guided_prepare,
)
from .learning import LearnedPlan, LearnedRule, learn_rules
from .linkage import CandidatePair, LinkageReport, link
from .mechanism import ColumnMechanism, Mechanism, MechanismReport, mechanism
from .panel import PanelReport, Variation, panel
from .prepare import PreparationResult, auto_prepare, clean
from .preprocessing import (
    Goal,
    LeakageWarning,
    PreprocessingAdvice,
    Preprocessor,
    recommend_preprocessing,
)
from .privacy import PrivacyReport, PrivacyScanner, Sensitivity
from .repair import TreatmentPreview, preview, preview_candidates
from .reporting import publish
from .scan import Applicability, CheckOutcome, ScanResult, scan
from .studio import Studio, studio
from .timeseries import Cadence, TimeSeriesReport, timeseries
from .validation import DataContract, Outcome, ValidationPlan, ValidationResult
from .viz import ChartSet, ChartSpec, Composition, Mark, compose, fields_of, render_svg
from .viz import recommend as recommend_charts
from .workflow import (
    Node,
    Stage,
    Workflow,
    WorkflowError,
    WorkflowRun,
    default_workflow,
)

__version__ = "1.0.2"

__all__ = [
    # entry points
    "scan",
    "auto_prepare",
    "guided_prepare",
    "clean",
    "studio",
    # results
    "ScanResult",
    "PreparationResult",
    "CheckOutcome",
    "Applicability",
    "CompletionState",
    # guided mode
    "GuidedSession",
    "Question",
    "Decision",
    "Action",
    "QuestionLevel",
    # preprocessing
    "Preprocessor",
    "recommend_preprocessing",
    "PreprocessingAdvice",
    "LeakageWarning",
    "Goal",
    # eda and visualization
    "profile",
    "DatasetProfile",
    "ColumnProfile",
    "associations",
    "AssociationMatrix",
    "missingness",
    "MissingnessPattern",
    "compare_profiles",
    "support_for",
    "support_table",
    "ChartSpec",
    "ChartSet",
    "Mark",
    "render_svg",
    "Studio",
    # shared visual interaction state
    "StudioState",
    "Selection",
    "FilterClause",
    "Comparison",
    "StableRowIndex",
    # visual builder
    "Composition",
    "compose",
    "fields_of",
    "recommend_charts",
    # treatment sandbox
    "preview",
    "preview_candidates",
    "TreatmentPreview",
    # visual workflow
    "Workflow",
    "WorkflowRun",
    "WorkflowError",
    "Stage",
    "Node",
    "default_workflow",
    # domain-aware diagnostics
    "timeseries",
    "TimeSeriesReport",
    "Cadence",
    "panel",
    "PanelReport",
    "Variation",
    "link",
    "mechanism",
    "anomalies",
    "learn_rules",
    "LearnedPlan",
    "LearnedRule",
    "AnomalyReport",
    "Outlier",
    "Mechanism",
    "MechanismReport",
    "ColumnMechanism",
    "LinkageReport",
    "CandidatePair",
    # what this package claims it can do, in one testable place
    "CAPABILITIES",
    "Capability",
    "capability_table",
    # presentation
    "Table",
    "Column",
    "Align",
    "format_number",
    "publish",
    # validation and contracts
    "ValidationPlan",
    "ValidationResult",
    "Outcome",
    "DataContract",
    # privacy
    "PrivacyScanner",
    "PrivacyReport",
    "Sensitivity",
    # drift
    "compare_reference",
    "cleaning_drift",
    "DriftReport",
    "DriftSeverity",
    # issue model
    "Issue",
    "Evidence",
    "TreatmentCandidate",
    "IssueCategory",
    "RepairClass",
    "Severity",
    "RowSet",
    # repair model
    "Operation",
    "RepairPlan",
    "AuditLog",
    "AuditRecord",
    # policy
    "ConfidenceLadder",
    "DataHealthScore",
    # exceptions
    "SmartPrepError",
    "SmartPrepTypeError",
    "SmartPrepSchemaError",
    "SmartPrepValidationError",
    "SmartPrepBackendError",
    "SmartPrepAmbiguityError",
    "SmartPrepUnsafeRepairError",
    "SmartPrepPrivacyError",
    "SmartPrepContractError",
    "__version__",
]
