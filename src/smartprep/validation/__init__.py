"""Validation and data contracts.

Rules are inferred from reviewed data and proposed for confirmation, so
exploratory work becomes a production gate without anyone retyping it.
"""

from .contract import ChangeKind, ColumnContract, DataContract, SchemaChange
from .plan import Outcome, Rule, RuleResult, ValidationPlan, ValidationResult

__all__ = [
    "ValidationPlan",
    "ValidationResult",
    "Rule",
    "RuleResult",
    "Outcome",
    "DataContract",
    "ColumnContract",
    "SchemaChange",
    "ChangeKind",
]
