"""Negative acceptance tests -- what SmartPrep must NOT flag (AD-009).

These matter more than the detection tests. A cleaning tool that over-reports
trains users to ignore it, and an over-eager auto-fix corrupts data silently.
A build that finds every real issue but flags `Algérie` as damage has failed.
"""

from __future__ import annotations

import pandas as pd
import pytest

import smartprep as sp
from conftest import issue
from smartprep.core import IssueCategory, RepairClass, Severity
from smartprep.detectors.textual import UnicodeConfusableDetector

# --------------------------------------------------------------------------
# Legitimate non-ASCII text
# --------------------------------------------------------------------------


@pytest.mark.stress
def test_french_accent_is_not_unicode_corruption(result: sp.ScanResult) -> None:
    """`Algérie` is correct French. The é must never be reported as damage."""
    country_issues = [
        i
        for i in result.issues
        if i.category is IssueCategory.UNICODE_CONFUSABLE and "country" in i.columns
    ]
    assert not country_issues, (
        "flagged legitimate French spelling as Unicode corruption: "
        f"{country_issues[0].evidence.sample_values if country_issues else ''}"
    )


@pytest.mark.parametrize(
    "value",
    [
        "Algérie",
        "Fès",
        "François",
        "Köln",
        "São Paulo",
        "Beijing",
        "北京",
        "القاهرة",
    ],
)
def test_legitimate_scripts_are_not_flagged(value: str) -> None:
    frame = pd.DataFrame({"name": [value] * 3})
    assert not UnicodeConfusableDetector().detect(frame), f"false positive on {value!r}"


def test_genuine_confusable_is_still_caught() -> None:
    """The negative tests must not have disarmed the detector."""
    frame = pd.DataFrame({"sector": ["Manufacturıng"] * 3})
    assert UnicodeConfusableDetector().detect(frame)


# --------------------------------------------------------------------------
# Legitimate business states
# --------------------------------------------------------------------------


@pytest.mark.stress
def test_overdue_with_payment_date_is_not_a_contradiction(
    raw: pd.DataFrame, result: sp.ScanResult
) -> None:
    """97 rows are Overdue and carry a payment date. That is a late payment."""
    late = int(((raw["status"] == "Overdue") & raw["payment_date"].notna()).sum())
    assert late == 97

    flagged = [
        i
        for i in result.issues
        if i.category is IssueCategory.STATE_CONTRADICTION and "overdue" in i.id.lower()
    ]
    assert not flagged, "late payment reported as a state contradiction"


@pytest.mark.stress
def test_pending_without_payment_date_is_structural(result: sp.ScanResult) -> None:
    """Absence is the correct encoding for an unpaid invoice, not a defect."""
    structural = issue(result, "MISS-STRUCTURAL-payment_date")
    assert structural.category is IssueCategory.STRUCTURAL_MISSINGNESS
    assert structural.severity is Severity.INFO
    assert structural.repair_class.is_autonomous  # "leave unchanged" is safe


@pytest.mark.stress
def test_currency_mismatch_is_contextual_not_an_error(result: sp.ScanResult) -> None:
    """Foreign-currency invoicing is ordinary commerce."""
    found = issue(result, "CURRENCY-context")
    assert found.severity is Severity.NOTICE
    assert found.severity < Severity.HIGH_WARNING
    assert found.category is IssueCategory.CURRENCY_CONTEXT


@pytest.mark.stress
def test_large_real_revenue_is_not_a_sentinel(result: sp.ScanResult) -> None:
    """Only employee_count carries a placeholder. Big revenues are just big."""
    sentinels = [i for i in result.issues if i.category is IssueCategory.SENTINEL_CANDIDATE]
    assert {i.columns[0] for i in sentinels} == {"employee_count"}


# --------------------------------------------------------------------------
# Safety policy must hold on real findings
# --------------------------------------------------------------------------


@pytest.mark.stress
def test_conflicting_duplicates_are_never_auto_repaired(result: sp.ScanResult) -> None:
    found = issue(result, "DUP-CONFLICT-invoice_id")
    assert found.repair_class is RepairClass.DO_NOT_TOUCH
    assert not found.repair_class.is_autonomous


@pytest.mark.stress
def test_invalid_dates_offer_no_invented_correction(result: sp.ScanResult) -> None:
    found = issue(result, "DATE-INVALID-invoice_date")
    assert found.treatments == ()
    assert found.repair_class is RepairClass.AMBIGUOUS


@pytest.mark.stress
def test_ambiguous_dates_are_not_auto_resolved(result: sp.ScanResult) -> None:
    """A column's habit is evidence, not proof. Guessing moves dates by months."""
    assert not issue(result, "DATE-AMBIGUOUS-invoice_date").repair_class.is_autonomous


@pytest.mark.stress
def test_formula_is_proposed_never_enforced(result: sp.ScanResult) -> None:
    found = issue(result, "INVARIANT-invoice_amount")
    assert found.repair_class is RepairClass.DOMAIN_RULE_REQUIRED
    assert "not recomputed" in found.notes


@pytest.mark.stress
def test_semantic_category_merge_requires_confirmation(result: sp.ScanResult) -> None:
    merge = next(
        t for t in issue(result, "CAT-sector").treatments if t.name == "merge_semantic_variants"
    )
    from smartprep.core import classify
    from smartprep.core.eligibility import RiskProfile

    outcome, reasons = classify(
        merge.repair_confidence,
        RiskProfile(
            reversibility=merge.reversibility,
            information_loss_risk=merge.information_loss_risk,
            domain_sensitivity=merge.domain_sensitivity,
        ),
    )
    assert not outcome.is_autonomous
    assert any("irreversible" in r for r in reasons)


@pytest.mark.stress
def test_scan_reports_coverage_not_correctness(result: sp.ScanResult) -> None:
    """Full coverage with open issues is a valid, expected state."""
    assert result.coverage == 1.0
    assert result.issues, "coverage of 100% must not imply a clean dataset"
    assert "not data correctness" in result.summary()


@pytest.mark.stress
def test_int_float_mix_is_not_a_type_defect(result: sp.ScanResult) -> None:
    """Spreadsheets store 3 as int and 3.5 as float in the same column.

    Reporting that as a mixed-type issue buries the real finding -- text where
    a number belongs -- under noise on every numeric column.
    """
    reported = {i.columns[0] for i in result.issues if i.id.startswith("TYPE-")}
    numeric_only = {
        "discount_pct",
        "invoice_amount",
        "payment_amount",
        "customer_rating",
        "reported_profit",
        "quantity",
    }
    assert not (reported & numeric_only), (
        f"int/float storage reported as a defect on: {sorted(reported & numeric_only)}"
    )
    # The columns that genuinely mix text with numbers are still reported.
    assert {"unit_price", "annual_revenue", "invoice_date"} <= reported
