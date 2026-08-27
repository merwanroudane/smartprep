"""Missingness with semantics attached.

A headline rate is close to useless. 27.5% missing payment dates sounds alarming
until you notice that almost all of it sits on unpaid invoices, where a payment
date *should* be absent. The 7 rows where a paid invoice has no payment date are
the actual finding, and a flat percentage buries them.
"""

from __future__ import annotations

from typing import Any

import numpy as np
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
from .base import is_missing, register

__all__ = ["MissingnessDetector", "ConditionalMissingnessRule"]


class ConditionalMissingnessRule:
    """Declares when absence is expected rather than suspicious.

    ``expected_absent_when`` marks the states in which a missing value is the
    correct encoding of reality -- structural missingness, not a defect.
    """

    def __init__(
        self, column: str, condition_column: str, expected_absent_when: tuple[str, ...]
    ) -> None:
        self.column = column
        self.condition_column = condition_column
        self.expected_absent_when = expected_absent_when


DEFAULT_CONDITIONAL_RULES = (
    ConditionalMissingnessRule("payment_date", "status", ("Pending", "Overdue")),
    ConditionalMissingnessRule("payment_amount", "status", ("Pending", "Overdue")),
)


@register
class MissingnessDetector:
    """Report missingness split by whether it is structurally expected."""

    name = "missingness"

    def detect(
        self,
        frame: pd.DataFrame,
        *,
        conditional_rules: tuple[ConditionalMissingnessRule, ...] = DEFAULT_CONDITIONAL_RULES,
        **context: Any,
    ) -> list[Issue]:
        rules = {r.column: r for r in conditional_rules}
        issues: list[Issue] = []
        total = len(frame)

        for column in frame.columns:
            missing_mask = frame[column].map(is_missing)
            count = int(missing_mask.sum())
            if count == 0:
                continue
            rows = [int(i) for i in np.flatnonzero(missing_mask.to_numpy())]
            rate = count / total

            rule = rules.get(column)
            if rule and rule.condition_column in frame.columns:
                condition = frame[rule.condition_column]
                structural_mask = missing_mask & condition.isin(rule.expected_absent_when)
                suspicious_mask = missing_mask & ~condition.isin(rule.expected_absent_when)
                structural = int(structural_mask.sum())
                suspicious = int(suspicious_mask.sum())

                # Per-state counts, because "9 suspicious" is less useful than
                # "8 Paid and 1 Partial" when the reviewer decides what to do.
                by_state: dict[str, int] = (
                    {str(k): int(v) for k, v in condition[suspicious_mask].value_counts().items()}
                    if suspicious
                    else {}
                )

                if structural:
                    issues.append(self._structural(column, rule, structural, structural_mask, rate))
                if suspicious:
                    issues.append(
                        self._suspicious(column, rule, suspicious, suspicious_mask, by_state)
                    )
                continue

            issues.append(self._plain(column, count, rate, rows))
        return issues

    @staticmethod
    def _plain(column: str, count: int, rate: float, rows: list[int]) -> Issue:
        return Issue(
            id=f"MISS-{column}",
            category=IssueCategory.MISSINGNESS,
            severity=Severity.WARNING if rate > 0.05 else Severity.NOTICE,
            detection_confidence=1.0,
            rule_source=RuleSource.PHYSICAL_TYPE_INFERENCE,
            columns=(column,),
            evidence=Evidence(
                summary=f"{column!r} is missing in {count} rows ({rate:.2%})",
                affected_rows=tuple(rows),
                details={"count": count, "rate": rate},
            ),
            treatments=(
                TreatmentCandidate(
                    name="record_only",
                    description=(
                        "Record the missingness and change nothing. Imputation is a "
                        "modelling decision, not a cleaning one, and adding an "
                        "indicator column silently alters the schema."
                    ),
                    repair_confidence=0.99,
                    reversibility=Reversibility.REVERSIBLE,
                    information_loss_risk=InformationLossRisk.NONE,
                    statistical_impact=StatisticalImpact.NONE,
                ),
            ),
            recommended="record_only",
        )

    @staticmethod
    def _structural(
        column: str,
        rule: ConditionalMissingnessRule,
        count: int,
        mask: pd.Series,
        rate: float,
    ) -> Issue:
        return Issue(
            id=f"MISS-STRUCTURAL-{column}",
            category=IssueCategory.STRUCTURAL_MISSINGNESS,
            # Informational. This is the data being correct, not broken.
            severity=Severity.INFO,
            detection_confidence=0.95,
            rule_source=RuleSource.INFERRED_RELATIONSHIP,
            columns=(column, rule.condition_column),
            evidence=Evidence(
                summary=(
                    f"{count} of the missing {column!r} values occur where "
                    f"{rule.condition_column} is in {rule.expected_absent_when} -- "
                    "absence is the correct encoding here"
                ),
                affected_rows=tuple(int(i) for i in np.flatnonzero(mask.to_numpy())),
                details={
                    "count": count,
                    "column_missing_rate": rate,
                    "expected_absent_when": list(rule.expected_absent_when),
                },
            ),
            treatments=(
                TreatmentCandidate(
                    name="leave_unchanged",
                    description="No action. Imputing here would fabricate events.",
                    repair_confidence=0.99,
                    reversibility=Reversibility.REVERSIBLE,
                    information_loss_risk=InformationLossRisk.NONE,
                ),
            ),
            recommended="leave_unchanged",
            notes=(
                "Excluded from the suspicious-missingness count so the headline rate "
                "does not misrepresent data quality."
            ),
        )

    @staticmethod
    def _suspicious(
        column: str,
        rule: ConditionalMissingnessRule,
        count: int,
        mask: pd.Series,
        by_state: dict[str, int],
    ) -> Issue:
        return Issue(
            id=f"MISS-SUSPICIOUS-{column}",
            category=IssueCategory.SUSPICIOUS_MISSINGNESS,
            severity=Severity.HIGH_WARNING,
            detection_confidence=0.95,
            rule_source=RuleSource.INFERRED_RELATIONSHIP,
            columns=(column, rule.condition_column),
            evidence=Evidence(
                summary=(
                    f"{count} rows are missing {column!r} in a state where it should be "
                    f"present ({rule.condition_column} not in {rule.expected_absent_when})"
                ),
                affected_rows=tuple(int(i) for i in np.flatnonzero(mask.to_numpy())),
                details={"count": count, "by_state": dict(by_state)},
            ),
            treatments=(
                TreatmentCandidate(
                    name="review_contradiction",
                    description=(
                        "Either the state or the missing field is wrong. Which one is "
                        "a business question."
                    ),
                    repair_confidence=0.30,
                    reversibility=Reversibility.REVERSIBLE,
                    domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                ),
            ),
            recommended="review_contradiction",
        )
