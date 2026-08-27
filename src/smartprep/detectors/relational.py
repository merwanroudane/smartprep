"""Cross-field detectors: invariants, workflow state, geography, currency.

Every detector here answers to one rule: a relationship that *usually* holds is
a hypothesis, not a law. It is proposed with its fit rate and left for
confirmation. The library never assumes it discovered the business.
"""

from __future__ import annotations

from collections.abc import Callable
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
from ..reference.entities import EXPECTED_CURRENCY, WORLD, EntityPack
from .base import numeric_series, register

__all__ = [
    "FormulaInvariantDetector",
    "StateConsistencyDetector",
    "GeographicConsistencyDetector",
    "CurrencyContextDetector",
    "AccountingPlausibilityDetector",
]


@register
class FormulaInvariantDetector:
    """Propose arithmetic relationships and report where they break.

    The plan is emphatic that the formula must not be assumed correct. A 91.7%
    fit is evidence of a rule *and* evidence that the rule is not the whole
    story -- surcharges, rounding policies and manual overrides all look like
    violations to arithmetic.
    """

    name = "formula_invariant"

    #: ``(name, expression, required columns, target)``
    CANDIDATES: tuple[tuple[str, Callable[..., pd.Series], tuple[str, ...], str], ...] = (
        (
            "invoice_amount = quantity * unit_price * (1 - discount_pct) * (1 + tax_pct)",
            lambda q, up, dp, tp: q * up * (1 - dp) * (1 + tp),
            ("quantity", "unit_price", "discount_pct", "tax_pct"),
            "invoice_amount",
        ),
    )

    def __init__(self, tolerance: float = 0.01, min_fit: float = 0.60) -> None:
        self.tolerance = tolerance
        self.min_fit = min_fit

    def detect(self, frame: pd.DataFrame, **context: Any) -> list[Issue]:
        issues: list[Issue] = []
        for label, expr, inputs, target in self.CANDIDATES:
            if not set(inputs + (target,)).issubset(frame.columns):
                continue
            args = [numeric_series(frame, c) for c in inputs]
            actual = numeric_series(frame, target)
            expected = expr(*args)

            evaluable = expected.notna() & actual.notna()
            if not evaluable.any():
                continue
            agree = np.isclose(expected, actual, atol=self.tolerance, rtol=0) & evaluable
            fit = agree.sum() / evaluable.sum()
            if fit < self.min_fit:
                continue  # not a credible rule for this dataset

            violations = evaluable & ~agree
            if not violations.any():
                continue
            rows = [int(i) for i in np.flatnonzero(violations.to_numpy())]
            residual = (actual - expected)[violations]

            issues.append(
                Issue(
                    id=f"INVARIANT-{target}",
                    category=IssueCategory.FORMULA_VIOLATION,
                    severity=Severity.HIGH_WARNING,
                    # High confidence the rows *deviate*; that is arithmetic.
                    # Zero claim that the formula is the intended one.
                    detection_confidence=0.99,
                    rule_source=RuleSource.INFERRED_RELATIONSHIP,
                    columns=inputs + (target,),
                    evidence=Evidence(
                        summary=(
                            f"candidate relation holds for {fit:.1%} of evaluable rows; "
                            f"{int(violations.sum())} rows deviate"
                        ),
                        affected_rows=tuple(rows),
                        sample_values=tuple(round(float(v), 2) for v in residual.head(5)),
                        details={
                            "relation": label,
                            "fit": float(fit),
                            "violations": int(violations.sum()),
                            "tolerance": self.tolerance,
                            "median_absolute_residual": float(residual.abs().median()),
                        },
                    ),
                    treatments=(
                        TreatmentCandidate(
                            name="confirm_relation_as_rule",
                            description=(
                                "Adopt the relation as a validation rule and route the "
                                "deviating rows to review. Requires confirmation that "
                                "this is the intended business formula."
                            ),
                            repair_confidence=0.45,
                            reversibility=Reversibility.REVERSIBLE,
                            domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                        ),
                    ),
                    recommended="confirm_relation_as_rule",
                    notes=(
                        "Values are not recomputed from the formula. A high fit rate is "
                        "not authority to overwrite the recorded amount."
                    ),
                )
            )
        return issues


@register
class StateConsistencyDetector:
    """Check workflow states against the fields that should corroborate them.

    Which combinations are contradictory depends on what each state *means*, so
    the legitimate ones are declared explicitly. ``Overdue`` with a payment date
    is the important case: it looks like a contradiction and is simply a late
    payment.
    """

    name = "state_consistency"

    def detect(
        self,
        frame: pd.DataFrame,
        *,
        status: str = "status",
        paid_state: str = "Paid",
        pending_state: str = "Pending",
        partial_state: str = "Partial",
        payment_date: str = "payment_date",
        payment_amount: str = "payment_amount",
        invoice_amount: str = "invoice_amount",
        **context: Any,
    ) -> list[Issue]:
        if status not in frame.columns:
            return []

        state = frame[status]
        pay_amount = numeric_series(frame, payment_amount) if payment_amount in frame else None
        inv_amount = numeric_series(frame, invoice_amount) if invoice_amount in frame else None
        has_date = frame[payment_date].notna() if payment_date in frame else None

        rules: list[tuple[str, pd.Series, str, Severity]] = []
        if has_date is not None:
            rules.append(
                (
                    "paid_without_payment_date",
                    (state == paid_state) & ~has_date,
                    f"marked {paid_state} but no {payment_date}",
                    Severity.HIGH_WARNING,
                )
            )
            rules.append(
                (
                    "partial_without_payment_date",
                    (state == partial_state) & ~has_date,
                    f"marked {partial_state} but no {payment_date}",
                    Severity.WARNING,
                )
            )
        if pay_amount is not None:
            rules.append(
                (
                    "paid_without_payment_amount",
                    (state == paid_state) & pay_amount.isna(),
                    f"marked {paid_state} but no {payment_amount}",
                    Severity.HIGH_WARNING,
                )
            )
            rules.append(
                (
                    "pending_with_payment",
                    (state == pending_state) & (pay_amount > 0),
                    f"marked {pending_state} yet money was received",
                    Severity.HIGH_WARNING,
                )
            )
        if pay_amount is not None and inv_amount is not None:
            rules.append(
                (
                    "paid_amount_mismatch",
                    (state == paid_state)
                    & pay_amount.notna()
                    & inv_amount.notna()
                    & ~np.isclose(pay_amount, inv_amount, atol=0.01, rtol=0),
                    f"marked {paid_state} but {payment_amount} != {invoice_amount}",
                    Severity.WARNING,
                )
            )

        issues: list[Issue] = []
        for rule_name, mask, description, severity in rules:
            mask = mask.fillna(False)
            if not mask.any():
                continue
            rows = [int(i) for i in np.flatnonzero(mask.to_numpy())]
            issues.append(
                Issue(
                    id=f"STATE-{rule_name}",
                    category=IssueCategory.STATE_CONTRADICTION,
                    severity=severity,
                    detection_confidence=0.95,
                    rule_source=RuleSource.INFERRED_RELATIONSHIP,
                    columns=(status,),
                    evidence=Evidence(
                        summary=f"{int(mask.sum())} rows {description}",
                        affected_rows=tuple(rows),
                        details={"rule": rule_name},
                    ),
                    treatments=(
                        TreatmentCandidate(
                            name="review_state_transition",
                            description=(
                                "Surface the contradiction. Which field is authoritative "
                                "depends on the state machine the business uses."
                            ),
                            repair_confidence=0.30,
                            reversibility=Reversibility.REVERSIBLE,
                            domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                        ),
                    ),
                    recommended="review_state_transition",
                )
            )
        return issues


@register
class GeographicConsistencyDetector:
    """Compare a row's city against its country via the entity graph."""

    name = "geographic_consistency"

    def detect(
        self,
        frame: pd.DataFrame,
        *,
        country: str = "country",
        city: str = "city",
        pack: EntityPack = WORLD,
        **context: Any,
    ) -> list[Issue]:
        if country not in frame.columns or city not in frame.columns:
            return []

        conflicts: list[int] = []
        unknown_cities: dict[str, int] = {}
        samples: list[str] = []

        pairs_iter = zip(frame[country], frame[city], strict=True)
        for idx, (country_value, city_value) in enumerate(pairs_iter):
            city_hit = pack.resolve(city_value, "city")
            if city_hit.entity is None:
                if isinstance(city_value, str) and city_value.strip():
                    unknown_cities[city_value] = unknown_cities.get(city_value, 0) + 1
                continue
            country_hit = pack.resolve(country_value, "country")
            if country_hit.entity is None:
                continue
            if city_hit.entity.parent != country_hit.entity.id:
                conflicts.append(idx)
                if len(samples) < 5:
                    samples.append(f"{country_value} + {city_value}")

        issues: list[Issue] = []
        if conflicts:
            issues.append(
                Issue(
                    id="GEO-country-city",
                    category=IssueCategory.GEOGRAPHIC_CONFLICT,
                    severity=Severity.HIGH_WARNING,
                    detection_confidence=0.98,
                    rule_source=RuleSource.DOMAIN_PACK,
                    columns=(country, city),
                    evidence=Evidence(
                        summary=(
                            f"{len(conflicts)} rows pair a city with a country it does "
                            "not belong to"
                        ),
                        affected_rows=tuple(conflicts),
                        sample_values=tuple(samples),
                        details={"pack": f"{pack.name}@{pack.version}"},
                    ),
                    treatments=(
                        TreatmentCandidate(
                            name="review_geographic_pair",
                            description=(
                                "Flag for review. Either field could be the wrong one, "
                                "and the data does not say which."
                            ),
                            repair_confidence=0.40,
                            reversibility=Reversibility.REVERSIBLE,
                            domain_sensitivity=DomainSensitivity.CONTEXTUAL,
                        ),
                    ),
                    recommended="review_geographic_pair",
                )
            )

        if unknown_cities:
            issues.append(
                Issue(
                    id="GEO-unknown-city",
                    category=IssueCategory.UNKNOWN_ENTITY,
                    # Informational: a gap in our reference data is our problem,
                    # not necessarily the data's.
                    severity=Severity.NOTICE,
                    detection_confidence=1.0,
                    rule_source=RuleSource.DOMAIN_PACK,
                    columns=(city,),
                    evidence=Evidence(
                        summary=(
                            f"{len(unknown_cities)} city values are absent from the "
                            "reference pack and could not be checked"
                        ),
                        sample_values=tuple(sorted(unknown_cities)[:10]),
                        details={"counts": unknown_cities},
                    ),
                    treatments=(
                        TreatmentCandidate(
                            name="extend_reference_pack",
                            description="Add the unrecognised entities to a geography pack.",
                            repair_confidence=0.50,
                            reversibility=Reversibility.REVERSIBLE,
                        ),
                    ),
                    recommended="extend_reference_pack",
                    notes="Unresolved entities are reported, never assumed consistent.",
                )
            )
        return issues


@register
class CurrencyContextDetector:
    """Report currency that differs from the country's domestic one.

    This is deliberately not an error. Invoicing a Algerian customer in euro is
    ordinary commerce. Classifying it as a defect would produce 22 false
    positives on the fixture alone.
    """

    name = "currency_context"

    def detect(
        self,
        frame: pd.DataFrame,
        *,
        country: str = "country",
        currency: str = "currency",
        pack: EntityPack = WORLD,
        expected: dict[str, str] = EXPECTED_CURRENCY,
        **context: Any,
    ) -> list[Issue]:
        if country not in frame.columns or currency not in frame.columns:
            return []

        rows: list[int] = []
        pairs: dict[str, int] = {}
        pairs_iter = zip(frame[country], frame[currency], strict=True)
        for idx, (country_value, currency_value) in enumerate(pairs_iter):
            hit = pack.resolve(country_value, "country")
            if hit.entity is None or not isinstance(currency_value, str):
                continue
            domestic = expected.get(hit.entity.id)
            if domestic and currency_value.strip() != domestic:
                rows.append(idx)
                key = f"{hit.entity.canonical_name} + {currency_value.strip()}"
                pairs[key] = pairs.get(key, 0) + 1

        if not rows:
            return []

        return [
            Issue(
                id="CURRENCY-context",
                category=IssueCategory.CURRENCY_CONTEXT,
                # NOTICE, not an error: this is a question, not a defect.
                severity=Severity.NOTICE,
                detection_confidence=0.90,
                rule_source=RuleSource.DOMAIN_PACK,
                columns=(country, currency),
                evidence=Evidence(
                    summary=(
                        f"{len(rows)} rows are denominated in a currency other than the "
                        "country's domestic one -- legitimate for foreign-currency trade"
                    ),
                    affected_rows=tuple(rows),
                    sample_values=tuple(sorted(pairs)),
                    details={"pairs": pairs},
                ),
                treatments=(
                    TreatmentCandidate(
                        name="define_currency_policy",
                        description=(
                            "Declare whether foreign-currency invoicing is permitted, "
                            "then re-evaluate. No change is made meanwhile."
                        ),
                        repair_confidence=0.50,
                        reversibility=Reversibility.REVERSIBLE,
                        domain_sensitivity=DomainSensitivity.CONTEXTUAL,
                    ),
                ),
                recommended="define_currency_policy",
                notes="Contextual observation. Never treated as a hard error.",
            )
        ]


@register
class AccountingPlausibilityDetector:
    """Soft accounting checks that depend on how the terms are defined."""

    name = "accounting_plausibility"

    def detect(
        self,
        frame: pd.DataFrame,
        *,
        revenue: str = "annual_revenue",
        profit: str = "reported_profit",
        **context: Any,
    ) -> list[Issue]:
        if revenue not in frame.columns or profit not in frame.columns:
            return []

        rev = numeric_series(frame, revenue)
        prof = numeric_series(frame, profit)
        mask = (prof > rev) & rev.notna() & prof.notna()
        if not mask.any():
            return []

        rows = [int(i) for i in np.flatnonzero(mask.to_numpy())]
        return [
            Issue(
                id="ACCOUNTING-profit-exceeds-revenue",
                category=IssueCategory.ACCOUNTING_IMPLAUSIBILITY,
                severity=Severity.WARNING,
                detection_confidence=0.85,
                rule_source=RuleSource.INFERRED_RELATIONSHIP,
                columns=(revenue, profit),
                evidence=Evidence(
                    summary=f"{int(mask.sum())} rows report profit exceeding revenue",
                    affected_rows=tuple(rows),
                    details={
                        "alternative_explanations": [
                            "different reporting periods",
                            "different currency or unit between the two fields",
                            "profit includes non-operating income",
                            "data-entry error",
                        ]
                    },
                ),
                treatments=(
                    TreatmentCandidate(
                        name="review_accounting_definition",
                        description=(
                            "Confirm how each field is defined before treating this as an error."
                        ),
                        repair_confidence=0.35,
                        reversibility=Reversibility.REVERSIBLE,
                        domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                        statistical_impact=StatisticalImpact.NONE,
                        information_loss_risk=InformationLossRisk.NONE,
                    ),
                ),
                recommended="review_accounting_definition",
            )
        ]
