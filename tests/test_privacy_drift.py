"""Privacy detection and drift comparison."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

import smartprep as sp
from smartprep.drift import cleaning_drift, compare, jensen_shannon, ks_statistic, psi
from smartprep.privacy import (
    PrivacyScanner,
    Sensitivity,
    generalise,
    hash_value,
    mask,
    pseudonymise,
    redact,
)


@pytest.fixture
def personal() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "email": ["a@b.com", "x@y.org", "p@q.net", "m@n.io"],
            # Valid Luhn checksums.
            "card": [
                "4539578763621486",
                "4485275742308327",
                "4716258050958645",
                "4556737586899855",
            ],
            "ip": ["10.0.0.1", "192.168.1.5", "8.8.8.8", "172.16.0.9"],
            # Chosen to FAIL the Luhn checksum. An earlier version of this
            # fixture used 4234567890123456, which happens to be Luhn-valid --
            # so the scanner was right to flag it and the test was wrong.
            "order_ref": [
                "1234567890123456",
                "2234567890123456",
                "3234567890123456",
                "5234567890123456",
            ],
            "amount": [10.0, 20.0, 30.0, 40.0],
        }
    )


# -- detection ------------------------------------------------------------


def test_email_is_a_direct_identifier(personal: pd.DataFrame) -> None:
    report = PrivacyScanner().scan(personal)
    email = next(f for f in report.findings if f.column == "email")
    assert email.sensitivity is Sensitivity.DIRECT_IDENTIFIER


def test_card_numbers_are_checksum_validated(personal: pd.DataFrame) -> None:
    """A regex alone flags every 16-digit string -- order refs, serials, hashes."""
    report = PrivacyScanner().scan(personal)
    kinds = {f.column: f.kind for f in report.findings}
    assert kinds.get("card") == "credit_card"
    assert "order_ref" not in kinds, "a 16-digit reference is not a card number"


def test_a_luhn_valid_reference_is_still_reported() -> None:
    """Honesty about the limit of the check.

    A 16-digit string that satisfies the checksum is indistinguishable from a
    card number by any local test, so it is reported. Suppressing it because
    the column is named `order_ref` would be trusting a label over evidence.
    """
    frame = pd.DataFrame({"order_ref": ["4234567890123456", "0000", "0001"]})
    report = PrivacyScanner().scan(frame)
    assert any(f.kind == "credit_card" for f in report.findings)


def test_ip_is_a_quasi_identifier(personal: pd.DataFrame) -> None:
    report = PrivacyScanner().scan(personal)
    assert next(f for f in report.findings if f.column == "ip").sensitivity is (
        Sensitivity.QUASI_IDENTIFIER
    )


def test_plain_numbers_are_not_flagged(personal: pd.DataFrame) -> None:
    report = PrivacyScanner().scan(personal)
    assert "amount" not in {f.column for f in report.findings}


def test_column_name_evidence_is_marked_as_a_guess() -> None:
    frame = pd.DataFrame({"customer_name": ["Amina", "Yacine", "Sofia"]})
    finding = PrivacyScanner().scan(frame).findings[0]
    assert finding.from_column_name
    assert finding.confidence < 0.7
    assert "guess" in finding.evidence


def test_a_clean_report_still_carries_the_caveat() -> None:
    """A scanner that says 'no PII' with no caveat invites a bad publication."""
    report = PrivacyScanner().scan(pd.DataFrame({"n": [1, 2, 3]}))
    assert not report.findings
    assert "not a guarantee" in report.summary()
    assert "cannot prove" in report.to_dict()["caveat"]


def test_report_serialises(personal: pd.DataFrame) -> None:
    payload = json.loads(PrivacyScanner().scan(personal).to_json())
    assert payload["schema_version"] == 1
    assert payload["findings"]


# -- re-identification ----------------------------------------------------


def test_quasi_identifier_combination_is_measured() -> None:
    """A table with no names can still identify people by combination."""
    frame = pd.DataFrame(
        {
            "postcode": ["16000", "16000", "31000", "31000"],
            "city": ["Algiers", "Algiers", "Oran", "Oran"],
        }
    )
    report = PrivacyScanner().scan(frame)
    risk = report.reidentification_risk(frame)
    assert risk["level"] in {"low", "medium", "high"}
    assert risk["smallest_group"] == 2


def test_unique_combinations_are_high_risk() -> None:
    frame = pd.DataFrame({"postcode": ["16000", "16001", "16002"], "city": ["A", "B", "C"]})
    risk = PrivacyScanner().scan(frame).reidentification_risk(frame)
    assert risk["level"] == "high"
    assert risk["unique_rate"] == 1.0


# -- transformations ------------------------------------------------------


def test_mask_keeps_the_email_domain() -> None:
    assert mask("merwan@example.com").endswith("@example.com")
    assert "merwan" not in mask("merwan@example.com")


def test_mask_keeps_a_recognisable_tail() -> None:
    assert mask("0555123456").endswith("56")


def test_redact_removes_everything() -> None:
    assert redact("anything") == "[REDACTED]"


def test_hash_is_stable_and_salt_dependent() -> None:
    assert hash_value("x", salt="s") == hash_value("x", salt="s")
    assert hash_value("x", salt="s") != hash_value("x", salt="t")


def test_pseudonyms_are_consistent_so_joins_survive() -> None:
    out = pseudonymise(pd.Series(["a", "b", "a"]))
    assert out.iloc[0] == out.iloc[2] != out.iloc[1]


def test_generalise_buckets_into_ranges() -> None:
    assert generalise(37, bucket=10) == "[30, 40)"


def test_transformations_preserve_missing_values() -> None:
    for fn in (mask, redact, hash_value, generalise):
        assert pd.isna(fn(None))


# -- drift metrics --------------------------------------------------------


def test_identical_distributions_show_no_drift() -> None:
    values = np.linspace(0, 1, 200)
    assert psi(values, values) == pytest.approx(0.0, abs=1e-6)
    assert ks_statistic(values, values) == pytest.approx(0.0, abs=1e-6)


def test_shifted_distribution_is_detected() -> None:
    rng = np.random.default_rng(3)
    reference = rng.normal(0, 1, 500)
    assert psi(reference, reference + 3) > 0.25
    assert ks_statistic(reference, reference + 3) > 0.4


def test_empty_input_does_not_divide_by_zero() -> None:
    assert psi(np.array([]), np.array([1.0])) == 0.0
    assert ks_statistic(np.array([]), np.array([1.0])) == 0.0


def test_jensen_shannon_is_bounded() -> None:
    assert jensen_shannon({"a": 1.0}, {"a": 1.0}) == pytest.approx(0.0, abs=1e-9)
    assert 0 < jensen_shannon({"a": 1.0}, {"b": 1.0}) <= np.log(2) + 1e-9


# -- drift report ---------------------------------------------------------


@pytest.fixture
def drifted() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(11)
    reference = pd.DataFrame({"x": rng.normal(0, 1, 400), "cat": rng.choice(["a", "b", "c"], 400)})
    current = pd.DataFrame({"x": rng.normal(2, 1, 400), "cat": rng.choice(["a", "b", "d"], 400)})
    return reference, current


def test_drift_is_graded_not_boolean(drifted) -> None:
    reference, current = drifted
    report = compare(reference, current)
    assert report.severity is not sp.DriftSeverity.NONE
    assert all(c.severity.value for c in report.columns)


def test_drift_names_its_contributors(drifted) -> None:
    """'Drift detected: True' is not actionable. A ranked attribution is."""
    reference, current = drifted
    contributors = compare(reference, current).contributors()
    assert contributors
    assert contributors[0][0] == "x"
    assert sum(share for _, share in contributors) == pytest.approx(1.0)


def test_unseen_category_is_treated_as_severe(drifted) -> None:
    reference, current = drifted
    cat = next(c for c in compare(reference, current).columns if c.column == "cat")
    assert "d" in cat.new_categories
    assert cat.severity is sp.DriftSeverity.SEVERE


def test_no_drift_between_identical_frames() -> None:
    frame = pd.DataFrame({"x": np.linspace(0, 1, 100), "cat": ["a", "b"] * 50})
    report = compare(frame, frame)
    assert report.severity is sp.DriftSeverity.NONE
    assert not report.drifted


def test_schema_change_is_critical() -> None:
    reference = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    report = compare(reference, reference.drop(columns=["b"]))
    assert report.removed_columns == ("b",)
    assert report.severity is sp.DriftSeverity.CRITICAL


def test_missingness_drift_is_reported_separately() -> None:
    reference = pd.DataFrame({"a": [1.0] * 20})
    current = pd.DataFrame({"a": [1.0] * 10 + [None] * 10})
    report = compare(reference, current)
    assert any(c.kind == "missingness" for c in report.columns)


def test_report_says_drift_is_not_automatically_an_error(drifted) -> None:
    reference, current = drifted
    assert "not automatically an error" in compare(reference, current).to_dict()["note"]


def test_drift_report_serialises(drifted) -> None:
    reference, current = drifted
    payload = json.loads(compare(reference, current).to_json())
    assert payload["schema_version"] == 1
    assert payload["contributors"]


# -- cleaning drift -------------------------------------------------------


def test_same_problems_recurring_is_stable(synthetic: pd.DataFrame) -> None:
    from conftest import SCAN_CONTEXT

    scan = sp.scan(synthetic, **SCAN_CONTEXT)
    verdict = cleaning_drift(scan, scan)
    assert verdict["verdict"] == "stable"
    assert verdict["stability_score"] == 100.0


def test_new_problems_point_upstream(synthetic: pd.DataFrame) -> None:
    """If each batch needs different repairs, no local rule fixes the cause."""
    from conftest import SCAN_CONTEXT

    reference = sp.scan(synthetic.head(6), **SCAN_CONTEXT)
    current = sp.scan(synthetic, **SCAN_CONTEXT)
    verdict = cleaning_drift(reference, current)
    assert verdict["verdict"] == "upstream_change_likely"
    assert verdict["new_problems"]
    assert "source changed" in verdict["interpretation"]


# -- P0 regressions -------------------------------------------------------


def test_low_rate_pii_in_free_text_is_reported() -> None:
    """One email in ten rows is not an email column. It is still an email.

    The scanner previously judged both questions off one threshold and
    reported nothing at all.
    """
    frame = pd.DataFrame({"notes": ["hello", "world", "contact a@b.com please"] + ["filler"] * 7})
    report = PrivacyScanner().scan(frame)

    assert report.findings, "a single embedded email must not be silently dropped"
    finding = report.findings[0]
    assert finding.kind == "email"
    assert finding.embedded
    assert finding.match_rate == pytest.approx(0.1)


def test_column_classification_still_needs_a_majority() -> None:
    """Detecting a cell must not retype the whole column."""
    frame = pd.DataFrame({"notes": ["hello", "world", "contact a@b.com please"] + ["filler"] * 7})
    finding = PrivacyScanner().scan(frame).findings[0]
    assert finding.embedded, "10% of values is not an email column"


def test_cell_detection_threshold_is_configurable() -> None:
    frame = pd.DataFrame({"notes": ["hello", "world", "contact a@b.com please"] + ["filler"] * 7})
    strict = PrivacyScanner(cell_detection_threshold=5).scan(frame)
    assert not strict.findings


def test_embedded_findings_are_listed_separately() -> None:
    frame = pd.DataFrame({"notes": ["reach me at x@y.com", "nothing here"]})
    report = PrivacyScanner().scan(frame)
    assert len(report.embedded_findings) == 1
