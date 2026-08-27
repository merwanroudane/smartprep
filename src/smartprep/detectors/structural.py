"""Structural detectors: representation, duplication, identifier integrity."""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from typing import Any

import pandas as pd

from ..core.enums import (
    DomainSensitivity,
    InformationLossRisk,
    IssueCategory,
    Reversibility,
    RuleSource,
    Severity,
    StatisticalImpact,
)
from ..core.issue import Evidence, Issue, TreatmentCandidate
from .base import physical_type, register, to_number

__all__ = [
    "MixedPhysicalTypeDetector",
    "DuplicateIdentifierDetector",
    "IdentifierMetadataDetector",
]

_NUMERIC_FORMS = {"int", "float", "numeric-string", "formatted-numeric-string"}
_TEMPORAL_FORMS = {"datetime", "date"}

#: Representation families. Variation *within* a family is storage detail;
#: variation *across* families is the mixed-type problem worth reporting.
_FAMILY = {
    "int": "native_number",
    "float": "native_number",
    "bool": "native_bool",
    "datetime": "native_temporal",
    "date": "native_temporal",
    "numeric-string": "text",
    "formatted-numeric-string": "text",
    "string": "text",
}


@register
class MixedPhysicalTypeDetector:
    """Report columns holding more than one storage representation.

    ``dtype == object`` is not a diagnosis. A column can be 98% float and 2%
    thousands-separated text, and only the composition reveals it.
    """

    name = "mixed_physical_type"

    def detect(self, frame: pd.DataFrame, **context: Any) -> list[Issue]:
        issues: list[Issue] = []
        for column in frame.columns:
            forms = Counter(physical_type(v) for v in frame[column])
            present = {f: n for f, n in forms.items() if f != "missing"}
            if len(present) < 2:
                continue
            # A column holding both int and float is not a defect -- that is
            # simply how spreadsheets store numbers. Reporting it would bury the
            # real finding, which is text sitting where a number belongs.
            if len({_FAMILY.get(f, f) for f in present}) < 2:
                continue

            total = sum(present.values())
            composition = {f: n / total for f, n in present.items()}
            numeric_share = sum(n for f, n in present.items() if f in _NUMERIC_FORMS) / total
            temporal_share = sum(n for f, n in present.items() if f in _TEMPORAL_FORMS) / total

            if numeric_share == 1.0:
                target, treatment = "numeric", self._numeric_treatment(frame, column)
            elif temporal_share > 0:
                target, treatment = "datetime", self._temporal_treatment(present, total)
            else:
                target, treatment = "text", self._text_treatment()

            issues.append(
                Issue(
                    id=f"TYPE-{column}",
                    category=IssueCategory.MIXED_PHYSICAL_TYPE,
                    severity=Severity.HIGH_WARNING,
                    detection_confidence=1.0,
                    rule_source=RuleSource.PHYSICAL_TYPE_INFERENCE,
                    columns=(column,),
                    evidence=Evidence(
                        summary=(
                            f"{column!r} stores {len(present)} physical representations; "
                            f"semantic target is {target}"
                        ),
                        affected_rows=tuple(
                            int(i)
                            for i, v in enumerate(frame[column])
                            if physical_type(v) not in ("missing", forms.most_common(1)[0][0])
                        ),
                        sample_values=tuple(
                            v
                            for v in frame[column]
                            if physical_type(v) in present
                            and physical_type(v) != forms.most_common(1)[0][0]
                        )[:5],
                        details={
                            "composition": composition,
                            "counts": dict(present),
                            "semantic_target": target,
                        },
                    ),
                    treatments=(treatment,),
                    recommended=treatment.name,
                )
            )
        return issues

    @staticmethod
    def _numeric_treatment(frame: pd.DataFrame, column: str) -> TreatmentCandidate:
        values = [v for v in frame[column] if physical_type(v) != "missing"]
        parsed = sum(1 for v in values if to_number(v) == to_number(v))
        rate = parsed / len(values) if values else 0.0
        return TreatmentCandidate(
            name="parse_numeric",
            description=(
                "Coerce every representation to a single numeric type, keeping the "
                "original values alongside for reversal."
            ),
            repair_confidence=rate,
            reversibility=Reversibility.REVERSIBLE_WITH_SNAPSHOT,
            information_loss_risk=InformationLossRisk.NONE,
            statistical_impact=StatisticalImpact.NONE,
            parameters={"parse_success_rate": rate},
        )

    @staticmethod
    def _temporal_treatment(present: dict[str, int], total: int) -> TreatmentCandidate:
        # Text inside a datetime column may be invalid or ambiguous; the date
        # detector owns that judgement, so this treatment claims only the share
        # it can convert without interpretation.
        #
        # Confidence is in *the conversion*, not in how much of the column was
        # already clean. Parsing "24/02/2024" is deterministic whether it sits
        # among two other strings or two hundred. Scaling confidence by the text
        # ratio would gate a safe conversion on an unrelated fact and leave the
        # column mixed for no reason.
        textual = sum(n for f, n in present.items() if f not in _TEMPORAL_FORMS)
        return TreatmentCandidate(
            name="parse_datetime_unambiguous",
            description=(
                "Convert unambiguous string dates to datetime; leave invalid and "
                "ambiguous values for the date detector to escalate."
            ),
            repair_confidence=0.99,
            reversibility=Reversibility.REVERSIBLE_WITH_SNAPSHOT,
            information_loss_risk=InformationLossRisk.LOW,
            parameters={"textual_values": textual, "converts": "unambiguous values only"},
        )

    @staticmethod
    def _text_treatment() -> TreatmentCandidate:
        return TreatmentCandidate(
            name="normalise_text_representation",
            description="Normalise to a single textual representation.",
            repair_confidence=0.70,
            reversibility=Reversibility.REVERSIBLE_WITH_SNAPSHOT,
        )


@register
class DuplicateIdentifierDetector:
    """Separate identical duplicates from conflicting ones.

    ``drop_duplicates()`` cannot tell the difference, and the difference decides
    whether deletion is safe or destructive. Identical payloads are redundant;
    conflicting payloads mean two sources disagree about one entity, and picking
    a survivor without a precedence rule destroys information.
    """

    name = "duplicate_identifier"

    def applicability(self, frame: pd.DataFrame, context: dict[str, Any]) -> tuple[Any, str]:
        from ..scan import Applicability

        key = context.get("key") or context.get("identifier")
        if key is None:
            return (
                Applicability.SKIPPED_MISSING_CONTEXT,
                "no business key given; pass identifier=... to check duplicate keys",
            )
        if key not in frame.columns:
            return (
                Applicability.NOT_APPLICABLE,
                f"identifier column {key!r} is not present",
            )
        return Applicability.APPLICABLE, ""

    def detect(self, frame: pd.DataFrame, *, key: str | None = None, **context: Any) -> list[Issue]:
        key = key or context.get("identifier")
        if key is None or key not in frame.columns:
            return []

        duplicated = frame[frame.duplicated(key, keep=False)]
        if duplicated.empty:
            return []

        exact_ids: list[Any] = []
        conflicting_ids: list[Any] = []
        for value, group in duplicated.groupby(key, sort=False):
            if group.astype(str).drop_duplicates().shape[0] == 1:
                exact_ids.append(value)
            else:
                conflicting_ids.append(value)

        issues: list[Issue] = []

        if exact_ids:
            rows = frame.index[frame[key].isin(exact_ids)].tolist()
            treatment = TreatmentCandidate(
                name="keep_first",
                description="Retain one row per identifier; the others are byte-identical.",
                repair_confidence=0.99,
                # Deleting rows can never be undone from the surviving data alone.
                reversibility=Reversibility.IRREVERSIBLE,
                information_loss_risk=InformationLossRisk.LOW,
                statistical_impact=StatisticalImpact.NEGLIGIBLE,
            )
            issues.append(
                Issue(
                    id=f"DUP-EXACT-{key}",
                    category=IssueCategory.EXACT_DUPLICATE,
                    severity=Severity.WARNING,
                    detection_confidence=1.0,
                    rule_source=RuleSource.STATISTICAL_RULE,
                    columns=(key,),
                    evidence=Evidence(
                        summary=(
                            f"{len(exact_ids)} identifiers repeat with an identical "
                            "payload across every column"
                        ),
                        affected_rows=tuple(int(r) for r in rows),
                        sample_values=tuple(exact_ids[:5]),
                        details={"identifier_count": len(exact_ids), "row_count": len(rows)},
                    ),
                    treatments=(treatment,),
                    recommended=treatment.name,
                )
            )

        if conflicting_ids:
            rows = frame.index[frame[key].isin(conflicting_ids)].tolist()
            issues.append(
                Issue(
                    id=f"DUP-CONFLICT-{key}",
                    category=IssueCategory.CONFLICTING_DUPLICATE,
                    # BLOCKING forces DO_NOT_TOUCH in triage -- automatic
                    # deletion here would destroy valid information.
                    severity=Severity.BLOCKING,
                    detection_confidence=1.0,
                    rule_source=RuleSource.STATISTICAL_RULE,
                    columns=(key,),
                    evidence=Evidence(
                        summary=(
                            f"{len(conflicting_ids)} identifiers appear on rows whose "
                            "other columns disagree"
                        ),
                        affected_rows=tuple(int(r) for r in rows),
                        sample_values=tuple(conflicting_ids[:5]),
                        details={
                            "identifier_count": len(conflicting_ids),
                            "row_count": len(rows),
                        },
                    ),
                    treatments=(
                        TreatmentCandidate(
                            name="define_precedence_rule",
                            description=(
                                "Choose a survivor per identifier using a user-supplied "
                                "precedence rule, then record field-level provenance."
                            ),
                            repair_confidence=0.10,
                            reversibility=Reversibility.IRREVERSIBLE,
                            information_loss_risk=InformationLossRisk.HIGH,
                            domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                        ),
                    ),
                    recommended="define_precedence_rule",
                    notes=(
                        "Automatic resolution is disabled. Which record is correct is "
                        "not recoverable from the data."
                    ),
                )
            )

        return issues


@register
class IdentifierMetadataDetector:
    """Validate metadata embedded inside an identifier against its own row.

    ``INV-2025-00109`` asserts a year. When the row's date disagrees, one of the
    two is wrong -- and the data alone cannot say which.
    """

    name = "identifier_embedded_metadata"

    def applicability(self, frame: pd.DataFrame, context: dict[str, Any]) -> tuple[Any, str]:
        from ..scan import Applicability

        identifier, compare_to = context.get("identifier"), context.get("compare_to")
        if identifier is None or compare_to is None:
            return (
                Applicability.SKIPPED_MISSING_CONTEXT,
                "needs identifier=... and compare_to=... to validate embedded metadata",
            )
        if identifier not in frame.columns or compare_to not in frame.columns:
            return Applicability.NOT_APPLICABLE, "named columns are not present"
        return Applicability.APPLICABLE, ""

    def detect(
        self,
        frame: pd.DataFrame,
        *,
        identifier: str | None = None,
        pattern: str = r"^[A-Z]+-(?P<year>\d{4})-\d+$",
        compare_to: str | None = None,
        **context: Any,
    ) -> list[Issue]:
        if identifier is None or compare_to is None:
            return []
        if identifier not in frame.columns or compare_to not in frame.columns:
            return []

        rx = re.compile(pattern)
        mismatches: list[int] = []
        samples: list[str] = []
        paired = zip(frame[identifier], frame[compare_to], strict=True)
        for idx, (ident, other) in enumerate(paired):
            match = rx.match(str(ident))
            if not match:
                continue
            # Compare only against values that are already real datetimes.
            # Coercing here would crash on the very invalid dates this dataset
            # contains, and a repaired date is not this detector's evidence.
            if not isinstance(other, (dt.datetime, dt.date, pd.Timestamp)):
                continue
            stamp = pd.Timestamp(other)
            if int(match.group("year")) != stamp.year:
                mismatches.append(idx)
                if len(samples) < 5:
                    samples.append(f"{ident} vs {stamp.date()}")

        if not mismatches:
            return []

        return [
            Issue(
                id=f"ID-META-{identifier}",
                category=IssueCategory.IDENTIFIER_METADATA_MISMATCH,
                severity=Severity.HIGH_WARNING,
                detection_confidence=0.99,
                rule_source=RuleSource.INFERRED_RELATIONSHIP,
                columns=(identifier, compare_to),
                evidence=Evidence(
                    summary=(
                        f"{len(mismatches)} rows where the year embedded in "
                        f"{identifier!r} differs from {compare_to!r}"
                    ),
                    affected_rows=tuple(mismatches),
                    sample_values=tuple(samples),
                    details={"pattern": pattern},
                ),
                treatments=(
                    TreatmentCandidate(
                        name="flag_for_review",
                        description=(
                            "Record the contradiction. Whether the identifier or the "
                            "date is authoritative is a business decision."
                        ),
                        repair_confidence=0.35,
                        reversibility=Reversibility.REVERSIBLE,
                        domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                    ),
                ),
                recommended="flag_for_review",
            )
        ]
