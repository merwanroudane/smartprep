"""Missingness mechanism evidence, and the limit of what data can establish.

The library can rule out MCAR. It can never establish MNAR, because MAR and
MNAR differ only in whether absence depends on the value that is missing, and
no test on observed data can see an unobserved value. Half these tests exist
to hold that line: a library that reported "MNAR" would be reporting a domain
judgement as a measurement.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import smartprep as sp
from smartprep.mechanism import Mechanism, mechanism


@pytest.fixture(scope="module")
def frames() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(0)
    n = 300
    region = rng.choice(["north", "south"], n)

    # MAR: income is missing far more often in the south, and the south is
    # observable, so the dependence is detectable.
    income = pd.Series(rng.lognormal(10, 0.6, n))
    income[rng.random(n) < np.where(region == "south", 0.45, 0.05)] = np.nan

    # MCAR: absence unrelated to anything.
    age = pd.Series(rng.integers(20, 70, n).astype(float))
    age[rng.random(n) < 0.2] = np.nan

    return {
        "mixed": pd.DataFrame(
            {
                "income": income,
                "region": region,
                "age": age,
                "noise": rng.normal(size=n),
            }
        ),
        "complete": pd.DataFrame({"a": range(50), "b": rng.normal(size=50)}),
    }


def test_the_report_never_touches_the_data(frames: dict) -> None:
    frame = frames["mixed"]
    before = frame.copy(deep=True)
    mechanism(frame)
    pd.testing.assert_frame_equal(frame, before)


def test_a_dependence_on_an_observed_column_rules_out_mcar(frames: dict) -> None:
    """Income is missing more often in the south. That is visible in the data,
    so MCAR can be rejected."""
    column = mechanism(frames["mixed"]).get("income")
    assert column.verdict is Mechanism.NOT_MCAR
    assert "region" in {d.predictor for d in column.predictors}


def test_absence_unrelated_to_anything_does_not_reject_mcar(frames: dict) -> None:
    """The negative case. Flagging a genuinely random absence would train a
    reader to ignore the finding."""
    column = mechanism(frames["mixed"]).get("age")
    assert column.verdict is Mechanism.MCAR_NOT_REJECTED
    assert not column.predictors


def test_not_rejecting_mcar_is_not_proof_of_it(frames: dict) -> None:
    """The wording matters: a test that fails to reject is not a test that
    confirms, and a reader who reads 'MCAR' as established will delete rows."""
    column = mechanism(frames["mixed"]).get("age")
    assert "not the same as proof" in column.verdict.describe


def test_mnar_is_never_claimed(frames: dict) -> None:
    """The line this module exists to hold.

    MNAR means absence depends on the value that is missing. No test on
    observed data can see an unobserved value, so reporting MNAR would be
    reporting a judgement about data collection as if it were a measurement.
    """
    assert not any(m.value == "mnar" for m in Mechanism)

    report = mechanism(frames["mixed"])
    rendered = report.summary().lower()
    assert "mnar" in rendered, "the report must still name MNAR as a possibility"
    assert "cannot say which" in rendered or "no further" in rendered


def test_the_caveat_travels_with_every_report(frames: dict) -> None:
    report = mechanism(frames["mixed"])
    assert "MAR or MNAR and no further" in report.caveat
    assert report.caveat in report.summary()
    assert report.to_dict()["caveat"] == report.caveat


def test_p_values_are_corrected_for_multiple_testing() -> None:
    """Twenty columns give a hundred and ninety pairs; at a nominal 5% about
    ten are significant by arithmetic alone. Without correction every wide
    dataset would be diagnosed MAR."""
    from smartprep.mechanism import _holm

    raw = [0.001, 0.02, 0.04, 0.5]
    adjusted = _holm(raw)
    assert adjusted[0] > raw[0]
    assert all(a >= b for a, b in zip(adjusted, raw, strict=True))
    assert all(a <= 1.0 for a in adjusted)
    # Step-down keeps the ordering monotone.
    ordered = [adjusted[i] for i in sorted(range(len(raw)), key=lambda i: raw[i])]
    assert ordered == sorted(ordered)


def test_a_wide_frame_of_pure_noise_is_not_diagnosed_mar() -> None:
    """The multiple-testing guard, end to end."""
    rng = np.random.default_rng(7)
    n = 200
    data = {f"x{i}": rng.normal(size=n) for i in range(18)}
    target = pd.Series(rng.normal(size=n))
    target[rng.random(n) < 0.25] = np.nan
    data["target"] = target

    report = mechanism(pd.DataFrame(data))
    assert report.get("target").verdict is Mechanism.MCAR_NOT_REJECTED


def test_too_few_rows_is_undetermined_rather_than_a_verdict() -> None:
    """A verdict from five rows is a guess wearing a p-value."""
    frame = pd.DataFrame({"a": [1.0, np.nan, 3.0, 4.0], "b": [1.0, 2.0, 3.0, 4.0]})
    assert mechanism(frame).get("a").verdict is Mechanism.UNDETERMINED


def test_a_complete_frame_reports_nothing(frames: dict) -> None:
    report = mechanism(frames["complete"])
    assert report.columns == []
    assert report.summary() == "no column has missing values"


def test_columns_missing_together_are_named() -> None:
    """In longitudinal data this is drop-out; elsewhere one source failed."""
    rng = np.random.default_rng(1)
    n = 120
    gone = rng.random(n) < 0.3
    frame = pd.DataFrame(
        {
            "sensor_a": np.where(gone, np.nan, rng.normal(size=n)),
            "sensor_b": np.where(gone, np.nan, rng.normal(size=n)),
            "id": range(n),
        }
    )
    column = mechanism(frame).get("sensor_a")
    assert "sensor_b" in column.monotone_with


def test_findings_are_ordinary_issues(frames: dict) -> None:
    """Not a parallel review path: a mechanism finding routes through the same
    triage as everything else, and offers no automatic repair."""
    report = mechanism(frames["mixed"])
    assert report.issues
    for finding in report.issues:
        assert finding.detector == "mechanism"
        assert all(t.repair_confidence == 0.0 for t in finding.treatments)
        assert not finding.triage()[0].is_autonomous
        assert "no further" in finding.notes


def test_the_finding_says_what_it_costs_to_ignore(frames: dict) -> None:
    """Deletion and naive imputation are both biased here, and a reader who is
    told only 'not random' will do one of them anyway."""
    finding = mechanism(frames["mixed"]).issues[0]
    summary = finding.evidence.summary
    assert "biases" in summary
    assert "imputing without conditioning" in summary


def test_the_chart_colours_by_verdict(frames: dict) -> None:
    charts = mechanism(frames["mixed"]).charts()
    assert charts
    spec = charts[0]
    assert spec.color is not None and spec.color.field == "verdict"
    assert set(spec.colour_groups()) <= {v.value for v in Mechanism}


def test_the_public_api_exposes_it() -> None:
    assert hasattr(sp, "mechanism")
    assert "mechanism" in sp.__all__
