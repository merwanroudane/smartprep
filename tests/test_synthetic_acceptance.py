"""Acceptance contract that ships with the package.

Every count here is frozen. These tests run wherever SmartPrep is installed --
they need no external data file -- so the contract the README advertises is one
that anyone can actually execute.
"""

from __future__ import annotations

import pandas as pd
import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT, issue
from smartprep.core import IssueCategory, RepairClass, Severity


def test_fixture_shape(synthetic: pd.DataFrame, expected: dict[str, int]) -> None:
    assert synthetic.shape == (expected["rows"], expected["columns"])


def test_fixture_is_deterministic() -> None:
    """A drifting fixture would silently invalidate every count below."""
    from synthetic import build

    pd.testing.assert_frame_equal(build(), build())


def test_scan_does_not_mutate(synthetic: pd.DataFrame) -> None:
    before = synthetic.copy(deep=True)
    sp.scan(synthetic, **SCAN_CONTEXT)
    pd.testing.assert_frame_equal(synthetic, before)


def test_every_detector_is_exercised(scanned: sp.ScanResult) -> None:
    """The fixture must reach all 14 detectors, or it is not a real contract."""
    from smartprep.detectors import REGISTRY

    ran = {o.detector for o in scanned.completed_checks}
    assert ran == set(REGISTRY.names()), f"never ran: {set(REGISTRY.names()) - ran}"


def test_total_issue_count(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    assert len(scanned.issues) == expected["total_issues"]


# -- dates: four distinct classes -----------------------------------------


def test_invalid_dates(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    found = issue(scanned, "DATE-INVALID-invoice_date")
    assert found.affected_row_count == expected["invalid_dates"]
    assert found.treatments == (), "no correction may be invented for an impossible date"


def test_ambiguous_dates(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    found = issue(scanned, "DATE-AMBIGUOUS-invoice_date")
    assert found.affected_row_count == expected["ambiguous_dates"]


def test_format_conflict_dates(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    found = issue(scanned, "DATE-FORMAT-CONFLICT-invoice_date")
    assert found.affected_row_count == expected["format_conflict_dates"]
    assert found.evidence.details["dominant_layout"] == "day_first"


# -- duplicates -----------------------------------------------------------


def test_duplicates_split_exact_from_conflicting(
    scanned: sp.ScanResult, expected: dict[str, int]
) -> None:
    exact = issue(scanned, "DUP-EXACT-invoice_id")
    conflicting = issue(scanned, "DUP-CONFLICT-invoice_id")
    assert exact.evidence.details["identifier_count"] == expected["exact_duplicate_ids"]
    assert conflicting.evidence.details["identifier_count"] == expected["conflicting_duplicate_ids"]
    assert conflicting.repair_class is RepairClass.DO_NOT_TOUCH


def test_identifier_year_mismatch(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    assert (
        issue(scanned, "ID-META-invoice_id").affected_row_count
        == expected["identifier_year_mismatch"]
    )


# -- cross-field ----------------------------------------------------------


def test_geographic_conflicts(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    assert issue(scanned, "GEO-country-city").affected_row_count == expected["geographic_conflicts"]


def test_marrakesh_resolves_through_the_alias_graph(scanned: sp.ScanResult) -> None:
    """A flat city map would miss this pair and under-report the conflict."""
    assert not scanned.find(IssueCategory.UNKNOWN_ENTITY), (
        "an unresolved city silently reduces the geographic conflict count"
    )


def test_currency_is_contextual(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    found = issue(scanned, "CURRENCY-context")
    assert found.affected_row_count == expected["currency_context"]
    assert found.severity is Severity.NOTICE


def test_formula_violations(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    found = issue(scanned, "INVARIANT-invoice_amount")
    assert found.evidence.details["violations"] == expected["formula_violations"]
    assert found.repair_class is RepairClass.DOMAIN_RULE_REQUIRED


def test_sentinel_not_range_violation(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    found = issue(scanned, "SENTINEL-employee_count")
    assert found.affected_row_count == expected["sentinel_values"]
    assert found.category is IssueCategory.SENTINEL_CANDIDATE


def test_profit_exceeds_revenue(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    assert (
        issue(scanned, "ACCOUNTING-profit-exceeds-revenue").affected_row_count
        == expected["profit_exceeds_revenue"]
    )


# -- text -----------------------------------------------------------------


def test_unicode_confusable(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    found = issue(scanned, "UNICODE-sector")
    assert found.affected_row_count == expected["unicode_confusables"]
    assert found.evidence.details["proposed"]["Manufacturıng"] == "Manufacturing"


def test_mechanical_and_semantic_merges_are_graded_apart(scanned: sp.ScanResult) -> None:
    country = issue(scanned, "CAT-country").evidence.details
    sector = issue(scanned, "CAT-sector").evidence.details

    assert "ALGERIA" in country["mechanical_merges"]
    assert "I.C.T" in sector["mechanical_merges"]
    assert country["semantic_candidates"].get("Algérie") == "Algeria"
    assert sector["semantic_candidates"].get("Tourismm") == "Tourism"


# -- missingness ----------------------------------------------------------


def test_missingness_split_by_state(scanned: sp.ScanResult, expected: dict[str, int]) -> None:
    structural = issue(scanned, "MISS-STRUCTURAL-payment_date")
    suspicious = issue(scanned, "MISS-SUSPICIOUS-payment_date")
    assert structural.evidence.details["count"] == expected["structural_missing_payment_date"]
    assert suspicious.evidence.details["count"] == expected["suspicious_missing_payment_date"]
    assert structural.severity is Severity.INFO


@pytest.mark.parametrize(
    "column", ["quantity", "discount_pct", "tax_pct", "customer_rating", "employee_count"]
)
def test_range_violations_reported(scanned: sp.ScanResult, column: str) -> None:
    assert issue(scanned, f"RANGE-{column}").affected_row_count > 0
