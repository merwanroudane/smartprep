"""Enumerations that encode the frozen safety policy.

Every value here traces to a decision in ``_ARCHITECTURE_DECISIONS.md``.
Changing an ordering is a breaking change.
"""

from __future__ import annotations

from enum import Enum, IntEnum

__all__ = [
    "Severity",
    "RepairClass",
    "Reversibility",
    "InformationLossRisk",
    "StatisticalImpact",
    "DomainSensitivity",
    "RuleSource",
    "IssueCategory",
    "CompletionState",
    "MatchKind",
]


class Severity(IntEnum):
    """Escalation weight of a finding. Ordered: higher is more urgent."""

    INFO = 0
    NOTICE = 1
    WARNING = 2
    HIGH_WARNING = 3
    CRITICAL_REVIEW = 4
    BLOCKING = 5


class RepairClass(IntEnum):
    """Triage outcome for a finding (AD-007).

    Ordered from most to least autonomy so that demotion is simply ``min()``.
    ``DO_NOT_TOUCH`` is the floor: nothing can demote below it.
    """

    SAFE_AUTO_FIX = 6
    AUTO_FIX_WITH_LOG = 5
    REVIEW_RECOMMENDED = 4
    USER_CONFIRMATION_REQUIRED = 3
    DOMAIN_RULE_REQUIRED = 2
    AMBIGUOUS = 1
    DO_NOT_TOUCH = 0

    @property
    def is_autonomous(self) -> bool:
        """True when auto mode is permitted to apply this without asking."""
        return self >= RepairClass.AUTO_FIX_WITH_LOG


class Reversibility(Enum):
    """Can the repair be undone from the stored evidence alone?"""

    REVERSIBLE = "reversible"
    REVERSIBLE_WITH_SNAPSHOT = "reversible_with_snapshot"
    IRREVERSIBLE = "irreversible"


class InformationLossRisk(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StatisticalImpact(Enum):
    """Expected effect on distributions, relationships or inference."""

    NONE = "none"
    NEGLIGIBLE = "negligible"
    MODERATE = "moderate"
    MATERIAL = "material"


class DomainSensitivity(Enum):
    """Does resolving this require knowledge the data cannot supply?"""

    NONE = "none"
    CONTEXTUAL = "contextual"
    REQUIRES_DOMAIN_RULE = "requires_domain_rule"


class RuleSource(Enum):
    """Provenance of the rule that produced a finding.

    A schema-derived rule and a model suggestion must never carry equal weight
    (plan, "Rule Source Provenance").
    """

    PHYSICAL_TYPE_INFERENCE = "physical_type_inference"
    STATISTICAL_RULE = "statistical_rule"
    DATA_DICTIONARY = "data_dictionary"
    INFERRED_RELATIONSHIP = "inferred_relationship"
    DOMAIN_PACK = "domain_pack"
    USER_DEFINED = "user_defined"
    EXTERNAL_REFERENCE = "external_reference"
    LLM_SUGGESTION = "llm_suggestion"


class IssueCategory(Enum):
    """What kind of defect a finding is.

    The category decides which pipeline stage owns the repair (AD-018) and
    which treatments are even considered, so every detector must map onto one
    -- a finding in no category is a finding no stage would run.
    """

    MIXED_PHYSICAL_TYPE = "mixed_physical_type"
    MISSINGNESS = "missingness"
    SUSPICIOUS_MISSINGNESS = "suspicious_missingness"
    STRUCTURAL_MISSINGNESS = "structural_missingness"
    INVALID_DATE = "invalid_date"
    AMBIGUOUS_DATE = "ambiguous_date"
    EXACT_DUPLICATE = "exact_duplicate"
    CONFLICTING_DUPLICATE = "conflicting_duplicate"
    IDENTIFIER_METADATA_MISMATCH = "identifier_metadata_mismatch"
    CATEGORY_VARIANT = "category_variant"
    UNICODE_CONFUSABLE = "unicode_confusable"
    RANGE_VIOLATION = "range_violation"
    SENTINEL_CANDIDATE = "sentinel_candidate"
    FORMULA_VIOLATION = "formula_violation"
    STATE_CONTRADICTION = "state_contradiction"
    GEOGRAPHIC_CONFLICT = "geographic_conflict"
    CURRENCY_CONTEXT = "currency_context"
    ACCOUNTING_IMPLAUSIBILITY = "accounting_implausibility"
    UNKNOWN_ENTITY = "unknown_entity"
    UNUSUAL_PATTERN = "unusual_pattern"


class CompletionState(Enum):
    """Terminal state of an auto-prepare run (AD-004)."""

    CLEAN = "CLEAN"
    CLEAN_WITH_NOTES = "CLEAN_WITH_NOTES"
    CLEAN_WITH_WARNINGS = "CLEAN_WITH_WARNINGS"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    GUIDED_REVIEW_RECOMMENDED = "GUIDED_REVIEW_RECOMMENDED"
    GUIDED_REVIEW_REQUIRED = "GUIDED_REVIEW_REQUIRED"
    DOMAIN_REVIEW_REQUIRED = "DOMAIN_REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"


class MatchKind(Enum):
    """How an entity reference resolved against a reference pack (AD-008)."""

    EXACT = "exact"
    ALIAS = "alias"
    TRANSLITERATION = "transliteration"
    LANGUAGE_VARIANT = "language_variant"
    HISTORICAL = "historical"
    FUZZY = "fuzzy"
    UNRESOLVED = "unresolved"
