"""Positive acceptance tests -- every count is frozen ground truth.

Sources: plan sections 110-134, verified against the workbook and recorded in
``_STRESS_TEST_BASELINE.md``.
"""

from __future__ import annotations

import pandas as pd
import pytest

import smartprep as sp
from conftest import issue
from smartprep.core import IssueCategory

#: Every test here needs the real 1,210-row workbook, which is not distributed.
#: They skip cleanly without it; the contract that ships with the package lives
#: in test_synthetic_acceptance.py.
pytestmark = pytest.mark.stress

# --------------------------------------------------------------------------
# Fingerprint
# --------------------------------------------------------------------------


def test_fixture_fingerprint(raw: pd.DataFrame) -> None:
    assert raw.shape == (1210, 21)


def test_scan_does_not_mutate(raw: pd.DataFrame) -> None:
    before = raw.copy(deep=True)
    sp.scan(raw)
    pd.testing.assert_frame_equal(raw, before)


# --------------------------------------------------------------------------
# Missingness
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "column, expected",
    [("payment_date", 333), ("city", 26), ("payment_amount", 16), ("reported_profit", 18)],
)
def test_missingness_counts(raw: pd.DataFrame, column: str, expected: int) -> None:
    assert int(raw[column].isna().sum()) == expected


def test_payment_date_missingness_is_split_by_state(result: sp.ScanResult) -> None:
    """The headline 27.52% must decompose into structural and suspicious.

    Pending (229) and Overdue (96) are unpaid, so an absent payment date is
    correct. Paid (7) and Partial (1) are the real findings.
    """
    structural = issue(result, "MISS-STRUCTURAL-payment_date")
    suspicious = issue(result, "MISS-SUSPICIOUS-payment_date")

    assert structural.evidence.details["count"] == 325
    assert suspicious.evidence.details["count"] == 8
    assert suspicious.evidence.details["by_state"] == {"Paid": 7, "Partial": 1}
    assert structural.evidence.details["count"] + suspicious.evidence.details["count"] == 333


def test_suspicious_payment_amount_missingness(result: sp.ScanResult) -> None:
    """8 Paid plus 1 Partial. Overdue without an amount is expected, not a defect."""
    found = issue(result, "MISS-SUSPICIOUS-payment_amount")
    assert found.evidence.details["by_state"] == {"Paid": 8, "Partial": 1}
    assert found.evidence.details["count"] == 9


# --------------------------------------------------------------------------
# Types
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "column, forms",
    [
        ("invoice_date", {"datetime", "string"}),
        ("unit_price", {"float", "int", "numeric-string", "formatted-numeric-string"}),
        ("annual_revenue", {"float", "int", "formatted-numeric-string"}),
    ],
)
def test_mixed_physical_types_detected(result: sp.ScanResult, column: str, forms: set) -> None:
    found = issue(result, f"TYPE-{column}")
    assert set(found.evidence.details["counts"]) == forms


def test_unit_price_composition(result: sp.ScanResult) -> None:
    counts = issue(result, "TYPE-unit_price").evidence.details["counts"]
    assert counts == {"float": 1186, "int": 11, "numeric-string": 7, "formatted-numeric-string": 6}


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------


def test_hard_invalid_dates(result: sp.ScanResult) -> None:
    found = issue(result, "DATE-INVALID-invoice_date")
    assert found.affected_row_count == 4
    assert found.evidence.details["value_counts"] == {"31/02/2025": 3, "2025-13-04": 1}


def test_ambiguous_dates_are_separate_from_invalid(result: sp.ScanResult) -> None:
    found = issue(result, "DATE-AMBIGUOUS-invoice_date")
    assert found.affected_row_count == 5
    assert found.category is IssueCategory.AMBIGUOUS_DATE


def test_format_conflict_is_its_own_class(result: sp.ScanResult) -> None:
    """`08-26-2024` parses uniquely but contradicts the column's day-first norm."""
    found = issue(result, "DATE-FORMAT-CONFLICT-invoice_date")
    assert found.affected_row_count == 1
    assert found.evidence.details["dominant_layout"] == "day_first"


# --------------------------------------------------------------------------
# Duplicates and identifiers
# --------------------------------------------------------------------------


def test_duplicate_identifiers_split_exact_from_conflicting(result: sp.ScanResult) -> None:
    exact = issue(result, "DUP-EXACT-invoice_id")
    conflicting = issue(result, "DUP-CONFLICT-invoice_id")

    assert exact.evidence.details["identifier_count"] == 9
    assert conflicting.evidence.details["identifier_count"] == 9
    assert exact.evidence.details["row_count"] + conflicting.evidence.details["row_count"] == 36


def test_identifier_embedded_year_mismatch(result: sp.ScanResult) -> None:
    assert issue(result, "ID-META-invoice_id").affected_row_count == 6


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------


def test_unicode_confusable_found_in_sector(result: sp.ScanResult) -> None:
    found = issue(result, "UNICODE-sector")
    assert "Manufacturıng" in found.evidence.sample_values
    assert found.evidence.details["proposed"]["Manufacturıng"] == "Manufacturing"


@pytest.mark.parametrize(
    "column, surface_forms",
    [("country", 10), ("sector", 15), ("payment_method", 11)],
)
def test_category_variants_detected(
    raw: pd.DataFrame, result: sp.ScanResult, column: str, surface_forms: int
) -> None:
    assert raw[column].nunique(dropna=True) == surface_forms
    issue(result, f"CAT-{column}")  # must be reported


def test_country_variants_separate_mechanical_from_language(result: sp.ScanResult) -> None:
    """Case and spacing fold mechanically. `Algérie` is a language variant.

    Folding cannot reach `Algérie` -> `Algeria`: they differ by a real letter.
    It must surface as a proposal, not as a silent merge.
    """
    details = issue(result, "CAT-country").evidence.details
    algeria = next(v for v in details["clusters"].values() if any("lger" in x for x in v))

    assert set(algeria) == {"Algeria", "ALGERIA", "algeria", " Algeria", "Algeria "}
    assert details["semantic_candidates"].get("Algérie") == "Algeria"


def test_spelling_correction_is_not_mechanical(result: sp.ScanResult) -> None:
    """`Tourismm -> Tourism` is a judgement; whitespace and case are not."""
    details = issue(result, "CAT-sector").evidence.details
    assert details["semantic_candidates"].get("Tourismm") == "Tourism"
    assert "Retail " in details["mechanical_merges"]
    assert "I.C.T" in details["mechanical_merges"]


# --------------------------------------------------------------------------
# Numeric
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "column, expected",
    [
        ("quantity", 5),  # 3 negative + 2 zero
        ("discount_pct", 5),  # 4 below 0 + 1 above 1
        ("tax_pct", 4),  # 1 below 0 + 3 above 1
        ("customer_rating", 5),
        # 1 negative + 1 zero. The two 999999 rows are a sentinel finding, not
        # a range violation -- there is no declared upper bound on headcount.
        ("employee_count", 2),
    ],
)
def test_range_violations(result: sp.ScanResult, column: str, expected: int) -> None:
    assert issue(result, f"RANGE-{column}").affected_row_count == expected


def test_sentinel_is_not_reported_as_an_outlier(result: sp.ScanResult) -> None:
    found = issue(result, "SENTINEL-employee_count")
    assert found.category is IssueCategory.SENTINEL_CANDIDATE
    assert found.evidence.details["occurrences"] == {999999.0: 2}


# --------------------------------------------------------------------------
# Cross-field
# --------------------------------------------------------------------------


def test_formula_violations(result: sp.ScanResult) -> None:
    found = issue(result, "INVARIANT-invoice_amount")
    assert found.evidence.details["violations"] == 101
    assert found.evidence.details["fit"] == pytest.approx(0.917, abs=0.002)


def test_geographic_conflicts(result: sp.ScanResult) -> None:
    assert issue(result, "GEO-country-city").affected_row_count == 26


def test_every_fixture_city_resolves(result: sp.ScanResult) -> None:
    """A gap in the reference pack would silently under-report conflicts."""
    unknown = [i for i in result.issues if i.id == "GEO-unknown-city"]
    assert not unknown, f"unresolved cities: {unknown[0].evidence.sample_values}"


def test_currency_context_count(result: sp.ScanResult) -> None:
    assert issue(result, "CURRENCY-context").affected_row_count == 22


@pytest.mark.parametrize(
    "rule, expected",
    [
        ("paid_without_payment_date", 7),
        ("paid_without_payment_amount", 8),
        ("paid_amount_mismatch", 55),
        ("pending_with_payment", 2),
        ("partial_without_payment_date", 1),
    ],
)
def test_state_contradictions(result: sp.ScanResult, rule: str, expected: int) -> None:
    assert issue(result, f"STATE-{rule}").affected_row_count == expected


def test_profit_exceeds_revenue(result: sp.ScanResult) -> None:
    assert issue(result, "ACCOUNTING-profit-exceeds-revenue").affected_row_count == 8
