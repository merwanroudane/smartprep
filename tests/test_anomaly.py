"""Outliers no single column can see, and the refusal to act on them."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import smartprep as sp
from smartprep.anomaly import anomalies


@pytest.fixture(scope="module")
def bodies() -> pd.DataFrame:
    """Height and weight, correlated, with one row inside both columns' IQR
    fences and far off the line they sit on.

    1.90 m and 56 kg: tall people are ordinary, light people are ordinary, and
    someone who is both is a long way from everyone else. The values were
    chosen against the actual fences (height [1.50, 1.93], weight
    [43.3, 86.9]) so the test proves what it claims -- an earlier draft used
    140 kg, which is a univariate outlier and would have passed for the wrong
    reason.
    """
    rng = np.random.default_rng(0)
    n = 400
    height = rng.normal(1.72, 0.08, n)
    weight = 22 * height**2 + rng.normal(0, 4, n)
    frame = pd.DataFrame({"height": height, "weight": weight})
    frame.loc[0, "height"] = 1.90
    frame.loc[0, "weight"] = 56.0
    return frame


@pytest.fixture(scope="module")
def weather() -> pd.DataFrame:
    """Two cities with different climates, and one warm day in the cold one."""
    rng = np.random.default_rng(1)
    rows = [
        {"city": city, "temp": base + rng.normal(0, 2), "humidity": rng.normal(60, 5)}
        for city, base in (("Reykjavik", 2.0), ("Cairo", 28.0))
        for _ in range(40)
    ]
    frame = pd.DataFrame(rows)
    frame.loc[0, "temp"] = 30.0
    return frame


# ==========================================================================
# Multivariate
# ==========================================================================


def test_detection_never_touches_the_data(bodies: pd.DataFrame) -> None:
    before = bodies.copy(deep=True)
    anomalies(bodies)
    pd.testing.assert_frame_equal(bodies, before)


def test_a_row_ordinary_on_every_column_can_still_be_far_away(
    bodies: pd.DataFrame,
) -> None:
    """The case the IQR fences structurally cannot reach: 1.90 m is ordinary,
    56 kg is ordinary, and someone who is both is a long way from everyone
    else."""
    report = anomalies(bodies)
    assert any(o.row == 0 for o in report.multivariate)

    # And confirm the univariate check really would have missed it.
    for column in ("height", "weight"):
        q1, q3 = bodies[column].quantile([0.25, 0.75])
        fence = 1.5 * (q3 - q1)
        assert q1 - fence <= bodies.loc[0, column] <= q3 + fence


def test_the_explanation_names_the_columns_that_drove_it(bodies: pd.DataFrame) -> None:
    """'Anomalous' with no reason is a row nobody can act on."""
    outlier = next(o for o in anomalies(bodies).multivariate if o.row == 0)
    assert "height" in outlier.explanation
    assert "weight" in outlier.explanation
    assert "jointly" in outlier.explanation


def test_ordinary_data_produces_few_flags() -> None:
    """At the 95th percentile one row in twenty is 'anomalous', which is a
    list nobody reads. The cutoff is deliberately far out."""
    rng = np.random.default_rng(3)
    frame = pd.DataFrame({"a": rng.normal(size=500), "b": rng.normal(size=500)})
    assert len(anomalies(frame).multivariate) <= 5


def test_too_few_rows_for_a_covariance_says_so() -> None:
    """A covariance estimated from six rows is not a shape, and a distance
    measured against it is a number with no meaning."""
    frame = pd.DataFrame({"a": [1.0, 2, 3, 4, 5, 6], "b": [2.0, 4, 6, 8, 10, 12]})
    report = anomalies(frame)
    assert not report.multivariate
    assert any("complete rows" in note for note in report.skipped)


def test_one_numeric_column_is_not_multivariate() -> None:
    frame = pd.DataFrame({"a": np.random.default_rng(0).normal(size=100)})
    report = anomalies(frame)
    assert any("at least two numeric" in note for note in report.skipped)


# ==========================================================================
# Contextual
# ==========================================================================


def test_a_value_can_be_extreme_only_for_its_group(weather: pd.DataFrame) -> None:
    """30 °C sits comfortably inside the column's overall range and is absurd
    in Reykjavik."""
    report = anomalies(weather, by="city", value="temp")
    assert len(report.contextual) == 1

    outlier = report.contextual[0]
    assert outlier.group == "Reykjavik"
    assert weather["temp"].min() < 30.0 < weather["temp"].max()


def test_the_contextual_explanation_names_the_group(weather: pd.DataFrame) -> None:
    outlier = anomalies(weather, by="city", value="temp").contextual[0]
    assert "Reykjavik" in outlier.explanation
    assert "unremarkable against the column as a whole" in outlier.explanation


def test_a_small_group_is_skipped_and_said_so() -> None:
    """A within-group score from four rows is noise wearing a threshold."""
    frame = pd.DataFrame(
        {"g": ["a"] * 4 + ["b"] * 30, "v": [1.0, 2, 3, 99] + list(np.arange(30.0))}
    )
    report = anomalies(frame, by="g", value="v")
    assert any("fewer than" in note for note in report.skipped)


def test_a_contextual_outlier_needs_something_to_be_relative_to() -> None:
    frame = pd.DataFrame({"g": ["a"] * 20, "v": np.arange(20.0)})
    with pytest.raises(ValueError, match="both 'by' and 'value'"):
        anomalies(frame, value="v")


def test_an_unknown_column_is_named() -> None:
    frame = pd.DataFrame({"g": ["a"] * 20, "v": np.arange(20.0)})
    with pytest.raises(KeyError, match="nope"):
        anomalies(frame, by="nope", value="v")


def test_the_spread_used_is_robust_to_the_outlier_it_is_finding() -> None:
    """A standard deviation is inflated by the very point being detected, and
    on a small group the point can hide itself entirely."""
    rng = np.random.default_rng(5)
    values = list(rng.normal(10, 1, 30)) + [400.0]
    frame = pd.DataFrame({"g": ["only"] * 31, "v": values})
    report = anomalies(frame, by="g", value="v")
    assert report.contextual
    assert report.contextual[0].row == 30


# ==========================================================================
# What it refuses to do
# ==========================================================================


def test_nothing_is_repaired(bodies: pd.DataFrame, weather: pd.DataFrame) -> None:
    """Deleting a row because it is far away is how a dataset loses its most
    informative records."""
    for report in (anomalies(bodies), anomalies(weather, by="city", value="temp")):
        for finding in report.issues:
            assert all(t.repair_confidence == 0.0 for t in finding.treatments)
            assert not finding.triage()[0].is_autonomous


def test_findings_are_grouped_not_one_per_row(bodies: pd.DataFrame) -> None:
    """Fifty findings that each say 'look at this row' is a queue nobody
    works."""
    report = anomalies(bodies)
    assert len(report.issues) <= 2
    finding = report.issues[0]
    assert len(finding.evidence.affected_rows) == len(report.multivariate)


def test_the_finding_says_an_outlier_is_a_question(bodies: pd.DataFrame) -> None:
    finding = anomalies(bodies).issues[0]
    assert "not a defect in it" in finding.notes
    assert "most interesting records" in finding.treatments[0].description


def test_both_kinds_reach_one_chart(weather: pd.DataFrame) -> None:
    report = anomalies(weather, by="city", value="temp")
    charts = report.charts()
    assert charts
    assert charts[0].color is not None and charts[0].color.field == "kind"


def test_the_public_api_exposes_it() -> None:
    assert hasattr(sp, "anomalies")
    assert "anomalies" in sp.__all__


def test_outlier_rows_survive_a_duplicated_index() -> None:
    """Rows are resolved positionally.

    ``Index.get_indexer`` raises on a duplicated index, and a frame with one
    is ordinary after a concat. Resolving by label would also return the wrong
    row wherever several answer to the same label -- the failure this project
    has now hit in four separate places.
    """
    rng = np.random.default_rng(11)
    n = 200
    height = rng.normal(1.72, 0.08, n)
    weight = 22 * height**2 + rng.normal(0, 4, n)
    frame = pd.DataFrame({"height": height, "weight": weight}, index=[0, 1] * (n // 2))
    frame.iloc[7, frame.columns.get_loc("height")] = 1.90
    frame.iloc[7, frame.columns.get_loc("weight")] = 56.0

    report = anomalies(frame)
    assert any(o.row == 7 for o in report.multivariate)
    for outlier in report.multivariate:
        assert 0 <= outlier.row < len(frame)


def test_contextual_rows_survive_a_duplicated_index() -> None:
    rng = np.random.default_rng(12)
    values = list(rng.normal(10, 1, 30)) + [400.0]
    frame = pd.DataFrame({"g": ["only"] * 31, "v": values}, index=[0] * 31)
    report = anomalies(frame, by="g", value="v")
    assert report.contextual[0].row == 30
