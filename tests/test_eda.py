"""The EDA model: statistics as data, computed without any renderer."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT
from smartprep.eda import (
    ColumnKind,
    associations,
    compare_profiles,
    correlation_ratio,
    cramers_v,
    missingness,
    profile,
)


@pytest.fixture
def mixed() -> pd.DataFrame:
    rng = np.random.default_rng(5)
    return pd.DataFrame(
        {
            "amount": list(rng.lognormal(5, 1, 60)) + [None] * 4,
            "count": list(rng.integers(0, 10, 64)),
            "grade": (["a", "b", "c"] * 22)[:64],
            "note": [f"free text number {i}" for i in range(64)],
            "when": pd.date_range("2024-01-01", periods=64, freq="D"),
            "constant": ["same"] * 64,
            "row_id": [f"R-{i:04d}" for i in range(64)],
        }
    )


# -- shape ----------------------------------------------------------------


def test_profile_does_not_modify_the_frame(mixed: pd.DataFrame) -> None:
    before = mixed.copy(deep=True)
    profile(mixed)
    pd.testing.assert_frame_equal(mixed, before)


def test_profile_is_serialisable(mixed: pd.DataFrame) -> None:
    """A profile that only exists inside a template cannot be tested or diffed."""
    payload = json.loads(json.dumps(profile(mixed).to_dict()))
    assert payload["schema_version"] == 1
    assert len(payload["columns_profiled"]) == mixed.shape[1]


def test_nan_becomes_null_not_a_crash() -> None:
    """JSON has no NaN; emitting one produces a file nothing else can read."""
    payload = profile(pd.DataFrame({"x": [None, None, 1.0]})).to_dict()
    text = json.dumps(payload)
    assert "NaN" not in text and "Infinity" not in text


# -- classification -------------------------------------------------------


@pytest.mark.parametrize(
    "column, kind",
    [
        ("amount", ColumnKind.NUMERIC),
        ("grade", ColumnKind.CATEGORICAL),
        ("when", ColumnKind.DATETIME),
        ("constant", ColumnKind.CONSTANT),
    ],
)
def test_columns_are_classified_by_what_applies(
    mixed: pd.DataFrame, column: str, kind: ColumnKind
) -> None:
    assert profile(mixed).get(column).kind is kind


def test_a_mostly_datetime_column_is_still_datetime() -> None:
    """Requiring purity would lose range, frequency and gap analysis exactly
    when a column has some unparsed values -- when they matter most."""
    frame = pd.DataFrame(
        {"d": list(pd.date_range("2024-01-01", periods=18, freq="D")) + ["31/02/2025", "oops"]}
    )
    assert profile(frame).get("d").kind is ColumnKind.DATETIME


def test_identifier_columns_are_flagged(mixed: pd.DataFrame) -> None:
    assert profile(mixed).get("row_id").is_identifier_like
    assert not profile(mixed).get("grade").is_identifier_like


def test_constant_column_is_flagged(mixed: pd.DataFrame) -> None:
    assert profile(mixed).get("constant").is_constant


# -- summaries ------------------------------------------------------------


def test_numeric_summary_reports_shape_and_outliers(mixed: pd.DataFrame) -> None:
    summary = profile(mixed).get("amount").numeric
    assert summary is not None
    assert summary.count == 60
    assert summary.q1 < summary.median < summary.q3
    assert summary.skew > 0
    assert summary.histogram.counts


def test_histogram_handles_a_constant_column() -> None:
    """Binning a zero-range column must not divide by zero."""
    hist = profile(pd.DataFrame({"x": [5.0] * 20})).get("x")
    assert hist.is_constant


def test_categorical_summary_finds_rare_levels() -> None:
    values = ["common"] * 200 + ["rare"]
    summary = profile(pd.DataFrame({"c": values})).get("c").categorical
    assert summary is not None
    assert "rare" in summary.rare
    assert summary.imbalance > 0.99


def test_datetime_summary_infers_frequency_and_gaps() -> None:
    dates = list(pd.date_range("2024-01-01", periods=30, freq="D"))
    dates += [pd.Timestamp("2025-06-01")]  # a deliberate hole
    summary = profile(pd.DataFrame({"d": dates})).get("d").datetime
    assert summary is not None
    assert summary.inferred_frequency == "daily"
    assert summary.gaps >= 1


def test_text_summary_measures_length_and_non_ascii() -> None:
    """Enough distinct long values that the column reads as free text rather
    than as a small set of categories."""
    values = [f"free text entry number {i} with content" for i in range(60)]
    values += ["Algérie", "  ", "", "short"]
    summary = profile(pd.DataFrame({"t": values})).get("t").text
    assert summary is not None
    assert summary.non_ascii == 1
    assert summary.whitespace_only == 1


# -- associations ---------------------------------------------------------


def test_cramers_v_is_bounded_and_detects_dependence() -> None:
    independent = pd.DataFrame({"a": ["x", "y"] * 50, "b": ["p", "q", "q", "p"] * 25})
    assert cramers_v(independent["a"], independent["b"]) < 0.3

    dependent = pd.DataFrame({"a": ["x", "y"] * 50})
    dependent["b"] = dependent["a"]
    assert cramers_v(dependent["a"], dependent["b"]) > 0.9


def test_correlation_ratio_measures_group_separation() -> None:
    frame = pd.DataFrame({"g": ["a"] * 30 + ["b"] * 30, "v": [1.0] * 30 + [10.0] * 30})
    assert correlation_ratio(frame["g"], frame["v"]) > 0.95

    noise = pd.DataFrame({"g": ["a", "b"] * 30, "v": list(range(60))})
    assert correlation_ratio(noise["g"], noise["v"]) < 0.3


def test_mixed_pairs_get_the_measure_that_applies(mixed: pd.DataFrame) -> None:
    """A Pearson-only matrix drops categoricals and implies they carry nothing."""
    matrix = associations(mixed)
    measures = {p.measure for p in matrix.pairs}
    assert "cramers_v" in measures or "correlation_ratio" in measures
    for pair in matrix.pairs:
        assert pair.measure in {"spearman", "pearson", "cramers_v", "correlation_ratio"}


def test_identifier_columns_are_excluded(mixed: pd.DataFrame) -> None:
    """Correlating a key with anything measures row order, not a relationship."""
    assert "row_id" not in associations(mixed).columns


def test_constant_columns_are_excluded(mixed: pd.DataFrame) -> None:
    assert "constant" not in associations(mixed).columns


def test_association_grid_is_square_with_unit_diagonal(mixed: pd.DataFrame) -> None:
    matrix = associations(mixed)
    grid = matrix.as_grid()
    for column in matrix.columns:
        assert grid[column][column] == 1.0


def test_association_matrix_states_measures_are_not_interchangeable(
    mixed: pd.DataFrame,
) -> None:
    assert "not interchangeable" in associations(mixed).to_dict()["note"]


# -- missingness ----------------------------------------------------------


def test_missingness_finds_columns_that_go_missing_together() -> None:
    """Two columns absent on the same rows usually share one upstream cause."""
    frame = pd.DataFrame(
        {
            "a": [1.0, None, 3.0, None],
            "b": [1.0, None, 3.0, None],
            "c": [1.0, 2.0, 3.0, 4.0],
        }
    )
    pattern = missingness(frame)
    assert pattern.by_column["a"] == 2
    assert pattern.co_missing
    assert {pattern.co_missing[0][0], pattern.co_missing[0][1]} == {"a", "b"}


def test_missingness_counts_complete_rows() -> None:
    frame = pd.DataFrame({"a": [1.0, None], "b": [1.0, 2.0]})
    pattern = missingness(frame)
    assert pattern.rows_complete == 1
    assert pattern.rows_any_missing == 1


def test_missingness_serialises(mixed: pd.DataFrame) -> None:
    json.dumps(missingness(mixed).to_dict())


# -- before / after -------------------------------------------------------


def test_comparison_detects_variance_shrinkage() -> None:
    """The signature of centre-imputation: spread reduced, intervals too narrow."""
    before = pd.DataFrame({"x": [1.0, 2.0, 3.0, 100.0, None, None, None, None]})
    after = before.fillna(2.5)

    comparison = compare_profiles(profile(before), profile(after))
    column = next(c for c in comparison.columns if c.name == "x")
    assert any("variance shrank" in f for f in column.flags)


def test_comparison_flags_merged_categories() -> None:
    before = pd.DataFrame({"c": ["a", "A", "b", "B", "c", "C"]})
    after = pd.DataFrame({"c": ["a", "a", "b", "b", "c", "c"]})
    comparison = compare_profiles(profile(before), profile(after))
    column = next(c for c in comparison.columns if c.name == "c")
    assert any("merged" in f for f in column.flags)


def test_comparison_reports_row_loss_as_a_red_flag() -> None:
    before = pd.DataFrame({"x": list(range(100))})
    after = pd.DataFrame({"x": list(range(80))})
    assert any(
        w == "row_count" for w, _ in compare_profiles(profile(before), profile(after)).red_flags
    )


def test_identical_data_compares_as_unchanged(mixed: pd.DataFrame) -> None:
    comparison = compare_profiles(profile(mixed), profile(mixed))
    assert not comparison.red_flags
    assert all(c.status == "unchanged" for c in comparison.columns)


def test_preparation_result_exposes_the_comparison(synthetic: pd.DataFrame) -> None:
    result = sp.auto_prepare(synthetic, **SCAN_CONTEXT)
    comparison = result.compare_profiles()
    assert comparison.before.rows == comparison.after.rows
    json.dumps(comparison.to_dict())
